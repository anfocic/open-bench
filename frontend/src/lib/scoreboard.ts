import type { ScoreboardEntry, Run } from '../data/types';

// Round 2 ("Break"): the winner is the rank-1 model from the
// defense-weighted combined ranking; score reported is its attacker score.
export function findAttackChampion(entries: ScoreboardEntry[]): { impl: string; score: number } {
  const winner = entries.find(e => e.rank === 1);
  return winner ? { impl: winner.impl, score: winner.attackerScore ?? 0 }
                : { impl: '—', score: 0 };
}

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