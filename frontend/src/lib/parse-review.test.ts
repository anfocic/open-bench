import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
import { parseReview } from './parse.ts';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REVIEW = resolve(__dirname, '../../../results/reviews/sandbox-2026-05-05.md');

test('parseReview: round 1 snapshot shape', () => {
  const md = readFileSync(REVIEW, 'utf-8');
  const r = parseReview(md);

  assert.ok(r.scoreboard.length > 0, 'scoreboard empty');
  assert.ok(r.judgeRanking.length > 0, 'judgeRanking empty');
  assert.ok(r.selfBias.length > 0, 'selfBias empty');
  assert.ok(r.agreement.length > 0, 'agreement empty');
  assert.ok(r.perImplDetail.length > 0, 'perImplDetail empty');
  assert.ok(r.costEfficiency.length > 0, 'costEfficiency empty');

  for (const row of r.scoreboard) {
    assert.equal(typeof row.impl, 'string');
    assert.ok(row.impl.length > 0);
    assert.equal(typeof row.hardFail, 'boolean');
    assert.equal(typeof row.verdict, 'string');
  }
});

test('parseReview: throws on heading present but no rows', () => {
  const broken = `# x\n\n## Scoreboard\n\nno table here, just prose\n\n## Per-judge ranking\n| j | 1 | 2 | 3 |\n|---|---|---|---|\n| a | x | y | z |\n`;
  assert.throws(() => parseReview(broken), /Scoreboard/);
});
