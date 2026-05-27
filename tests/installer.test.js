#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { install } = require('../scripts/install-harness');
const { assert, exists, readJson, tmpDir, writeText } = require('./test-utils');

const target = tmpDir('harness-installer');
const dryRun = install({ target, profile: 'base', dryRun: true });
assert(dryRun.dry_run === true, 'dry-run flag should be reported');
assert(dryRun.actions.some((action) => action.action === 'create'), 'dry-run should preview creates');
assert(!exists(path.join(target, '.harness/config.json')), 'dry-run must not create files');

const installed = install({ target, profile: 'shopify-theme' });
assert(installed.actions.some((action) => action.path === '.harness/config.json'), 'install should include config');
assert(exists(path.join(target, '.harness/config.json')), 'install should create config');
assert(readJson(path.join(target, '.harness/config.json')).project_type === 'shopify-theme', 'install should use selected profile');

writeText(path.join(target, 'docs/harness/GUARDRAILS.md'), 'custom guardrails\n');
const skipped = install({ target, profile: 'shopify-theme' });
const guardrailAction = skipped.actions.find((action) => action.path === 'docs/harness/GUARDRAILS.md');
assert(guardrailAction.action === 'skip', 'existing files should be skipped without force');
assert(fs.readFileSync(path.join(target, 'docs/harness/GUARDRAILS.md'), 'utf8') === 'custom guardrails\n', 'skip must preserve content');

install({ target, profile: 'shopify-theme', force: true });
assert(fs.readFileSync(path.join(target, 'docs/harness/GUARDRAILS.md'), 'utf8').includes('# Guardrails'), 'force should overwrite content');

console.log('installer ok');

