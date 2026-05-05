import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { parseMeta } from '../lib/parse-meta';
import { parseReview, type ParsedReview } from '../lib/parse-review';
import type { Round, Run, Config, MetaJson } from './types';

// astro build/dev cwd is the frontend/ dir
const ROOT = process.cwd();

function readJSON<T>(relPath: string): T | null {
  try {
    const data = readFileSync(resolve(ROOT, relPath), 'utf-8');
    return JSON.parse(data) as T;
  } catch {
    return null;
  }
}

function readFile(relPath: string): string | null {
  try {
    return readFileSync(resolve(ROOT, relPath), 'utf-8');
  } catch {
    return null;
  }
}

function loadRuns(): Run[] {
  const runs: Run[] = [];
  const buildsDir = resolve(ROOT, '../builds');
  let modelDirs: string[];
  try {
    modelDirs = readdirSync(buildsDir).filter(d => !d.startsWith('.'));
  } catch {
    return [];
  }
  for (const model of modelDirs) {
    const roundsDir = resolve(buildsDir, model, 'rounds');
    let roundDirs: string[];
    try {
      roundDirs = readdirSync(roundsDir);
    } catch {
      continue;
    }
    for (const rd of roundDirs) {
      const metaPath = resolve(roundsDir, rd, 'meta.json');
      if (!existsSync(metaPath)) continue;
      try {
        const raw = JSON.parse(readFileSync(metaPath, 'utf-8')) as MetaJson;
        raw.model = model;
        const run = parseMeta(raw);
        if (run) runs.push(run);
      } catch {
        continue;
      }
    }
  }
  return runs;
}

function loadConfig(): Config | null {
  return readJSON<Config>('../bench/config.json');
}

function loadReview(date: string): ParsedReview | null {
  const md = readFile(`../results/reviews/sandbox-${date}.md`);
  if (!md) return null;
  return parseReview(md);
}

export function loadRounds(): Round[] {
  const allRuns = loadRuns();
  const config = loadConfig();

  const roundDates = [...new Set(allRuns.map(r => r.round))].sort().reverse();

  if (roundDates.length === 0) return [];

  return roundDates.map(date => {
    const samples = allRuns.filter(r => r.round === date);
    const review = loadReview(date);

    return {
      date,
      samples,
      scoreboard: review?.scoreboard ?? [],
      judgeRanking: review?.judgeRanking ?? [],
      selfBias: review?.selfBias ?? [],
      agreement: review?.agreement ?? [],
      perImplDetail: review?.perImplDetail ?? [],
      costEfficiency: review?.costEfficiency ?? [],
      judgingCost: review?.judgingCost ?? [],
      crossModelObservations: review?.crossModelObservations ?? null,
      recommendation: review?.recommendation ?? null,
      specChanges: review?.specChanges ?? null,
    };
  });
}
