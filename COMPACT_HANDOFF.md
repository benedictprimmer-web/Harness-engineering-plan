# Compact Handoff - 2026-05-26

## Repo

`/Users/benrimmer/harness-engineering-lab`

Local git repo initialized. No remote is configured yet.

## What Was Built

- Created reusable no-dependency Node harness lab.
- Added portable harness docs:
  - `docs/HARNESS-PRINCIPLES.md`
  - `docs/PATTERNS.md`
  - `docs/AUTO-HARNESS-LOOP.md`
  - `docs/SOURCE-RULES.md`
- Added profiles:
  - `base`
  - `shopify-theme`
  - `nextjs-app`
  - `research-project`
  - `content-operation`
- Added scripts:
  - `scripts/install-harness.js`
  - `scripts/harness-audit.js`
  - `scripts/harness-loop.js`
  - `scripts/promote-improvement.js`
- Added tests:
  - `tests/harness-contract.test.js`
  - `tests/installer.test.js`
  - `tests/audit.test.js`
- Added `package.json` with `npm test`.

## Behavior

- Installer creates missing files only.
- Existing target files are skipped unless `--force` is passed.
- `--dry-run` previews install actions without writing.
- Audit scores task clarity, context discipline, traceability, branch freshness, test coverage, and safety.
- Loop runs `observe -> audit -> classify -> propose -> create task -> stop`.
- Loop creates exactly one task and mutates only `.harness/`, `TODO.md`, and harness notes.

## Validation

Passed:

```bash
npm test
node tests/harness-contract.test.js
node tests/installer.test.js
node tests/audit.test.js
```

## GitHub Change Summary

Suggested PR title:

```text
Create reusable harness engineering lab
```

Suggested PR body:

```markdown
## Summary

- Scaffold reusable `harness-engineering-lab` repo for installing and improving AI-agent harnesses across target projects.
- Add no-dependency Node installer, audit, and conservative loop scripts.
- Add base and project-type profiles, including Shopify theme support based on Offside Goods.
- Add contract, installer, and audit/loop tests.

## Tests

- `npm test`
```

## Remaining Work

- Create private GitHub remote `jamesobrien261004-bot/harness-engineering-lab`.
- Commit and push this repo when ready.
- Optionally add richer examples under `examples/offside-goods-snapshot/`.

