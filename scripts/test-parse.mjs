#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parsePromptFile } from './generate-images-from-prompts.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function run() {
  const fixturePath = path.join(__dirname, '..', 'tests', 'fixtures', '01.md');
  const content = await fs.readFile(fixturePath, 'utf8');
  const result = parsePromptFile(content);

  assert.equal(result.images.length, 8, 'Expected 8 image prompts');

  const titles = result.images.map((image) => image.title);
  assert.deepEqual(titles, [
    'Hero Image - The Shift-Change Problem',
    'Context Window Visualization',
    'The Two Failure Modes',
    'AGENCY.md as Shared Memory',
    'The Deep Work Session',
    'The Cortex Orchestrator',
    'Vendor Agnostic Operation',
    'Building the Operating System for Agents',
  ]);

  const captions = result.images.map((image) => image.caption);
  assert.ok(captions[0].includes('Shift-Change Problem'));
  assert.ok(captions[1].includes('Context windows'));
  assert.ok(captions[7].includes('Agent Hive as an operating system'));

  const aspects = result.images.map((image) => image.aspect);
  assert.deepEqual(aspects, [
    '16:9',
    '4:3',
    '16:9',
    '16:9',
    '16:9',
    '4:3',
    '16:9',
    '4:3',
  ]);

  console.log('parse prompt fixture: ok');
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
