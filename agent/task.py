#!/usr/bin/env python3
"""
agent/task.py — Agentic task runner.

Decomposes hard tasks into ≤7 subtasks with verification commands,
uses Claude to execute each subtask (with read/write/shell tools),
verifies success, commits on pass, retries on failure (max 3 attempts).

Usage:
    python agent/task.py "implement user authentication"
    python agent/task.py "add pagination to the API" /path/to/project
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

MODEL = "claude-opus-4-7"
MAX_RETRIES = 3
MAX_TOOL_ITERATIONS = 20


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class Subtask:
    index: int
    description: str
    verify_cmd: str
    status: str = "pending"  # pending | done | blocked
    attempts: int = 0
    diagnosis: str = ""
    commit_hash: str = ""


@dataclass
class TaskPlan:
    goal: str
    subtasks: list[Subtask] = field(default_factory=list)
    status: str = "IN PROGRESS"
    started: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))


# ── Shell helpers ──────────────────────────────────────────────────────────────

def _run(cmd: str, cwd: Path, timeout: int = 60) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return 1, "", str(e)


def _git_commit(message: str, project_root: Path) -> str:
    _run("git add -A", project_root)
    rc, _, _ = _run(f'git commit -m "{message}"', project_root)
    if rc != 0:
        return ""
    _, hash_out, _ = _run("git log -1 --pretty=%h", project_root)
    return hash_out.strip()


# ── Checklist I/O ──────────────────────────────────────────────────────────────

def _write_checklist(plan: TaskPlan, project_root: Path) -> None:
    lines = [
        f"# Task: {plan.goal}",
        f"**Goal:** {plan.goal}",
        f"**Started:** {plan.started}",
        f"**Status:** {plan.status}",
        "",
        "## Subtasks",
    ]
    for st in plan.subtasks:
        check = "x" if st.status == "done" else " "
        suffix = " ⚠ BLOCKED" if st.status == "blocked" else ""
        commit_note = f" ← {st.commit_hash}" if st.commit_hash else ""
        lines.append(f"- [{check}] {st.index}. {st.description}{suffix}{commit_note}")
        lines.append(f"       Verify: `{st.verify_cmd}`")
        if st.diagnosis:
            lines.append(f"       Diagnosis: {st.diagnosis}")
    path = project_root / ".claude" / "current-task.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Agentic tool definitions and executor ─────────────────────────────────────

EXEC_TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file in the project. Always read before editing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to project root"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a file in the project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to project root"},
                "content": {"type": "string", "description": "Full file content"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_command",
        "description": "Run a shell command in the project root. Returns stdout + stderr.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and subdirectories at a path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to project root (default: '.')",
                },
            },
            "required": ["path"],
        },
    },
]


def _execute_tool(name: str, inputs: dict, project_root: Path) -> str:
    if name == "read_file":
        path = project_root / inputs["path"]
        if not path.exists():
            return f"File not found: {inputs['path']}"
        try:
            return path.read_text(errors="replace")[:8000]
        except Exception as e:
            return f"Error reading {inputs['path']}: {e}"

    if name == "write_file":
        path = project_root / inputs["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(inputs["content"], encoding="utf-8")
        return f"Written: {inputs['path']} ({len(inputs['content'])} chars)"

    if name == "run_command":
        rc, stdout, stderr = _run(inputs["command"], project_root, timeout=120)
        combined = (stdout + ("\n" + stderr if stderr else "")).strip()
        return f"exit {rc}\n{combined[:3000]}"

    if name == "list_directory":
        path = project_root / inputs.get("path", ".")
        if not path.is_dir():
            return f"Not a directory: {inputs.get('path')}"
        items = sorted(path.iterdir())
        return "\n".join(
            f"{'d' if p.is_dir() else 'f'}  {p.name}" for p in items
        )

    return f"Unknown tool: {name}"


# ── Claude API helpers ─────────────────────────────────────────────────────────

def _get_client():
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic SDK not installed. Run: pip install anthropic")
        sys.exit(1)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


def _read_commands_section(project_root: Path) -> str:
    claude_md = project_root / "CLAUDE.md"
    if not claude_md.exists():
        return ""
    content = claude_md.read_text(errors="replace")
    m = re.search(r"^## Commands\s*\n(.*?)(?=^## |\Z)", content, re.M | re.DOTALL)
    return m.group(1).strip() if m else ""


# ── Phase 1: Decompose ────────────────────────────────────────────────────────

def decompose(goal: str, project_root: Path) -> TaskPlan:
    client = _get_client()
    commands = _read_commands_section(project_root)

    prompt = f"""You are planning how to execute the following task for a software project.

Task: {goal}
Project root: {project_root}

Project commands from CLAUDE.md:
{commands or "(no CLAUDE.md commands found — use standard commands for the stack)"}

Break this task into at most 7 concrete, ordered subtasks. Each subtask must:
1. Be a single-concern piece of work (one file / one feature / one test suite)
2. Have a machine-verifiable shell command that exits 0 only when done

Respond ONLY with valid JSON — no markdown fences, no commentary:
{{
  "subtasks": [
    {{
      "description": "one sentence describing what to do",
      "verify_cmd": "exact shell command that exits 0 on success"
    }}
  ]
}}

Good verify commands: pytest tests/test_auth.py -v, grep -q 'def login' src/auth.py
Bad verify commands: "check the code looks right", "run the app and see if it works\""""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Strip ```json fences if Claude added them
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    data = json.loads(text)
    plan = TaskPlan(goal=goal)
    for i, item in enumerate(data["subtasks"][:7], start=1):
        plan.subtasks.append(
            Subtask(index=i, description=item["description"], verify_cmd=item["verify_cmd"])
        )
    return plan


# ── Phase 2: Execute one subtask ──────────────────────────────────────────────

def _execute_subtask(subtask: Subtask, project_root: Path, claude_md_snippet: str) -> None:
    """Run an agentic Claude loop to complete one subtask."""
    client = _get_client()

    system = (
        f"You are an autonomous coding agent working on a software project.\n"
        f"Project root: {project_root}\n\n"
        f"Your task: {subtask.description}\n"
        f"Verification command (must exit 0 when done): {subtask.verify_cmd}\n\n"
        f"Project CLAUDE.md:\n{claude_md_snippet}\n\n"
        "Use the tools to read relevant files, write changes, and run commands.\n"
        "Stop when you believe the subtask is complete."
    )

    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"Complete this subtask: {subtask.description}\n\n"
                f"Verification command: {subtask.verify_cmd}"
            ),
        }
    ]

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=EXEC_TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _execute_tool(block.name, block.input, project_root)
                    key = str(block.input)[:60]
                    print(f"    [{block.name}] {key} → {result[:80]}")
                    results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": result}
                    )
            messages.append({"role": "user", "content": results})
        else:
            break


# ── Main orchestration ─────────────────────────────────────────────────────────

def run(goal: str, project_root_str: str = ".") -> None:
    project_root = Path(project_root_str).resolve()
    print(f"\n[task.py] Goal   : {goal}")
    print(f"[task.py] Project: {project_root}\n")

    # Read CLAUDE.md once for context
    claude_md_path = project_root / "CLAUDE.md"
    claude_md_snippet = (
        claude_md_path.read_text(errors="replace")[:3000]
        if claude_md_path.exists()
        else "(no CLAUDE.md)"
    )

    # Phase 1 — Decompose
    print("Phase 1 — Decomposing task...")
    plan = decompose(goal, project_root)
    _write_checklist(plan, project_root)

    print(f"\n  {len(plan.subtasks)} subtasks:\n")
    for st in plan.subtasks:
        print(f"  {st.index}. {st.description}")
        print(f"     Verify: {st.verify_cmd}")
    print()

    # Phase 2 — Execute → Verify → Commit
    print("Phase 2 — Executing subtasks...\n")
    last_output = ""

    for st in plan.subtasks:
        print(f"\n  [{st.index}/{len(plan.subtasks)}] {st.description}")

        for attempt in range(1, MAX_RETRIES + 1):
            st.attempts = attempt
            print(f"    Attempt {attempt}: executing...")
            _execute_subtask(st, project_root, claude_md_snippet)

            rc, stdout, stderr = _run(st.verify_cmd, project_root)
            last_output = (stdout + "\n" + stderr).strip()[:300]

            if rc == 0:
                st.status = "done"
                print(f"    ✓ Verify passed")
                st.commit_hash = _git_commit(
                    f"task: subtask {st.index} — {st.description}", project_root
                )
                if st.commit_hash:
                    print(f"    ✓ Committed: {st.commit_hash}")
                _write_checklist(plan, project_root)
                break
            else:
                print(f"    ✗ Verify failed: {last_output[:80]}")
                if attempt < MAX_RETRIES:
                    print("    → Retrying...")
        else:
            st.status = "blocked"
            st.diagnosis = (
                f"Failed after {MAX_RETRIES} attempts. Last output: {last_output[:200]}"
            )
            print(f"    ⚠ Blocked: {st.diagnosis}")
            _write_checklist(plan, project_root)

    # Phase 3 — Close
    print("\nPhase 3 — Closing task...\n")
    done = [st for st in plan.subtasks if st.status == "done"]
    blocked = [st for st in plan.subtasks if st.status == "blocked"]

    plan.status = "COMPLETE" if not blocked else "PARTIAL"
    _write_checklist(plan, project_root)

    print(f"Status     : {plan.status}")
    print(f"Completed  : {len(done)}/{len(plan.subtasks)} subtasks")
    if done:
        for st in done:
            commit = f" [{st.commit_hash}]" if st.commit_hash else ""
            print(f"  ✓ Subtask {st.index}: {st.description}{commit}")
    if blocked:
        print(f"Blocked    : {len(blocked)} subtask(s)")
        for st in blocked:
            print(f"  ⚠ Subtask {st.index}: {st.description}")
            print(f"    {st.diagnosis}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python agent/task.py \"task description\" [project_root]")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
