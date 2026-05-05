import type { ScoreboardEntry, Run } from '../data/types';

export function findChampion(entries: ScoreboardEntry[]): { impl: string; score: number } {
  return entries.reduce(
    (best, e) => {
      const score = (e.specPeer ?? 0) + (e.qualityPeer ?? 0);
      return score > best.score ? { impl: e.impl, score } : best;
    },
    { impl: '—', score: 0 },
  );
}

export function uniqueModelCount(samples: Run[]): number {
  return new Set(samples.map(s => s.model)).size;
}

export function totalCost(samples: Run[]): number {
  return samples.reduce((sum, s) => sum + (s.costUsd ?? 0), 0);
}