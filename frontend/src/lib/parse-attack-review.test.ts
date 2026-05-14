import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
import { parseReview, parseAttackReview } from './parse.ts';

const __dirname = dirname(fileURLToPath(import.meta.url));
// The round-2 review renderer's snapshot goldens double as our fixtures.
const FIXTURES = resolve(__dirname, '../../../bench/scripts/_tests/fixtures');
const GOLDEN = resolve(FIXTURES, 'golden_break_review-2026-05-14.md');
// The "with reference" golden carries the post-oracle "## Reference oracle"
// section; the plain golden predates it.
const GOLDEN_ORACLE = resolve(
  FIXTURES, 'golden_break_review_with_reference-2026-05-14.md');

test('parseReview: dispatches a Break review to the objective parser', () => {
  const md = readFileSync(GOLDEN, 'utf-8');
  const r = parseReview(md);

  assert.equal(r.scoringMode, 'objective');
  assert.equal(r.judgeRanking.length, 0);
  assert.equal(r.selfBias.length, 0);
  assert.ok(r.scoreboard.length > 0, 'objective scoreboard empty');
  assert.ok(r.attackMatrix.length > 0, 'attack matrix empty');
});

test('parseAttackReview: round ranking carries rank and scores, no elimination', () => {
  const md = readFileSync(GOLDEN, 'utf-8');
  const r = parseAttackReview(md);

  // "## Round ranking" from the fixture: alpha (1), beta (2), gamma (3).
  // It's a per-round ranking only — no elimination is parsed or emitted.
  const byRank = [...r.scoreboard].sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0));
  assert.deepEqual(byRank.map(e => e.impl), ['alpha', 'beta', 'gamma']);

  const alpha = r.scoreboard.find(e => e.impl === 'alpha')!;
  assert.equal(alpha.rank, 1);
  assert.equal(alpha.defenderScore, 0);
  assert.equal(alpha.attackerScore, 3);

  const gamma = r.scoreboard.find(e => e.impl === 'gamma')!;
  assert.equal(gamma.rank, 3);
  // elimination is no longer a per-round concept — never parsed
  assert.equal(r.scoreboard.every(e => e.eliminated === undefined), true);
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

test('parseAttackReview: reference oracle rows, with bogus exploits flagged', () => {
  const md = readFileSync(GOLDEN_ORACLE, 'utf-8');
  const r = parseAttackReview(md);

  assert.deepEqual(r.referenceOracle.map(o => o.attacker),
    ['alpha', 'beta', 'gamma']);

  const alpha = r.referenceOracle.find(o => o.attacker === 'alpha')!;
  assert.equal(alpha.exploitsRun, 3);
  assert.deepEqual(alpha.excluded, ['test_escape_fs__x']);

  // beta's suite was clean — "—" parses to an empty exclusion list.
  const beta = r.referenceOracle.find(o => o.attacker === 'beta')!;
  assert.deepEqual(beta.excluded, []);

  const gamma = r.referenceOracle.find(o => o.attacker === 'gamma')!;
  assert.deepEqual(gamma.excluded, ['test_escape_shellinj__e']);
});

test('parseAttackReview: reference oracle is empty for a pre-oracle review', () => {
  // The plain golden predates the reference oracle — no "## Reference oracle".
  const md = readFileSync(GOLDEN, 'utf-8');
  const r = parseAttackReview(md);
  assert.deepEqual(r.referenceOracle, []);
});
