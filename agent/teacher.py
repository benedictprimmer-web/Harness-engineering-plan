from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

try:
    from .install import install_harness
except ImportError:  # pragma: no cover - direct script execution
    from install import install_harness


@dataclass
class ProjectProfile:
    language: str
    framework: str
    package_manager: str
    commands: List[str]
    detected_files: List[str]


@dataclass
class TaskIntent:
    user_task: str
    workflow_type: str
    success_criteria: List[str]


@dataclass
class TeacherPlan:
    project_profile: Dict[str, object]
    task_intent: Dict[str, object]
    current_harness_score: Dict[str, object]
    recommended_files: List[str]
    agents: List[Dict[str, object]]
    commands: List[Dict[str, object]]
    memory_plan: List[str]
    safety_plan: List[str]
    apply_policy: Dict[str, object]


def _read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback
    except json.JSONDecodeError:
        return fallback


def _package_manager(target: Path) -> str:
    if (target / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (target / "yarn.lock").exists():
        return "yarn"
    if (target / "package-lock.json").exists():
        return "npm"
    if (target / "package.json").exists():
        return "npm"
    if (target / "uv.lock").exists():
        return "uv"
    if (target / "poetry.lock").exists():
        return "poetry"
    if (target / "requirements.txt").exists():
        return "pip"
    return "unknown"


def detect_project(target: Path) -> ProjectProfile:
    target = target.resolve()
    detected: List[str] = []
    language = "unknown"
    framework = "unknown"
    commands: List[str] = []

    package_json = target / "package.json"
    if package_json.exists():
        detected.append("package.json")
        language = "javascript"
        package = _read_json(package_json, {})
        deps = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
        scripts = package.get("scripts", {})
        if "next" in deps:
            framework = "nextjs"
        elif "vite" in deps:
            framework = "vite"
        elif "react" in deps:
            framework = "react"
        else:
            framework = "node"
        manager = _package_manager(target)
        if "test" in scripts:
            commands.append(f"{manager} test")
        if "lint" in scripts:
            commands.append(f"{manager} run lint")
        if "build" in scripts:
            commands.append(f"{manager} run build")

    pyproject = target / "pyproject.toml"
    requirements = target / "requirements.txt"
    if pyproject.exists() or requirements.exists():
        language = "python" if language == "unknown" else f"{language}+python"
        if pyproject.exists():
            detected.append("pyproject.toml")
            text = pyproject.read_text(encoding="utf-8", errors="ignore").lower()
            if "django" in text:
                framework = "django"
            elif "fastapi" in text:
                framework = "fastapi"
            elif framework == "unknown":
                framework = "python"
        if requirements.exists():
            detected.append("requirements.txt")
            text = requirements.read_text(encoding="utf-8", errors="ignore").lower()
            if "django" in text:
                framework = "django"
            elif "fastapi" in text:
                framework = "fastapi"
            elif framework == "unknown":
                framework = "python"
        commands.append("python -m pytest")

    if (target / ".harness/config.json").exists():
        detected.append(".harness/config.json")
    if (target / "CLAUDE.md").exists():
        detected.append("CLAUDE.md")
    if (target / ".claude/settings.json").exists():
        detected.append(".claude/settings.json")

    return ProjectProfile(
        language=language,
        framework=framework,
        package_manager=_package_manager(target),
        commands=commands,
        detected_files=sorted(set(detected)),
    )


def audit_harness(target: Path) -> Dict[str, object]:
    repo_root = Path(__file__).resolve().parents[1]
    audit_script = repo_root / "scripts" / "harness-audit.js"
    if audit_script.exists() and (target / ".harness/config.json").exists():
        try:
            completed = subprocess.run(
                ["node", str(audit_script), "--target", str(target)],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            existing = json.loads(completed.stdout)
            return {
                "score": existing.get("score", 0),
                "summary": "Existing harness scored with scripts/harness-audit.js.",
                "findings": existing.get("findings", []),
            }
        except (FileNotFoundError, subprocess.SubprocessError, json.JSONDecodeError):
            pass

    checks = [
        (target / ".harness/config.json", "missing existing .harness/config.json"),
        (target / "CLAUDE.md", "missing CLAUDE.md project memory"),
        (target / ".claude/settings.json", "missing .claude/settings.json safety settings"),
        (target / ".claude/commands", "missing project slash commands"),
        (target / ".claude/agents", "missing project subagents"),
    ]
    findings: List[str] = []
    score = 100
    for path, label in checks:
        if not path.exists():
            findings.append(label)
            score -= 15
    return {
        "score": max(score, 0),
        "summary": "Existing harness checked for Claude memory, settings, commands, agents, and .harness config.",
        "findings": findings,
    }


def classify_task(task: str) -> TaskIntent:
    lowered = task.lower()
    words = set(re.findall(r"[a-z0-9]+", lowered))
    if words.intersection({"bug", "fix", "broken", "error", "debug"}):
        workflow = "debugging"
    elif words.intersection({"design", "ui", "visual", "portfolio"}):
        workflow = "design implementation"
    elif words.intersection({"test", "qa", "verify"}):
        workflow = "verification"
    else:
        workflow = "feature implementation"
    return TaskIntent(
        user_task=task,
        workflow_type=workflow,
        success_criteria=[
            "Repository conventions are identified before editing.",
            "Harness files give Claude a narrow task workflow and verification path.",
            "Application source files are not moved or reorganized by teacher mode.",
        ],
    )


def create_teacher_plan(target: Path, task: str) -> TeacherPlan:
    profile = detect_project(target)
    intent = classify_task(task)
    return TeacherPlan(
        project_profile=asdict(profile),
        task_intent=asdict(intent),
        current_harness_score=audit_harness(target),
        recommended_files=[
            "CLAUDE.md",
            ".claude/settings.json",
            ".claude/agents/project-researcher.md",
            ".claude/agents/project-implementer.md",
            ".claude/commands/plan-task.md",
            ".claude/commands/work-task.md",
        ],
        agents=[
            {
                "name": "project-researcher",
                "description": "Inspect repo conventions and produce source-backed plans.",
                "tools": ["Read", "Grep", "Glob", "Bash"],
            },
            {
                "name": "project-implementer",
                "description": "Make scoped code changes after a plan is approved.",
                "tools": ["Read", "Grep", "Glob", "Edit", "Bash"],
            },
        ],
        commands=[
            {"name": "plan-task", "path": ".claude/commands/plan-task.md"},
            {"name": "work-task", "path": ".claude/commands/work-task.md"},
        ],
        memory_plan=[
            "Add project profile and current task intent to CLAUDE.md.",
            "Add context-loading rules that prefer targeted search and repo-local evidence.",
            "List verification commands detected from project metadata.",
        ],
        safety_plan=[
            "Deny reads of common secret and credential files in .claude/settings.json.",
            "Do not install hooks with side effects by default.",
            "Do not move or refactor application source files in v1 teacher mode.",
        ],
        apply_policy={
            "allowed_paths": [
                "CLAUDE.md",
                ".claude/settings.json",
                ".claude/hooks/",
                ".claude/commands/",
                ".claude/agents/",
                ".env.example",
            ],
            "skip_existing_unless_force": True,
            "never_modify_application_source": True,
        },
    )


def plan_to_markdown(plan: TeacherPlan) -> str:
    data = asdict(plan)
    files = "\n".join(f"- `{path}`" for path in data["recommended_files"])
    agents = "\n".join(f"- `{agent['name']}`: {agent['description']}" for agent in data["agents"])
    commands = "\n".join(f"- `/{command['name']}` from `{command['path']}`" for command in data["commands"])
    criteria = "\n".join(f"- {item}" for item in data["task_intent"]["success_criteria"])
    findings = data["current_harness_score"].get("findings", [])
    findings_text = "\n".join(f"- {finding}" for finding in findings) or "- No major harness gaps detected."
    return f"""# Teacher Plan

## Project Profile

- Language: {data["project_profile"]["language"]}
- Framework: {data["project_profile"]["framework"]}
- Package manager: {data["project_profile"]["package_manager"]}
- Commands: {", ".join(data["project_profile"]["commands"]) or "none detected"}

## Task Intent

{data["task_intent"]["user_task"]}

Workflow type: {data["task_intent"]["workflow_type"]}

## Success Criteria

{criteria}

## Current Harness Score

Score: {data["current_harness_score"]["score"]}

{findings_text}

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


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan and optionally install a Claude project harness.")
    parser.add_argument("target", help="Target project path")
    parser.add_argument("--task", required=True, help="User task the harness should support")
    parser.add_argument("--apply", action="store_true", help="Install recommended harness files")
    parser.add_argument("--force", action="store_true", help="Overwrite existing harness files when applying")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args(argv)

    target = Path(args.target).resolve()
    plan = create_teacher_plan(target, args.task)
    if args.apply:
        actions = install_harness(target, asdict(plan), force=args.force)
        payload = {"plan": asdict(plan), "actions": [action.to_dict() for action in actions]}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(plan_to_markdown(plan))
            print("\n## Apply Actions\n")
            for action in actions:
                suffix = f" ({action.reason})" if action.reason else ""
                print(f"- {action.action}: `{action.path}`{suffix}")
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
