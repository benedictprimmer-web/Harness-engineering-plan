You are in Ultra Plan mode. Task: $ARGUMENTS

Do NOT write any code or make any changes yet. Execute this four-phase research and planning loop:

## Phase 1 — Parallel Exploration

Launch 3 Explore sub-agents simultaneously, each with a distinct focus:
- **Agent A**: locate every file, function, and pattern directly relevant to this task
- **Agent B**: find existing utilities, helpers, and abstractions that can be REUSED (avoid reinventing)
- **Agent C**: identify tests, dependencies, callers, and potential blast radius of changes

Collect all findings before proceeding to Phase 2.

## Phase 2 — Design

Based on exploration:
1. List affected files with current state (key functions, line ranges)
2. Identify what can be reused vs. what must be written from scratch
3. Choose the implementation order (dependency-safe sequence)
4. Name at least two risks or edge cases

## Phase 3 — Plan Document

Write the full plan to `/tmp/ultraplan-current.md`:

```
# Ultra Plan: [task name]

## Context
[Why this change. What problem it solves. What prompted it.]

## Affected Files
[file : function / lines — what changes and why]

## Implementation Steps
1. [step] → verify: [how to confirm this step worked]
2. ...

## Reuse
[existing functions/utils to call instead of reimplementing]

## Risks
[what could go wrong; rollback approach]

## Verification
[end-to-end test plan: exact commands to run]
```

## Phase 4 — Approval Gate

Print a concise summary of the plan (≤ 20 lines). Ask the user to confirm before proceeding.
Do not begin implementation until you receive explicit approval.
