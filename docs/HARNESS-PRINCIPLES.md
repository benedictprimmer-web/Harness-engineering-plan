# Harness Principles

## Simple, Composable Workflow

Prefer small scripts that read and write explicit files. A target project should be able to understand its harness without a service, database, or package install.

## Context Discipline

Agents should receive the smallest sufficient packet of context for the current task. Prompt packets should explain editable paths, acceptance criteria, expected tests, and sources used.

## One Improvement At A Time

The loop creates exactly one proposed improvement task per run. It does not rewrite the harness or source project unless explicitly run in implementation mode.

## Traceability

Every run should leave a trace summary: what was attempted, what changed, what was verified, and what remains risky.

## Abstention And Safety

If the harness does not have enough context to make a safe recommendation, it should create a task to gather context rather than inventing work. Live admin, deploy, and destructive actions are out of scope for the automatic loop.

