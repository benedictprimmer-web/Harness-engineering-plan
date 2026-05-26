#!/usr/bin/env bash
# .claude/hooks/session-start.sh
# Runs once when a Claude Code session opens.
# Idempotent — safe to run many times a day.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# ── Session banner ────────────────────────────────────────────────────────────
echo "=== Claude Code Session ==="
echo "Branch : $(git branch --show-current 2>/dev/null || echo 'unknown')"
echo "Commit : $(git log -1 --pretty='%h %s' 2>/dev/null || echo 'no commits')"
echo "Date   : $(date '+%Y-%m-%d %H:%M')"
echo ""

# ── Node.js deps ──────────────────────────────────────────────────────────────
if [ -f "package.json" ]; then
  if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies..."
    if command -v pnpm &>/dev/null; then
      pnpm install --frozen-lockfile
    elif command -v yarn &>/dev/null; then
      yarn install --frozen-lockfile
    else
      npm ci
    fi
    echo "Node deps: installed"
  else
    echo "Node deps: OK"
  fi
fi

# ── Python deps ───────────────────────────────────────────────────────────────
if [ -f "pyproject.toml" ] && command -v uv &>/dev/null; then
  echo "Syncing Python deps (uv)..."
  uv sync --quiet
  echo "Python deps: OK"
elif [ -f "requirements.txt" ]; then
  echo "Installing Python deps..."
  pip install -q -r requirements.txt
  echo "Python deps: OK"
fi

# ── Environment variable checks ───────────────────────────────────────────────
# EDIT: list the env vars your project actually requires
REQUIRED_VARS=(
  # "DATABASE_URL"
  # "API_KEY"
  # "GITHUB_TOKEN"
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
  echo "Copy .env.example to .env and fill them in."
fi

# ── .env file check ───────────────────────────────────────────────────────────
ENV_FILE=""
[ -f ".env" ] && ENV_FILE=".env"
[ -f ".env.local" ] && ENV_FILE=".env.local"

if [ -f ".env.example" ] && [ -z "$ENV_FILE" ]; then
  echo ""
  echo "WARNING: No .env or .env.local found."
  echo "Run: cp .env.example .env  (then fill in your values)"
fi

# ── Docker / services check ───────────────────────────────────────────────────
# Uncomment if your project uses docker compose for local services
# if [ -f "docker-compose.yml" ] || [ -f "compose.yml" ]; then
#   if ! docker compose ps --quiet 2>/dev/null | grep -q .; then
#     echo ""
#     echo "NOTE: Docker services are not running."
#     echo "Start them with: docker compose up -d"
#   else
#     echo "Docker services: running"
#   fi
# fi

# ── Pending migrations check ──────────────────────────────────────────────────
# Uncomment for Alembic (Python):
# if command -v alembic &>/dev/null && [ -f "alembic.ini" ]; then
#   PENDING=$(alembic check 2>&1 || true)
#   if echo "$PENDING" | grep -q "head"; then
#     echo "NOTE: Database is up to date"
#   else
#     echo "WARNING: There may be pending database migrations. Run: alembic upgrade head"
#   fi
# fi

echo ""
echo "Session ready."
