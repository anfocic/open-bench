import type { MetaJson, Run } from '../data/types';

export function parseMeta(json: unknown): Run | null {
  if (!json || typeof json !== 'object') return null;
  const m = json as Record<string, unknown>;
  if (typeof m.model !== 'string' || typeof m.slug !== 'string') return null;

  const slug = m.slug as string;
  const dateMatch = slug.match(/(\d{4}-\d{2}-\d{2})/);
  const date = dateMatch ? dateMatch[1] : '';
  const sampleMatch = slug.match(/-r(\d+)$/);
  const sample = sampleMatch ? parseInt(sampleMatch[1], 10) : 1;

  return {
    model: m.model as string,
    round: date,
    sample,
    wallSec: typeof m.model_wall_clock_seconds === 'number' ? m.model_wall_clock_seconds : null,
    costUsd: typeof m.cost_usd === 'number' ? m.cost_usd : null,
    tokensTotal: typeof m.tokens_total === 'number' ? m.tokens_total : null,
    inputTokens: typeof m.input_tokens === 'number' ? m.input_tokens : null,
    outputTokens: typeof m.output_tokens === 'number' ? m.output_tokens : null,
    cacheReadTokens: typeof m.cache_read_tokens === 'number' ? m.cache_read_tokens : null,
    loc: typeof m.sandbox_py_loc === 'number' ? m.sandbox_py_loc : null,
    testExitCode: typeof m.test_exit_code === 'number' ? m.test_exit_code : null,
    modelSlug: typeof m.model_slug === 'string' ? m.model_slug : null,
  };
}
