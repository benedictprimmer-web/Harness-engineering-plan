# Harness Engineering — Literature Review Notes

*May 2026 — compiled from Caleb Writes Code (YouTube) and supporting sources*

---

## The 98% Harness Finding

The most striking empirical finding in the current literature:

> Roughly **1.6% of Claude Code's source is AI decision logic**. The remaining **98.4% is the harness** — permission pipeline, context management, sandboxing layer, tool router, and recovery infrastructure.

Source: analysis of the leaked Claude Code source, covered by Caleb Writes Code in:
- *"What Is an AI Agent Harness? (The Secret Behind Claude Code)"* — [youtube.com/watch?v=e5B2XP7apXs](https://www.youtube.com/watch?v=e5B2XP7apXs)
- *"Anthropic Just Dropped a Masterclass on Building Agent Harnesses (for Large Codebases)"* — [youtube.com/watch?v=efRIrLXoOVA](https://www.youtube.com/watch?v=efRIrLXoOVA)

**Why this matters for harness engineering:** The model is a small slice of what makes an agent work. If your Claude Code sessions feel unpredictable or unsafe, the answer is almost certainly in the harness (CLAUDE.md, hooks, permissions) not the model.

---

## Independent Convergence Signal

Four competing teams independently building coding agents converged on the **same structural skeleton**:

1. Outer loop: model call → tool execution → result capture
2. A primitive toolset of ~12 capabilities (file read/write/edit, shell, search, web fetch)
3. A multi-stage permission pipeline that gates every tool call through sequential checks

When independent teams invent the same architecture, that convergence is a strong signal the pattern is a **constraint imposed by the problem**, not a preference.

Source: TechTimes, May 2026 — [techtimes.com/articles/316928](https://www.techtimes.com/articles/316928/20260521/claude-code-study-four-competing-teams-built-same-agent-harness-pointing-real-ai-moat.htm)

---

## Key Architectural Patterns from the Claude Code Leak

### Skeptical Memory
The system prompt tells Claude its own memory is fallible — treat it as a "hint". Before executing critical changes, the agent must grep the codebase or fetch topic files to verify the **current state of reality**.

**Harness engineering implication:** Your CLAUDE.md should explicitly tell Claude to verify before acting on assumptions, especially in long sessions. Example addition to CLAUDE.md:
```
Before modifying files, confirm their current state by reading them first.
Never assume the file matches what you last saw in a previous turn.
```

### Write Discipline
The harness only allows memory/index updates **after the OS confirms a successful file write**. Claude cannot record "I did X" before X actually happened.

**Harness engineering implication:** Hooks can enforce this — a PostToolUse hook can verify the write succeeded before allowing downstream actions.

### Plan Mode
`EnterPlanModeTool` temporarily locks Claude out of file modifications, forcing it to output a step-by-step reasoning plan before touching anything. This is Chain-of-Thought reasoning enforced at the system level.

**Harness engineering implication:** For complex multi-file tasks, your CLAUDE.md can instruct Claude to write a plan first: `"For tasks touching more than 2 files, write a numbered plan before making any edits."`

### StreamingToolExecutor
Claude Code runs **40+ highly specialised tools in parallel** — not serial. The tools are robust environment wrappers (with error handling, timeouts, retries), not simple read/write stubs.

**Harness engineering implication:** Investing in good tool definitions pays off. Each tool in your settings.json permission list should have clear semantics.

---

## Performance Impact

On Terminal Bench 2.0:
- Claude Opus 4.6 inside Claude Code scores **lower** than the same model in a custom harness
- One team moved a coding agent from **Top 30 → Top 5** by changing only the harness

This is the clearest evidence that harness quality dominates model quality for agentic tasks.

---

## The Karpathy Rules (65 lines → 94% accuracy)

Separately from the architectural analysis, Andrej Karpathy's 4-rule CLAUDE.md hit #1 on GitHub trending (220k+ combined stars). See `examples/karpathy-minimal/CLAUDE.md` for the full text.

The 4 rules solve the **most common LLM coding failure modes**:

| Rule | Failure it prevents |
|------|---------------------|
| Think Before Coding | Silent wrong assumptions → wrong output |
| Simplicity First | Over-engineering, unnecessary abstraction |
| Surgical Changes | Unasked-for "improvements" that break things |
| Goal-Driven Execution | Vague tasks with no verifiable exit condition |

**Reported impact:** AI coding accuracy 65% → 94% (65 lines of CLAUDE.md).

**Recommendation:** Treat these 4 rules as the **minimum viable CLAUDE.md** for any project. Add project-specific context on top. See `examples/karpathy-minimal/CLAUDE.md`.

---

## Synthesis: What Harness Engineering Is Now

Based on the current literature, the field has consolidated around this view:

> An agent harness is **everything between the language model and the real world**. The model generates text. The harness decides what that text can touch.

The four levers this repo documents (CLAUDE.md, settings.json, hooks, MCP servers) map directly onto the harness components found in production systems:

| Harness Component | This Repo's Lever |
|-------------------|-------------------|
| Behavioural guidelines | CLAUDE.md |
| Permission pipeline | settings.json allow/deny rules |
| Pre/post action enforcement | Hooks (PreToolUse, PostToolUse) |
| Tool surface | MCP servers + Bash permissions |

---

## Sources

- Caleb Writes Code: [What Is an AI Agent Harness?](https://www.youtube.com/watch?v=e5B2XP7apXs)
- Caleb Writes Code: [Anthropic's Masterclass on Agent Harnesses](https://www.youtube.com/watch?v=efRIrLXoOVA)
- Caleb Writes Code: [My Pi Agent Teams. Claude Code Leak SIGNAL. Harness Engineering](https://www.youtube.com/watch?v=RairMJflUSA)
- TechTimes: [Claude Code 98% Harness study](https://www.techtimes.com/articles/316928/20260521/claude-code-study-four-competing-teams-built-same-agent-harness-pointing-real-ai-moat.htm)
- Karpathy CLAUDE.md: [github.com/multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md)
- miraflow.ai: [Karpathy's CLAUDE.md explained](https://miraflow.ai/blog/karpathy-claude-md-100k-github-stars-ai-coding-2026)
