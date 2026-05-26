# Harness Matrix by Project Type

## Decision Tree: Which Harness Do I Need?

```
What kind of project is it?
│
├── Has a UI / runs in a browser?
│   ├── Full-stack? → Monorepo harness
│   └── Frontend only? → Web App harness
│
├── Serves HTTP requests?
│   ├── Python? → API Service (Python) harness
│   └── Node.js? → API Service (Node) harness
│
├── Transforms data / runs pipelines?
│   ├── Uses dbt? → Data Pipeline harness
│   └── Pure Python? → Data Pipeline harness
│
├── A command-line tool?
│   └── CLI Tool harness
│
└── Multiple services in one repo?
    └── Monorepo harness
```

## Harness Matrix

| Component | Web App | API Service | Data Pipeline | CLI Tool | Monorepo |
|-----------|---------|-------------|---------------|----------|----------|
| **CLAUDE.md sections** | | | | | |
| Project identity | ✓ | ✓ | ✓ | ✓ | ✓ |
| Stack + versions | ✓ | ✓ | ✓ | ✓ | ✓ per package |
| Commands (dev/test/build) | ✓ | ✓ | ✓ | ✓ | ✓ root + per-pkg |
| Architecture / key files | ✓ | ✓ | ✓ | ✓ | ✓ |
| Environment setup | ✓ | ✓ | ✓ | optional | ✓ |
| Gotchas | ✓ | ✓ | ✓ | ✓ | ✓ |
| Deployment info | optional | ✓ | ✓ | optional | ✓ |
| Data schema / models | — | ✓ | ✓ | — | varies |
| **Settings** | | | | | |
| Read(*) | ✓ | ✓ | ✓ | ✓ | ✓ |
| git commands | ✓ | ✓ | ✓ | ✓ | ✓ |
| npm/pnpm | ✓ | maybe | — | maybe | ✓ |
| python/pip/pytest | — | ✓ | ✓ | maybe | varies |
| docker compose | optional | ✓ | ✓ | — | optional |
| dbt | — | — | ✓ | — | — |
| **SessionStart hook** | | | | | |
| Install deps | ✓ | ✓ | ✓ | ✓ | ✓ |
| Check env vars | ✓ | ✓ | ✓ | — | ✓ |
| Start DB/services | — | ✓ | ✓ | — | ✓ |
| **PreToolUse hook** | | | | | |
| Block force push | ✓ | ✓ | ✓ | ✓ | ✓ |
| Block prod DB queries | — | ✓ | ✓ | — | varies |
| Audit log | optional | ✓ | ✓ | — | optional |
| **PostToolUse hook** | | | | | |
| Auto-format | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Stop hook** | | | | | |
| Uncommitted check | ✓ | ✓ | ✓ | ✓ | ✓ |
| Run tests | optional | optional | optional | optional | optional |
| **MCP servers** | | | | | |
| GitHub MCP | ✓ | ✓ | ✓ | ✓ | ✓ |
| DB MCP | — | ✓ | ✓ | — | varies |
| Filesystem MCP | — | — | ✓ (data dir) | — | — |
| Custom MCP | — | optional | optional | — | optional |

## Per-Type Detail

---

### Web App

**Profile**: Next.js, React, Vue, Svelte. Frontend-only or BFF pattern.

**Key CLAUDE.md additions**:
- Component library and design system (shadcn, MUI, etc.)
- State management approach (Zustand, Redux, React Query)
- Routing conventions (App Router vs Pages Router)
- Which files are auto-generated (API clients, icon sets)
- Storybook if present

**Key settings additions**:
```json
"Bash(pnpm *)", "Bash(npx *)",
"Edit(app/**)", "Edit(src/**)", "Edit(components/**)",
"Write(public/generated/**)"
```

**SessionStart extras**: check for `.env.local`, note the dev server URL.

**Watch out for**: build cache invalidation, route group naming conventions, server vs. client component boundaries.

---

### API Service (Python)

**Profile**: FastAPI, Django, Flask. May have background workers, DB migrations.

**Key CLAUDE.md additions**:
- Database engine and migration tool (Alembic, Django migrations)
- Auth pattern (JWT, session, OAuth)
- API schema location (OpenAPI spec, Pydantic models)
- Background task queue (Celery, ARQ, etc.)
- Which endpoints are internal vs. public

**Key settings additions**:
```json
"Bash(python *)", "Bash(pip *)", "Bash(pytest *)",
"Bash(alembic *)", "Bash(ruff *)", "Bash(mypy *)",
"Bash(uvicorn *)", "Bash(gunicorn *)"
```

**PreToolUse extras**: block direct SQL against production, require confirmation for migrations.

**SessionStart extras**: activate virtualenv, run `alembic check` to show pending migrations.

---

### Data Pipeline

**Profile**: dbt, Airflow, Prefect, Dagster, or custom Python ETL.

**Key CLAUDE.md additions**:
- Data warehouse / database topology (which DBs are prod vs. dev vs. local)
- DAG naming conventions
- How to run a partial pipeline vs. full refresh
- Source data locations
- Idempotency guarantees (or lack thereof)

**Key settings additions**:
```json
"Bash(dbt *)", "Bash(airflow *)", "Bash(prefect *)",
"Bash(python *)", "Bash(pytest *)"
```

**Deny list** (critical):
```json
"deny": [
  "Bash(dbt run --full-refresh --target prod *)",
  "Bash(airflow dags trigger * --conf *prod*)"
]
```

**PreToolUse extras**: detect and block any command targeting prod target/environment.

---

### CLI Tool

**Profile**: A Python or Node tool distributed via pip/npm. No server, no DB.

**Key CLAUDE.md additions**:
- How to run the CLI locally during development
- How the CLI is packaged and published
- Where integration tests live and how to run them
- Versioning scheme

**Key settings additions**:
```json
"Bash(python -m mypackage *)",
"Bash(pip install -e .)",
"Bash(pytest *)", "Bash(tox *)"
```

**Minimal harness**: CLI tools need less harness. Focus on CLAUDE.md and basic permissions. Heavy hooks are overkill.

---

### Monorepo

**Profile**: Multiple packages/services in one repo (Turborepo, Nx, Lerna, or manual).

**Structure pattern**:
```
/CLAUDE.md             ← org-wide conventions, how the monorepo works
/packages/
  web-app/CLAUDE.md    ← web app specifics
  api/CLAUDE.md        ← API specifics
  shared/CLAUDE.md     ← shared library specifics
/.claude/settings.json ← repo-wide permissions
```

**Root CLAUDE.md extras**:
- How packages relate to each other (dependency graph)
- How to run all tests vs. a single package
- Shared tooling: lint, format, CI
- How to add a new package
- Which packages are published vs. internal

**Key settings additions**:
```json
"Bash(turbo *)", "Bash(nx *)",
"Bash(pnpm -r *)",           // recursive pnpm
"Bash(pnpm --filter * *)"    // filtered package commands
```

**Monorepo gotcha**: Claude navigating into subdirectories will pick up that package's CLAUDE.md. Make sure subdirectory CLAUDE.md files don't contradict the root — they should extend it.
