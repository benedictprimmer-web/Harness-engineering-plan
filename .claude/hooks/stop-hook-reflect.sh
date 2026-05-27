#!/usr/bin/env bash
# .claude/hooks/stop-hook-reflect.sh — harness-engineering-plan
# Runs at session end via the Stop hook.
# Calls agent/reflect.py to propose harness improvements from this session.
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
REFLECT_PY="$REPO_ROOT/agent/reflect.py"

if [ ! -f "$REFLECT_PY" ]; then
  exit 0
fi

# 30s hard timeout; reflect.py has an internal 25s API limit and exits 0 always
timeout 30 python3 "$REFLECT_PY" "$REPO_ROOT" 2>&1 || true

exit 0
