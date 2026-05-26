# Acme Platform (Monorepo)

## Project

Internal platform monorepo for Acme Corp — contains the customer-facing web app (`apps/web`), the API backend (`apps/api`), shared UI components (`packages/ui`), and shared utilities (`packages/utils`). Teams work in their app or package; root-level tooling is shared.

## Stack

- **Runtime**: Node 20 LTS (`.nvmrc` in repo root)
- **Package manager**: pnpm 9 with workspaces (`pnpm-workspace.yaml`)
- **Build system**: Turborepo (pipeline defined in `turbo.json`)
- **Apps**: Next.js 14 (`apps/web`), Fastify 4 (`apps/api`)
- **Shared packages**: React + Tailwind (`packages/ui`), TypeScript utilities (`packages/utils`)
- **Testing**: Vitest (unit), Playwright (e2e in `apps/web`)
- **Linting**: ESLint + Prettier (shared config in `packages/eslint-config`)

## Commands

```bash
# Root — runs across all workspaces via Turborepo
pnpm install                    # install all workspace deps (run from root)
pnpm turbo build               # build all apps and packages in dependency order
pnpm turbo test                # run all tests across workspaces
pnpm turbo lint                # lint all workspaces
pnpm turbo dev                 # start all dev servers in parallel

# Target a specific workspace
pnpm --filter @acme/web dev    # start only the web app
pnpm --filter @acme/api dev    # start only the API
pnpm --filter @acme/ui build   # build only the UI package

# Generate
pnpm --filter @acme/api generate:api   # regenerates OpenAPI client in apps/web/src/api/
```

## Architecture

```
apps/
  web/          ← Next.js customer dashboard (port 3000)
    src/
      app/      ← App Router pages and layouts
      api/      ← auto-generated OpenAPI client — NEVER edit by hand
      components/features/  ← feature-specific components
      components/ui/        ← re-exports from packages/ui (don't add logic here)
  api/          ← Fastify backend (port 8000)
    src/
      routes/   ← one file per resource
      services/ ← business logic — no HTTP here
      db/       ← Prisma schema + migrations
packages/
  ui/           ← shared React components (published to @acme/ui)
  utils/        ← shared TypeScript helpers (published to @acme/utils)
  eslint-config/← shared ESLint rules (consumed by all apps + packages)
  tsconfig/     ← shared tsconfig bases
turbo.json      ← Turborepo pipeline config — defines task dependencies
pnpm-workspace.yaml  ← workspace glob patterns
```

## Conventions

- **Think Before Coding**: state assumptions, ask when uncertain, never silently guess
- **Simplicity First**: minimum code that solves the problem; no speculative abstractions
- **Surgical Changes**: touch only what the task requires; don't improve adjacent code
- **Goal-Driven Execution**: convert vague requests into verifiable success criteria first
- **Package manager**: only `pnpm` — never `npm` or `yarn`. Running `npm install` creates a `package-lock.json` that breaks the workspace.
- **Adding a shared dep**: add to the package that needs it — not to root unless it's a dev tool for all packages. `pnpm --filter @acme/web add react-query`
- **Imports across packages**: use workspace package names (`@acme/ui`, `@acme/utils`), never relative paths across package boundaries.
- **Component location**: feature logic in `apps/web/src/components/features/`; pure UI in `packages/ui/`. Never add business logic to `packages/ui/`.
- **API changes**: update the Fastify route → run `pnpm --filter @acme/api generate:api` → commit the updated client in `apps/web/src/api/`.

## Environment

Copy `.env.example` to `.env.local` in the app that needs it (e.g., `apps/web/.env.local`):
- `DATABASE_URL` — Postgres connection string (get from 1Password → "Local Dev DB")
- `NEXTAUTH_SECRET` — any random string locally; get prod value from team lead
- `NEXTAUTH_URL` — `http://localhost:3000` for local dev
- `API_BASE_URL` — `http://localhost:8000` for local dev

## Gotchas

- **pnpm only**: npm/yarn will silently create a lockfile that desynchronises the workspace. CI rejects this. If it happens: `git checkout pnpm-lock.yaml && pnpm install`.
- **Run installs from root**: `pnpm install` at root installs all workspace deps. Running it inside `apps/web/` installs only that package's deps and can corrupt the workspace symlinks.
- **Turborepo caches aggressively**: if you add a new env var that a build depends on, add it to `turbo.json` under `globalEnv` or the task won't invalidate correctly.
- **auto-generated API client**: `apps/web/src/api/` is generated from `apps/api/openapi.json` — never edit those files. If the API changes, regenerate: `pnpm --filter @acme/api generate:api`.
- **`packages/ui` peer deps**: all peer deps (React, etc.) must match the version in the consuming app. A version mismatch causes silent duplicate-React bugs that only appear at runtime.
- **Playwright tests need the full stack**: e2e tests in `apps/web/tests/e2e/` need both the web app (port 3000) and API (port 8000) running. Use `pnpm turbo dev` before running Playwright.
- **tsconfig path aliases**: each app has its own `tsconfig.json` with `@/` path alias pointing to its `src/`. Editors sometimes pick up the wrong tsconfig — check the bottom-right of VS Code if paths show red.
