#!/usr/bin/env python3
"""
Plan-first teacher mode for installing a scoped Claude Code harness.

Usage:
    python agent/teacher.py /path/to/project --task "what I want this project to do"
    python agent/teacher.py /path/to/project --task "..." --apply
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from agent.install import ProjectInfo, detect_project, generate_env_example
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from agent.install import ProjectInfo, detect_project, generate_env_example


ALLOWED_WRITE_PATHS = (
    "CLAUDE.md",
    ".claude/settings.json",
    ".claude/hooks/",
    ".claude/commands/",
    ".claude/agents/",
    ".env.example",
)


@dataclass
class TeacherPlan:
    project_profile: dict[str, Any]
    task_intent: dict[str, Any]
    current_harness_score: dict[str, Any]
    recommended_files: list[str]
    agents: list[dict[str, Any]]
    commands: list[dict[str, Any]]
    memory_plan: list[str]
    safety_plan: list[str]
    apply_policy: dict[str, Any]


def _project_profile(info: ProjectInfo) -> dict[str, Any]:
    commands = [
        command
        for command in [
            info.install_cmd,
            info.dev_cmd,
            info.build_cmd,
            info.test_cmd,
            info.lint_cmd,
        ]
        if command and not command.startswith("# TODO")
    ]
    return {
        "name": info.name,
        "language": info.language,
        "runtime": info.runtime,
        "framework": info.framework,
        "commands": commands,
        "package_manager": _package_manager(info.install_cmd),
        "dependencies": sorted(info.deps),
    }


def _package_manager(install_cmd: str) -> str:
    if not install_cmd or install_cmd.startswith("#"):
        return "unknown"
    return install_cmd.split()[0]


def _classify_task(task: str) -> str:
    words = set(re.findall(r"[a-z0-9]+", task.lower()))
    if words.intersection({"bug", "fix", "broken", "error", "debug"}):
        return "debugging"
    if words.intersection({"test", "qa", "verify", "audit"}):
        return "verification"
    if words.intersection({"design", "ui", "visual", "portfolio"}):
        return "design implementation"
    if words.intersection({"research", "plan", "strategy", "architecture"}):
        return "research and planning"
    return "feature implementation"


def _audit_target(target: Path) -> dict[str, Any]:
    audit_py = Path(__file__).parent / "audit.py"
    if audit_py.exists():
        try:
            completed = subprocess.run(
                [sys.executable, str(audit_py), str(target), "--json"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            data = json.loads(completed.stdout)
            return {
                "score": data.get("total"),
                "max": data.get("max"),
                "percent": data.get("pct"),
                "weakest_layer": data.get("layers", [{}])[-1].get("name"),
                "priority_actions": data.get("priority_actions", []),
                "source": "agent/audit.py",
            }
        except (subprocess.SubprocessError, json.JSONDecodeError):
            pass

    checks = [
        (target / "CLAUDE.md", "missing CLAUDE.md"),
        (target / ".claude" / "settings.json", "missing .claude/settings.json"),
        (target / ".claude" / "commands", "missing project slash commands"),
        (target / ".claude" / "agents", "missing project subagents"),
    ]
    findings = [message for path, message in checks if not path.exists()]
    return {
        "score": 4 - len(findings),
        "max": 4,
        "percent": round((4 - len(findings)) / 4 * 100),
        "findings": findings,
        "source": "teacher fallback audit",
    }


def create_teacher_plan(target: Path, task: str) -> TeacherPlan:
    info = detect_project(target)
    profile = _project_profile(info)
    workflow_type = _classify_task(task)
    recommended_files = [
        "CLAUDE.md",
        ".claude/settings.json",
        ".claude/agents/project-researcher.md",
        ".claude/agents/project-implementer.md",
        ".claude/commands/plan-task.md",
        ".claude/commands/work-task.md",
    ]
    if not (target / ".env.example").exists():
        recommended_files.append(".env.example")

    return TeacherPlan(
        project_profile=profile,
        task_intent={
            "user_task": task,
            "workflow_type": workflow_type,
            "success_criteria": [
                "Project conventions are inspected before implementation.",
                "Claude receives a focused context-loading path for the task.",
                "Only harness files are installed by teacher mode.",
                "Application source files are not moved or reorganized.",
            ],
        },
        current_harness_score=_audit_target(target),
        recommended_files=recommended_files,
        agents=[
            {
                "name": "project-researcher",
                "description": "Inspect the target repo and produce a source-backed implementation plan.",
                "tools": ["Read", "Grep", "Glob", "Bash"],
            },
            {
                "name": "project-implementer",
                "description": "Make scoped changes after an implementation plan is approved.",
                "tools": ["Read", "Grep", "Glob", "Edit", "Bash"],
            },
        ],
        commands=[
            {"name": "plan-task", "path": ".claude/commands/plan-task.md"},
            {"name": "work-task", "path": ".claude/commands/work-task.md"},
        ],
        memory_plan=[
            "Add task intent, project profile, and verification commands to CLAUDE.md.",
            "Load narrow context first; use targeted search before reading broad directories.",
            "Route planning work to project-researcher and implementation to project-implementer.",
        ],
        safety_plan=[
            "Install a deny list for secrets and destructive git operations.",
            "Do not enable hooks with side effects in teacher mode v1.",
            "Skip existing files unless --force is passed.",
        ],
        apply_policy={
            "allowed_paths": list(ALLOWED_WRITE_PATHS),
            "skip_existing_unless_force": True,
            "never_modify_application_source": True,
        },
    )


def _is_allowed(relative_path: str) -> bool:
    clean = relative_path.replace("\\", "/").lstrip("/")
    return any(clean == allowed or clean.startswith(allowed) for allowed in ALLOWED_WRITE_PATHS)


def _settings_json() -> str:
    settings = {
        "permissions": {
            "deny": [
                "Read(.env)",
                "Read(.env.*)",
                "Read(**/*secret*)",
                "Read(**/*credential*)",
                "Bash(git push --force*)",
                "Bash(git reset --hard*)",
                "Bash(rm -rf /*)",
            ]
        },
        "hooks": {},
    }
    return json.dumps(settings, indent=2) + "\n"


def _agent_markdown(name: str, description: str, tools: list[str], body: str) -> str:
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        f"tools: {', '.join(tools)}\n"
        "---\n\n"
        f"{body.rstrip()}\n"
    )


def _command_markdown(description: str, body: str, argument_hint: str) -> str:
    return (
        "---\n"
        f"description: {description}\n"
        f"argument-hint: {argument_hint}\n"
        "---\n\n"
        f"{body.rstrip()}\n"
    )


def _claude_md(plan: TeacherPlan) -> str:
    profile = plan.project_profile
    commands = "\n".join(f"- `{command}`" for command in profile["commands"]) or "- Add verification commands after setup."
    criteria = "\n".join(f"- {item}" for item in plan.task_intent["success_criteria"])
    return f"""# {profile["name"] or "Project"} Claude Harness

## Project Profile

- Language: {profile["language"]}
- Runtime: {profile["runtime"] or "unknown"}
- Framework: {profile["framework"] or "unknown"}
- Package manager: {profile["package_manager"]}

## Current Task Intent

{plan.task_intent["user_task"]}

Workflow type: {plan.task_intent["workflow_type"]}

## Success Criteria

{criteria}

## Commands

{commands}

## Context Loading

- Read this file before implementation.
- Use targeted search before opening broad directories.
- Ask `project-researcher` to map source evidence and plan work.
- Ask `project-implementer` to make scoped changes only after the plan is clear.

## Guardrails

- Do not move or reorganize application source as part of harness setup.
- Keep edits scoped to the user's task.
- Record verification and remaining risk before finishing.
"""


def _files_for_plan(plan: TeacherPlan, info: ProjectInfo) -> dict[str, str]:
    files = {
        "CLAUDE.md": _claude_md(plan),
        ".claude/settings.json": _settings_json(),
        ".claude/agents/project-researcher.md": _agent_markdown(
            "project-researcher",
            "Use proactively to inspect this repository and recommend the smallest source-backed plan.",
            ["Read", "Grep", "Glob", "Bash"],
            "Map relevant files, conventions, commands, and risks. Prefer local evidence. Cite official docs when outside research is needed.",
        ),
        ".claude/agents/project-implementer.md": _agent_markdown(
            "project-implementer",
            "Use after planning to make scoped code changes and verify them with project commands.",
            ["Read", "Grep", "Glob", "Edit", "Bash"],
            "Implement the approved plan with surgical changes. Preserve existing architecture and run the most relevant checks before reporting completion.",
        ),
        ".claude/commands/plan-task.md": _command_markdown(
            "Create an approval-ready implementation plan for this project.",
            """Inspect this repository for the task below and return:

- relevant files and conventions
- proposed edits
- verification commands
- risks and assumptions

Task: $ARGUMENTS
""",
            "task description",
        ),
        ".claude/commands/work-task.md": _command_markdown(
            "Implement an approved scoped task in this project.",
            """Implement the approved task below using CLAUDE.md rules.

Before editing, state the expected files to touch. After editing, run relevant verification commands and summarize results.

Task: $ARGUMENTS
""",
            "approved task",
        ),
    }
    files[".env.example"] = generate_env_example(info)
    return files


def apply_plan(target: Path, plan: TeacherPlan, force: bool = False) -> list[dict[str, str]]:
    info = detect_project(target)
    actions: list[dict[str, str]] = []
    for relative_path, content in _files_for_plan(plan, info).items():
        if relative_path not in plan.recommended_files:
            continue
        if not _is_allowed(relative_path):
            raise ValueError(f"Refusing to write outside harness scope: {relative_path}")
        destination = target / relative_path
        exists = destination.exists()
        if exists and not force:
            actions.append({"action": "skip", "path": relative_path, "reason": "exists"})
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        actions.append({"action": "overwrite" if exists else "create", "path": relative_path})
    return actions


def plan_to_markdown(plan: TeacherPlan) -> str:
    files = "\n".join(f"- `{path}`" for path in plan.recommended_files)
    agents = "\n".join(f"- `{agent['name']}`: {agent['description']}" for agent in plan.agents)
    commands = "\n".join(f"- `/{command['name']}` from `{command['path']}`" for command in plan.commands)
    return f"""# Teacher Plan

## Project Profile

- Language: {plan.project_profile["language"]}
- Framework: {plan.project_profile["framework"] or "unknown"}
- Package manager: {plan.project_profile["package_manager"]}
- Commands: {", ".join(plan.project_profile["commands"]) or "none detected"}

## Task Intent

{plan.task_intent["user_task"]}

Workflow type: {plan.task_intent["workflow_type"]}

## Current Harness Score

```json
{json.dumps(plan.current_harness_score, indent=2)}
```

## Recommended Files

{files}

## Agents

{agents}

## Commands

{commands}

## Apply Policy

- Skip existing files unless `--force` is passed.
- Write only Claude harness files and optional `.env.example`.
- Never reorganize application source in v1.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan and optionally install a task-specific Claude harness.")
    parser.add_argument("project", help="Target project path")
    parser.add_argument("--task", required=True, help="User task the harness should support")
    parser.add_argument("--apply", action="store_true", help="Write recommended harness files")
    parser.add_argument("--force", action="store_true", help="Overwrite existing harness files")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args(argv)

    target = Path(args.project).expanduser().resolve()
    if not target.is_dir():
        print(f"Error: {target} is not a directory", file=sys.stderr)
        return 1

    plan = create_teacher_plan(target, args.task)
    if args.apply:
        actions = apply_plan(target, plan, force=args.force)
        payload = {"plan": asdict(plan), "actions": actions}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(plan_to_markdown(plan))
            print("\n## Apply Actions\n")
            for action in actions:
                suffix = f" ({action['reason']})" if action.get("reason") else ""
                print(f"- {action['action']}: `{action['path']}`{suffix}")
        return 0

    if args.json:
        print(json.dumps(asdict(plan), indent=2))
    else:
        print(plan_to_markdown(plan))
        print("\n## JSON\n")
        print("```json")
        print(json.dumps(asdict(plan), indent=2))
        print("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
