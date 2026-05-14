import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
import { parseReview, parseAttackReview } from './parse.ts';

const __dirname = dirname(fileURLToPath(import.meta.url));
// The round-2 review renderer's snapshot golden doubles as our fixture.
const GOLDEN = resolve(
  __dirname,
  '../../../bench/scripts/_tests/fixtures/golden_break_review-2026-05-14.md',
);

test('parseReview: dispatches a Break review to the objective parser', () => {
  const md = readFileSync(GOLDEN, 'utf-8');
  const r = parseReview(md);

  assert.equal(r.scoringMode, 'objective');
  assert.equal(r.judgeRanking.length, 0);
  assert.equal(r.selfBias.length, 0);
  assert.ok(r.scoreboard.length > 0, 'objective scoreboard empty');
  assert.ok(r.attackMatrix.length > 0, 'attack matrix empty');
});

test('parseAttackReview: scoreboard carries rank, scores, elimination', () => {
  const md = readFileSync(GOLDEN, 'utf-8');
  const r = parseAttackReview(md);

  // Combined ranking from the fixture: alpha (1), beta (2), gamma (3, out).
  const byRank = [...r.scoreboard].sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0));
  assert.deepEqual(byRank.map(e => e.impl), ['alpha', 'beta', 'gamma']);

  const alpha = r.scoreboard.find(e => e.impl === 'alpha')!;
  assert.equal(alpha.rank, 1);
  assert.equal(alpha.defenderScore, 0);
  assert.equal(alpha.attackerScore, 3);
  assert.equal(alpha.eliminated, false);

  const gamma = r.scoreboard.find(e => e.impl === 'gamma')!;
  assert.equal(gamma.rank, 3);
  assert.equal(gamma.eliminated, true);
});

test('parseAttackReview: attack matrix rows and cells', () => {
  const md = readFileSync(GOLDEN, 'utf-8');
  const r = parseAttackReview(md);

  assert.deepEqual(r.attackMatrix.map(row => row.attacker),
    ['alpha', 'beta', 'gamma']);

  const alphaRow = r.attackMatrix.find(row => row.attacker === 'alpha')!;
  assert.deepEqual(alphaRow.cells.map(c => c.target),
    ['alpha', 'beta', 'gamma']);
  // alpha vs alpha is a self-pair ("—" -> null); alpha breaches gamma in 2 classes.
  assert.equal(alphaRow.cells.find(c => c.target === 'alpha')!.value, null);
  assert.equal(alphaRow.cells.find(c => c.target === 'beta')!.value, 1);
  assert.equal(alphaRow.cells.find(c => c.target === 'gamma')!.value, 2);
});
