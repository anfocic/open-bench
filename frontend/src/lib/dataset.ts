import type { Round, Run } from '../data/types';

export const SCHEMA_VERSION = 1;

export interface DatasetRow {
  round: string;
  impl: string;
  model_slug: string | null;
  spec_peer: number | null;
  quality_peer: number | null;
  composite: number | null;
  passed_hard_fail: boolean;
  tests: string;
  verdict: string;
  samples: number;
  total_cost_usd: number;
  total_tokens: number;
  median_wall_seconds: number | null;
  median_loc: number | null;
}

export interface DatasetMeta {
  generated_at: string;
  schema_version: number;
  license: string;
  source: string;
  rounds: number;
  rows: number;
}

function median(nums: number[]): number | null {
  if (nums.length === 0) return null;
  const sorted = [...nums].sort((a, b) => a - b);
  const mid = sorted.length / 2;
  return sorted.length % 2 === 0
    ? (sorted[mid - 1] + sorted[mid]) / 2
    : sorted[Math.floor(mid)];
}

function samplesFor(samples: Run[], impl: string): Run[] {
  return samples.filter(s => s.model === impl);
}

export function roundsToRows(rounds: Round[]): DatasetRow[] {
  const rows: DatasetRow[] = [];
  const sorted = [...rounds].sort((a, b) => a.date.localeCompare(b.date));
  for (const r of sorted) {
    for (const e of r.scoreboard) {
      const runs = samplesFor(r.samples, e.impl);
      const composite = e.specPeer != null && e.qualityPeer != null
        ? e.specPeer + e.qualityPeer
        : null;
      const totalCost = runs.reduce((s, x) => s + (x.costUsd ?? 0), 0);
      const totalTokens = runs.reduce((s, x) => s + (x.tokensTotal ?? 0), 0);
      const wallSecs = runs.map(x => x.wallSec).filter((v): v is number => v != null && v >= 0);
      const locs = runs.map(x => x.loc).filter((v): v is number => v != null);
      const slug = runs.find(x => x.modelSlug)?.modelSlug ?? null;
      rows.push({
        round: r.date,
        impl: e.impl,
        model_slug: slug,
        spec_peer: e.specPeer,
        quality_peer: e.qualityPeer,
        composite,
        passed_hard_fail: e.hardFail,
        tests: e.tests,
        verdict: e.verdict,
        samples: runs.length,
        total_cost_usd: totalCost,
        total_tokens: totalTokens,
        median_wall_seconds: median(wallSecs),
        median_loc: median(locs),
      });
    }
  }
  return rows;
}

const CSV_COLUMNS: (keyof DatasetRow)[] = [
  'round', 'impl', 'model_slug',
  'spec_peer', 'quality_peer', 'composite',
  'passed_hard_fail', 'tests', 'verdict',
  'samples', 'total_cost_usd', 'total_tokens',
  'median_wall_seconds', 'median_loc',
];

function csvCell(v: unknown): string {
  if (v === null || v === undefined) return '';
  const s = typeof v === 'number' ? String(v) : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function rowsToCsv(rows: DatasetRow[]): string {
  const header = CSV_COLUMNS.join(',');
  const body = rows.map(r => CSV_COLUMNS.map(c => csvCell(r[c])).join(','));
  return [header, ...body].join('\n');
}

export interface Dataset {
  meta: DatasetMeta;
  rounds: Round[];
  flat: DatasetRow[];
}

export function roundsToDataset(rounds: Round[], opts?: { generatedAt?: string }): Dataset {
  const flat = roundsToRows(rounds);
  return {
    meta: {
      generated_at: opts?.generatedAt ?? new Date().toISOString(),
      schema_version: SCHEMA_VERSION,
      license: 'MIT',
      source: 'https://openbenchmark.dev/dataset',
      rounds: rounds.length,
      rows: flat.length,
    },
    rounds: [...rounds].sort((a, b) => a.date.localeCompare(b.date)),
    flat,
  };
}
