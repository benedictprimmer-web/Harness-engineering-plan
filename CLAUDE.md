# Claude Code Harness Engineering — Research & Reference Repository

## What This Repo Is

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
