import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import type { MetaJson, Run } from './types';
import { parseMeta } from '../lib/parse-meta';

// astro build / dev cwd is the frontend/ dir; repo root is one up.
const REPO_ROOT = resolve(process.cwd(), '..');

export interface RunArtifacts {
  model: string;
  date: string;
  sample: number;
  runPath: string;
  meta: Run | null;
  sandboxPy: string | null;
  diffPatch: string | null;
  testOutput: string | null;
  transcript: string | null;
}

export interface RunIndex {
  model: string;
  date: string;
  sample: number;
  runPath: string;
}

function readOptional(p: string): string | null {
  try { return existsSync(p) ? readFileSync(p, 'utf-8') : null; }
  catch { return null; }
}

export function loadRunArtifacts(model: string, roundDir: string): RunArtifacts | null {
  const fullDir = resolve(REPO_ROOT, 'builds', model, 'rounds', roundDir);
  if (!existsSync(fullDir)) return null;

  const m = roundDir.match(/^sandbox-(\d{4}-\d{2}-\d{2})(?:-r(\d+))?$/);
  if (!m) return null;
  const date = m[1];
  const sample = m[2] ? Number(m[2]) : 1;

  const metaRaw = readOptional(resolve(fullDir, 'meta.json'));
  let meta: Run | null = null;
  if (metaRaw) {
    try {
      const parsed = JSON.parse(metaRaw) as MetaJson;
      parsed.model = model;
      meta = parseMeta(parsed);
    } catch { /* ignore */ }
  }

  return {
    model,
    date,
    sample,
    runPath: `builds/${model}/rounds/${roundDir}`,
    meta,
    sandboxPy: readOptional(resolve(fullDir, 'sandbox.py')),
    diffPatch: readOptional(resolve(fullDir, 'diff.patch')),
    testOutput: readOptional(resolve(fullDir, 'test-output.txt')),
    transcript: readOptional(resolve(fullDir, 'transcript.md')),
  };
}

export function listRuns(): RunIndex[] {
  const buildsDir = resolve(REPO_ROOT, 'builds');
  const out: RunIndex[] = [];
  let models: string[];
  try { models = readdirSync(buildsDir).filter(d => !d.startsWith('.')); }
  catch { return []; }
  for (const model of models) {
    const roundsDir = resolve(buildsDir, model, 'rounds');
    let dirs: string[];
    try { dirs = readdirSync(roundsDir); }
    catch { continue; }
    for (const rd of dirs) {
      const m = rd.match(/^sandbox-(\d{4}-\d{2}-\d{2})(?:-r(\d+))?$/);
      if (!m) continue;
      out.push({
        model,
        date: m[1],
        sample: m[2] ? Number(m[2]) : 1,
        runPath: `builds/${model}/rounds/${rd}`,
      });
    }
  }
  return out;
}

export function pickCanonicalRun(model: string, date: string, runPathHint?: string): RunArtifacts | null {
  if (runPathHint) {
    const dir = runPathHint.replace(/^builds\/[^/]+\/rounds\//, '');
    const a = loadRunArtifacts(model, dir);
    if (a) return a;
  }
  const all = listRuns().filter(r => r.model === model && r.date === date);
  all.sort((a, b) => a.sample - b.sample);
  if (all.length === 0) return null;
  const dir = all[0].runPath.split('/').pop()!;
  return loadRunArtifacts(model, dir);
}
