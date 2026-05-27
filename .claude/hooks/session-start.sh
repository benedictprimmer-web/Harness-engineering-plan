#!/usr/bin/env bash
# .claude/hooks/session-start.sh — harness-engineering-plan
# Runs once when a Claude Code session opens.
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# ── Session banner ─────────────────────────────────────────────────────────────
echo "=== Claude Code Session — Harness Engineering Plan ==="
echo "Branch : $(git branch --show-current 2>/dev/null || echo 'unknown')"
echo "Commit : $(git log -1 --pretty='%h %s' 2>/dev/null || echo 'no commits')"
echo "Date   : $(date '+%Y-%m-%d %H:%M')"
echo ""

# ── Python agent deps ──────────────────────────────────────────────────────────
if python3 -c "import anthropic, rich" 2>/dev/null; then
  echo "Agent deps: OK (anthropic + rich)"
else
  echo "WARNING: Agent dependencies not installed."
  echo "  Run: pip install -r requirements-agent.txt"
fi

# ── Required env vars ─────────────────────────────────────────────────────────
REQUIRED_VARS=(
  "ANTHROPIC_API_KEY"
)

MISSING_VARS=()
for VAR in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!VAR:-}" ]; then
    MISSING_VARS+=("$VAR")
  fi
done

if [ "${#MISSING_VARS[@]}" -gt 0 ]; then
  echo ""
  echo "WARNING: Missing required environment variables:"
  for VAR in "${MISSING_VARS[@]}"; do
    echo "  - $VAR"
  done
  echo "  Set it: export ANTHROPIC_API_KEY=sk-ant-..."
  echo "  Or:     cp .env.example .env  (then fill in)"
fi

# ── Research notes count ───────────────────────────────────────────────────────
NOTES_DIR="$REPO_ROOT/research/notes"
if [ -d "$NOTES_DIR" ]; then
  NOTE_COUNT=$(find "$NOTES_DIR" -name "*.md" | wc -l | tr -d ' ')
  echo ""
  echo "Research notes: $NOTE_COUNT file(s) in research/notes/"
fi

# ── Pending learnings banner ───────────────────────────────────────────────────
LEARNINGS="$REPO_ROOT/.claude/session-learnings.md"
if [ -f "$LEARNINGS" ]; then
  SUGGESTION_COUNT=$(grep -c "^##\|^-" "$LEARNINGS" 2>/dev/null || echo "?")
  echo ""
  echo "⚡ Pending learnings: .claude/session-learnings.md exists from a previous session."
  echo "   Review and apply suggestions, then delete the file."
  echo "   View: cat .claude/session-learnings.md"
fi

echo ""
echo "Session ready. Use /ultraplan, /goal, /agents, /ultrareview, /task."
