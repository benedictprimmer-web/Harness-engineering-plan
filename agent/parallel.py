#!/usr/bin/env python3
"""
Parallel literature research runner.

Fires multiple topics concurrently via AsyncAnthropic, shows live per-topic
status, then combines results into a report saved to research/notes/.

Usage:
  python agent/parallel.py                       # default topics from prompts.py
  python agent/parallel.py "topic 1" "topic 2"   # custom topics
"""

from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.prompts import DEFAULT_TOPICS, LITERATURE_PROMPT
from agent.tools import TOOL_DEFINITIONS, execute_tool, save_note

MODEL = "claude-opus-4-7"
MAX_TOKENS = 6000  # per topic — keep parallel calls economical


# --------------------------------------------------------------------------- #
# Per-topic async research loop
# --------------------------------------------------------------------------- #


async def research_one(
    client: anthropic.AsyncAnthropic,
    topic: str,
    status: dict[str, str],
    started_at: dict[str, float],
) -> tuple[str, str]:
    """
    Run the full agentic loop for one topic.
    Returns (topic, answer_text).
    """
    started_at[topic] = time.monotonic()
    messages: list[dict] = [
        {"role": "user", "content": f"Research this topic:\n\n**{topic}**"}
    ]
    text_chunks: list[str] = []

    while True:
        status[topic] = "reasoning…"

        response = await client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": LITERATURE_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=TOOL_DEFINITIONS,
            messages=messages,
            thinking={"type": "adaptive"},
        )

        for block in response.content:
            if block.type == "text":
                text_chunks.append(block.text)

        if response.stop_reason == "end_turn":
            messages.append({"role": "assistant", "content": response.content})
            break

        # Tool use round
        tool_results: list[dict] = []
        for block in response.content:
            if block.type == "tool_use":
                status[topic] = f"→ {block.name}"
                result = await asyncio.to_thread(execute_tool, block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    elapsed = time.monotonic() - started_at[topic]
    status[topic] = f"done ✓  {elapsed:.0f}s"
    return topic, "".join(text_chunks)


# --------------------------------------------------------------------------- #
# Parallel orchestrator
# --------------------------------------------------------------------------- #


async def run_parallel(
    topics: list[str],
    console: Console,
) -> list[tuple[str, str]]:
    """Run all topics concurrently. Returns list of (topic, answer) pairs."""
    client = anthropic.AsyncAnthropic()
    status: dict[str, str] = {t: "queued" for t in topics}
    started_at: dict[str, float] = {}

    def make_table() -> Table:
        table = Table(show_header=False, box=None, padding=(0, 1))
        for topic, state in status.items():
            short = topic[:58] + "…" if len(topic) > 58 else topic
            is_done = state.startswith("done")
            color = "green" if is_done else ("cyan" if state != "queued" else "dim")
            table.add_row(f"[{color}]{short}[/{color}]", f"[dim]{state}[/dim]")
        return table

    console.print(
        Panel(
            f"[bold cyan]Parallel Literature Research[/bold cyan]"
            f"[dim] — {len(topics)} topics[/dim]",
            border_style="cyan",
        )
    )

    with Live(make_table(), console=console, refresh_per_second=4) as live:
        async def _refresh() -> None:
            while True:
                live.update(make_table())
                await asyncio.sleep(0.25)

        refresher = asyncio.create_task(_refresh())
        try:
            results = await asyncio.gather(
                *[research_one(client, t, status, started_at) for t in topics],
                return_exceptions=False,
            )
        finally:
            refresher.cancel()
            live.update(make_table())

    return list(results)


# --------------------------------------------------------------------------- #
# Report builder
# --------------------------------------------------------------------------- #


def build_report(label: str, results: list[tuple[str, str]]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = [
        f"# Literature Research Report\n",
        f"**{label}**\n",
        f"*{now} — {len(results)} topics*\n",
    ]
    for topic, answer in results:
        parts.append(f"\n---\n\n## {topic}\n\n{answer}")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# CLI entry point
# --------------------------------------------------------------------------- #


def main() -> None:
    console = Console()
    topics = sys.argv[1:] if sys.argv[1:] else DEFAULT_TOPICS

    results = asyncio.run(run_parallel(topics, console))

    # Display each result
    for topic, answer in results:
        console.print(
            Panel(
                Markdown(answer),
                title=f"[bold green]{topic[:70]}[/bold green]",
                border_style="green",
            )
        )

    # Save combined report
    label = (
        "Harness engineering — default topics"
        if not sys.argv[1:]
        else " | ".join(topics)
    )
    report = build_report(label, results)
    date = datetime.now().strftime("%Y%m%d-%H%M")
    saved = save_note(f"{date}-parallel-research.md", report)
    console.print(f"\n[green]✓ {saved}[/green]")


if __name__ == "__main__":
    main()
