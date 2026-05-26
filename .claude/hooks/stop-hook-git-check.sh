#!/usr/bin/env bash
# .claude/hooks/stop-hook-git-check.sh
# Runs when Claude finishes a response turn.
# Non-zero exit + output feeds back to Claude as context for next turn.
set -uo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

UNTRACKED=$(git status --porcelain 2>/dev/null | grep '^?' | wc -l | tr -d ' ')
MODIFIED=$(git status --porcelain 2>/dev/null | grep -v '^?' | grep -v '^$' | wc -l | tr -d ' ')

if [ "$UNTRACKED" -gt 0 ] || [ "$MODIFIED" -gt 0 ]; then
  echo "[stop-hook-git-check.sh]: There are uncommitted changes in the repository. Please commit and push these changes to the remote branch."
  echo "  Untracked files : $UNTRACKED"
  echo "  Modified files  : $MODIFIED"
  git status --short 2>/dev/null | head -20
  exit 1
fi

exit 0
