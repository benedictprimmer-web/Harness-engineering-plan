Set the session goal: $ARGUMENTS

1. Write `.claude/session-goal.md` (create if missing, overwrite if exists):

```markdown
# Session Goal

**Goal:** $ARGUMENTS
**Set:** [current timestamp]
**Status:** IN PROGRESS

**Done when:**
- [derive 2–3 specific, verifiable completion criteria from the goal above]
```

2. Read current repo state to understand what's already done:
   - Run `git status` — what's in progress
   - Run `git log --oneline -5` — recent commits
   - Run `ls research/notes/ 2>/dev/null || echo "(none)"` — existing outputs

3. State clearly what "done" looks like: which files will exist or change, which
   commands will succeed, what the user will be able to do.

4. For the rest of this session: before each significant action, check
   `.claude/session-goal.md` and confirm the action directly serves the goal.
   If it doesn't, flag it and ask whether to proceed or defer.

5. When the goal is complete (or at session end), append to `.claude/session-goal.md`:

```markdown
## Outcome

**Status:** DONE / PARTIAL / BLOCKED
**Accomplished:** [what was completed]
**Remaining:** [what was not completed, if anything]
```
