# Slash Commands — Quick Reference

Four project-level commands available in any Claude Code session on this repo.
Type `/` in Claude Code to see them in the menu.

| Command | Use when | Output |
|---------|----------|--------|
| `/ultraplan <task>` | Before writing any non-trivial code | Plan in `/tmp/ultraplan-current.md`; waits for approval before proceeding |
| `/goal <description>` | Starting a session with a specific objective | `.claude/session-goal.md` with verifiable done-criteria; tracks goal through session |
| `/agents <topic1, topic2>` | Need parallel research on multiple questions | Spawns sub-agents per topic; saves synthesised report to `research/notes/` |
| `/ultrareview <file or dir>` | Before committing, or reviewing unfamiliar code | Five-pass review (correctness/security/perf/style/coverage); saves to `research/notes/` |

## Tips

- `/ultraplan` will **not** write code until you confirm the plan — use it to catch bad assumptions early.
- `/goal` persists across turns and reminds Claude to stay on task. Use it at the start of any session with a clear objective.
- `/agents` accepts comma-separated topics: `/agents performance bottlenecks, caching strategy, database indexes`
- `/ultrareview` with no argument reviews everything in the current `git diff`.
