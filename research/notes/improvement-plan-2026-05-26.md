# Harness Repo — Iterative Improvement Plan
**Date:** 2026-05-26  
**Method:** 5 parallel research agents (installer gaps, audit accuracy, loop mechanics, template gaps, README/docs)  
**Current score:** 22/25

---

## What the Research Found

### Audit accuracy problems (3 false positives, 2 gaps)
1. **Placeholder gotchas inflate score** — `{{GOTCHA_1}}` matches the gotcha regex, so a fresh install.py template immediately scores 3+ gotchas without real content
2. **`#` in code blocks triggers "architecture annotations"** — any `#` character in the Architecture section counts as an annotation, including shell comments in code blocks
3. **Hook files never validated on disk** — settings.json can register 4 hooks pointing to non-existent files and still score 5/5 on hooks
4. **MCP servers never scored** — the five-layer model has no signal for MCP server configuration despite it being a real harness layer
5. **Scoped allows mislabelled** — `Bash(git *)` is treated as "not scoped" because it contains `*`, discouraging good practice

### Installer gaps
1. **Slash commands not copied** — install.py creates `.claude/commands/` as empty dir but never copies the four high-value command files
2. **Bun, poetry, uv-lock not detected** — ~10% of modern projects use these
3. **Testing/linting names left as `{{PLACEHOLDERS}}`** despite being detectable from deps
4. **No merge mode** — only skip-or-overwrite for existing CLAUDE.md; no smart update
5. **No Edit() scope rules** — generated settings.json has no file-scope restrictions

### Loop mechanics missing entirely
1. No `--json` output — can't programmatically track scores across runs
2. No `--compare` — no way to see what changed between two audits
3. No `--auto-fix` — even safe mechanical fixes require manual editing
4. No `--watch` — must manually re-run after each file change
5. No history or progress dashboard

### Template and example gaps
1. **settings.json.template has invalid JSON** (JS-style `//` comments) — breaks direct copy-paste
2. **Missing examples:** monorepo, CLI tool, data science/Jupyter
3. **Gotchas template too sparse** — doesn't guide what to capture
4. **Slash commands not discoverable** — no README inside `.claude/commands/`

### Documentation gaps
1. **install.py not mentioned anywhere in README** — the fastest on-ramp is hidden
2. **No "5-minute quick start"** — current "where to start" is 4 vague bullets
3. **README 37% redundant** — Karpathy result appears 4×, "start here" appears 4×

---

## The Improvement Plan

Each iteration is ~1–2 hours and leaves the repo in a better, shippable state.

---

### Iteration 1 — Fix Audit Accuracy (Trust)
*Goal: stop the audit from lying. False positives undermine confidence in the tool.*

| Fix | File | What to change |
|-----|------|---------------|
| Filter placeholder gotchas | `agent/audit.py` | Skip lines matching `{{` when counting gotchas |
| Fix architecture annotation regex | `agent/audit.py` | Require `←` or `—` on a *directory* line, not just anywhere in the section |
| Validate hook files exist on disk | `agent/audit.py` | Cross-reference hook commands against actual `.sh` files in `.claude/hooks/` |
| Add MCP server scoring | `agent/audit.py` | Check `settings.json` for `mcpServers` key; award up to 1 bonus point in settings layer |
| Fix scoped-allows detection | `agent/audit.py` | Any rule that names a specific command (not `Bash(*)`) counts as scoped |

**Expected score after:** more accurate (may go slightly down on repos that scored via false positives — that's correct behaviour)

---

### Iteration 2 — Complete the Installer (Completeness)
*Goal: install.py should produce a fully wired harness in one command.*

| Fix | File | What to change |
|-----|------|---------------|
| Copy slash commands | `agent/install.py` | After hooks, copy all `.claude/commands/*.md` from this repo into target |
| Add Bun detection | `agent/install.py` | Check `bun.lockb` before pnpm/yarn in Node detection |
| Add poetry.lock detection | `agent/install.py` | Add `poetry.lock` to Python signals; set `poetry install` and `Bash(poetry *)` |
| Add uv.lock-only detection | `agent/install.py` | If `uv.lock` exists without `pyproject.toml`, set `uv sync` |
| Auto-fill test/lint names | `agent/install.py` | Detect `pytest`, `jest`, `vitest`, `rspec` from deps; pre-fill `{{TEST_FRAMEWORK}}` |
| Add Edit() scope rules | `agent/install.py` | Node → `Edit(src/**)`, Python → `Edit(src/**)`, narrow per framework |

**Expected score on a fresh install:** 22–23/25 (up from 21)

---

### Iteration 3 — Close the Loop (Repeatability)
*Goal: make "again and again" mechanical — run, see score, fix, repeat.*

| Feature | File | What to add |
|---------|------|-------------|
| `--json` output | `agent/audit.py` | Emit structured JSON: score, layer scores, gaps, priority actions, timestamp |
| `--compare prev.json` | `agent/audit.py` | Read a prior JSON, diff scores and gaps, show what improved |
| `--save` produces JSON too | `agent/audit.py` | When `--save` is used, write both `.md` and `.json` to `research/notes/` |
| `--history` | `agent/audit.py` | Parse all `audit-*.json` in `research/notes/`, show score trend per layer |
| `--next-fix` | `agent/audit.py` | Print the single highest-priority action from the current audit |

**Schema for JSON output:**
```json
{
  "project": "string",
  "timestamp": "ISO-8601",
  "total": 18,
  "max": 25,
  "layers": [{"name": "CLAUDE.md", "score": 4, "max": 5, "gaps": [], "fixes": []}],
  "priority_actions": [{"rank": 1, "action": "...", "layer": "...", "score_gain": 2}]
}
```

---

### Iteration 4 — Fix the Docs (Discoverability)
*Goal: a developer who finds this repo should reach their first working harness in 5 minutes.*

| Fix | File | What to change |
|-----|------|---------------|
| Add install.py to README | `README.md` | New "Quick Start (5 minutes)" section at top; add to At a Glance table |
| Add project detection table | `README.md` | Show which languages auto-detected: Python/Node/Go/Rust/Ruby/Java |
| Trim Karpathy repetition | `README.md` | Reduce from 4× to 1× (keep in "Key Findings", cut from Big Idea and At a Glance) |
| Add commands/README.md | `.claude/commands/README.md` | Quick-reference table for all 4 slash commands |
| Fix settings.json.template | `templates/settings.json.template` | Add note at top that `//` comments make it JSON5/documentation-only; link to install.py |
| Expand gotchas template | `templates/CLAUDE.md.template` | Add 6 guiding questions as comments: package manager, auto-generated files, env safety, etc. |

---

### Iteration 5 — Add Examples (Coverage)
*Goal: developers can find an example close to their project type.*

| Example | Path | Key content |
|---------|------|-------------|
| Monorepo | `examples/monorepo/CLAUDE.md` | Root conventions + per-package override pattern; shared hooks; workspace commands |
| CLI tool | `examples/cli-tool/CLAUDE.md` | Entry point, build/publish steps, minimal harness (Karpathy-style) |
| Data science | `examples/data-science/CLAUDE.md` | Jupyter conventions, venv, notebook cell ordering, data path gotchas |

---

### Iteration 6+ — Auto-Fix Mode (Automation)
*Goal: reduce the gap between "audit identifies a problem" and "problem is fixed" to zero for safe mechanical fixes.*

**The 5 safe auto-fixes (require no human judgment):**
1. Create `.claude/settings.json` from template if missing
2. Add deny rules to existing `settings.json` if none present
3. Create `.claude/hooks/` and copy templates if hooks missing
4. Add `## Gotchas` section stub to CLAUDE.md if section missing
5. Create `.env.example` if missing

**Interface:**
```bash
python agent/audit.py /project --auto-fix --dry-run   # preview
python agent/audit.py /project --auto-fix --apply     # execute
```

**Merge mode for CLAUDE.md** (more complex):
- Parse existing sections
- Replace Commands and Stack (auto-detectable) with fresh detection
- Preserve Conventions, Gotchas, Environment (hand-written)
- Add missing sections as stubs

---

## Execution Order

```
Iteration 1 (fix audit)        →  audit is trustworthy
Iteration 2 (complete install) →  install.py produces 22+/25
Iteration 3 (close the loop)   →  scores track across runs
Iteration 4 (fix docs)         →  5-minute on-ramp exists
Iteration 5 (add examples)     →  coverage for more project types
Iteration 6+ (auto-fix)        →  hands-free improvement
```

Each iteration is independently shippable. Start with Iteration 1 because trust in the scoring tool underlies everything else.

---

## Score Projection

| After iteration | Expected score (this repo) | New capability |
|----------------|---------------------------|----------------|
| 1 | 22/25 (more accurate) | Trustworthy scoring |
| 2 | 23/25 | Complete 1-command install |
| 3 | 23/25 | Measurable progress loop |
| 4 | 23/25 | 5-minute on-ramp documented |
| 5 | 23/25 | Broader example coverage |
| 6 | 24/25 | Auto-fix mechanical gaps |
