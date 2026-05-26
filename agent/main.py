#!/usr/bin/env python3
"""
Harness Engineering Research Agent
====================================
Interactive CLI that runs a two-pass "stretch" research loop:
  EXPLORE  — Claude uses repo tools to gather evidence and write a draft
  STRETCH  — Claude critiques the draft, digs deeper, writes the final answer

Usage:
  pip install anthropic rich          # one-time
  export ANTHROPIC_API_KEY=sk-...
  python agent/main.py
"""

from __future__ import annotations

import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path

# Allow running as: python agent/main.py  (from any cwd)
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from agent.core import ResearchAgent
from agent.parallel import build_report, run_parallel
from agent.prompts import DEFAULT_TOPICS
from agent.tools import save_note

BANNER = """\
[bold cyan]Harness Engineering Research Agent[/bold cyan]
[dim]Claude Opus 4.7 · Adaptive Thinking · Two-pass Stretch Loop[/dim]

Ask anything about configuring Claude Code for software projects.
Append [bold]save[/bold] to auto-save the answer.

[bold]parallel:[/bold] [dim]topic1, topic2, ...[/dim]  run a parallel literature review
[bold]parallel[/bold]                           run the default 5-topic literature review

Type [bold]quit[/bold] or press Ctrl-C to exit.\
"""


def main() -> None:
    console = Console()
    console.print(Panel(BANNER, border_style="cyan", title="[bold]◉[/bold]"))

    agent = ResearchAgent(console)

    while True:
        console.print()
        try:
            raw = Prompt.ask("[bold cyan]>[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]bye[/dim]")
            break

        if not raw:
            continue
        if raw.lower() in ("quit", "exit", "q"):
            console.print("[dim]bye[/dim]")
            break

        # ── parallel literature review ──────────────────────────────────────
        if raw.lower().startswith("parallel"):
            rest = raw[len("parallel"):].lstrip(": ").strip()
            topics = [t.strip() for t in rest.split(",") if t.strip()] or DEFAULT_TOPICS
            try:
                results = asyncio.run(run_parallel(topics, console))
                label = rest or "Harness engineering — default topics"
                report = build_report(label, results)
                for topic, answer in results:
                    console.print(
                        Panel(
                            Markdown(answer),
                            title=f"[bold green]{topic[:70]}[/bold green]",
                            border_style="green",
                        )
                    )
                date = datetime.now().strftime("%Y%m%d-%H%M")
                saved = save_note(f"{date}-parallel-research.md", report)
                console.print(f"[green]✓ {saved}[/green]")
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted[/yellow]")
            continue
        # ────────────────────────────────────────────────────────────────────

        auto_save = raw.lower().endswith(" save")
        question = raw[:-5].strip() if auto_save else raw

        try:
            answer = agent.research(question)

            console.print(
                Panel(
                    Markdown(answer),
                    title="[bold green]◉ FINAL ANSWER[/bold green]",
                    border_style="green",
                )
            )

            if auto_save:
                _save(question, answer, console)
            else:
                resp = Prompt.ask(
                    "\n[dim]Save to research/notes/? (y/N)[/dim]", default="n"
                ).strip().lower()
                if resp == "y":
                    _save(question, answer, console)

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/red]")
            raise


def _save(question: str, answer: str, console: Console) -> None:
    slug = re.sub(r"[^a-z0-9]+", "-", question.lower())[:50].strip("-")
    date = datetime.now().strftime("%Y%m%d")
    filename = f"{date}-{slug}.md"
    content = f"# {question}\n\n*{datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n{answer}\n"
    result = save_note(filename, content)
    console.print(f"[green]✓ {result}[/green]")


if __name__ == "__main__":
    main()
