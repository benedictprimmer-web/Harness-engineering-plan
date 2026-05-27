# Guide 07 — The Self-Improving Harness

## The Core Idea

A harness that never changes is a harness that gets stale. Every Claude session produces information that could make the next one better: commands that needed pre-approval, mistakes that could have been caught by a deny rule, gotchas that hit Claude three times before being documented. The self-improving harness captures this information automatically and feeds it back.

The system has three layers:

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Session                        │
│                                                         │
│  Pre-hook logs every command → .claude/tool-audit.log  │
│  Claude edits files → git diff records what changed    │
│                          ↓                             │
│               Stop hook fires → reflect.py runs        │
│                          ↓                             │
│     .claude/session-learnings.md  ← proposed changes  │
│                          ↓                             │
│  Next SessionStart shows pending learnings banner      │
│                          ↓                             │
│     Developer reviews → applies → harness improves    │
└─────────────────────────────────────────────────────────┘
```

## Layer 1 — Session Reflection (reflect.py)

`agent/reflect.py` runs at the end of every session via the Stop hook. It does three things:

**1. Reads what happened**
- Scans `.claude/tool-audit.log` — every command Claude ran or tried to run
- Reads `git diff HEAD` — every file that changed during the session
- Reads the existing CLAUDE.md — so it knows what's already documented

**2. Proposes improvements** (if ANTHROPIC_API_KEY is set)
Calls Claude with a structured prompt: "Given what happened in this session, what should change in the harness?" It looks for:
- Commands that ran many times → candidates for the allow list
- Commands that were blocked → verify the deny rule was appropriate, or flag if it was too aggressive
- Patterns in what changed → gotchas worth documenting
- Gaps between what CLAUDE.md says and what actually happened

**3. Writes proposals to `.claude/session-learnings.md`**
A human-readable file in the project's `.claude/` directory. Never auto-applies — always requires human review. Clears itself once applied.

## Layer 2 — Agentic Task Execution (task.py + /task)

The `/task` slash command and `agent/task.py` implement the "set it off and come back when it's done" workflow.

**The loop:**

```
/task "implement user authentication"
         ↓
Phase 1: Decompose
  Claude breaks the task into ≤7 concrete subtasks
  Each subtask has a specific verification command
  Writes .claude/current-task.md checklist
         ↓
Phase 2: Execute → Verify → Commit
  For each subtask:
    1. Claude does the work (edit files, run commands)
    2. Runs the verification command
    3. If passes → mark done, commit, next subtask
    4. If fails → diagnose, fix, retry (max 3 attempts)
    5. If still failing → mark blocked, explain why, move on
         ↓
Phase 3: Close
  Final test run
  Update task status: COMPLETE or PARTIAL
  Summary of what was done and what's blocked
```

**Why subtasks?**

Hard tasks fail because Claude loses context halfway through. Subtasks force each piece to be verifiable before moving on. A failing test is caught at subtask 2, not after 20 file changes that are hard to untangle.

**The verification command**

The most important part of each subtask definition. Good verification commands:
- `pytest tests/test_auth.py -v` — run only the relevant tests
- `python agent/audit.py . --next-fix` — check harness score
- `git diff --stat HEAD~1` — verify only expected files changed
- `curl -s localhost:8000/health | jq .status` — observable behaviour

Bad verification: "check the code looks right" — not machine-verifiable.

## Layer 3 — Research Loop (parallel.py + /loop)

The research loop keeps the harness guides current as Claude Code evolves. Running `/loop` with the parallel agent fires async research on core topics and saves findings to `research/notes/`. A human then decides what's worth promoting into the main guides.

```bash
# Run once manually:
/agents Claude Code hooks new patterns, settings.json 2025 changes, MCP server best practices

# Or set up a recurring loop:
/loop 24h /agents Claude Code latest harness patterns
```

## The Full Feedback Loop

```
New project
    ↓
python agent/install.py /path    ← installs harness + reflect hook + task tools
    ↓
First session
    ↓
/task "implement feature X"      ← decomposes, executes, verifies
    ↓
Session ends → Stop hook fires → reflect.py runs
    ↓
.claude/session-learnings.md     ← "add pytest -v to allow list, document this gotcha"
    ↓
Developer reviews + applies
    ↓
python agent/audit.py /path      ← score improves
    ↓
Next session starts stronger
    ↓
repeat
```

## What "Self-Improving" Means in Practice

It does not mean Claude autonomously edits its own harness. That would be unsafe — a badly-written allow rule could let Claude do destructive things. The loop always has a human decision point before anything is applied.

What it means:
- Every session produces a list of specific, actionable proposals
- Those proposals are based on actual observed behaviour, not guesses
- The human's job is review + approve, not discovery + write

Over 5–10 sessions on a project, a CLAUDE.md that started as a skeleton with `{{PLACEHOLDERS}}` should converge on something dense with real gotchas, accurate command lists, and well-tuned permissions.

## Setting Up on an Existing Project

```bash
# 1. Install the harness (gets you reflect + task from day one)
python agent/install.py /path/to/project

# 2. Fill in the CLAUDE.md placeholders
# (project description, real gotchas, env vars)

# 3. Run a task
# In Claude Code: /task "your first hard task"

# 4. After the session, check the learnings
cat /path/to/project/.claude/session-learnings.md

# 5. Apply what makes sense, then re-audit
python agent/audit.py /path/to/project
```

## Anti-Patterns to Avoid

- **Auto-applying all suggestions**: reflect.py proposes, humans decide. A suggestion to add `Bash(rm -rf build/)` might be right for a build cleanup — or it might be too broad. Review first.
- **Never clearing session-learnings.md**: once applied, delete it. Stale suggestions from three weeks ago confuse more than they help.
- **Subtasks that can't be verified**: if you can't write a verification command, the subtask is too vague. Break it down further or make it observable.
- **Tasks with more than 7 subtasks**: Claude loses the thread. Split into two separate `/task` runs.
