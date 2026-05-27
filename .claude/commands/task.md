Decompose and execute the following task iteratively: $ARGUMENTS

You are in Agentic Task mode. Work through the task in three phases.

## Phase 1 — Decompose

Break "$ARGUMENTS" into at most 7 concrete subtasks. For each subtask provide:
- A one-sentence description of what to do
- A specific, machine-verifiable command that exits 0 only when the subtask is done

Write the checklist to `.claude/current-task.md`:

```
# Task: [short name]
**Goal:** $ARGUMENTS
**Started:** [timestamp]
**Status:** IN PROGRESS

## Subtasks
- [ ] 1. [description]
       Verify: `[command]`
- [ ] 2. ...
```

**Stop and ask** if the task cannot be decomposed into ≤7 verifiable subtasks — it needs
to be narrowed in scope. Verification commands must be machine-executable (no "check it
looks right").

## Phase 2 — Execute → Verify → Commit Loop

For each subtask in order:

1. **Do the work** — edit files, run commands, write tests
2. **Run the verify command** — check the exit code
3. **If it passes** →
   - Mark done in `.claude/current-task.md`
   - `git add -A && git commit -m "task: subtask N — [description]"`
   - Move to the next subtask
4. **If it fails** →
   - Read the output, diagnose the problem, fix it
   - Re-run the verify command
   - Retry up to 3 times total
5. **If still failing after 3 attempts** →
   - Mark blocked in `.claude/current-task.md` with a one-line diagnosis
   - Move to the next subtask

## Phase 3 — Close

After all subtasks:

1. Run the full test suite (check `## Commands` in CLAUDE.md for the test command)
2. Update `.claude/current-task.md` status: **COMPLETE** or **PARTIAL**
3. Print a summary:
   - What was completed (subtask numbers + commit hashes)
   - What was blocked (subtask numbers + diagnosis)
   - What remains for the next session

Good verification commands:
- `pytest tests/test_auth.py -v`
- `grep -q 'def login' src/auth.py`
- `git diff --name-only HEAD~1`
- `curl -sf http://localhost:8000/health`

Bad verification commands:
- "check the code looks right"
- "run the app and see if it works"
