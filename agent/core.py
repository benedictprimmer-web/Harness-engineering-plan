from __future__ import annotations

import anthropic
from rich.console import Console

from .prompts import SYSTEM_PROMPT, STRETCH_PROMPT
from .tools import TOOL_DEFINITIONS, execute_tool

MODEL = "claude-opus-4-7"
MAX_TOKENS = 8192


class ResearchAgent:
    def __init__(self, console: Console) -> None:
        self.client = anthropic.Anthropic()
        self.console = console

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def research(self, question: str) -> str:
        """Run the two-pass stretch loop. Returns the final polished answer."""
        initial = (
            f"Research this question using the repository tools:\n\n"
            f"**{question}**\n\n"
            f"Explore structure first, then read the most relevant files. "
            f"Write a thorough draft answer with specific file citations."
        )

        messages: list[dict] = [{"role": "user", "content": initial}]

        self._header("EXPLORE", "cyan", "researching the repo…")
        draft_text, messages = self._agentic_pass(messages, show_thinking=True)

        messages.append({"role": "user", "content": STRETCH_PROMPT})

        self._header("STRETCH", "yellow", "critiquing and deepening…")
        final_text, _ = self._agentic_pass(messages, show_thinking=False)

        return final_text

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _header(self, label: str, color: str, subtitle: str) -> None:
        from rich.panel import Panel
        self.console.print()
        self.console.print(
            Panel(
                f"[bold {color}]◉ {label}[/bold {color}]",
                subtitle=f"[dim]{subtitle}[/dim]",
                border_style=color,
                expand=False,
            )
        )

    def _agentic_pass(
        self,
        messages: list[dict],
        *,
        show_thinking: bool,
    ) -> tuple[str, list[dict]]:
        """
        Run the agentic loop until end_turn.
        Returns (accumulated_text, updated_messages_list).
        """
        current = list(messages)
        accumulated_text: list[str] = []

        thinking_param: dict = (
            {"type": "adaptive", "display": "summarized"}
            if show_thinking
            else {"type": "adaptive"}
        )

        while True:
            text_chunks: list[str] = []
            in_thinking = False

            with self.client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=TOOL_DEFINITIONS,
                messages=current,
                thinking=thinking_param,
            ) as stream:
                for event in stream:
                    if event.type == "content_block_start":
                        btype = event.content_block.type
                        if btype == "thinking":
                            in_thinking = True
                            if show_thinking:
                                self.console.print(
                                    "\n[dim italic]◌ thinking…[/dim italic] ",
                                    end="",
                                )
                        elif btype == "text":
                            in_thinking = False
                        elif btype == "tool_use":
                            in_thinking = False
                            self.console.print(
                                f"\n[dim cyan]  → {event.content_block.name}[/dim cyan]",
                                end="",
                            )

                    elif event.type == "content_block_delta":
                        if event.delta.type == "thinking_delta" and show_thinking:
                            self.console.print(
                                f"[dim]{event.delta.thinking}[/dim]", end=""
                            )
                        elif event.delta.type == "text_delta":
                            text_chunks.append(event.delta.text)
                            self.console.print(event.delta.text, end="")

                    elif event.type == "content_block_stop" and in_thinking:
                        if show_thinking:
                            self.console.print()
                        in_thinking = False

                final_msg = stream.get_final_message()

            self.console.print()  # newline after streamed block

            if final_msg.stop_reason == "end_turn":
                accumulated_text.extend(text_chunks)
                current.append({"role": "assistant", "content": final_msg.content})
                return "".join(accumulated_text), current

            # Tool use — execute each tool and continue the loop
            tool_results: list[dict] = []
            for block in final_msg.content:
                if block.type == "tool_use":
                    input_preview = str(block.input)[:80].replace("\n", " ")
                    self.console.print(f"[dim]     {input_preview}[/dim]")
                    result = execute_tool(block.name, block.input)
                    preview = result.split("\n")[0][:100]
                    self.console.print(
                        f"[dim]     ← {len(result):,} chars  {preview}[/dim]"
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            accumulated_text.extend(text_chunks)
            current.append({"role": "assistant", "content": final_msg.content})
            current.append({"role": "user", "content": tool_results})
