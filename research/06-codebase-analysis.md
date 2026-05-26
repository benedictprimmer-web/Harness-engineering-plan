# Auditing and Optimising an Existing Codebase's Harness

## The Core Problem

Most codebases acquire a harness by accident — a CLAUDE.md someone wrote on day one and never updated, a hook copied from a blog post, permissions set to "allow everything" to stop the prompts. The result is a harness that is simultaneously over-permissive and under-informative.

This guide gives you a repeating audit-fix-verify loop that progressively improves any existing project's harness.

---

## The Audit-Fix-Verify Loop

```
┌─────────────┐
│    AUDIT    │  ← Run agent/audit.py against the project
│  (score 0–5 │
│  per layer) │
└──────┬──────┘
       │ gap report
       ▼
┌─────────────┐
│     FIX     │  ← Address the highest-priority gaps first
│  (one layer │     (see Priority Order below)
│   at a time)│
└──────┬──────┘
       │ changes committed
       ▼
┌─────────────┐
│   VERIFY    │  ← Re-run agent/audit.py; score should increase
│  (rescore;  │     Run a real Claude session; observe behaviour
│  smoke test)│
└──────┬──────┘
       │ improved baseline
       └──────────────────► repeat
```

Run `python agent/audit.py /path/to/project` at each iteration. The script outputs a score card and a prioritised gap list — work through the list top-to-bottom, one category per iteration.

---

## Scoring Matrix

Each of the five harness layers is scored 0–5. A healthy harness scores ≥ 3 on every layer.

### Layer 1: CLAUDE.md

| Score | Signal |
|-------|--------|
| 0 | No CLAUDE.md exists |
| 1 | File exists but < 20 lines; only project name present |
| 2 | Stack and commands present; no conventions or gotchas |
| 3 | All seven sections present; at least 3 gotchas |
| 4 | Karpathy behavioural rules merged in; project-specific constraints documented |
| 5 | Validated against real sessions — Claude behaves correctly without extra prompting |

**Most common defects in existing codebases:**
- Missing `## Gotchas` section (Claude hits known landmines repeatedly)
- No mention of auto-generated files (Claude edits `lib/api/` or `dist/`)
- Stale content ("we're migrating to X" when migration finished 6 months ago)
- Commands missing flags (`pytest` instead of `uv run pytest -x -q`)

### Layer 2: settings.json Permissions

| Score | Signal |
|-------|--------|
| 0 | No `.claude/settings.json` — Claude prompts for every command |
| 1 | Blanket `allow: ["Bash(*)"]` — no safety; too broad |
| 2 | Some allow rules; no deny rules |
| 3 | Allow rules match actual project commands; at least one deny rule |
| 4 | Per-command scoping (e.g. `Bash(git log *)` not `Bash(git *)`) |
| 5 | Deny rules block destructive commands; allow list reviewed against audit log |

**Most common defects:**
- `Bash(*)` allows `rm -rf`, `curl | bash`, `git push --force`
- Allow list written once and never updated as project commands evolve
- No deny list at all (missing the force-push and reset guards)
- Missing MCP server registrations for tools the team actually uses (GitHub, DB)

### Layer 3: Hooks

| Score | Signal |
|-------|--------|
| 0 | No hooks configured |
| 1 | One hook exists; does something but may error silently |
| 2 | SessionStart hook checks deps/env; no other hooks |
| 3 | SessionStart + at least one PreToolUse safety guard |
| 4 | PostToolUse auto-formatter; Stop hook for uncommitted changes |
| 5 | All four events covered; hooks are idempotent and fast (< 2s) |

**Most common defects:**
- `set -e` without `|| true` guards — hook fails silently, Claude gets no signal
- SessionStart runs `npm install` unconditionally (slow; should check `node_modules`)
- No PreToolUse guard → Claude can `git reset --hard` or `rm -rf build/` without warning
- Hooks not committed to the repo (live only in `~/.claude/`)

### Layer 4: Architecture (CLAUDE.md quality)

This layer scores how well CLAUDE.md reflects the actual project architecture — not just whether sections exist.

| Score | Signal |
|-------|--------|
| 0 | No architectural context |
| 1 | Directory listing only; no explanation of what each part does |
| 2 | Key directories explained; materialisation/ownership notes missing |
| 3 | Non-obvious boundaries documented (e.g. "never reference raw tables, use `{{ source() }}`") |
| 4 | Auto-generated paths explicitly flagged; naming conventions enforced |
| 5 | Architecture section validated: Claude can navigate the codebase correctly cold |

### Layer 5: Environment & Secrets

| Score | Signal |
|-------|--------|
| 0 | No environment documentation |
| 1 | `.env.example` exists but CLAUDE.md doesn't reference it |
| 2 | Required env vars listed; no setup instructions |
| 3 | Setup instructions present; where to get credentials documented |
| 4 | Local dev setup fully automated (docker compose, seed data, migrations) |
| 5 | Claude can complete onboarding from a cold clone without asking questions |

---

## Priority Order for Improvements

When you have gaps across multiple layers, fix in this order:

```
1. CLAUDE.md exists at all          (unblocks everything else)
2. Karpathy baseline rules          (biggest behaviour improvement per line)
3. Destructive-command deny rules   (safety before productivity)
4. SessionStart hook                (catch env/dep issues before work starts)
5. Project-specific gotchas         (stop repeating the same mistakes)
6. PreToolUse safety guard          (block git reset --hard, rm -rf)
7. PostToolUse formatter            (code quality, consistency)
8. Per-command allow scoping        (tighten after you know the allow list is stable)
9. MCP servers                      (add only when a repeated friction point emerges)
10. Stop hook                       (last — polish, not safety)
```

---

## Common Anti-Patterns in Existing Codebases

### The "First Day" CLAUDE.md
Written in the first session, never touched again. Usually just:
```markdown
# My Project
This is a React app. Use TypeScript.
```
**Fix:** Run `agent/audit.py`, score each layer, address gaps in priority order.

### The Blanket Allow
```json
{ "permissions": { "allow": ["Bash(*)"] } }
```
Written to stop the constant approval prompts. Now Claude can run anything.  
**Fix:** Replace with a scoped list. Run `grep -h "Bash(" ~/.claude/projects/*/transcripts/*.jsonl | sort | uniq -c | sort -rn | head -30` to see the 30 most common commands in your actual sessions, then allow exactly those.

### The Dead Hook
```json
"hooks": { "SessionStart": [{ "command": "~/.claude/hooks/session-start.sh" }] }
```
The script exists on one developer's machine. No one else has it. It's not in the repo.  
**Fix:** Move hooks to `.claude/hooks/` and commit them. Reference via `"command": ".claude/hooks/session-start.sh"` (relative path from repo root).

### The Stale Architecture Lie
```markdown
## Architecture
src/api/ ← REST handlers
src/db/  ← database queries
```
Three migrations ago, the team moved to a repository pattern. Now Claude puts DB code directly in handlers because that's what CLAUDE.md says.  
**Fix:** Date-stamp architecture descriptions. Add a checklist item to update CLAUDE.md as part of any significant refactor PR.

### No Gotchas
Gotchas are the highest-value addition to any existing CLAUDE.md. Every time Claude makes the same mistake twice, that mistake belongs in Gotchas.

**Template for capturing a new gotcha:**
```markdown
- **[symptom]**: [why it happens]. [what to do instead].
  Example: **`npm install` breaks the lockfile**: we use pnpm. Always `pnpm install`.
```

---

## The Repeating Workflow in Practice

### Iteration 0: Establish Baseline
```bash
python agent/audit.py /path/to/project > research/notes/audit-baseline.md
```
Record the scores. Don't fix anything yet — just understand where you are.

### Iteration 1–3: Foundations
- Merge the Karpathy baseline into CLAUDE.md (or create CLAUDE.md from scratch)
- Add the destructive-command deny rules to settings.json
- Commit a minimal SessionStart hook that checks required env vars

Re-run audit after each change. Score should move from 0–1 to 2–3 across all layers.

### Iteration 4–6: Project Context
- Write the Gotchas section based on your last 10 sessions with Claude
- Document the non-obvious architecture boundaries
- Scope the allow list to actual commands (use the session transcript grep)

Re-run audit. Target: score ≥ 3 on all layers.

### Iteration 7+: Refinement
- Add PreToolUse + PostToolUse hooks
- Add MCP servers where repeated friction points exist
- Tighten per-command allow scoping

At this stage, the metric shifts from the audit score to **session quality** — fewer course corrections, fewer repeated mistakes, fewer approval prompts.

---

## Running the Audit Tool

```bash
# Audit a project
python agent/audit.py /path/to/project

# Audit and save the report
python agent/audit.py /path/to/project --save

# Audit this repo itself
python agent/audit.py .

# Compare two iterations
diff research/notes/audit-2026-05-01.md research/notes/audit-2026-05-26.md
```

See `agent/audit.py` for the full implementation. The tool scans for all harness files, scores each layer, and outputs a prioritised gap list with specific fixes.

---

## What "Optimised" Looks Like

A fully optimised harness is not one with the most configuration — it's one where:

1. Claude completes 90%+ of tasks correctly on the first attempt
2. Approval prompts appear only for genuinely novel or risky operations
3. New developers can onboard with `git clone` + `python agent/audit.py .` and know exactly what to do
4. The harness is self-documenting — CLAUDE.md explains the *why*, not just the *what*

The Karpathy result (65% → 94% accuracy from 65 lines) is the benchmark: significant gains come from surprisingly small, precise changes to the harness. You don't need 500 lines of CLAUDE.md. You need the right 65.
