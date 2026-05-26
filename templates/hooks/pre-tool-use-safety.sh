#!/usr/bin/env bash
# .claude/hooks/pre-tool-use-safety.sh
# Runs before every Bash tool call. Can block execution.
#
# To BLOCK a tool call: print JSON to stdout and exit non-zero.
#   {"decision": "block", "reason": "explanation shown to Claude"}
#
# To ALLOW: exit 0 (even with no output).
set -uo pipefail

# ── Read tool input from stdin ────────────────────────────────────────────────
TOOL_INPUT=$(cat)

# Parse with python3 (available on almost all systems)
TOOL_NAME=$(echo "$TOOL_INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_name', ''))
except:
    print('')
" 2>/dev/null || echo "")

COMMAND=$(echo "$TOOL_INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except:
    print('')
" 2>/dev/null || echo "")

# ── Audit log ─────────────────────────────────────────────────────────────────
LOG_FILE="${HOME}/.claude/tool-audit.log"
mkdir -p "$(dirname "$LOG_FILE")"
echo "[$(date -Is)] [$TOOL_NAME] $COMMAND" >> "$LOG_FILE" 2>/dev/null || true

# ── Safety rules ──────────────────────────────────────────────────────────────
# Only apply to Bash tool calls
[ "$TOOL_NAME" != "Bash" ] && exit 0

# Block: force push (catches --force and -f, in any position)
if echo "$COMMAND" | grep -qE 'git\s+push\b.*(--force|-f)\b'; then
  echo '{"decision": "block", "reason": "Force push is blocked by the project safety hook. If you genuinely need to force push, use --force-with-lease and get a human to confirm first."}'
  exit 1
fi

# Block: hard reset (extremely destructive)
if echo "$COMMAND" | grep -qE 'git\s+reset\s+--hard'; then
  echo '{"decision": "block", "reason": "git reset --hard is blocked. Use git stash or git restore for safer alternatives. If you need to reset, ask a human to run this manually."}'
  exit 1
fi

# Block: rm -rf on non-temp directories
if echo "$COMMAND" | grep -qE 'rm\s+-rf?\s+[^/]' || echo "$COMMAND" | grep -qP 'rm\s+-rf?\s+/(?!tmp|var/folders)'; then
  # Allow rm -rf on clearly temporary paths
  if ! echo "$COMMAND" | grep -qE 'rm\s+-rf?\s+(\.\/)?((node_modules|dist|build|\.next|__pycache__|\.pytest_cache|coverage|\.cache|tmp|temp)(/|$))'; then
    echo '{"decision": "block", "reason": "rm -rf on non-build directories is blocked. Specify files explicitly, or if you need to remove a directory, ask a human to confirm."}'
    exit 1
  fi
fi

# Block: drop production database
if echo "$COMMAND" | grep -qiE '(DROP\s+DATABASE|DROP\s+TABLE\s+IF\s+EXISTS|TRUNCATE\s+TABLE)\b'; then
  echo '{"decision": "block", "reason": "Destructive SQL DDL is blocked. Run database operations manually after human review."}'
  exit 1
fi

# Block: curl pipe to bash (remote code execution pattern)
if echo "$COMMAND" | grep -qE 'curl\b.*\|\s*(bash|sh|zsh|fish)\b'; then
  echo '{"decision": "block", "reason": "curl | bash is blocked for security. Download the script first, review it, then run it separately."}'
  exit 1
fi

# ── Project-specific rules ────────────────────────────────────────────────────
# UNCOMMENT and adapt:

# Block dbt full-refresh against production
# if echo "$COMMAND" | grep -qE 'dbt\s+run\b.*--full-refresh\b.*--target\s+prod\b'; then
#   echo '{"decision": "block", "reason": "dbt full-refresh against prod is blocked. Run against dev target first and get approval before touching prod."}'
#   exit 1
# fi

# Block pushing to main/master directly
# CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
# if echo "$COMMAND" | grep -qE 'git\s+push\b' && [ "$CURRENT_BRANCH" = "main" -o "$CURRENT_BRANCH" = "master" ]; then
#   echo '{"decision": "block", "reason": "Direct push to main/master is blocked. Create a branch and open a PR instead."}'
#   exit 1
# fi

exit 0
