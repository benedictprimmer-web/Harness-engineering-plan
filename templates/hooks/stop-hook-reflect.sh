#!/usr/bin/env bash
# templates/hooks/stop-hook-reflect.sh
# Installed by agent/install.py to .claude/hooks/stop-hook-reflect.sh in target projects.
# Calls reflect.py at session end to propose harness improvements.
#
# reflect.py is installed to .claude/scripts/reflect.py by agent/install.py.
# The script always exits 0 and never blocks the session.
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
REFLECT_PY="$REPO_ROOT/.claude/scripts/reflect.py"

if [ ! -f "$REFLECT_PY" ]; then
  # Not installed — skip silently
  exit 0
fi

# 30s hard timeout — reflect.py also has an internal 25s API timeout
timeout 30 python3 "$REFLECT_PY" "$REPO_ROOT" 2>&1 || true

exit 0
