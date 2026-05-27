#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { ensureArray, parseArgs, readJson, readText } = require('./lib');

function taskList(target) {
  const data = readJson(path.join(target, '.harness/tasks.json'), { tasks: [] });
  return ensureArray(data.tasks);
}

function hasTraceSummary(text) {
  return /trace summary|what changed|verified|remaining risk/i.test(text || '');
}

function branchIsStale(branchStatus) {
  if (!branchStatus || !branchStatus.checked_at) return true;
  const checked = Date.parse(branchStatus.checked_at);
  if (Number.isNaN(checked)) return true;
  const ageHours = (Date.now() - checked) / (1000 * 60 * 60);
  return ageHours > 24;
}

function hasAcceptance(task) {
  return (Array.isArray(task.acceptance_criteria) && task.acceptance_criteria.length > 0)
    || (Array.isArray(task.acceptance) && task.acceptance.length > 0);
}

function highImpactWithoutEditablePaths(tasks, config) {
  const highImpactPaths = ensureArray(config.high_impact_paths);
  if (highImpactPaths.length === 0) return false;
  return tasks.some((task) => {
    const title = `${task.title || ''} ${task.description || ''}`.toLowerCase();
    const appearsHighImpact = highImpactPaths.some((p) => title.includes(p.replace('/', '').toLowerCase()));
    return appearsHighImpact && ensureArray(task.editable_paths).length === 0;
  });
}

function audit(target) {
  const config = readJson(path.join(target, '.harness/config.json'), {
    schema_version: 1,
    test_commands: [],
    high_impact_paths: []
  });
  const tasks = taskList(target);
  const branchStatus = readJson(path.join(target, '.harness/branch-status.json'), {});
  const currentRun = readText(path.join(target, '.harness/current-run.md'), '');
  const runLog = readText(path.join(target, '.harness/run-log.ndjson'), '');
  const contextIndex = readText(path.join(target, 'docs/harness/CONTEXT-INDEX.md'), '');
  const guardrails = readText(path.join(target, 'docs/harness/GUARDRAILS.md'), '');

  const openTasks = tasks.filter((task) => task.status !== 'done');
  const unclearAcceptance = openTasks.filter((task) => !hasAcceptance(task));
  const staleBranch = branchIsStale(branchStatus);
  const missingTrace = !hasTraceSummary(currentRun) && !hasTraceSummary(runLog);
  const missingEditable = openTasks.some((task) => !Array.isArray(task.editable_paths));
  const unsafeHighImpact = highImpactWithoutEditablePaths(openTasks, config);
  const missingContextBudget = !/context budget/i.test(contextIndex) && !/context budget/i.test(guardrails);
  const noTests = ensureArray(config.test_commands).length === 0;

  const dimensions = {
    task_clarity: unclearAcceptance.length ? 5 : 9,
    context_discipline: missingContextBudget ? 7 : 9,
    traceability: missingTrace ? 5 : 9,
    branch_freshness: staleBranch ? 5 : 10,
    test_coverage: noTests ? 4 : 7,
    safety: unsafeHighImpact ? 5 : 9
  };

  const findings = [];
  if (missingTrace) {
    findings.push({
      id: 'missing_trace_summary',
      category: 'missing_trace_summary',
      severity: 'medium',
      recommended_task: 'Add a trace summary requirement to current run and handoff docs'
    });
  }
  if (staleBranch) {
    findings.push({
      id: 'stale_branch_state',
      category: 'stale_branch_state',
      severity: 'medium',
      recommended_task: 'Refresh branch status before the next high-impact task'
    });
  }
  if (unclearAcceptance.length) {
    findings.push({
      id: 'unclear_task_acceptance',
      category: 'unclear_task_acceptance',
      severity: 'medium',
      recommended_task: 'Add acceptance criteria to open harness tasks'
    });
  }
  if (missingEditable) {
    findings.push({
      id: 'missing_editable_paths',
      category: 'missing_editable_paths',
      severity: 'low',
      recommended_task: 'Add editable paths to open harness tasks'
    });
  }
  if (unsafeHighImpact) {
    findings.push({
      id: 'unsafe_high_impact_task',
      category: 'unsafe_high_impact_task',
      severity: 'high',
      recommended_task: 'Require editable paths and checks for high-impact tasks'
    });
  }
  if (missingContextBudget) {
    findings.push({
      id: 'context_budget_missing',
      category: 'weak_or_untested_prompt_rule',
      severity: 'medium',
      recommended_task: 'Add context budget rules to generated prompt packets'
    });
  }
  if (noTests) {
    findings.push({
      id: 'test_commands_missing',
      category: 'weak_or_untested_prompt_rule',
      severity: 'medium',
      recommended_task: 'Add at least one harness verification command'
    });
  }

  const score = Math.round(Object.values(dimensions).reduce((sum, value) => sum + value, 0) / 6 * 10);

  return {
    score,
    dimensions,
    top_finding: findings[0] || {
      id: 'no_major_findings',
      severity: 'info',
      recommended_task: 'Review harness examples and keep trace summaries current'
    },
    findings
  };
}

if (require.main === module) {
  try {
    const args = parseArgs(process.argv.slice(2));
    const target = path.resolve(args.target || process.cwd());
    console.log(JSON.stringify(audit(target), null, 2));
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

module.exports = { audit, branchIsStale, hasTraceSummary };
