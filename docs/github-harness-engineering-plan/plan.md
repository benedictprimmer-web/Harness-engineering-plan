# GitHub Harness Engineering Plan

Source: https://claude.ai/public/artifacts/6c778af7-0b8c-491b-820c-ace7fa6818ca
Captured: 2026-05-27

Note: the source is a Claude public artifact. Treat it as user-generated research, not an authoritative vendor specification.

## Purpose

This plan adapts the artifact's harness-engineering guidance into concrete work for `harness-engineering-lab`: a GitHub-ready project that installs, audits, and improves reusable AI-agent harnesses across target repos.

The core idea is that the durable value is not the model alone, but the files, rules, gates, tests, state, and feedback loops around it. Agent mistakes should become one-time inputs to the harness, not repeated review issues.

## Design Principles

1. Treat the repository as an agent harness.
   - Keep the harness portable and file-based.
   - Put repeatable rules in repo files, scripts, hooks, tests, and CI.
   - Avoid relying on memory or chat history for critical process.

2. Optimize for agent navigation.
   - Prefer explicit names over generic names such as `utils`, `helpers`, or `common`.
   - Keep files short enough for a coding agent to read confidently.
   - Keep docs split by responsibility: principles, patterns, source rules, loop mechanics, and project plans.

3. Use file contracts between phases.
   - Research writes source notes.
   - Planning writes plan files.
   - Execution writes task updates and code changes.
   - Verification writes test output, audit results, and handoff notes.

4. Make advisory rules enforceable where possible.
   - Rules that affect safety or merge quality should become tests, audits, hooks, or CI checks.
   - Agent-facing prose should be short and load-bearing.
   - Long procedural guidance belongs in skills, runbooks, or reference docs.

5. Keep the loop conservative.
   - Observe first.
   - Audit the current harness.
   - Classify the highest-value issue.
   - Propose exactly one improvement.
   - Write one task and stop.

## Repo-Level Application

The current repo already matches several source recommendations:

- `docs/HARNESS-PRINCIPLES.md` explains the operating model.
- `docs/PATTERNS.md` captures reusable harness patterns.
- `docs/AUTO-HARNESS-LOOP.md` describes the observe-audit-improve loop.
- `docs/SOURCE-RULES.md` defines research-source discipline.
- `templates/*/profile.json` keeps installable profiles data-driven.
- `scripts/install-harness.js`, `scripts/harness-audit.js`, and `scripts/harness-loop.js` provide deterministic behavior.
- `tests/*` encode the harness contract as executable checks.

The next GitHub-facing step is to make those pieces legible to a reviewer landing on the repository for the first time.

## Recommended GitHub Structure

Target top-level shape:

```text
harness-engineering-lab/
  README.md
  COMPACT_HANDOFF.md
  docs/
    AUTO-HARNESS-LOOP.md
    github-harness-engineering-plan/plan.md
    HARNESS-PRINCIPLES.md
    PATTERNS.md
    SOURCE-RULES.md
  templates/
    base/profile.json
    content-operation/profile.json
    nextjs-app/profile.json
    research-project/profile.json
    shopify-theme/profile.json
  scripts/
    install-harness.js
    harness-audit.js
    harness-loop.js
    promote-improvement.js
  tests/
    audit.test.js
    harness-contract.test.js
    installer.test.js
    test-utils.js
  research/
    sources/
```

Keep the public GitHub story centered on three commands:

```bash
node scripts/install-harness.js --target /path/to/project --profile shopify-theme --dry-run
node scripts/harness-audit.js --target /path/to/project
node scripts/harness-loop.js --target /path/to/project
```

## Harness Contract

Every installed target project should receive:

```text
.harness/
  config.json
  tasks.json
  branch-status.json
  run-log.ndjson
  current-run.md
  prompt-packets/
  research-notes/
docs/harness/
  CONTEXT-INDEX.md
  TASK-BOARD.md
  SESSION-HANDOFF.md
  BRANCH-CHECKING-FLOW.md
  AUTOMATION-RUNBOOK.md
  GUARDRAILS.md
  research-lab/
scripts/harness/
  todo-runner.js
  add-todo.js
  harness-audit.js
  harness-loop.js
tests/
  harness-todo.test.js
```

This contract should remain stable unless the tests and README are updated in the same change.

## Information To Incorporate From The Artifact

### Context Discipline

- Keep always-loaded instructions short.
- Move detailed procedural knowledge into on-demand docs or skills.
- Prefer file-scoped validation commands during inner-loop work.
- Use index files to let agents route without repeatedly rediscovering the repo.

For this repo, that means `README.md` should stay short, `docs/` should hold the deeper rationale, and generated harness files should include compact context indexes rather than long essays.

### Spec To Task Flow

The artifact recommends a repeated flow:

```text
research -> spec -> plan -> tasks -> implement -> verify -> ship
```

For this repo, the installable harness should support a lightweight version:

```text
observe -> audit -> classify -> propose -> create task -> stop
```

The loop intentionally stops before implementation so the user keeps control over whether the queued improvement is worth applying.

### State And Resumability

The source emphasizes durable state after each phase. This repo should continue using:

- `.harness/current-run.md` for the active run.
- `.harness/run-log.ndjson` for append-only events.
- `.harness/tasks.json` for queued work.
- `docs/harness/SESSION-HANDOFF.md` for human-readable continuation state.

Future improvement: add a stricter schema check for each `.harness/*.json` file during audit.

### Enforcement

The artifact separates guidance from gates:

- Put orientation and project rules in Markdown.
- Put safety and correctness gates in code.
- Use tests or CI for anything that would block a merge.

For this repo, `harness-audit.js` should remain the main local enforcement surface. GitHub CI should run:

```bash
npm test
```

Later CI can add fixture installs against all profiles to catch template drift.

### Source Handling

The source warns that external research and ecosystem numbers can move quickly. This repo should avoid hard-coding transient ecosystem claims into generated harness files.

Use research notes for:

- Vendor guidance.
- Community patterns.
- Benchmarks.
- Adoption statistics.

Use generated target files for:

- Stable local commands.
- Project-specific guardrails.
- Current task state.
- Verification steps.

## Implementation Backlog

1. Add a GitHub-ready README section.
   - Explain what the repo installs.
   - Show the three main commands.
   - Link to the harness contract and principles.

2. Add CI.
   - Run `npm test` on pull requests.
   - Keep CI dependency-free unless the project adds a real dependency.

3. Add profile fixture tests.
   - Install each profile into a temporary target.
   - Assert required files exist.
   - Assert existing files are skipped unless `--force` is passed.

4. Add JSON schema validation.
   - Validate `.harness/config.json`.
   - Validate `.harness/tasks.json`.
   - Validate `.harness/branch-status.json`.

5. Improve research provenance.
   - Add a source index under `research/sources/`.
   - Record source URL, capture date, summary, and confidence notes.

6. Prepare initial GitHub push.
   - Confirm no local-only files should be excluded.
   - Commit the repo.
   - Create the private remote `jamesobrien261004-bot/harness-engineering-lab`.
   - Push the initial branch.

## Caveats

- Do not copy long external reports into generated harness installs. Summarize and link instead.
- Do not make generated `CLAUDE.md` or `AGENTS.md` files encyclopedic; keep them short and project-specific.
- Do not add multi-agent orchestration until single-agent audit and install flows are stable.
- Do not make the auto-loop mutate application code. Its job is to queue the next harness improvement.
