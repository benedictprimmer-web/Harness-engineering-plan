Run parallel research agents on: $ARGUMENTS

Parse `$ARGUMENTS` as comma-separated topics (split on `", "` or `" / "`).

## Option A — Use the repo's parallel runner (preferred)

If `agent/parallel.py` is available and `ANTHROPIC_API_KEY` is set, run:

```bash
python agent/parallel.py "topic 1" "topic 2" "topic 3" ...
```

This fires `AsyncAnthropic` calls for all topics simultaneously, shows a live
status table, and saves the combined report to `research/notes/`.

## Option B — Spawn Explore sub-agents directly

If Option A is not available, launch one Explore sub-agent per topic (up to 5 in parallel).
Give each agent a specific search focus derived from its topic.
Collect all results and synthesize into a structured report.

## Output format (both options)

For each topic produce:

### [Topic Name]

**Key findings:**
[2–4 bullet points with the most important insights]

**Repo references:**
[specific file paths and line numbers that are relevant]

**Gaps:**
[what is missing, unclear, or undocumented]

**Recommendations:**
[top 3 actionable next steps]

---

Offer to save the combined report to `research/notes/` when complete.
