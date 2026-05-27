const fs = require('fs');
const os = require('os');
const path = require('path');

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function tmpDir(name) {
  return fs.mkdtempSync(path.join(os.tmpdir(), `${name}-`));
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

function writeText(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, value);
}

function exists(filePath) {
  return fs.existsSync(filePath);
}

module.exports = {
  assert,
  exists,
  readJson,
  tmpDir,
  writeJson,
  writeText
};

