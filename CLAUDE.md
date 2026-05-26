# Claude Code Harness Engineering — Research & Reference Repository

## Project

This repository is a structured research project documenting **how to configure Claude Code effectively for any software project**. It captures patterns, templates, and concrete examples for what we call "harness engineering" — the discipline of setting up Claude Code so that AI-assisted sessions are productive, consistent, safe, and low-friction.

The word "harness" is deliberate: just as a test harness wraps a system under test with scaffolding that controls how tests run, a Claude Code harness wraps a software project with configuration that controls how Claude sessions run.

## Repository Layout

```
/
├── CLAUDE.md                        ← you are here
├── .claude/
│   └── settings.json                ← Claude Code settings for this repo
├── research/
│   ├── 00-overview.md               ← What is harness engineering? Why it matters.
│   ├── 01-claude-md-guide.md        ← How to write great CLAUDE.md files
│   ├── 02-settings-guide.md         ← settings.json deep dive
│   ├── 03-hooks-guide.md            ← Hook patterns (SessionStart, Pre/PostToolUse)
│   ├── 04-mcp-guide.md              ← MCP server integration
│   └── 05-project-types.md          ← Per-project-type harness matrix
├── templates/
│   ├── CLAUDE.md.template           ← Fill-in-the-blank CLAUDE.md
│   ├── settings.json.template       ← Base settings.json with annotations
│   └── hooks/
│       ├── session-start.sh         ← SessionStart hook (installs deps, checks env)
│       └── pre-tool-use-safety.sh   ← PreToolUse safety guard + logger
└── examples/
    ├── web-app/CLAUDE.md            ← Next.js app example
    ├── api-service/CLAUDE.md        ← Python FastAPI example
    └── data-pipeline/CLAUDE.md      ← Data pipeline example
```

## Research Goals

1. **Identify** the minimal viable harness for each major project type (web app, API service, CLI, data pipeline, monorepo).
2. **Document** every configurable surface in Claude Code: CLAUDE.md conventions, settings.json schema, hook lifecycle, MCP integration.
3. **Produce** reusable templates that a developer can fill out in under 15 minutes for a new project.
4. **Capture anti-patterns** — what makes Claude sessions frustrating or unsafe — so they can be avoided by default.

## Stack

- Python 3.11+, pip
- `anthropic` SDK ≥ 0.52 — LLM calls in the research agent
- `rich` ≥ 13.7 — terminal UI
- No Node, no Docker required.

## Commands

```bash
pip install -r requirements-agent.txt   # one-time setup
export ANTHROPIC_API_KEY=sk-ant-...     # required for agent/
python agent/main.py                    # interactive stretch-loop REPL
python agent/parallel.py                # 5-topic parallel literature review
python agent/audit.py /path/to/proj     # score a project's harness (0–25)
python agent/audit.py . --save          # audit this repo, save to research/notes/
```

## Architecture

```
agent/
  main.py      ← REPL entry point; parallel: command; save suffix
  core.py      ← ResearchAgent: two-pass stretch loop (EXPLORE → STRETCH)
  parallel.py  ← AsyncAnthropic + asyncio.gather concurrent runner
  audit.py     ← five-layer harness scorer; point at any project dir
  prompts.py   ← SYSTEM_PROMPT, STRETCH_PROMPT, LITERATURE_PROMPT, DEFAULT_TOPICS
  tools.py     ← read_file, list_directory, search_repo, save_note + JSON schemas
research/      ← seven numbered guides (00-overview … 06-codebase-analysis)
  notes/       ← auto-saved research outputs (generated; prune freely)
templates/     ← fill-in-the-blank CLAUDE.md, settings.json, four hook scripts
examples/      ← web-app, api-service, data-pipeline, karpathy-minimal CLAUDE.md
.claude/
  commands/    ← project slash commands: /ultraplan /goal /agents /ultrareview
  hooks/       ← SessionStart, PreToolUse, PostToolUse, Stop scripts
```

## Conventions

- **Think Before Coding**: state assumptions explicitly; ask when uncertain; never silently guess
- **Simplicity First**: minimum code that solves the stated problem; no speculative abstractions
- **Surgical Changes**: touch only what the task requires; don't improve adjacent code
- **Goal-Driven Execution**: convert vague requests into verifiable success criteria before acting
- All research notes save to `research/notes/` via `agent.tools.save_note()`
- Never edit files under `examples/karpathy-minimal/` by hand — it is a reference copy

## Environment

`ANTHROPIC_API_KEY` — required to run `agent/`. Get from console.anthropic.com.
No other env vars are required for local use.
Copy `.env.example` to `.env` if you prefer not to `export` in the shell.

## Gotchas

- **No API key = silent error at first request**: `ANTHROPIC_API_KEY` unset raises `AuthenticationError` on the first call, not at import. Set it before running `agent/main.py`.
- **`research/notes/` grows fast**: `parallel.py` saves a dated `.md` per run. These are generated outputs — git-ignore or prune periodically.
- **`audit.py` on a research repo**: the scorer expects a software project. This repo will never hit 5/5 on Environment (no production `.env`) — that is expected.
- **Karpathy rules are a baseline, not a ceiling**: merge `examples/karpathy-minimal/CLAUDE.md` into any target project's CLAUDE.md, then add project-specific gotchas on top.
- **`search_repo` uses basic grep regex**: escape dots and special chars. For literal strings, pass `case_sensitive=True` with the exact pattern.
- **`parallel.py` fires all topics simultaneously**: with 10+ topics you may hit rate limits. Stay at ≤ 7 topics per run.

## How to Use This Repo

- **Starting fresh?** Jump to `research/00-overview.md` for the conceptual model.
- **Setting up a new project?** Go to `templates/` and copy the files you need, then fill in the placeholders.
- **Looking for a specific project type?** Check `research/05-project-types.md` for the decision matrix, then browse `examples/`.
- **Debugging hooks or permissions?** `research/03-hooks-guide.md` and `research/02-settings-guide.md` are your references.

## Key Concepts (Quick Reference)

| Term | Meaning |
|------|---------|
| **CLAUDE.md** | The project's "system prompt file" — read automatically by Claude Code at session start |
| **settings.json** | Machine-readable config: permissions, hooks, env vars, MCP servers |
| **Hook** | Shell script or command triggered by a lifecycle event (session start, before/after tool use) |
| **Permission** | An `allow` or `deny` rule that lets Claude run commands without prompting |
| **MCP server** | A subprocess exposing extra tools to Claude (e.g., GitHub API, database queries) |

## Contributing

This is a living research document. When you discover a useful pattern, add it to the relevant guide and update the templates. Follow the existing heading/structure conventions in each file.

## Status

- [x] Initial research structure created
- [ ] Settings.json schema fully validated against Claude Code source
- [ ] Hook examples tested on all three major OS types (macOS, Linux, WSL)
- [ ] MCP server examples verified against current MCP SDK versions
