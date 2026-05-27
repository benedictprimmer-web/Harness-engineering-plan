# Auto Harness Loop

The loop runs:

```text
observe -> audit -> classify -> propose -> create task -> stop
```

Inputs:

- `.harness/run-log.ndjson`
- `.harness/current-run.md`
- `.harness/tasks.json`
- `.harness/branch-status.json`
- `.harness/config.json`
- `docs/harness/`

Outputs:

- One task appended to `.harness/tasks.json`
- One task appended to `TODO.md`
- One note in `.harness/research-notes/`

The default mode never edits project source files.

