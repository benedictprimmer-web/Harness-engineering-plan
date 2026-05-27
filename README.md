# Harness Engineering Lab

Reusable operating system for AI-agent projects.

This repo installs a portable harness into a target project, observes agent runs, scores harness health, queues one improvement at a time, and repeats. It is intentionally small: Node.js scripts, no required npm dependencies, and file-based state that works in Shopify themes, Next.js apps, research projects, and content operations.

## Quick Start

Preview an install:

```bash
node scripts/install-harness.js --target /path/to/project --profile shopify-theme --dry-run
```

Install missing harness files:

```bash
node scripts/install-harness.js --target /path/to/project --profile shopify-theme
```

Audit a target project:

```bash
node scripts/harness-audit.js --target /path/to/project
```

Queue exactly one harness improvement:

```bash
node scripts/harness-loop.js --target /path/to/project
```

## Contract

Every target project receives:

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

The loop is conservative by default. It observes, audits, classifies, proposes, creates one task, writes notes, and stops.

## Tests

```bash
node tests/harness-contract.test.js
node tests/installer.test.js
node tests/audit.test.js
```

