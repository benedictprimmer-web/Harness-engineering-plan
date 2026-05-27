#!/usr/bin/env python3
"""
agent/reflect.py — Session reflection tool.

Reads what happened during a Claude session (tool audit log + git diff),
calls Claude to propose harness improvements, and writes a human-readable
proposal file to .claude/session-learnings.md in the target project.

Always exits 0 — designed to run inside a Stop hook without disrupting the session.

Usage:
    python agent/reflect.py [project_root]
    python agent/reflect.py .               # reflect on this repo
    python agent/reflect.py /path/to/proj   # reflect on another project
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MODEL = "claude-opus-4-7"
API_TIMEOUT = 25  # seconds (shell wrapper uses 30s hard limit)
AUDIT_LOG = Path.home() / ".claude" / "tool-audit.log"


# ── Data gathering ─────────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10, cwd=cwd
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _read_audit_log(limit: int = 200) -> str:
    if not AUDIT_LOG.exists():
        return "(no tool-audit.log found — pre-tool-use hook may not be installed)"
    try:
        lines = AUDIT_LOG.read_text(errors="replace").splitlines()
        recent = lines[-limit:]
        return "\n".join(recent) if recent else "(audit log is empty)"
    except Exception:
        return "(could not read tool-audit.log)"


def _read_git_diff(project_root: Path) -> str:
    diff_stat = _run(["git", "diff", "HEAD", "--stat"], cwd=project_root)
    if not diff_stat:
        diff_stat = _run(["git", "diff", "--cached", "--stat"], cwd=project_root)
    if not diff_stat:
        diff_stat = "(no uncommitted changes)"
    recent_log = _run(
        ["git", "log", "--oneline", "-10"], cwd=project_root
    )
    return f"Uncommitted changes:\n{diff_stat}\n\nRecent commits:\n{recent_log or '(none)'}"


def _read_claude_md(project_root: Path) -> str:
    claude_md = project_root / "CLAUDE.md"
    if claude_md.exists():
        try:
            return claude_md.read_text(errors="replace")[:4000]
        except Exception:
            return "(could not read CLAUDE.md)"
    return "(no CLAUDE.md found)"


# ── Claude call ────────────────────────────────────────────────────────────────

def _build_prompt(audit_log: str, git_diff: str, claude_md: str) -> str:
    return f"""You are reviewing a completed Claude Code session to propose improvements \
to the project's harness configuration.

## Tool Audit Log (last 200 commands)
```
{audit_log}
```

## Session Git Activity
```
{git_diff}
```

## Current CLAUDE.md (first 4000 chars)
```
{claude_md}
```

Based on what happened this session, propose specific, evidence-based improvements.

Look for:
- Commands that ran many times → candidates for the allow list
- Commands that were blocked → verify the deny rule was appropriate
- Patterns in what changed → worth documenting as gotchas
- Gaps between what CLAUDE.md documents and what actually happened

Respond with a structured markdown document using these sections:

## What Happened
Brief (3–5 sentence) summary of session activity.

## Suggested Allow Rules
Commands that ran frequently and could be pre-approved (skip if none):
- `Bash(command *)` — reason it ran so often

## Suggested Gotchas
New project-specific gotchas to add to the ## Gotchas section of CLAUDE.md (skip if none):
- **Topic**: concrete description

## Suggested Conventions
Patterns in how Claude worked that should be encoded as conventions (skip if none):
- **Convention**: description

## How to Apply
Specific instructions for applying the above (e.g., which lines to add to which files).

Only suggest things with clear evidence from the session. If there is nothing \
significant to suggest, say so in one sentence under ## What Happened and omit \
the other sections."""


async def _call_claude_async(prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        return "(anthropic SDK not installed — run: pip install anthropic)"

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "(ANTHROPIC_API_KEY not set — skipping Claude analysis)"

    client = anthropic.Anthropic(api_key=api_key)

    async def _make_call() -> str:
        response = await asyncio.to_thread(
            client.messages.create,
            model=MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    try:
        return await asyncio.wait_for(_make_call(), timeout=API_TIMEOUT)
    except asyncio.TimeoutError:
        return "(Claude call timed out after 25s — session was too short to analyse)"
    except Exception as e:
        return f"(Claude call failed: {type(e).__name__}: {e})"


def _call_claude(prompt: str) -> str:
    try:
        return asyncio.run(_call_claude_async(prompt))
    except Exception as e:
        return f"(asyncio error: {e})"


# ── Main ───────────────────────────────────────────────────────────────────────

def run(project_root_str: str = ".") -> None:
    project_root = Path(project_root_str).resolve()
    print(f"[reflect.py] Reflecting on session for: {project_root}")

    audit_log = _read_audit_log()
    git_diff = _read_git_diff(project_root)
    claude_md = _read_claude_md(project_root)

    print("[reflect.py] Calling Claude for analysis…")
    prompt = _build_prompt(audit_log, git_diff, claude_md)
    proposal = _call_claude(prompt)

    dot_claude = project_root / ".claude"
    dot_claude.mkdir(parents=True, exist_ok=True)

    learnings_path = dot_claude / "session-learnings.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    content = (
        f"# Session Learnings — {timestamp}\n\n"
        "> Auto-generated by `agent/reflect.py`. "
        "Review and apply manually — never auto-applied.\n"
        "> Delete this file after applying what makes sense.\n\n"
        f"{proposal}\n"
    )

    try:
        learnings_path.write_text(content, encoding="utf-8")
        print(f"[reflect.py] Wrote proposals to: {learnings_path}")
    except Exception as e:
        print(f"[reflect.py] Could not write session-learnings.md: {e}")


if __name__ == "__main__":
    try:
        project_root = sys.argv[1] if len(sys.argv) > 1 else "."
        run(project_root)
    except Exception as e:
        print(f"[reflect.py] Error (non-fatal): {type(e).__name__}: {e}")
    sys.exit(0)
