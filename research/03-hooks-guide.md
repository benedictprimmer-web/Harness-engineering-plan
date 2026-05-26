# Hook Patterns

## What Hooks Are

Hooks are shell commands (or scripts) that Claude Code executes at lifecycle events. They run as the user — not as Claude — which means they have full access to the system and can block, log, or automate anything around Claude's tool calls.

Hooks are defined in `settings.json` under the `hooks` key and reference scripts that live (by convention) in `.claude/hooks/`.

## The Hook Lifecycle

```
Session starts
      │
      ▼
[SessionStart hooks run]
      │
      ▼
Claude thinks → calls a tool
      │
      ▼
[PreToolUse hooks run]  ←── can BLOCK the tool call
      │
      ▼
Tool executes
      │
      ▼
[PostToolUse hooks run]
      │
      ▼
Claude responds to user
      │
      ▼
[Stop hooks run]  ←── output feeds back to Claude next turn
      │
      ▼
(repeat from "Claude thinks")
```

## SessionStart Hooks

### Purpose
Run once when the session opens. Use for:
- Installing/verifying dependencies
- Checking required env vars are set
- Starting background services (docker, local DB)
- Printing a session banner with useful info

### Key Principle: Idempotency
SessionStart runs every time a session opens — possibly many times a day. Every operation must be safe to repeat. Use guards like:
```bash
[ -d node_modules ] || pnpm install    # only install if missing
command -v docker &>/dev/null || echo "WARNING: docker not found"
```

### Example: Full SessionStart Script

```bash
#!/usr/bin/env bash
# .claude/hooks/session-start.sh
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "=== Claude Code Session Start ==="
echo "Branch: $(git branch --show-current)"
echo "Last commit: $(git log -1 --pretty='%h %s')"
echo ""

# --- Dependency checks ---
if [ -f "package.json" ]; then
  if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules/.package-lock.json" ]; then
    echo "Installing Node dependencies..."
    pnpm install --frozen-lockfile
  else
    echo "Node deps: OK"
  fi
fi

if [ -f "requirements.txt" ]; then
  echo "Checking Python deps..."
  pip install -q -r requirements.txt
fi

if [ -f "pyproject.toml" ] && command -v uv &>/dev/null; then
  uv sync --quiet
fi

# --- Environment variable checks ---
REQUIRED_VARS=(
  "DATABASE_URL"
  "API_KEY"
)

MISSING=0
for VAR in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!VAR:-}" ]; then
    echo "WARNING: Required env var $VAR is not set"
    MISSING=1
  fi
done

if [ "$MISSING" -eq 1 ]; then
  echo ""
  echo "Some env vars are missing. Copy .env.example to .env and fill them in."
fi

# --- Check for .env file ---
if [ -f ".env.example" ] && [ ! -f ".env" ] && [ ! -f ".env.local" ]; then
  echo "WARNING: No .env or .env.local found. Copy .env.example to get started."
fi

echo ""
echo "Session ready. Working directory: $REPO_ROOT"
```

### Minimal SessionStart (Node Project)

```bash
#!/usr/bin/env bash
cd "$(git rev-parse --show-toplevel)"
[ -d node_modules ] || pnpm install --frozen-lockfile
echo "Ready. Branch: $(git branch --show-current)"
```

## PreToolUse Hooks

### Purpose
Run before every tool call. Can **block** the call by exiting with a specific format. Use for:
- Blocking dangerous commands
- Logging all tool calls for audit
- Enforcing code review before git push

### Blocking a Tool Call

To block a tool call, the hook must:
1. Exit with a **non-zero** exit code
2. Print a JSON object to stdout: `{"decision": "block", "reason": "explanation"}`

```bash
#!/usr/bin/env bash
# .claude/hooks/pre-tool-use-safety.sh

# Read tool info from stdin
TOOL_INPUT=$(cat)
TOOL_NAME=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))")
COMMAND=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# Block force pushes to protected branches
if echo "$COMMAND" | grep -qE 'git push.*(--force|-f)'; then
  echo '{"decision": "block", "reason": "Force push is blocked. Use git push with --force-with-lease if you must, or ask a human to review first."}'
  exit 1
fi

# Block rm -rf on anything outside /tmp
if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+(?!/tmp)'; then
  echo '{"decision": "block", "reason": "rm -rf outside /tmp is blocked. Specify files individually or use trash instead."}'
  exit 1
fi

# Log all Bash commands to audit log
if [ "$TOOL_NAME" = "Bash" ]; then
  echo "[$(date -Is)] BASH: $COMMAND" >> /tmp/claude-audit.log
fi

exit 0
```

### Lightweight PreToolUse (Just Logging)

```bash
#!/usr/bin/env bash
TOOL_INPUT=$(cat)
TOOL_NAME=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name','unknown'))" 2>/dev/null)
echo "[$(date -Is)] $TOOL_NAME" >> ~/.claude/tool-audit.log
exit 0
```

## PostToolUse Hooks

### Purpose
Run after a tool call completes. **Cannot** block or undo the tool call. Use for:
- Auto-formatting files after edits
- Updating indexes or caches
- Triggering downstream actions (e.g., hot-reload)

### Example: Auto-format After Edit

```bash
#!/usr/bin/env bash
# .claude/hooks/post-edit-format.sh
# Runs after every Edit/Write tool call to format the modified file.

TOOL_INPUT=$(cat)
FILE_PATH=$(echo "$TOOL_INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null || echo "")

[ -z "$FILE_PATH" ] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

# Format based on file extension
case "$FILE_PATH" in
  *.ts|*.tsx|*.js|*.jsx|*.json|*.css|*.md)
    command -v prettier &>/dev/null && prettier --write --log-level=silent "$FILE_PATH"
    ;;
  *.py)
    command -v ruff &>/dev/null && ruff format --quiet "$FILE_PATH"
    ;;
esac

exit 0
```

## Stop Hooks

### Purpose
Run when Claude finishes a response turn. Output is fed back to Claude as context for the next turn. Use for:
- Validating the state of the repo after Claude's work
- Checking that tests still pass
- Committing auto-checkpoints
- Sending notifications

### Example: Uncommitted Changes Warning

```bash
#!/usr/bin/env bash
# .claude/hooks/stop-hook-git-check.sh
# Warns Claude if it left uncommitted changes behind.

cd "$(git rev-parse --show-toplevel)" 2>/dev/null || exit 0

UNTRACKED=$(git status --porcelain 2>/dev/null | grep '^?' | wc -l | tr -d ' ')
MODIFIED=$(git status --porcelain 2>/dev/null | grep -v '^?' | wc -l | tr -d ' ')

if [ "$UNTRACKED" -gt 0 ] || [ "$MODIFIED" -gt 0 ]; then
  echo "[stop-hook]: There are uncommitted changes in the repository."
  echo "Untracked files: $UNTRACKED, Modified files: $MODIFIED"
  echo "Please commit and push these changes to the remote branch."
  exit 1
fi
```

### Example: Run Tests on Stop

```bash
#!/usr/bin/env bash
# Only run if source files were recently changed
RECENT_CHANGES=$(git diff --name-only HEAD 2>/dev/null | grep -E '\.(ts|tsx|py)$' | wc -l)

if [ "$RECENT_CHANGES" -gt 0 ]; then
  echo "Running tests on changed files..."
  if ! pnpm test --run 2>&1 | tail -5; then
    echo "Tests failed after Claude's changes. Review before committing."
    exit 1
  fi
fi
```

## wiring Hooks in settings.json

```json
{
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
        "matcher": "Bash",
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
        "matcher": "Edit|Write",
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
            "command": "bash .claude/hooks/stop-hook-git-check.sh"
          }
        ]
      }
    ]
  }
}
```

## Hook Best Practices

1. **Always `cd` to repo root first** — hooks may run from unexpected working directories
   ```bash
   cd "$(git rev-parse --show-toplevel)"
   ```

2. **Fail fast, fail clearly** — if your hook errors out, the error message is what Claude sees
   ```bash
   set -euo pipefail
   ```

3. **Guard external tools** — don't assume formatters or CLIs are installed
   ```bash
   command -v prettier &>/dev/null && prettier --write "$FILE"
   ```

4. **Keep hooks fast** — slow SessionStart hooks make sessions feel sluggish. Target < 5s total.

5. **Log to a file, not stdout** — stdout in PreToolUse/PostToolUse has special semantics. Use stderr or a log file for debug output.
   ```bash
   echo "debug info" >&2          # goes to Claude's debug log
   echo "debug info" >> /tmp/hook.log  # goes to a file
   ```

6. **Use `|| true` for optional operations** — if a step isn't critical, don't let it kill the hook
   ```bash
   pnpm typecheck || true   # warn but don't block
   ```
