#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { loadProfile, parseArgs, writeText } = require('./lib');

const REPO_ROOT = path.resolve(__dirname, '..');

function defaultTasks() {
  return {
    schema_version: 1,
    tasks: []
  };
}

function filesForProfile(profile) {
  const config = JSON.stringify(profile.config, null, 2);
  return {
    '.harness/config.json': `${config}\n`,
    '.harness/tasks.json': `${JSON.stringify(defaultTasks(), null, 2)}\n`,
    '.harness/branch-status.json': `${JSON.stringify({
      schema_version: 1,
      main_branch: profile.config.main_branch || 'main',
      checked_at: new Date().toISOString(),
      status: 'unknown',
      summary: 'Branch state has not been checked yet.'
    }, null, 2)}\n`,
    '.harness/run-log.ndjson': '',
    '.harness/current-run.md': '# Current Run\n\nNo active run has been recorded yet.\n',
    '.harness/prompt-packets/.gitkeep': '',
    '.harness/research-notes/.gitkeep': '',
    'docs/harness/CONTEXT-INDEX.md': '# Context Index\n\nList the smallest sufficient context packets for target project work.\n',
    'docs/harness/TASK-BOARD.md': '# Task Board\n\nMirror active harness tasks and acceptance criteria here.\n',
    'docs/harness/SESSION-HANDOFF.md': '# Session Handoff\n\nRecord what changed, what was verified, and what remains risky.\n',
    'docs/harness/BRANCH-CHECKING-FLOW.md': '# Branch Checking Flow\n\n1. Confirm the main branch.\n2. Check freshness before high-impact work.\n3. Record status in `.harness/branch-status.json`.\n',
    'docs/harness/AUTOMATION-RUNBOOK.md': '# Automation Runbook\n\nAutomation may propose and queue harness improvements. It must not deploy, delete, or perform live admin actions.\n',
    'docs/harness/GUARDRAILS.md': '# Guardrails\n\n- State editable paths before implementation.\n- Include acceptance criteria for each task.\n- Run configured tests before marking work complete.\n- Leave a trace summary.\n',
    'docs/harness/research-lab/.gitkeep': '',
    'scripts/harness/lib.js': fs.readFileSync(path.join(REPO_ROOT, 'scripts/lib.js'), 'utf8'),
    'scripts/harness/todo-runner.js': todoRunnerScript(),
    'scripts/harness/add-todo.js': addTodoScript(),
    'scripts/harness/harness-audit.js': fs.readFileSync(path.join(REPO_ROOT, 'scripts/harness-audit.js'), 'utf8'),
    'scripts/harness/harness-loop.js': fs.readFileSync(path.join(REPO_ROOT, 'scripts/harness-loop.js'), 'utf8'),
    'tests/harness-todo.test.js': harnessTodoTest(),
    'TODO.md': '# TODO\n\n'
  };
}

function todoRunnerScript() {
  return `#!/usr/bin/env node\nconst fs = require('fs');\nconst tasks = JSON.parse(fs.readFileSync('.harness/tasks.json', 'utf8'));\nconst open = (tasks.tasks || []).filter((task) => task.status !== 'done');\nconsole.log(JSON.stringify({ open_tasks: open.length, tasks: open }, null, 2));\n`;
}

function addTodoScript() {
  return `#!/usr/bin/env node\nconst fs = require('fs');\nconst title = process.argv.slice(2).join(' ').trim();\nif (!title) {\n  console.error('Usage: node scripts/harness/add-todo.js <title>');\n  process.exit(1);\n}\nconst file = '.harness/tasks.json';\nconst data = JSON.parse(fs.readFileSync(file, 'utf8'));\ndata.tasks = data.tasks || [];\ndata.tasks.push({ id: 'manual-' + Date.now(), title, status: 'open', acceptance_criteria: [] });\nfs.writeFileSync(file, JSON.stringify(data, null, 2) + '\\n');\nfs.appendFileSync('TODO.md', '\\n- [ ] ' + title + '\\n');\n`;
}

function harnessTodoTest() {
  return `#!/usr/bin/env node\nconst fs = require('fs');\nfunction fail(message) { console.error(message); process.exit(1); }\nif (!fs.existsSync('.harness/tasks.json')) fail('Missing .harness/tasks.json');\nconst data = JSON.parse(fs.readFileSync('.harness/tasks.json', 'utf8'));\nif (data.schema_version !== 1) fail('tasks.json schema_version must be 1');\nif (!Array.isArray(data.tasks)) fail('tasks.json tasks must be an array');\nfor (const task of data.tasks) {\n  if (!task.id || !task.title || !task.status) fail('Each task needs id, title, and status');\n  if (!Array.isArray(task.acceptance_criteria)) fail('Each task needs acceptance_criteria array');\n}\nconsole.log('harness todo contract ok');\n`;
}

function install(options) {
  const target = path.resolve(options.target || process.cwd());
  const profileName = options.profile || 'base';
  const profile = loadProfile(REPO_ROOT, profileName);
  const files = filesForProfile(profile);
  const actions = [];

  for (const [relativePath, content] of Object.entries(files)) {
    const destination = path.join(target, relativePath);
    const exists = fs.existsSync(destination);
    if (exists && !options.force) {
      actions.push({ action: 'skip', path: relativePath, reason: 'exists' });
      continue;
    }
    actions.push({ action: exists ? 'overwrite' : 'create', path: relativePath });
    if (!options.dryRun) {
      writeText(destination, content);
      if (relativePath.endsWith('.js')) fs.chmodSync(destination, 0o755);
    }
  }

  return { target, profile: profileName, dry_run: Boolean(options.dryRun), actions };
}

if (require.main === module) {
  try {
    const args = parseArgs(process.argv.slice(2));
    const result = install({
      target: args.target,
      profile: args.profile,
      dryRun: Boolean(args['dry-run']),
      force: Boolean(args.force)
    });
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

module.exports = { filesForProfile, install };
