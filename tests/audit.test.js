#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { install } = require('../scripts/install-harness');
const { audit } = require('../scripts/harness-audit');
const { runLoop } = require('../scripts/harness-loop');
const { assert, readJson, tmpDir, writeJson, writeText } = require('./test-utils');

function fixture() {
  const target = tmpDir('harness-audit');
  install({ target, profile: 'shopify-theme' });
  return target;
}

const missingTraceTarget = fixture();
let result = audit(missingTraceTarget);
assert(result.findings.some((finding) => finding.id === 'missing_trace_summary'), 'audit should detect missing trace summaries');

const staleTarget = fixture();
writeJson(path.join(staleTarget, '.harness/branch-status.json'), {
  schema_version: 1,
  main_branch: 'main',
  checked_at: '2000-01-01T00:00:00.000Z',
  status: 'unknown'
});
result = audit(staleTarget);
assert(result.findings.some((finding) => finding.id === 'stale_branch_state'), 'audit should detect stale branch status');

const unclearTarget = fixture();
writeJson(path.join(unclearTarget, '.harness/tasks.json'), {
  schema_version: 1,
  tasks: [
    {
      id: 'task-1',
      title: 'Improve task board',
      status: 'open'
    }
  ]
});
result = audit(unclearTarget);
assert(result.findings.some((finding) => finding.id === 'unclear_task_acceptance'), 'audit should detect missing acceptance criteria');

const loopTarget = fixture();
writeText(path.join(loopTarget, 'src-file.txt'), 'source stays unchanged\n');
const beforeSource = fs.readFileSync(path.join(loopTarget, 'src-file.txt'), 'utf8');
const beforeTasks = readJson(path.join(loopTarget, '.harness/tasks.json')).tasks.length;
const loopResult = runLoop(loopTarget);
const afterTasks = readJson(path.join(loopTarget, '.harness/tasks.json')).tasks.length;
assert(afterTasks === beforeTasks + 1, 'loop should create exactly one task');
assert(fs.readFileSync(path.join(loopTarget, 'src-file.txt'), 'utf8') === beforeSource, 'loop must not mutate source files');
assert(loopResult.mutated_paths.every((p) => p.startsWith('.harness/') || p === 'TODO.md'), 'loop should only report harness/task doc mutations');

execFileSync('node', [path.join(loopTarget, 'tests/harness-todo.test.js')], { cwd: loopTarget, stdio: 'pipe' });

console.log('audit and loop ok');

