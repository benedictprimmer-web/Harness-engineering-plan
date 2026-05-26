# Writing Great CLAUDE.md Files

## What CLAUDE.md Is

CLAUDE.md is read automatically at the start of every Claude Code session. It's the primary way to give Claude persistent, project-specific context without repeating it in every prompt. Think of it as the project's "system prompt" — but written in plain Markdown and committed to git.

Claude also reads any CLAUDE.md files found in parent directories (up to the filesystem root) and in subdirectories it navigates into. This enables monorepo patterns: a root CLAUDE.md for org-wide conventions, package-level CLAUDE.md for each service.

## The Seven Essential Sections

### 1. Project Identity (2–4 sentences)

Tell Claude what the project is, what it does, and who uses it. Be specific — "a React app" is less useful than "a customer-facing dashboard for managing IoT device fleets, used by enterprise operations teams."

```markdown
## Project

Acme Fleet Dashboard — a Next.js 14 web application that lets enterprise
customers monitor and configure IoT sensor networks in real time.
The backend is a separate service (see `api-service/`); this repo is
frontend-only.
```

### 2. Tech Stack

List the actual versions and key libraries. Claude knows many frameworks, but knowing the exact version avoids it suggesting deprecated APIs.

```markdown
## Stack

- **Runtime**: Node 20, pnpm 9
- **Framework**: Next.js 14 (App Router)
- **UI**: Tailwind CSS 3.4, shadcn/ui components
- **State**: Zustand 4, React Query 5
- **Testing**: Vitest + React Testing Library
- **Linting**: ESLint (config in `eslint.config.mjs`), Prettier
```

### 3. Key Commands

The most important section for day-to-day use. Include every command Claude might need to run. Be exact — wrong flags waste time.

```markdown
## Commands

```bash
pnpm install          # install dependencies
pnpm dev              # start dev server on :3000
pnpm build            # production build
pnpm test             # run all tests (vitest)
pnpm test:watch       # tests in watch mode
pnpm lint             # eslint + tsc --noEmit
pnpm lint:fix         # auto-fix lint issues
pnpm storybook        # component explorer on :6006
```
```

### 4. Architecture & Key Files

Tell Claude where things live and how they're organized. Don't describe every file — focus on the non-obvious structure.

```markdown
## Architecture

- `app/` — Next.js App Router pages and layouts
- `app/(dashboard)/` — authenticated dashboard routes (route group)
- `components/ui/` — shadcn/ui primitives (don't edit these directly)
- `components/features/` — product-specific components
- `lib/api/` — generated API client (run `pnpm generate:api` after schema changes)
- `lib/stores/` — Zustand stores
- `hooks/` — shared React hooks

**Important**: The `lib/api/` directory is auto-generated. Never edit files
there by hand — changes will be overwritten on the next `pnpm generate:api` run.
```

### 5. Conventions & Constraints

Capture decisions that differ from defaults or that Claude wouldn't infer from reading the code.

```markdown
## Conventions

- **Imports**: use `@/` alias for src root (not relative `../../`)
- **Components**: one component per file, named exports only (no default exports)
- **Styling**: Tailwind classes only — no inline styles, no CSS modules
- **API calls**: always go through `lib/api/` client, never raw fetch
- **Dates**: use `date-fns` for all date manipulation (already installed)
- **Forms**: use `react-hook-form` + `zod` validation schema
```

### 6. Environment Setup

What does a fresh developer (or a fresh Claude session) need to know to get the project running?

```markdown
## Environment

Copy `.env.example` to `.env.local` and fill in:
- `NEXT_PUBLIC_API_URL` — backend API base URL (use `http://localhost:8000` locally)
- `NEXT_PUBLIC_MAPBOX_TOKEN` — get from 1Password under "Mapbox Dev Token"

The `.env.local` file is gitignored. Never commit real credentials.
```

### 7. Gotchas & Known Issues

The highest-value section — things Claude would waste time on without this warning.

```markdown
## Gotchas

- **pnpm, not npm**: always use `pnpm`. Running `npm install` creates a
  `package-lock.json` that conflicts with `pnpm-lock.yaml`.
- **Port 3000 conflict**: if `pnpm dev` fails, another process is likely on :3000.
  Use `lsof -i :3000` to find it.
- **Storybook HMR**: Storybook has a known HMR bug with our Tailwind config —
  if styles stop updating, restart with `pnpm storybook`.
- **Type errors in `lib/api/`**: these are upstream generator issues, not ours.
  Add `// @ts-ignore` with a comment rather than fixing them.
```

## Optional Sections (Add When Relevant)

- **Testing strategy**: what to test, what not to, where fixtures live
- **Deployment**: how to deploy, what environments exist, what branch maps to what
- **External services**: what APIs/databases this connects to and how to mock them locally
- **Code review checklist**: things the team always checks
- **Decision log**: why certain architectural choices were made

## Anti-Patterns to Avoid

### Too much structure
CLAUDE.md is not a wiki. If it takes more than 10 minutes to read, Claude will read it but it won't stick. Keep the total under ~300 lines.

### Describing what code already shows
```markdown
# BAD — Claude can read the import
The project uses React for the UI layer.

# GOOD — Claude can't infer this from code
Use React Query for all server state. Never use useEffect for data fetching.
```

### Stale content
Outdated CLAUDE.md is worse than none — it actively misleads Claude. Date-sensitive facts (like "currently migrating to X") should be removed once the migration is done. Add a "Last reviewed" date if the team is disciplined enough to update it.

### Missing the "why"
```markdown
# BAD — Claude will try to "fix" this
Don't use the Button component from shadcn for primary CTAs.

# GOOD — Claude understands the constraint
Don't use shadcn's Button for primary CTAs. We have a custom PrimaryButton
component in components/features/ that enforces our brand's interaction
states. The shadcn version doesn't match the design spec.
```

### Documenting things Claude already knows
Don't tell Claude how React works, what TypeScript is, or how git commits work. Use CLAUDE.md for project-specific knowledge only.

## The Karpathy Baseline: 4 Rules, 65 Lines

Before writing a full project-specific CLAUDE.md, know the minimum viable version. In May 2026, Forrest Chang's adaptation of Andrej Karpathy's coding principles hit #1 on GitHub trending (220k+ combined stars). The reported impact: AI coding accuracy from **65% → 94%** with 65 lines of plain text.

The four rules address the most common LLM coding failure modes:

| Rule | What it prevents |
|------|-----------------|
| **Think Before Coding** — state assumptions, surface tradeoffs, ask when confused | Silent wrong assumptions → wrong output |
| **Simplicity First** — minimum code, no speculative features, no unasked-for abstractions | Over-engineering and unnecessary complexity |
| **Surgical Changes** — touch only what the task requires, don't "improve" adjacent code | Unasked-for refactors that break things |
| **Goal-Driven Execution** — convert vague tasks to verifiable success criteria, plan before acting | Drift and tasks with no clear exit condition |

See the full text at `examples/karpathy-minimal/CLAUDE.md`. Use it as your starting point and merge your project-specific sections on top.

```markdown
# Merge order

1. Start with examples/karpathy-minimal/CLAUDE.md  (behavioural baseline)
2. Add your Stack, Commands, Architecture, Environment, Gotchas sections
3. Remove anything that duplicates what's already in the baseline
```

The four rules also explain why the seven-section template works: sections like "Gotchas" exist specifically to feed Claude the assumptions it would otherwise make silently (Rule 1), and "Conventions" exists to enforce surgical changes by telling Claude what the existing style actually is (Rule 3).

---

## Checklist: Is Your CLAUDE.md Ready?

- [ ] Project identity clearly stated (1 paragraph)
- [ ] Exact tech stack with versions listed
- [ ] Every command Claude will need is present (install, dev, test, lint, build)
- [ ] Key directory structure noted, especially non-obvious parts
- [ ] Auto-generated files/directories flagged as "don't edit"
- [ ] Import aliases and naming conventions documented
- [ ] Environment variables listed with setup instructions
- [ ] At least 3 project-specific gotchas captured
- [ ] Total length under 300 lines
- [ ] No information that's already obvious from reading the code
