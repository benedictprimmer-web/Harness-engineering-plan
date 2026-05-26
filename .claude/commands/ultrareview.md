Perform an Ultra Code Review of: $ARGUMENTS

**Scope:**
- If `$ARGUMENTS` is a file path → review that file
- If `$ARGUMENTS` is a directory → review all source files in it
- If `$ARGUMENTS` is empty → review all files in `git diff HEAD` (staged + unstaged)

For every finding record exactly:
```
FILE:     path/to/file.py:42
SEVERITY: CRITICAL | MAJOR | MINOR | SUGGESTION
ISSUE:    one-sentence description of the problem
FIX:      specific corrected code or approach
```

---

## Pass 1 — Correctness

Logic errors · wrong boolean conditions · off-by-one boundaries · unhandled
`None`/`null`/empty cases · incorrect algorithms · missing `return` values ·
silent state mutation

## Pass 2 — Security

Unvalidated external input · hardcoded secrets or tokens · shell/SQL/path
injection vectors · missing auth/permission checks · unsafe deserialization ·
sensitive data written to logs or error messages

## Pass 3 — Performance

N+1 database queries · blocking I/O inside `async` functions · unbounded memory
growth (lists that grow forever) · unnecessary recomputation inside hot loops ·
missing caching for expensive repeated calls

## Pass 4 — Style & Maintainability

Naming inconsistent with the rest of the codebase · dead/unreachable code ·
premature abstraction (one caller) · functions doing more than one thing ·
non-obvious code lacking a WHY comment

## Pass 5 — Test Coverage

Untested happy paths · missing error/exception path tests · brittle assertions
that will break on unrelated changes · tests that don't actually verify the
behaviour their name claims · missing edge cases (empty input, max values, concurrency)

---

## Output

1. Print a summary table of all findings sorted by severity (CRITICAL first).
2. For every CRITICAL finding, show the exact corrected code inline.
3. Save the full structured report to:
   `research/notes/review-[YYYYMMDD-HHMM]-[slug].md`
