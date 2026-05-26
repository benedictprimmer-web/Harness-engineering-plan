#!/usr/bin/env bash
# .claude/hooks/post-edit-format.sh
# Runs after every Edit or Write tool call.
# Auto-formats the modified file using the project's formatter.
set -uo pipefail

TOOL_INPUT=$(cat)

FILE_PATH=$(echo "$TOOL_INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except:
    print('')
" 2>/dev/null || echo "")

# Nothing to do if no file path
[ -z "$FILE_PATH" ] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

# Format based on file extension
case "$FILE_PATH" in
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.json|*.css|*.scss|*.md|*.mdx|*.yaml|*.yml)
    if command -v prettier &>/dev/null; then
      prettier --write --log-level=silent "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
  *.py)
    if command -v ruff &>/dev/null; then
      ruff format --quiet "$FILE_PATH" 2>/dev/null || true
    elif command -v black &>/dev/null; then
      black --quiet "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
  *.go)
    if command -v gofmt &>/dev/null; then
      gofmt -w "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
  *.rs)
    if command -v rustfmt &>/dev/null; then
      rustfmt "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
  *.sh|*.bash)
    if command -v shfmt &>/dev/null; then
      shfmt -w "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
esac

exit 0
