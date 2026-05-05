import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { parseMeta } from './parse.ts';

test('parseMeta: full valid input', () => {
  const result = parseMeta({
    task: 'sandbox',
    model: 'kimi',
    slug: 'sandbox-kimi-2026-05-05',
    started_at: '2026-05-05T10:00:00Z',
    ended_at: '2026-05-05T10:30:00Z',
    test_exit_code: 0,
    sandbox_py_loc: 142,
    cost_usd: 0.042,
    tokens_total: 15000,
    input_tokens: 12000,
    output_tokens: 3000,
    cache_read_tokens: 5000,
    model_wall_clock_seconds: 1800,
    model_slug: 'opencode-go/kimi-k2.6',
  });
  assert.deepEqual(result, {
    model: 'kimi',
    round: '2026-05-05',
    sample: 1,
    wallSec: 1800,
    costUsd: 0.042,
    tokensTotal: 15000,
    inputTokens: 12000,
    outputTokens: 3000,
    cacheReadTokens: 5000,
    loc: 142,
    testExitCode: 0,
    modelSlug: 'opencode-go/kimi-k2.6',
  });
});

test('parseMeta: extracts sample number from -r suffix', () => {
  const result = parseMeta({
    model: 'deepseek',
    slug: 'sandbox-deepseek-2026-05-05-r3',
    model_wall_clock_seconds: 600,
    cost_usd: 0.01,
    tokens_total: 8000,
    test_exit_code: 1,
  });
  assert.equal(result?.sample, 3);
  assert.equal(result?.round, '2026-05-05');
});

test('parseMeta: null for missing numeric fields', () => {
  const result = parseMeta({
    model: 'glm',
    slug: 'sandbox-glm-2026-05-05',
  });
  assert.equal(result?.wallSec, null);
  assert.equal(result?.costUsd, null);
  assert.equal(result?.tokensTotal, null);
  assert.equal(result?.inputTokens, null);
  assert.equal(result?.outputTokens, null);
  assert.equal(result?.cacheReadTokens, null);
  assert.equal(result?.loc, null);
  assert.equal(result?.testExitCode, null);
  assert.equal(result?.modelSlug, null);
});

test('parseMeta: null on non-object input', () => {
  assert.equal(parseMeta(null), null);
  assert.equal(parseMeta('string'), null);
  assert.equal(parseMeta(42), null);
});

test('parseMeta: null when model or slug missing', () => {
  assert.equal(parseMeta({ slug: 'x' }), null);
  assert.equal(parseMeta({ model: 'x' }), null);
  assert.equal(parseMeta({}), null);
});

test('parseMeta: empty round when slug has no date', () => {
  const result = parseMeta({
    model: 'kimi',
    slug: 'sandbox-kimi',
  });
  assert.equal(result?.round, '');
  assert.equal(result?.sample, 1);
});

test('parseMeta: ignores wrong-typed numeric fields', () => {
  const result = parseMeta({
    model: 'kimi',
    slug: 'sandbox-kimi-2026-05-05',
    cost_usd: 'free',
    tokens_total: null,
    model_wall_clock_seconds: undefined,
  });
  assert.equal(result?.costUsd, null);
  assert.equal(result?.tokensTotal, null);
  assert.equal(result?.wallSec, null);
});