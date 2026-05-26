#!/usr/bin/env python3
"""
Harness Engineering Audit Tool
================================
Scans an existing project directory, scores its Claude Code harness
across five layers (0–5 each), and outputs a prioritised gap report.

Usage:
  python agent/audit.py /path/to/project
  python agent/audit.py /path/to/project --save    # saves to research/notes/
  python agent/audit.py .                           # audit this repo
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

REPO_ROOT = Path(__file__).parent.parent


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #


@dataclass
class LayerResult:
    name: str
    score: int = 0      # 0–5
    max_score: int = 5
    findings: list[str] = field(default_factory=list)   # what was found (good)
    gaps: list[str] = field(default_factory=list)        # what's missing
    fixes: list[str] = field(default_factory=list)       # specific next steps


@dataclass
class AuditReport:
    project_path: Path
    timestamp: str
    layers: list[LayerResult] = field(default_factory=list)

    @property
    def total_score(self) -> int:
        return sum(r.score for r in self.layers)

    @property
    def max_total(self) -> int:
        return sum(r.max_score for r in self.layers)

    @property
    def weakest_layer(self) -> LayerResult:
        return min(self.layers, key=lambda r: r.score / r.max_score)


# --------------------------------------------------------------------------- #
# Audit logic — one function per layer
# --------------------------------------------------------------------------- #


def audit_claude_md(root: Path) -> LayerResult:
    result = LayerResult(name="CLAUDE.md")

    claude_files = list(root.rglob("CLAUDE.md"))
    root_claude = root / "CLAUDE.md"

    if not claude_files:
        result.score = 0
        result.gaps.append("No CLAUDE.md found anywhere in the project")
        result.fixes.append("Create CLAUDE.md — start from examples/karpathy-minimal/CLAUDE.md")
        return result

    result.findings.append(f"Found {len(claude_files)} CLAUDE.md file(s)")

    if not root_claude.exists():
        result.score = 1
        result.gaps.append("No root-level CLAUDE.md (only found in subdirectories)")
        result.fixes.append("Add a root CLAUDE.md — Claude reads this first in every session")
        return result

    text = root_claude.read_text(encoding="utf-8", errors="replace")
    lines = [l for l in text.splitlines() if l.strip()]
    line_count = len(lines)
    score = 1

    # Check for key sections
    sections = {
        "project": bool(re.search(r"##\s*(project|overview|about)", text, re.I)),
        "stack": bool(re.search(r"##\s*(stack|tech|technology|dependencies)", text, re.I)),
        "commands": bool(re.search(r"##\s*(commands?|scripts?|usage|getting.started)", text, re.I)),
        "architecture": bool(re.search(r"##\s*(architecture|structure|layout|directory)", text, re.I)),
        "conventions": bool(re.search(r"##\s*(conventions?|guidelines?|rules?|standards?)", text, re.I)),
        "environment": bool(re.search(r"##\s*(environment|env|setup|configuration)", text, re.I)),
        "gotchas": bool(re.search(r"##\s*(gotchas?|warnings?|pitfalls?|notes?|caveats?)", text, re.I)),
    }

    present = [k for k, v in sections.items() if v]
    missing = [k for k, v in sections.items() if not v]

    result.findings.append(f"{line_count} lines; {len(present)}/7 sections present")

    if line_count >= 20 and (sections["stack"] or sections["commands"]):
        score = 2

    if len(present) >= 5:
        score = 3
        result.findings.append(f"Sections found: {', '.join(present)}")

    # Karpathy rules check
    karpathy_signals = ["think before", "simplicity first", "surgical", "goal-driven",
                        "minimum code", "don't assume", "state your assumption"]
    has_karpathy = any(sig in text.lower() for sig in karpathy_signals)
    if has_karpathy:
        score = min(score + 1, 4)
        result.findings.append("Karpathy behavioural rules detected")

    # Gotchas quality
    gotcha_count = len(re.findall(r"^[-*]\s+\*\*", text, re.M))
    if gotcha_count >= 3 and score >= 3:
        score = min(score + 1, 5)
        result.findings.append(f"{gotcha_count} formatted gotchas found")

    result.score = score

    # Gaps
    if missing:
        result.gaps.append(f"Missing sections: {', '.join(missing)}")
        result.fixes.extend([
            f"Add a '## {s.title()}' section to CLAUDE.md" for s in missing[:3]
        ])
    if not has_karpathy:
        result.gaps.append("Karpathy behavioural baseline not present")
        result.fixes.append(
            "Merge examples/karpathy-minimal/CLAUDE.md rules into CLAUDE.md"
        )
    if gotcha_count < 3:
        result.gaps.append(f"Only {gotcha_count} formatted gotchas — aim for 5+")
        result.fixes.append(
            "Add gotchas for every repeated mistake Claude makes in real sessions"
        )

    return result


def audit_settings(root: Path) -> LayerResult:
    result = LayerResult(name="settings.json")
    settings_path = root / ".claude" / "settings.json"

    if not settings_path.exists():
        result.score = 0
        result.gaps.append("No .claude/settings.json found")
        result.fixes.append("Create .claude/settings.json with at minimum a deny list")
        return result

    try:
        settings = json.loads(settings_path.read_text())
    except json.JSONDecodeError as e:
        result.score = 0
        result.gaps.append(f"settings.json is invalid JSON: {e}")
        result.fixes.append("Fix JSON syntax error in .claude/settings.json")
        return result

    perms = settings.get("permissions", {})
    allow = perms.get("allow", [])
    deny = perms.get("deny", [])
    hooks = settings.get("hooks", {})

    result.findings.append(f"{len(allow)} allow rule(s), {len(deny)} deny rule(s), {len(hooks)} hook event(s)")
    score = 1

    # Blanket allow check
    blanket = any(r in ("Bash(*)", "Bash(* *)") for r in allow)
    if blanket:
        result.gaps.append("Blanket Bash(*) allow — over-permissive, blocks no dangerous commands")
        result.fixes.append(
            "Replace Bash(*) with scoped rules; check ~/.claude session transcripts for the "
            "actual commands Claude runs: grep 'Bash(' transcript.jsonl | sort | uniq -c | sort -rn"
        )
    elif allow:
        score = 2
        result.findings.append("Scoped allow rules present")

    if deny:
        score = max(score, 3)
        result.findings.append(f"Deny rules: {deny[:3]}")
    else:
        result.gaps.append("No deny rules — destructive commands (force push, rm -rf, reset --hard) not blocked")
        result.fixes.append(
            "Add deny rules: Bash(git push --force*), Bash(git reset --hard*), Bash(rm -rf /*),"
            " Bash(curl * | bash), Bash(wget * | bash)"
        )

    # Scoping check
    scoped = [r for r in allow if r.count("(") and "*" not in r.split("(")[1].rstrip(")")]
    if scoped and score >= 3:
        score = 4
        result.findings.append(f"{len(scoped)} fully-scoped rule(s) (no wildcard)")

    if hooks:
        score = min(score + 1, 5)
        result.findings.append(f"Hook events configured: {list(hooks.keys())}")

    result.score = score

    if score < 5 and not hooks:
        result.gaps.append("No hooks registered in settings.json")
        result.fixes.append("Register at least a SessionStart hook")

    return result


def audit_hooks(root: Path) -> LayerResult:
    result = LayerResult(name="Hooks")
    claude_dir = root / ".claude"

    # Find hook scripts
    hook_scripts: list[Path] = []
    if (claude_dir / "hooks").exists():
        hook_scripts = list((claude_dir / "hooks").glob("*.sh"))

    # Check settings.json for registered hooks
    settings_path = claude_dir / "settings.json"
    registered_events: list[str] = []
    if settings_path.exists():
        try:
            s = json.loads(settings_path.read_text())
            registered_events = list(s.get("hooks", {}).keys())
        except Exception:
            pass

    if not hook_scripts and not registered_events:
        result.score = 0
        result.gaps.append("No hook scripts found and no hooks registered")
        result.fixes.append(
            "Copy templates/hooks/session-start.sh to .claude/hooks/ and register in settings.json"
        )
        return result

    result.findings.append(
        f"{len(hook_scripts)} script(s) in .claude/hooks/; events registered: {registered_events or 'none'}"
    )
    score = 1

    # Check which events are covered
    event_coverage = {
        "SessionStart": any("session" in s.name.lower() for s in hook_scripts) or "SessionStart" in registered_events,
        "PreToolUse": any("pre" in s.name.lower() or "safety" in s.name.lower() for s in hook_scripts) or "PreToolUse" in registered_events,
        "PostToolUse": any("post" in s.name.lower() or "format" in s.name.lower() for s in hook_scripts) or "PostToolUse" in registered_events,
        "Stop": any("stop" in s.name.lower() or "git" in s.name.lower() for s in hook_scripts) or "Stop" in registered_events,
    }

    covered = [k for k, v in event_coverage.items() if v]
    result.findings.append(f"Events covered: {covered or ['none']}")

    if event_coverage["SessionStart"]:
        score = 2
    if event_coverage["SessionStart"] and event_coverage["PreToolUse"]:
        score = 3
    if sum(event_coverage.values()) >= 3:
        score = 4

    # Quality check — look for common issues
    issues = []
    for script in hook_scripts:
        content = script.read_text(errors="replace")
        if "set -e" in content and "|| true" not in content:
            issues.append(f"{script.name}: uses set -e without || true guards (may fail silently)")
        if "npm install" in content and "node_modules" not in content:
            issues.append(f"{script.name}: runs npm install unconditionally (slow — add a node_modules check)")

    if not issues and score >= 4:
        score = 5
        result.findings.append("No common hook anti-patterns detected")
    elif issues:
        result.gaps.extend(issues)

    result.score = score

    missing = [k for k, v in event_coverage.items() if not v]
    if missing:
        result.gaps.append(f"Missing hook events: {', '.join(missing)}")
        if "PreToolUse" in missing:
            result.fixes.append(
                "Add .claude/hooks/pre-tool-use-safety.sh to block rm -rf, force push, curl|bash"
            )
        if "PostToolUse" in missing:
            result.fixes.append(
                "Add .claude/hooks/post-edit-format.sh for auto-formatting after edits"
            )
        if "Stop" in missing:
            result.fixes.append(
                "Add .claude/hooks/stop-hook-git-check.sh to remind Claude to commit before stopping"
            )

    return result


def audit_architecture(root: Path) -> LayerResult:
    result = LayerResult(name="Architecture Context")
    claude_file = root / "CLAUDE.md"

    if not claude_file.exists():
        result.score = 0
        result.gaps.append("No CLAUDE.md — no architecture context possible")
        return result

    text = claude_file.read_text(encoding="utf-8", errors="replace")
    score = 0

    # Architecture section
    arch_match = re.search(
        r"##\s*(architecture|structure|layout|directory)[^\n]*\n(.*?)(?=\n##|\Z)",
        text, re.I | re.S
    )
    if not arch_match:
        result.gaps.append("No architecture/structure section in CLAUDE.md")
        result.fixes.append("Add a ## Architecture section with annotated directory tree")
        return result

    arch_text = arch_match.group(2)
    score = 1

    # Has annotations (← comments or descriptions)
    if "←" in arch_text or "—" in arch_text or "#" in arch_text:
        score = 2
        result.findings.append("Directory tree has inline annotations")

    # Documents boundaries (never, always, don't)
    boundary_signals = ["never", "always", "don't", "do not", "auto-generated", "don't edit"]
    if any(sig in text.lower() for sig in boundary_signals):
        score = 3
        result.findings.append("Explicit boundary/constraint language found")

    # Auto-generated paths flagged
    autogen_signals = ["auto-generated", "auto generated", "generated by", "don't edit", "do not edit", "managed by"]
    if any(sig in text.lower() for sig in autogen_signals):
        score = min(score + 1, 4)
        result.findings.append("Auto-generated paths explicitly flagged")

    # Naming conventions documented
    if re.search(r"prefix|suffix|naming|convention", text, re.I):
        score = min(score + 1, 5)
        result.findings.append("Naming conventions documented")

    result.score = score

    if score < 3:
        result.gaps.append(
            "Architecture section lacks boundary constraints (what Claude must NOT touch/assume)"
        )
        result.fixes.append(
            "Add explicit 'DO NOT EDIT' notes for auto-generated dirs; document naming conventions"
        )

    return result


def audit_environment(root: Path) -> LayerResult:
    result = LayerResult(name="Environment & Secrets")
    claude_file = root / "CLAUDE.md"

    score = 0

    # Check for .env.example
    env_example = (root / ".env.example").exists() or (root / ".env.sample").exists()
    if env_example:
        result.findings.append(".env.example present")
        score = 1

    if not claude_file.exists():
        result.score = score
        result.gaps.append("No CLAUDE.md — environment setup not documented")
        return result

    text = claude_file.read_text(encoding="utf-8", errors="replace")

    env_section = bool(re.search(r"##\s*(environment|env|setup|configuration)", text, re.I))
    if env_section:
        score = max(score, 2)
        result.findings.append("Environment section present in CLAUDE.md")

    # Lists env vars
    env_var_count = len(re.findall(r"`[A-Z][A-Z0-9_]{2,}`", text))
    if env_var_count >= 3:
        score = max(score, 3)
        result.findings.append(f"{env_var_count} environment variables referenced")

    # Setup instructions (where to get credentials)
    cred_signals = ["1password", "lastpass", "get from", "generate with", "obtain", "request from"]
    if any(sig in text.lower() for sig in cred_signals):
        score = max(score, 4)
        result.findings.append("Credential sourcing instructions present")

    # Local dev automation
    local_signals = ["docker compose", "docker-compose", "make setup", "./setup", "brew install"]
    if any(sig in text.lower() for sig in local_signals):
        score = min(score + 1, 5)
        result.findings.append("Local dev setup commands documented")

    result.score = score

    if score < 3:
        result.gaps.append("Environment variables not documented in CLAUDE.md")
        result.fixes.append(
            "Add a ## Environment section listing all required env vars with where to get them"
        )
    if not env_example:
        result.gaps.append("No .env.example file")
        result.fixes.append("Create .env.example with all required variables (values redacted)")

    return result


# --------------------------------------------------------------------------- #
# Report renderer
# --------------------------------------------------------------------------- #


BAR_CHARS = "▏▎▍▌▋▊▉█"


def score_bar(score: int, max_score: int = 5, width: int = 10) -> str:
    filled = int(score / max_score * width)
    return "█" * filled + "░" * (width - filled)


def colour(score: int, max_score: int = 5) -> str:
    ratio = score / max_score
    if ratio >= 0.8:
        return "green"
    if ratio >= 0.5:
        return "yellow"
    return "red"


def render_report(report: AuditReport, console: Console) -> str:
    """Render to console and return markdown string."""
    md_lines: list[str] = []

    # Header
    header = (
        f"[bold]Harness Audit — {report.project_path.resolve().name}[/bold]\n"
        f"[dim]{report.project_path.resolve()}  ·  {report.timestamp}[/dim]"
    )
    console.print(Panel(header, border_style="cyan"))
    md_lines += [
        f"# Harness Audit — {report.project_path.resolve().name}",
        f"*{report.project_path.resolve()} · {report.timestamp}*\n",
    ]

    # Score table
    table = Table(box=box.SIMPLE_HEAD, show_footer=True)
    table.add_column("Layer", footer="[bold]Total[/bold]")
    table.add_column("Score", justify="center",
                     footer=f"[bold]{report.total_score}/{report.max_total}[/bold]")
    table.add_column("Bar", footer="")

    md_lines.append("## Score Card\n")
    md_lines.append("| Layer | Score | Bar |")
    md_lines.append("|-------|-------|-----|")

    for r in report.layers:
        c = colour(r.score)
        bar = score_bar(r.score)
        table.add_row(r.name, f"[{c}]{r.score}/{r.max_score}[/{c}]", f"[{c}]{bar}[/{c}]")
        md_lines.append(f"| {r.name} | {r.score}/{r.max_score} | `{bar}` |")

    md_lines.append(f"\n**Total: {report.total_score}/{report.max_total}**\n")
    console.print(table)

    # Per-layer detail
    console.print()
    md_lines.append("## Layer Detail\n")

    for r in report.layers:
        c = colour(r.score)
        console.print(f"[bold {c}]{r.name}  {r.score}/{r.max_score}[/bold {c}]")
        md_lines.append(f"### {r.name}  {r.score}/{r.max_score}\n")

        if r.findings:
            for f in r.findings:
                console.print(f"  [dim]✓ {f}[/dim]")
            md_lines.append("**Found:**")
            md_lines.extend(f"- ✓ {f}" for f in r.findings)
            md_lines.append("")

        if r.gaps:
            for g in r.gaps:
                console.print(f"  [red]✗ {g}[/red]")
            md_lines.append("**Gaps:**")
            md_lines.extend(f"- ✗ {g}" for g in r.gaps)
            md_lines.append("")

        if r.fixes:
            md_lines.append("**Next steps:**")
            md_lines.extend(f"- {f}" for f in r.fixes)
            md_lines.append("")

        console.print()

    # Priority actions
    all_fixes: list[tuple[int, str]] = []
    for i, r in enumerate(report.layers):
        priority = (r.max_score - r.score) * 10 + (5 - i)
        for fix in r.fixes:
            all_fixes.append((priority, fix))

    all_fixes.sort(reverse=True)
    top = [f for _, f in all_fixes[:7]]

    if top:
        console.print(Panel(
            "\n".join(f"  {i+1}. {f}" for i, f in enumerate(top)),
            title="[bold yellow]Priority Actions[/bold yellow]",
            border_style="yellow",
        ))
        md_lines.append("## Priority Actions\n")
        md_lines.extend(f"{i+1}. {f}" for i, f in enumerate(top))

    return "\n".join(md_lines)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a project's Claude Code harness")
    parser.add_argument("project", help="Path to the project root")
    parser.add_argument("--save", action="store_true",
                        help="Save report to research/notes/ in this repo")
    args = parser.parse_args()

    root = Path(args.project).expanduser().resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    console = Console()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    report = AuditReport(project_path=root, timestamp=timestamp)
    report.layers = [
        audit_claude_md(root),
        audit_settings(root),
        audit_hooks(root),
        audit_architecture(root),
        audit_environment(root),
    ]

    md = render_report(report, console)

    if args.save:
        notes_dir = REPO_ROOT / "research" / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        date = datetime.now().strftime("%Y%m%d-%H%M")
        slug = re.sub(r"[^a-z0-9]+", "-", root.name.lower())[:30]
        filename = notes_dir / f"{date}-audit-{slug}.md"
        filename.write_text(md, encoding="utf-8")
        console.print(f"\n[green]✓ Saved → {filename.relative_to(REPO_ROOT)}[/green]")


if __name__ == "__main__":
    main()
