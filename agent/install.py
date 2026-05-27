from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping


ALLOWED_WRITE_PREFIXES = (
    "CLAUDE.md",
    ".claude/settings.json",
    ".claude/hooks/",
    ".claude/commands/",
    ".claude/agents/",
    ".env.example",
)


@dataclass(frozen=True)
class InstallAction:
    action: str
    path: str
    reason: str = ""

    def to_dict(self) -> Dict[str, str]:
        data = {"action": self.action, "path": self.path}
        if self.reason:
            data["reason"] = self.reason
        return data


def is_allowed_harness_path(relative_path: str) -> bool:
    clean = relative_path.replace(os.sep, "/").lstrip("/")
    return any(clean == prefix or clean.startswith(prefix) for prefix in ALLOWED_WRITE_PREFIXES)


def _yaml_agent(name: str, description: str, tools: Iterable[str], body: str) -> str:
    tools_list = [tool for tool in tools if tool]
    tool_line = f"tools: {', '.join(tools_list)}\n" if tools_list else ""
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        f"{tool_line}"
        "---\n\n"
        f"{body.rstrip()}\n"
    )


def command_markdown(description: str, prompt: str, argument_hint: str = "") -> str:
    hint = f"argument-hint: {argument_hint}\n" if argument_hint else ""
    return (
        "---\n"
        f"description: {description}\n"
        f"{hint}"
        "---\n\n"
        f"{prompt.rstrip()}\n"
    )


def generated_harness_files(plan: Mapping[str, object]) -> Dict[str, str]:
    project_profile = plan.get("project_profile", {}) or {}
    task_intent = plan.get("task_intent", {}) or {}
    task = str(task_intent.get("user_task", "")).strip() or "Improve this project for focused agent work."
    language = str(project_profile.get("language", "unknown"))
    framework = str(project_profile.get("framework", "unknown"))
    commands = project_profile.get("commands", []) or []
    test_commands = "\n".join(f"- `{command}`" for command in commands) or "- Add verification commands after project setup is confirmed."

    claude_md = f"""# Claude Project Harness

## Project Profile

- Language: {language}
- Framework: {framework}
- Package manager: {project_profile.get("package_manager", "unknown")}

## Current Task Intent

{task}

## Working Rules

- Start by reading the smallest set of files needed for the task.
- Keep application source edits scoped to the user's explicit request.
- Do not reorganize source directories as part of harness setup.
- Record verification commands and residual risk before finishing.

## Verification

{test_commands}

## Context Loading

- Read this file first.
- Prefer targeted search over broad file dumps.
- Use `.claude/agents/project-researcher.md` for repo mapping and source-backed recommendations.
- Use `.claude/agents/project-implementer.md` for implementation after the plan is clear.
"""

    settings = {
        "permissions": {
            "deny": [
                "Read(.env)",
                "Read(.env.*)",
                "Read(**/*secret*)",
                "Read(**/*credential*)",
            ]
        },
        "hooks": {},
    }

    files = {
        "CLAUDE.md": claude_md,
        ".claude/settings.json": f"{json.dumps(settings, indent=2)}\n",
        ".claude/agents/project-researcher.md": _yaml_agent(
            "project-researcher",
            "Use proactively to inspect this repository and recommend the smallest source-backed implementation plan.",
            ["Read", "Grep", "Glob", "Bash"],
            """You are a repository researcher for this project.

Map the relevant files, detect existing conventions, and produce a concise plan before implementation. Prefer local evidence from the repo. When outside documentation is needed, cite official sources or clearly label assumptions.
""",
        ),
        ".claude/agents/project-implementer.md": _yaml_agent(
            "project-implementer",
            "Use after planning to make scoped code changes and verify them with the project commands.",
            ["Read", "Grep", "Glob", "Edit", "Bash"],
            """You are a scoped implementation agent for this project.

Follow the current task intent, preserve existing architecture, avoid unrelated refactors, and run the most relevant verification commands before reporting completion.
""",
        ),
        ".claude/commands/plan-task.md": command_markdown(
            "Create an approval-ready implementation plan for this project.",
            """Inspect the repository for the task below and produce a plan with:

- relevant files and conventions
- exact proposed edits
- tests or checks to run
- risks and assumptions

Task: $ARGUMENTS
""",
            "task description",
        ),
        ".claude/commands/work-task.md": command_markdown(
            "Implement a scoped approved task in this project.",
            """Implement the approved task below using the project harness rules in CLAUDE.md.

Before editing, restate the files you expect to touch. After editing, run the relevant verification commands and summarize the result.

Task: $ARGUMENTS
""",
            "approved task",
        ),
    }

    if plan.get("include_env_example"):
        files[".env.example"] = "# Add required environment variable names here without secret values.\n"

    return files


def install_harness(target: Path, plan: Mapping[str, object], force: bool = False) -> List[InstallAction]:
    target = target.resolve()
    actions: List[InstallAction] = []
    for relative_path, content in generated_harness_files(plan).items():
        clean = relative_path.replace(os.sep, "/")
        if not is_allowed_harness_path(clean):
            raise ValueError(f"Refusing to write outside allowed harness scope: {relative_path}")
        destination = target / clean
        exists = destination.exists()
        if exists and not force:
            actions.append(InstallAction("skip", clean, "exists"))
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        actions.append(InstallAction("overwrite" if exists else "create", clean))
    return actions

