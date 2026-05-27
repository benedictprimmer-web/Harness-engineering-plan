#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { appendText, isoDate, parseArgs, readJson, readText, slugify, writeJson, writeText } = require('./lib');
const { audit } = require('./harness-audit');

function nextTaskId(tasks, findingId) {
  const base = `${isoDate()}-${slugify(findingId)}`;
  let id = base;
  let counter = 2;
  const existing = new Set(tasks.map((task) => task.id));
  while (existing.has(id)) {
    id = `${base}-${counter}`;
    counter += 1;
  }
  return id;
}

function createTaskFromFinding(tasks, finding, auditResult) {
  const acceptance = [
    `Audit finding ${finding.id} is addressed or explicitly documented.`,
    'A trace summary records what changed and what was verified.',
    'Configured harness tests pass.'
  ];
  return {
    id: nextTaskId(tasks, finding.id),
    title: finding.recommended_task,
    status: 'open',
    source: 'harness-loop',
    finding_id: finding.id,
    severity: finding.severity,
    editable_paths: [
      '.harness/',
      'docs/harness/',
      'TODO.md'
    ],
    acceptance_criteria: acceptance,
    acceptance,
    audit_score_at_creation: auditResult.score,
    created_at: new Date().toISOString()
  };
}

function taskAlreadyQueued(tasks, findingId) {
  return tasks.some((task) => task.status !== 'done' && task.finding_id === findingId);
}

function runLoop(target) {
  const targetRoot = path.resolve(target || process.cwd());
  readText(path.join(targetRoot, '.harness/run-log.ndjson'), '');
  readText(path.join(targetRoot, '.harness/current-run.md'), '');
  const tasksPath = path.join(targetRoot, '.harness/tasks.json');
  const tasksData = readJson(tasksPath, { schema_version: 1, tasks: [] });
  tasksData.tasks = Array.isArray(tasksData.tasks) ? tasksData.tasks : [];
  readJson(path.join(targetRoot, '.harness/branch-status.json'), {});

  const auditResult = audit(targetRoot);
  let finding = auditResult.top_finding;
  if (taskAlreadyQueued(tasksData.tasks, finding.id)) {
    finding = auditResult.findings.find((candidate) => !taskAlreadyQueued(tasksData.tasks, candidate.id)) || {
      id: 'review_harness_health',
      severity: 'info',
      recommended_task: 'Review harness health and close stale improvement tasks'
    };
  }

  const task = createTaskFromFinding(tasksData.tasks, finding, auditResult);
  tasksData.tasks.push(task);
  writeJson(tasksPath, tasksData);

  const todoPath = path.join(targetRoot, 'TODO.md');
  const todoEntry = `\n- [ ] ${task.title} (${task.id})\n`;
  if (fs.existsSync(todoPath)) {
    appendText(todoPath, todoEntry);
  } else {
    writeText(todoPath, `# TODO\n${todoEntry}`);
  }

  const notePath = path.join(targetRoot, '.harness/research-notes', `${task.id}.md`);
  writeText(notePath, `# ${task.title}\n\nFinding: \`${finding.id}\`\n\nSeverity: ${finding.severity}\n\nAudit score: ${auditResult.score}\n\nRecommended task: ${finding.recommended_task}\n\nThe auto harness loop queued this single improvement and stopped.\n`);

  return {
    created_task: task,
    audit: auditResult,
    mutated_paths: [
      '.harness/tasks.json',
      'TODO.md',
      path.relative(targetRoot, notePath)
    ]
  };
}

if (require.main === module) {
  try {
    const args = parseArgs(process.argv.slice(2));
    const result = runLoop(args.target || process.cwd());
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

module.exports = { runLoop };
