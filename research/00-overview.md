# Harness Engineering for Claude Code — Overview

## What Is It?

Harness engineering is the practice of configuring Claude Code so that AI-assisted sessions are **productive by default**, **safe by policy**, and **consistent across teammates and machines**.

Without a harness, every session starts with Claude asking permission for common operations, lacking context about the project's conventions, and making assumptions about tooling that may be wrong. With a well-engineered harness, the session starts knowing what the project is, what's allowed, what commands to run, and what guardrails exist.

## The Four Surfaces

```
┌─────────────────────────────────────────────────────────────┐
│                    A Claude Code Session                     │
│                                                             │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │  CLAUDE.md  │   │ settings.json│   │   MCP Servers   │  │
│  │             │   │              │   │                 │  │
│  │ Natural lang│   │ Permissions  │   │ Extra tools     │  │
│  │ context for │   │ Hooks        │   │ (GitHub, DB,    │  │
│  │ the model   │   │ Env vars     │   │  filesystem...) │  │
│  └─────────────┘   └──────────────┘   └─────────────────┘  │
│                            │                                │
│                   ┌────────┴────────┐                       │
│                   │     Hooks       │                       │
│                   │                 │                       │
│                   │ SessionStart    │                       │
│                   │ PreToolUse      │                       │
│                   │ PostToolUse     │                       │
│                   │ Stop            │                       │
│                   └─────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

| Surface | Format | Purpose | Audience |
|---------|--------|---------|----------|
| **CLAUDE.md** | Markdown | Project context, conventions, commands | The model |
| **settings.json** | JSON | Permissions, hooks, env vars, MCP | The runtime |
| **Hooks** | Shell scripts | Lifecycle automation | The OS |
| **MCP servers** | Processes | Extended tool capabilities | The model + runtime |

## Why It Matters

**Without a harness:**
- Claude asks "May I run npm install?" every time
- Claude doesn't know the project uses pnpm, not npm
- A junior mistake can `rm -rf` something important
- Different teammates get different behavior from the same codebase
- Session startup is manual (no auto-install, no env check)

**With a good harness:**
- Common operations run without prompting
- CLAUDE.md tells Claude the stack, conventions, and key files upfront
- Destructive commands are blocked or require confirmation
- Everyone on the team gets the same Claude behavior
- Sessions auto-provision themselves (install deps, check .env)

## Core Decisions for Every Project

### 1. Scope: project-level vs. user-level

Settings can live in:
- `.claude/settings.json` — project-specific, committed to git, shared with team
- `~/.claude/settings.json` — user-global, applies everywhere

Rule of thumb: **permissions and hooks go in the project file**. Personal preferences (theme, model) go in the user file.

### 2. Permission philosophy: allow-list vs. deny-list

You have two options:
- **Allow-list** (recommended): default deny, explicitly allow what Claude needs
- **Deny-list**: default allow, block specific dangerous commands

For most projects, a targeted allow-list is safer. Deny-lists are brittle — they miss variants (`rm` vs `/bin/rm`).

### 3. Hook strategy: automation vs. safety

Hooks serve two purposes that pull in opposite directions:
- **Automation hooks** (SessionStart, PostToolUse): make Claude more productive
- **Safety hooks** (PreToolUse, Stop): prevent mistakes

Design automation hooks to be fast and idempotent. Design safety hooks to be explicit about what they block and why.

### 4. CLAUDE.md depth vs. maintenance burden

More context = better Claude behavior, but CLAUDE.md that goes stale is worse than none. Focus on:
- Things Claude can't infer from the code (why decisions were made)
- Commands that aren't obvious (how to run tests, how to deploy)
- Conventions that differ from defaults (the project uses tabs, not spaces)

Skip describing what the code already makes obvious.

## The Harness Engineering Workflow

```
New project
    │
    ▼
1. Choose project type (web-app / api / cli / data-pipeline / monorepo)
    │
    ▼
2. Copy template CLAUDE.md → fill in {{PLACEHOLDERS}}
    │
    ▼
3. Copy template settings.json → add project-specific allow rules
    │
    ▼
4. Adapt session-start.sh → match your install commands
    │
    ▼
5. Run first Claude session → observe what Claude asks permission for
    │
    ▼
6. Add those to settings.json allow list
    │
    ▼
7. Commit .claude/ and CLAUDE.md alongside the codebase
    │
    ▼
Iterate as the project evolves
```

## What to Read Next

- **Writing CLAUDE.md** → `research/01-claude-md-guide.md`
- **settings.json schema** → `research/02-settings-guide.md`
- **Hook patterns** → `research/03-hooks-guide.md`
- **MCP integration** → `research/04-mcp-guide.md`
- **Per-project-type matrix** → `research/05-project-types.md`
