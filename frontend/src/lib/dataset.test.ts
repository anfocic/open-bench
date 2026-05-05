import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { roundsToRows, rowsToCsv, roundsToDataset } from './dataset.ts';
import type { Round, ScoreboardEntry, Run } from '../data/types.ts';

function entry(impl: string, specPeer: number | null, qualityPeer: number | null, passed = true, tests = '9/9', verdict = 'ship'): ScoreboardEntry {
  return {
    impl, hardFail: passed,
    specAll: null, specExpert: null, specPeer,
    qualityAll: null, qualityExpert: null, qualityPeer,
    tests, verdict,
  };
}

function run(model: string, date: string, costUsd: number, wallSec: number | null = 60, loc: number | null = 100, tokens: number | null = 1000, slug: string | null = null): Run {
  return {
    model, round: date, sample: 1, wallSec, costUsd, tokensTotal: tokens,
    inputTokens: null, outputTokens: null, cacheReadTokens: null, loc,
    testExitCode: 0, modelSlug: slug,
  };
}

function round(date: string, scoreboard: ScoreboardEntry[], samples: Run[]): Round {
  return {
    date, samples, scoreboard,
    judgeRanking: [], selfBias: [], agreement: [], perImplDetail: [],
    costEfficiency: [], judgingCost: [],
    crossModelObservations: null, recommendation: null, specChanges: null,
  };
}

test('roundsToRows: row count = sum of scoreboard sizes', () => {
  const r1 = round('2026-05-05', [entry('a', 14, 13), entry('b', 10, 10)], []);
  const r2 = round('2026-05-12', [entry('a', 12, 12), entry('c', 8, 8)], []);
  const rows = roundsToRows([r1, r2]);
  assert.equal(rows.length, 4);
});

test('roundsToRows: composite is sum, null when either component null', () => {
  const r = round('2026-05-05', [
    entry('a', 14, 13),
    entry('b', null, 10),
    entry('c', 10, null),
  ], []);
  const rows = roundsToRows([r]);
  assert.equal(rows.find(x => x.impl === 'a')!.composite, 27);
  assert.equal(rows.find(x => x.impl === 'b')!.composite, null);
  assert.equal(rows.find(x => x.impl === 'c')!.composite, null);
});

test('roundsToRows: aggregates samples + cost + tokens, picks median wall/loc', () => {
  const r = round('2026-05-05',
    [entry('a', 14, 13)],
    [
      run('a', '2026-05-05', 0.10, 30, 80, 500, 'opencode/a-v1'),
      run('a', '2026-05-05', 0.20, 60, 120, 1000),
      run('a', '2026-05-05', 0.30, 90, 100, 1500),
    ]
  );
  const rows = roundsToRows([r]);
  const a = rows[0];
  assert.equal(a.samples, 3);
  assert.equal(a.total_cost_usd.toFixed(2), '0.60');
  assert.equal(a.total_tokens, 3000);
  assert.equal(a.median_wall_seconds, 60);
  assert.equal(a.median_loc, 100);
  assert.equal(a.model_slug, 'opencode/a-v1');
});

test('roundsToRows: sorts by date ascending', () => {
  const r1 = round('2026-05-12', [entry('a', 1, 1)], []);
  const r2 = round('2026-05-05', [entry('a', 2, 2)], []);
  const rows = roundsToRows([r1, r2]);
  assert.equal(rows[0].round, '2026-05-05');
  assert.equal(rows[1].round, '2026-05-12');
});

test('roundsToRows: passed_hard_fail mirrors legacy hardFail field', () => {
  const r = round('2026-05-05', [
    entry('a', 14, 13, true),
    entry('b', 0, 0, false),
  ], []);
  const rows = roundsToRows([r]);
  assert.equal(rows.find(x => x.impl === 'a')!.passed_hard_fail, true);
  assert.equal(rows.find(x => x.impl === 'b')!.passed_hard_fail, false);
});

test('rowsToCsv: header + comma separation, no trailing newline', () => {
  const r = round('2026-05-05', [entry('a', 14, 13)], [run('a', '2026-05-05', 0.1)]);
  const csv = rowsToCsv(roundsToRows([r]));
  const lines = csv.split('\n');
  assert.ok(lines[0].startsWith('round,impl,model_slug,'));
  assert.equal(lines.length, 2);
  assert.notEqual(csv.endsWith('\n'), true);
});

test('rowsToCsv: escapes commas, quotes, newlines', () => {
  const r = round('2026-05-05', [
    entry('weird', 14, 13, true, '9/9', 'has, comma'),
    entry('quoty', 12, 12, true, '9/9', 'has "quote" inside'),
  ], []);
  const csv = rowsToCsv(roundsToRows([r]));
  assert.ok(csv.includes('"has, comma"'));
  assert.ok(csv.includes('"has ""quote"" inside"'));
});

test('roundsToDataset: meta populated, flat length matches', () => {
  const r1 = round('2026-05-05', [entry('a', 14, 13), entry('b', 10, 10)], []);
  const ds = roundsToDataset([r1], { generatedAt: '2026-05-06T00:00:00Z' });
  assert.equal(ds.meta.rounds, 1);
  assert.equal(ds.meta.rows, 2);
  assert.equal(ds.meta.schema_version, 1);
  assert.equal(ds.meta.license, 'MIT');
  assert.equal(ds.meta.generated_at, '2026-05-06T00:00:00Z');
  assert.equal(ds.flat.length, 2);
  assert.equal(ds.rounds.length, 1);
});
