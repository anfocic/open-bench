import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { buildChangelog } from './changelog.ts';
import type { Round, ScoreboardEntry } from '../data/types.ts';

function entry(impl: string): ScoreboardEntry {
  return {
    impl, hardFail: true,
    specAll: null, specExpert: null, specPeer: 10,
    qualityAll: null, qualityExpert: null, qualityPeer: 10,
    tests: '9/9', verdict: 'ship',
  };
}

function round(date: string, impls: string[], specChanges: string | null = null, recommendation: string | null = null): Round {
  return {
    date,
    samples: [],
    scoreboard: impls.map(entry),
    judgeRanking: [], selfBias: [], agreement: [], perImplDetail: [],
    costEfficiency: [], judgingCost: [],
    crossModelObservations: null,
    recommendation,
    specChanges,
  };
}

test('buildChangelog: round 1 has no added/removed (baseline)', () => {
  const r1 = round('2026-05-05', ['a', 'b', 'c']);
  const log = buildChangelog([r1]);
  assert.equal(log.length, 1);
  assert.equal(log[0].roundNumber, 1);
  assert.deepEqual(log[0].added, []);
  assert.deepEqual(log[0].removed, []);
  assert.deepEqual(log[0].lineup, ['a', 'b', 'c']);
});

test('buildChangelog: detects added and removed across rounds', () => {
  const r1 = round('2026-05-05', ['a', 'b', 'c']);
  const r2 = round('2026-05-12', ['b', 'c', 'd']);
  const log = buildChangelog([r1, r2]);
  assert.deepEqual(log[1].added, ['d']);
  assert.deepEqual(log[1].removed, ['a']);
});

test('buildChangelog: sorts ascending by date regardless of input order', () => {
  const r1 = round('2026-05-12', ['x']);
  const r2 = round('2026-05-05', ['y']);
  const log = buildChangelog([r1, r2]);
  assert.equal(log[0].date, '2026-05-05');
  assert.equal(log[1].date, '2026-05-12');
});

test('buildChangelog: strips placeholder text', () => {
  const r = round('2026-05-05', ['a'], '(human reviewer fills — actual changes)', '(human reviewer fills — pick a basis)');
  const log = buildChangelog([r]);
  assert.equal(log[0].specChanges, null);
  assert.equal(log[0].recommendation, null);
});

test('buildChangelog: keeps real specChanges text', () => {
  const r = round('2026-05-05', ['a'], 'Tightened the contract on `Sandbox.exec()` return type.');
  const log = buildChangelog([r]);
  assert.ok(log[0].specChanges?.startsWith('Tightened'));
});
