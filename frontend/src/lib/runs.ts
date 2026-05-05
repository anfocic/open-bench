import { resolve } from 'node:path';
import type { MetaJson, Run, RunIndex } from '../data/types';
import { parseMeta } from './parse';
import { repoRoot } from './paths';
import { readOptional, listDirs } from './io';

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

export function loadRunArtifacts(model: string, roundDir: string): RunArtifacts | null {
  const fullDir = resolve(repoRoot, 'builds', model, 'rounds', roundDir);
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
  const buildsDir = resolve(repoRoot, 'builds');
  const out: RunIndex[] = [];
  const models = listDirs(buildsDir);
  for (const model of models) {
    const roundsDir = resolve(buildsDir, model, 'rounds');
    const dirs = listDirs(roundsDir);
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