#!/usr/bin/env python3
"""
harness-install — one-command Claude Code harness setup for any project.

Usage:
    python agent/install.py /path/to/project
    python agent/install.py /path/to/project --dry-run
    python agent/install.py /path/to/project --force
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
HOOKS_TEMPLATE = REPO_ROOT / "templates" / "hooks"


# ── Project detection ──────────────────────────────────────────────────────────

@dataclass
class ProjectInfo:
    name: str = ""
    language: str = "Unknown"
    runtime: str = ""
    framework: str = ""
    install_cmd: str = ""
    dev_cmd: str = ""
    build_cmd: str = ""
    test_cmd: str = ""
    test_watch_cmd: str = ""
    lint_cmd: str = ""
    lint_fix_cmd: str = ""
    extra_allows: list = field(default_factory=list)
    deps: list = field(default_factory=list)


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def _read_python_deps(root: Path) -> list[str]:
    import re
    deps: list[str] = []
    for fname in ["requirements.txt", "requirements-dev.txt", "requirements-base.txt"]:
        p = root / fname
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip().lower()
                if line and not line.startswith(("#", "-")):
                    pkg = re.split(r"[>=<![\s]", line)[0].strip()
                    if pkg:
                        deps.append(pkg)
    if (root / "pyproject.toml").exists():
        content = (root / "pyproject.toml").read_text().lower()
        for m in re.finditer(r'"([a-z][a-z0-9_-]*)\s*[>=<!\[]', content):
            deps.append(m.group(1))
    return list(set(deps))


def detect_project(root: Path) -> ProjectInfo:
    info = ProjectInfo(name=root.name)

    # ── Python ────────────────────────────────────────────────────────────
    if any((root / f).exists() for f in
           ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile"]):
        info.language = "Python"
        info.runtime = _run(["python3", "--version"]) or "Python 3.x"
        info.extra_allows = [
            "Bash(python *)", "Bash(python3 *)",
            "Bash(pip *)", "Bash(pip3 *)",
            "Bash(pytest *)", "Bash(ruff *)", "Bash(mypy *)",
        ]
        deps = _read_python_deps(root)
        info.deps = deps

        if (root / "pyproject.toml").exists() and "uv" in (root / "pyproject.toml").read_text():
            info.install_cmd = "uv sync"
            info.extra_allows.append("Bash(uv *)")
        else:
            info.install_cmd = "pip install -r requirements.txt"

        info.test_cmd = "pytest"
        info.test_watch_cmd = "ptw"
        info.lint_cmd = "ruff check . && mypy ."
        info.lint_fix_cmd = "ruff check --fix ."

        if any(d in deps for d in ["fastapi", "uvicorn"]):
            info.framework = "FastAPI"
            info.dev_cmd = "uvicorn main:app --reload"
        elif "django" in deps:
            info.framework = "Django"
            info.dev_cmd = "python manage.py runserver"
            info.build_cmd = "python manage.py collectstatic --noinput"
        elif "flask" in deps:
            info.framework = "Flask"
            info.dev_cmd = "flask run --debug"
        elif any(d in deps for d in ["pandas", "polars", "dbt-core", "airflow", "prefect", "dagster"]):
            info.framework = "Data Pipeline"
            info.dev_cmd = "python -m {{ENTRY_POINT}}"
        else:
            info.framework = "Python"
            info.dev_cmd = "python -m {{ENTRY_POINT}}"

        if not info.build_cmd:
            info.build_cmd = "python -m build"
        return info

    # ── Node / TypeScript ──────────────────────────────────────────────────
    if (root / "package.json").exists():
        try:
            pkg = json.loads((root / "package.json").read_text())
        except Exception:
            pkg = {}

        info.language = "TypeScript" if (root / "tsconfig.json").exists() else "JavaScript"
        info.runtime = f"Node {_run(['node', '--version']) or 'LTS'}"

        deps_all = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        info.deps = list(deps_all.keys())
        scripts = pkg.get("scripts", {})

        pm = "pnpm" if (root / "pnpm-lock.yaml").exists() else \
             "yarn" if (root / "yarn.lock").exists() else "npm"

        info.install_cmd = f"{pm} install"
        info.dev_cmd = f"{pm} run dev" if "dev" in scripts else f"{pm} start"
        info.build_cmd = f"{pm} run build" if "build" in scripts else ""
        info.test_cmd = f"{pm} test"
        info.test_watch_cmd = f"{pm} run test:watch" if "test:watch" in scripts else ""
        info.lint_cmd = f"{pm} run lint" if "lint" in scripts else ""
        info.lint_fix_cmd = f"{pm} run lint:fix" if "lint:fix" in scripts else ""
        info.extra_allows = [f"Bash({pm} *)", "Bash(npx *)", "Bash(node *)"]

        if "next" in deps_all:
            info.framework = "Next.js"
        elif "react" in deps_all:
            info.framework = "React"
        elif "vue" in deps_all:
            info.framework = "Vue"
        elif "svelte" in deps_all:
            info.framework = "Svelte"
        elif "express" in deps_all:
            info.framework = "Express"
        elif "fastify" in deps_all:
            info.framework = "Fastify"
        else:
            info.framework = info.language
        return info

    # ── Go ────────────────────────────────────────────────────────────────
    if (root / "go.mod").exists():
        info.language = "Go"
        info.runtime = _run(["go", "version"]) or "Go 1.x"
        info.framework = "Go"
        info.install_cmd = "go mod tidy"
        info.dev_cmd = "go run ."
        info.build_cmd = "go build ./..."
        info.test_cmd = "go test ./..."
        info.lint_cmd = "golangci-lint run"
        info.lint_fix_cmd = "gofmt -w ."
        info.extra_allows = ["Bash(go *)", "Bash(golangci-lint *)"]
        return info

    # ── Rust ──────────────────────────────────────────────────────────────
    if (root / "Cargo.toml").exists():
        info.language = "Rust"
        info.runtime = _run(["rustc", "--version"]) or "Rust stable"
        info.framework = "Rust"
        info.install_cmd = "cargo fetch"
        info.dev_cmd = "cargo run"
        info.build_cmd = "cargo build --release"
        info.test_cmd = "cargo test"
        info.lint_cmd = "cargo clippy"
        info.lint_fix_cmd = "cargo fix --allow-dirty"
        info.extra_allows = ["Bash(cargo *)"]
        return info

    # ── Ruby ──────────────────────────────────────────────────────────────
    if (root / "Gemfile").exists():
        info.language = "Ruby"
        info.runtime = _run(["ruby", "--version"]) or "Ruby 3.x"
        gems = (root / "Gemfile").read_text()
        info.framework = "Rails" if "rails" in gems else "Ruby"
        info.install_cmd = "bundle install"
        info.dev_cmd = "rails server" if "rails" in gems else "ruby main.rb"
        info.test_cmd = "bundle exec rspec" if "rspec" in gems else "bundle exec rake test"
        info.lint_cmd = "bundle exec rubocop"
        info.lint_fix_cmd = "bundle exec rubocop -A"
        info.extra_allows = ["Bash(bundle *)", "Bash(rails *)", "Bash(rake *)"]
        return info

    # ── Java / Kotlin ─────────────────────────────────────────────────────
    if (root / "pom.xml").exists():
        info.language = "Java"
        info.runtime = _run(["java", "--version"]) or "Java 21+"
        info.framework = "Maven"
        info.install_cmd = "mvn install -DskipTests"
        info.build_cmd = "mvn package"
        info.test_cmd = "mvn test"
        info.lint_cmd = "mvn checkstyle:check"
        info.extra_allows = ["Bash(mvn *)"]
        return info

    if any((root / f).exists() for f in ["build.gradle", "build.gradle.kts"]):
        info.language = "Java/Kotlin"
        info.runtime = _run(["java", "--version"]) or "Java 21+"
        info.framework = "Gradle"
        info.install_cmd = "./gradlew dependencies"
        info.build_cmd = "./gradlew build"
        info.test_cmd = "./gradlew test"
        info.lint_cmd = "./gradlew check"
        info.extra_allows = ["Bash(./gradlew *)", "Bash(gradle *)"]
        return info

    # ── Generic fallback ──────────────────────────────────────────────────
    info.install_cmd = "# TODO: add install command"
    info.dev_cmd = "# TODO: add dev command"
    info.test_cmd = "# TODO: add test command"
    info.lint_cmd = "# TODO: add lint command"
    return info


# ── Content generators ─────────────────────────────────────────────────────────

def generate_claude_md(info: ProjectInfo) -> str:
    fw = info.framework
    lang = info.language
    stack_line = f"{fw} ({lang})" if fw and fw != lang else lang
    test_watch = info.test_watch_cmd or f"# {info.test_cmd} --watch"
    build = info.build_cmd or "# no separate build step"
    lint_fix = info.lint_fix_cmd or f"# see {info.lint_cmd}"

    return f"""\
# {info.name}

<!-- Generated by harness-install. Fill in the {{{{PLACEHOLDERS}}}} then delete these comments. -->

## Project

{{{{PROJECT_DESCRIPTION}}}}
<!-- 2–4 sentences: what this does, who uses it, what problem it solves. -->

## Stack

- **Runtime**: {info.runtime}
- **Framework**: {stack_line}
- **Testing**: {{{{TEST_FRAMEWORK}}}}
- **Linting**: {{{{LINTER}}}}
<!-- Add: UI library, ORM, state manager, task queue, etc. Include versions. -->

## Commands

```bash
{info.install_cmd}      # install dependencies
{info.dev_cmd}          # start dev server / run locally
{build}                 # production build
{info.test_cmd}         # run all tests
{test_watch}            # tests in watch mode
{info.lint_cmd}         # lint + type check
{lint_fix}              # auto-fix lint issues
```
<!-- Add project-specific commands: migrate, seed, generate:api, storybook, etc. -->

## Architecture

```
{{{{DIR}}}}/    ← {{{{what it contains}}}}
{{{{DIR}}}}/    ← {{{{what it contains}}}}
{{{{DIR}}}}/    ← {{{{what it contains}}}}
```
<!-- Focus on non-obvious structure. Flag auto-generated directories. -->

## Conventions

- **Think Before Coding**: state assumptions, ask when uncertain, never silently guess
- **Simplicity First**: minimum code that solves the problem; no speculative abstractions
- **Surgical Changes**: touch only what the task requires; don't improve adjacent code
- **Goal-Driven Execution**: convert vague requests into verifiable success criteria first
- **{{{{CONVENTION}}}}**: {{{{detail}}}}
<!-- Add: import style, naming rules, component patterns, API conventions, etc. -->

## Environment

Copy `.env.example` to `.env` and fill in:
- `{{{{ENV_VAR}}}}` — {{{{what it is and where to get it}}}}
<!-- Note which vars are optional vs. required for local dev. -->

## Gotchas

- **{{{{GOTCHA_1}}}}**: {{{{detail}}}}
- **{{{{GOTCHA_2}}}}**: {{{{detail}}}}
<!-- Highest-value section: wrong package manager, port conflicts, auto-generated
     files not to edit, known flaky tests, order-dependent steps. -->
"""


def generate_settings_json(info: ProjectInfo) -> str:
    base_allows = [
        "Bash(git *)",
        "Bash(ls *)",
        "Bash(find *)",
        "Bash(grep *)",
        "Bash(cat *)",
        "Bash(mkdir -p *)",
        "Bash(cp *)",
        "Bash(chmod *)",
    ]
    settings = {
        "permissions": {
            "allow": base_allows + info.extra_allows,
            "deny": [
                "Bash(git push --force*)",
                "Bash(git push -f *)",
                "Bash(git reset --hard*)",
                "Bash(rm -rf /*)",
                "Bash(curl * | bash)",
                "Bash(wget * | bash)",
            ],
        },
        "hooks": {
            "SessionStart": [{"command": ".claude/hooks/session-start.sh"}],
            "PreToolUse": [{"matcher": "Bash", "command": ".claude/hooks/pre-tool-use-safety.sh"}],
            "PostToolUse": [{"matcher": "Edit|Write|Create", "command": ".claude/hooks/post-edit-format.sh"}],
            "Stop": [{"command": ".claude/hooks/stop-hook-git-check.sh"}],
        },
    }
    return json.dumps(settings, indent=2) + "\n"


def generate_env_example(info: ProjectInfo) -> str:
    lines = [
        "# Required environment variables",
        "# Copy this file to .env and fill in the values",
        "",
        "# DATABASE_URL=postgresql://localhost/mydb",
    ]
    if info.language == "Python":
        lines.append("# ANTHROPIC_API_KEY=sk-ant-...")
    if info.framework in ("Next.js", "React"):
        lines += ["# NEXTAUTH_SECRET=...", "# NEXTAUTH_URL=http://localhost:3000"]
    lines.append("# API_KEY=...")
    return "\n".join(lines) + "\n"


# ── Installation ───────────────────────────────────────────────────────────────

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def install(root: Path, dry_run: bool = False, force: bool = False) -> None:
    print(f"\nHarness Install")
    print(f"Target : {root}")
    print(f"Mode   : {'DRY RUN — no files written' if dry_run else 'INSTALL'}")
    print()

    print("Detecting project…")
    info = detect_project(root)
    print(f"  Language  : {info.language}")
    print(f"  Framework : {info.framework}")
    print(f"  Runtime   : {info.runtime or 'unknown'}")
    print()

    # Collect actions: (label, dst_path, write_fn)
    actions: list[tuple[str, Path, callable]] = []

    def maybe(label: str, dst: Path, write_fn):
        if dst.exists() and not force:
            print(f"  skip  {dst.relative_to(root)}  (already exists — use --force to overwrite)")
        else:
            tag = " (overwrite)" if dst.exists() else ""
            actions.append((f"{label}{tag}", dst, write_fn))

    # CLAUDE.md
    claude_md_content = generate_claude_md(info)
    maybe("CLAUDE.md", root / "CLAUDE.md", lambda: _write(root / "CLAUDE.md", claude_md_content))

    # .env.example
    env_content = generate_env_example(info)
    maybe(".env.example", root / ".env.example", lambda: _write(root / ".env.example", env_content))

    # .claude/settings.json
    settings_content = generate_settings_json(info)
    maybe(
        ".claude/settings.json",
        root / ".claude" / "settings.json",
        lambda: _write(root / ".claude" / "settings.json", settings_content),
    )

    # Hook scripts
    hook_names = [
        "session-start.sh",
        "pre-tool-use-safety.sh",
        "post-edit-format.sh",
        "stop-hook-git-check.sh",
    ]
    for hook_name in hook_names:
        src = HOOKS_TEMPLATE / hook_name
        if not src.exists():
            print(f"  WARN  template missing: {src.relative_to(REPO_ROOT)}")
            continue
        dst = root / ".claude" / "hooks" / hook_name
        _src = src  # capture for closure

        def _install_hook(s=_src, d=dst):
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
            os.chmod(d, 0o755)

        maybe(f".claude/hooks/{hook_name}", dst, _install_hook)

    # .claude/commands/ (create directory so slash commands can be added)
    commands_dir = root / ".claude" / "commands"
    if not commands_dir.exists():
        actions.append((
            ".claude/commands/ (directory)",
            commands_dir,
            lambda: commands_dir.mkdir(parents=True, exist_ok=True),
        ))

    # ── Execute ────────────────────────────────────────────────────────────
    if not actions:
        print("Nothing to install — all files already exist.")
        print(f"Re-run with --force to overwrite, or run:")
        print(f"  python agent/audit.py {root}")
        return

    print("Installing:")
    for label, _dst, write_fn in actions:
        if dry_run:
            print(f"  [dry]  {label}")
        else:
            write_fn()
            print(f"  ✓  {label}")

    if dry_run:
        print("\nDry run complete. Re-run without --dry-run to apply.")
        return

    # ── Run audit ──────────────────────────────────────────────────────────
    print()
    audit_py = Path(__file__).parent / "audit.py"
    if audit_py.exists():
        print("Harness audit:")
        subprocess.run([sys.executable, str(audit_py), str(root)])

    print()
    print("Next steps:")
    print(f"  1. Open {root}/CLAUDE.md and fill in the {{{{PLACEHOLDERS}}}}")
    print("  2. Edit .claude/hooks/session-start.sh — add your required env vars")
    print("  3. Add project-specific deny rules to .claude/settings.json if needed")
    print(f"  4. Re-run `python agent/audit.py {root}` to check your score")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install a Claude Code harness into any project directory."
    )
    parser.add_argument("project", nargs="?", default=".", help="Path to target project (default: .)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing files")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    root = Path(args.project).expanduser().resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory")
        sys.exit(1)

    install(root, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
