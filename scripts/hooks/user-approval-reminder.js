#!/usr/bin/env node
'use strict';

/**
 * PreToolUse hook: Remind Claude to obtain user approval before
 * creating or modifying files.
 *
 * Reads the tool invocation from stdin and emits a notification
 * reminding that user approval is required. Exits 0 so it never
 * blocks execution — the reminder is advisory. The real enforcement
 * comes from the CLAUDE.md rule and the .claude/rules/ policy file.
 */

const fs = require('fs');

let raw = '';
try {
  raw = fs.readFileSync(0, 'utf8');
} catch {
  process.exit(0);
}

let input;
try {
  input = JSON.parse(raw);
} catch {
  process.exit(0);
}

const tool = input.tool_name || '';
const blockedTools = ['Write', 'Edit', 'MultiEdit', 'NotebookEdit'];

if (blockedTools.includes(tool)) {
  const message = [
    '[User Approval Policy]',
    'File modification detected. Ensure you have obtained explicit user approval',
    'before creating or editing files. See CLAUDE.md "User Approval Policy".'
  ].join(' ');

  process.stderr.write(message + '\n');
}

process.exit(0);
