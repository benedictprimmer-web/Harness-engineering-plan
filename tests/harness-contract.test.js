#!/usr/bin/env node
const path = require('path');
const { install } = require('../scripts/install-harness');
const { assert, exists, readJson, tmpDir } = require('./test-utils');

const target = tmpDir('harness-contract');
install({ target, profile: 'shopify-theme' });

const required = [
  '.harness/config.json',
  '.harness/tasks.json',
  '.harness/branch-status.json',
  '.harness/run-log.ndjson',
  '.harness/current-run.md',
  '.harness/prompt-packets/.gitkeep',
  '.harness/research-notes/.gitkeep',
  'docs/harness/CONTEXT-INDEX.md',
  'docs/harness/TASK-BOARD.md',
  'docs/harness/SESSION-HANDOFF.md',
  'docs/harness/BRANCH-CHECKING-FLOW.md',
  'docs/harness/AUTOMATION-RUNBOOK.md',
  'docs/harness/GUARDRAILS.md',
  'docs/harness/research-lab/.gitkeep',
  'scripts/harness/todo-runner.js',
  'scripts/harness/add-todo.js',
  'scripts/harness/harness-audit.js',
  'scripts/harness/harness-loop.js',
  'tests/harness-todo.test.js'
];

for (const relativePath of required) {
  assert(exists(path.join(target, relativePath)), `Missing ${relativePath}`);
}

const config = readJson(path.join(target, '.harness/config.json'));
assert(config.schema_version === 1, 'config schema_version must be 1');
assert(config.project_type === 'shopify-theme', 'profile project_type should be shopify-theme');
assert(Array.isArray(config.test_commands), 'test_commands must be an array');

console.log('harness contract ok');

