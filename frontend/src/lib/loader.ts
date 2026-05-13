import type { Loader } from 'astro:content';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { parseMeta, parseReview } from './parse';
import { repoRoot } from './paths';
import { listDirs, readJsonOptional } from './io';
import type { MetaJson } from '../data/types';

function loadRuns(): Map<string, ReturnType<typeof parseMeta>[]> {
  const byDate = new Map<string, ReturnType<typeof parseMeta>[]>();
  const buildsDir = resolve(repoRoot, 'builds');
  const modelDirs = listDirs(buildsDir);

  for (const model of modelDirs) {
    const roundsDir = resolve(buildsDir, model, 'rounds');
    const roundDirs = listDirs(roundsDir);
    for (const rd of roundDirs) {
      const metaPath = resolve(roundsDir, rd, 'meta.json');
      const raw = readJsonOptional<MetaJson>(metaPath);
      if (!raw) continue;
      raw.model = model;
      const run = parseMeta(raw);
      if (!run) continue;
      const runs = byDate.get(run.round) ?? [];
      runs.push(run);
      byDate.set(run.round, runs);
    }
  }
  return byDate;
}

function loadReview(task: string, date: string) {
  const mdPath = resolve(repoRoot, `results/reviews/${task}-${date}.md`);
  try {
    const md = readFileSync(mdPath, 'utf-8');
    return { review: parseReview(md), filePath: `../results/reviews/${task}-${date}.md` };
  } catch {
    return null;
  }
}

export const roundsLoader: Loader = {
  name: 'rounds',
  async load(context) {
    context.store.clear();

    const runsByDate = loadRuns();
    const dates = [...runsByDate.keys()].sort().reverse();

    for (const date of dates) {
      const samples = runsByDate.get(date)!;
      const task = samples[0]?.task ?? 'sandbox';
      const rev = loadReview(task, date);

      const roundData = {
        date,
        task,
        samples,
        scoreboard: rev?.review?.scoreboard ?? [],
        judgeRanking: rev?.review?.judgeRanking ?? [],
        selfBias: rev?.review?.selfBias ?? [],
        agreement: rev?.review?.agreement ?? [],
        perImplDetail: rev?.review?.perImplDetail ?? [],
        costEfficiency: rev?.review?.costEfficiency ?? [],
        judgingCost: rev?.review?.judgingCost ?? [],
        crossModelObservations: rev?.review?.crossModelObservations ?? null,
        recommendation: rev?.review?.recommendation ?? null,
        specChanges: rev?.review?.specChanges ?? null,
      };

      const parsed = await context.parseData({
        id: date,
        data: roundData,
        filePath: rev?.filePath,
      });

      context.store.set({
        id: date,
        data: parsed,
        filePath: rev?.filePath,
      });
    }
  },
};