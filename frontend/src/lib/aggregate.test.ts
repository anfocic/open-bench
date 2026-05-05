import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { computeStandings, computeElo, sparkline, compareModels, allPairs } from './aggregate.ts';
import type { Round, ScoreboardEntry, Run } from '../data/types.ts';

function entry(impl: string, specPeer: number, qualityPeer: number, dnf = false): ScoreboardEntry {
  return {
    impl, hardFail: !dnf, specAll: null, specExpert: null, specPeer,
    qualityAll: null, qualityExpert: null, qualityPeer,
    tests: '', verdict: '',
  };
}

function run(model: string, date: string, costUsd: number): Run {
  return {
    model, round: date, sample: 1, wallSec: null, costUsd, tokensTotal: null,
    inputTokens: null, outputTokens: null, cacheReadTokens: null, loc: null,
    testExitCode: 0, modelSlug: null,
  };
}

function round(date: string, scoreboard: ScoreboardEntry[], samples: Run[] = []): Round {
  return {
    date, samples, scoreboard,
    judgeRanking: [], selfBias: [], agreement: [], perImplDetail: [],
    costEfficiency: [], judgingCost: [],
    crossModelObservations: null, recommendation: null, specChanges: null,
  };
}

test('computeStandings: single round, winner has 1 win', () => {
  const r = round('2026-05-05', [
    entry('kimi', 14, 13),
    entry('glm', 12, 12),
    entry('qwen', 10, 10),
  ], [run('kimi', '2026-05-05', 0.10), run('glm', '2026-05-05', 0.20), run('qwen', '2026-05-05', 0.05)]);
  const s = computeStandings([r]);
  assert.equal(s.length, 3);
  const kimi = s.find(x => x.impl === 'kimi')!;
  assert.equal(kimi.wins, 1);
  assert.equal(kimi.rounds, 1);
  assert.equal(kimi.podium, 1);
  assert.equal(kimi.totalCost, 0.10);
  assert.equal(kimi.avgScore, 27);
  assert.equal(kimi.history.length, 1);
  assert.equal(kimi.history[0].rank, 1);
});

test('computeStandings: hardFail excluded from wins/podium but still counted in rounds', () => {
  const r = round('2026-05-05', [
    entry('kimi', 0, 0, true),
    entry('glm', 12, 12),
  ]);
  const s = computeStandings([r]);
  const kimi = s.find(x => x.impl === 'kimi')!;
  assert.equal(kimi.wins, 0);
  assert.equal(kimi.podium, 0);
  assert.equal(kimi.rounds, 1);
  const glm = s.find(x => x.impl === 'glm')!;
  assert.equal(glm.wins, 1);
});

test('computeStandings: 3 rounds, model joining mid-season', () => {
  const r1 = round('2026-05-05', [entry('kimi', 14, 13), entry('glm', 12, 12)]);
  const r2 = round('2026-05-12', [entry('kimi', 13, 13), entry('glm', 14, 14)]);
  const r3 = round('2026-05-19', [entry('kimi', 12, 12), entry('glm', 13, 13), entry('newcomer', 15, 15)]);
  const s = computeStandings([r1, r2, r3]);
  const kimi = s.find(x => x.impl === 'kimi')!;
  const glm = s.find(x => x.impl === 'glm')!;
  const nc = s.find(x => x.impl === 'newcomer')!;
  assert.equal(kimi.rounds, 3);
  assert.equal(glm.rounds, 3);
  assert.equal(nc.rounds, 1);
  assert.equal(kimi.wins, 1);
  assert.equal(glm.wins, 1);
  assert.equal(nc.wins, 1);
});

test('computeElo: winner ELO > loser ELO after one round', () => {
  const r = round('2026-05-05', [entry('a', 14, 13), entry('b', 10, 10)]);
  const elo = computeElo([r]);
  assert.ok(elo.a > 1000);
  assert.ok(elo.b < 1000);
  assert.equal(Math.round(elo.a + elo.b), 2000);
});

test('computeElo: tie keeps both at base', () => {
  const r = round('2026-05-05', [entry('a', 12, 12), entry('b', 12, 12)]);
  const elo = computeElo([r]);
  assert.equal(elo.a, 1000);
  assert.equal(elo.b, 1000);
});

test('computeElo: hardFail does not affect ELO', () => {
  const r = round('2026-05-05', [entry('a', 14, 14), entry('b', 0, 0, true)]);
  const elo = computeElo([r]);
  assert.equal(elo.a, 1000);
  assert.equal(elo.b, 1000);
});

test('computeStandings: sorted by ELO desc', () => {
  const r1 = round('2026-05-05', [entry('a', 14, 13), entry('b', 10, 10), entry('c', 5, 5)]);
  const s = computeStandings([r1]);
  assert.equal(s[0].impl, 'a');
  assert.equal(s[2].impl, 'c');
  assert.ok(s[0].elo >= s[1].elo);
  assert.ok(s[1].elo >= s[2].elo);
});

test('compareModels: head-to-head across overlapping rounds', () => {
  const r1 = round('2026-05-05', [entry('a', 14, 13), entry('b', 12, 12)],
    [run('a', '2026-05-05', 0.10), run('b', '2026-05-05', 0.20)]);
  const r2 = round('2026-05-12', [entry('a', 10, 10), entry('b', 14, 13)],
    [run('a', '2026-05-12', 0.15), run('b', '2026-05-12', 0.25)]);
  const cmp = compareModels('a', 'b', [r1, r2])!;
  assert.equal(cmp.common.length, 2);
  assert.equal(cmp.aWins, 1);
  assert.equal(cmp.bWins, 1);
  assert.equal(cmp.ties, 0);
  assert.equal(cmp.aTotalCost, 0.25);
  assert.equal(cmp.bTotalCost, 0.45);
});

test('compareModels: rounds where only one attended split into aOnly/bOnly', () => {
  const r1 = round('2026-05-05', [entry('a', 14, 13), entry('b', 12, 12)]);
  const r2 = round('2026-05-12', [entry('a', 14, 13)]);
  const r3 = round('2026-05-19', [entry('b', 14, 13)]);
  const cmp = compareModels('a', 'b', [r1, r2, r3])!;
  assert.equal(cmp.common.length, 1);
  assert.equal(cmp.aOnly.length, 1);
  assert.equal(cmp.bOnly.length, 1);
  assert.equal(cmp.aOnly[0].date, '2026-05-12');
  assert.equal(cmp.bOnly[0].date, '2026-05-19');
});

test('compareModels: hardFail counts as loss for the failed model', () => {
  const r = round('2026-05-05', [entry('a', 14, 13), entry('b', 0, 0, true)]);
  const cmp = compareModels('a', 'b', [r])!;
  assert.equal(cmp.aWins, 1);
  assert.equal(cmp.bWins, 0);
  assert.equal(cmp.common[0].winner, 'a');
});

test('compareModels: ties counted separately', () => {
  const r = round('2026-05-05', [entry('a', 12, 12), entry('b', 12, 12)]);
  const cmp = compareModels('a', 'b', [r])!;
  assert.equal(cmp.ties, 1);
  assert.equal(cmp.aWins, 0);
  assert.equal(cmp.bWins, 0);
  assert.equal(cmp.common[0].winner, 'tie');
});

test('compareModels: returns null for unknown impl', () => {
  const r = round('2026-05-05', [entry('a', 14, 13), entry('b', 12, 12)]);
  assert.equal(compareModels('a', 'ghost', [r]), null);
});

test('allPairs: sorted, unordered, no self-pairs', () => {
  const p = allPairs(['c', 'a', 'b']);
  assert.deepEqual(p, [['a', 'b'], ['a', 'c'], ['b', 'c']]);
});

test('sparkline: handles flat series and varying series', () => {
  assert.equal(sparkline([]), '');
  const flat = sparkline([
    { date: 'd1', score: 10, rank: 1, dnf: false, cost: 0 },
    { date: 'd2', score: 10, rank: 1, dnf: false, cost: 0 },
  ]);
  assert.equal(flat.length, 2);
  const varying = sparkline([
    { date: 'd1', score: 1, rank: 3, dnf: false, cost: 0 },
    { date: 'd2', score: 5, rank: 2, dnf: false, cost: 0 },
    { date: 'd3', score: 10, rank: 1, dnf: false, cost: 0 },
  ]);
  assert.equal(varying.length, 3);
});
