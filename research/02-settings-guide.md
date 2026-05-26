# settings.json Deep Dive

## File Locations & Precedence

Claude Code merges settings from multiple files. Lower in this list = higher precedence:

```
~/.claude/settings.json           # user-global (lowest precedence)
<project>/.claude/settings.json   # project-shared (committed to git)
<project>/.claude/settings.local.json  # project-local (gitignored, personal overrides)
```

Project files win over user-global. Local files win over shared. This lets you:
- Commit shared team settings to `.claude/settings.json`
- Let individuals override in `.claude/settings.local.json` (add to `.gitignore`)

## Full Schema Reference

```jsonc
{
  // Tool permissions — what Claude can run without asking
  "permissions": {
    "allow": [
      "Bash(command pattern)",   // allow specific bash patterns
      "Read(*)",                  // allow all file reads
      "Edit(src/**)",             // allow edits inside src/
      "Write(tmp/**)"             // allow writes inside tmp/
    ],
    "deny": [
      "Bash(rm -rf *)"            // block destructive commands
    ]
  },

  // Lifecycle hooks — shell commands triggered by events
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/session-start.sh"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",       // only trigger for Bash tool calls
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/pre-tool-use-safety.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/post-edit-format.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/stop-hook.sh"
          }
        ]
      }
    ]
  },

  // Environment variables injected into all Claude tool calls
  "env": {
    "NODE_ENV": "development",
    "PYTHONPATH": "./src"
  },

  // MCP server definitions
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  },

  // Model selection (optional — defaults to your subscription's best model)
  "model": "claude-opus-4-7",

  // Whether Claude can make network requests
  "enableAllProjectMcpServers": false
}
```

## Permission Patterns

### The Allow Rule Syntax

Allow rules use a `ToolName(pattern)` syntax:

```json
"Bash(git *)"              // any git command
"Bash(npm run *)"          // any npm script
"Bash(find . -name *)"     // find commands
"Read(*)"                  // all reads (recommended — reads are safe)
"Edit(src/**)"             // edits inside src/ (glob with **)
"Write(tmp/**)"            // writes inside tmp/
"Bash(*)"                  // ALL bash — use with caution
```

Patterns support `*` (single segment) and `**` (recursive). The match is against the full command string for Bash.

### Recommended Base Allow List (Most Projects)

```json
"permissions": {
  "allow": [
    "Read(*)",
    "Bash(git status)",
    "Bash(git diff *)",
    "Bash(git log *)",
    "Bash(git add *)",
    "Bash(git commit *)",
    "Bash(git push *)",
    "Bash(git pull *)",
    "Bash(git checkout *)",
    "Bash(git branch *)",
    "Bash(ls *)",
    "Bash(find . *)",
    "Bash(grep *)",
    "Bash(cat *)",
    "Bash(echo *)",
    "Bash(pwd)",
    "Bash(which *)",
    "Bash(mkdir -p *)"
  ]
}
```

### Adding Project-Specific Commands

Add only what your project actually needs:

```json
// Node.js project
"Bash(pnpm *)",
"Bash(npx *)",
"Bash(node *)"

// Python project
"Bash(python *)",
"Bash(pip *)",
"Bash(pytest *)",
"Bash(ruff *)",
"Bash(mypy *)"

// Docker project
"Bash(docker compose *)",
"Bash(docker build *)",
"Bash(docker ps)"
```

### Deny Rules

Deny rules block commands even if they match an allow rule. Use sparingly — they're brittle:

```json
"deny": [
  "Bash(git push --force *)",       // never force-push
  "Bash(git push * --force)",       // catch the flag in either position
  "Bash(rm -rf /)",                 // obvious
  "Bash(DROP TABLE *)",             // SQL injection guard
  "Bash(curl * | bash)"             // piped execution
]
```

**Warning**: Deny lists can't catch everything. They work on the literal command string. `rm -rf /tmp` would pass if the deny rule only checks `rm -rf /`. Safety hooks (PreToolUse) are more reliable for complex guards.

## Hook Event Reference

### SessionStart

- **When**: Once, when a new Claude Code session begins
- **Use for**: Installing dependencies, checking env vars, setting up tooling, printing a session banner
- **Input**: No special input
- **Exit code**: Non-zero causes session to warn but continues

### PreToolUse

- **When**: Before Claude calls any tool
- **Use for**: Safety checks, logging, blocking dangerous operations
- **Input**: JSON on stdin with `tool_name` and `tool_input` fields
- **Exit code**: Non-zero with specific format can BLOCK the tool call (see hooks guide)

### PostToolUse

- **When**: After Claude calls any tool (whether it succeeded or not)
- **Use for**: Auto-formatting after edits, logging, updating caches
- **Input**: JSON on stdin with `tool_name`, `tool_input`, and `tool_result` fields
- **Exit code**: Ignored (tool already ran)

### Stop

- **When**: When Claude finishes a response turn
- **Use for**: Committing checkpoints, posting notifications, running validation
- **Input**: No special input
- **Exit code**: Non-zero displays feedback to Claude for the next turn

### Hook Matchers

The `matcher` field in PreToolUse/PostToolUse filters which tools trigger the hook:

```json
{ "matcher": "Bash" }           // only Bash tool calls
{ "matcher": "Edit" }           // only Edit tool calls
{ "matcher": "Write" }          // only Write tool calls
{ "matcher": "Bash|Edit" }      // Bash or Edit (regex OR)
{}                               // no matcher = all tools
```

## Environment Variables

Variables in `env` are injected into the environment for all tool calls:

```json
"env": {
  "NODE_ENV": "development",
  "DATABASE_URL": "postgresql://localhost:5432/myapp_dev",
  "LOG_LEVEL": "debug"
}
```

You can reference existing env vars with `${VAR_NAME}` syntax:
```json
"env": {
  "GITHUB_TOKEN": "${GITHUB_TOKEN}"
}
```

**Never commit secrets directly.** Use `${VAR_NAME}` references and ensure the actual values are in the machine's environment or a local `.env` file.

## Per-Project-Type Recommended Defaults

### Web App (Node/Next.js)
```json
{
  "permissions": {
    "allow": [
      "Read(*)", "Bash(git *)", "Bash(pnpm *)", "Bash(npx *)",
      "Bash(ls *)", "Bash(find . *)", "Bash(grep *)",
      "Edit(src/**)", "Edit(app/**)", "Edit(components/**)",
      "Write(public/**)"
    ]
  },
  "env": { "NODE_ENV": "development" }
}
```

### API Service (Python)
```json
{
  "permissions": {
    "allow": [
      "Read(*)", "Bash(git *)", "Bash(python *)", "Bash(pip *)",
      "Bash(pytest *)", "Bash(ruff *)", "Bash(mypy *)",
      "Bash(ls *)", "Bash(find . *)", "Bash(grep *)",
      "Edit(src/**)", "Edit(tests/**)"
    ]
  },
  "env": { "PYTHONPATH": "./src", "ENV": "development" }
}
```

### Data Pipeline
```json
{
  "permissions": {
    "allow": [
      "Read(*)", "Bash(git *)", "Bash(python *)", "Bash(dbt *)",
      "Bash(airflow *)", "Bash(ls *)", "Bash(find . *)", "Bash(grep *)",
      "Edit(dbt/**)", "Edit(pipelines/**)", "Edit(tests/**)",
      "Write(data/scratch/**)"
    ],
    "deny": [
      "Bash(dbt run --full-refresh *)"
    ]
  }
}
```
