import type { Round, ScoreboardEntry, Run } from '../data/types';

export interface ModelHistoryEntry {
  date: string;
  score: number;
  rank: number;
  dnf: boolean;
  cost: number;
}

export interface ModelStanding {
  impl: string;
  rounds: number;
  wins: number;
  podium: number;
  avgScore: number;
  totalCost: number;
  avgCost: number;
  winRate: number;
  elo: number;
  lastSeen: string;
  history: ModelHistoryEntry[];
}

const ELO_BASE = 1000;
const ELO_K = 32;

function composite(e: ScoreboardEntry): number {
  return (e.specPeer ?? 0) + (e.qualityPeer ?? 0);
}

function rankOfRound(round: Round): { impl: string; score: number; dnf: boolean }[] {
  return [...round.scoreboard]
    .map(e => ({ impl: e.impl, score: composite(e), dnf: !e.hardFail }))
    .sort((a, b) => {
      if (a.dnf !== b.dnf) return a.dnf ? 1 : -1;
      return b.score - a.score;
    });
}

function costForImpl(samples: Run[], impl: string): number {
  return samples.filter(s => s.model === impl).reduce((sum, s) => sum + (s.costUsd ?? 0), 0);
}

export function computeElo(rounds: Round[]): Record<string, number> {
  const elo: Record<string, number> = {};
  const sorted = [...rounds].sort((a, b) => a.date.localeCompare(b.date));
  for (const round of sorted) {
    const ranked = rankOfRound(round).filter(r => !r.dnf);
    for (const r of ranked) if (elo[r.impl] === undefined) elo[r.impl] = ELO_BASE;
    for (const r of round.scoreboard) if (elo[r.impl] === undefined) elo[r.impl] = ELO_BASE;

    const updates: Record<string, number> = {};
    for (let i = 0; i < ranked.length; i++) {
      for (let j = i + 1; j < ranked.length; j++) {
        const a = ranked[i];
        const b = ranked[j];
        const ra = elo[a.impl];
        const rb = elo[b.impl];
        const ea = 1 / (1 + Math.pow(10, (rb - ra) / 400));
        const eb = 1 - ea;
        const sa = a.score === b.score ? 0.5 : 1;
        const sb = a.score === b.score ? 0.5 : 0;
        updates[a.impl] = (updates[a.impl] ?? 0) + ELO_K * (sa - ea);
        updates[b.impl] = (updates[b.impl] ?? 0) + ELO_K * (sb - eb);
      }
    }
    for (const [impl, delta] of Object.entries(updates)) elo[impl] += delta;
  }
  return elo;
}

export function computeStandings(rounds: Round[]): ModelStanding[] {
  const sorted = [...rounds].sort((a, b) => a.date.localeCompare(b.date));
  const elo = computeElo(rounds);
  const acc = new Map<string, {
    rounds: number;
    wins: number;
    podium: number;
    scoreSum: number;
    totalCost: number;
    lastSeen: string;
    history: ModelHistoryEntry[];
  }>();

  for (const round of sorted) {
    const ranked = rankOfRound(round);
    ranked.forEach((r, idx) => {
      const rank = idx + 1;
      const cost = costForImpl(round.samples, r.impl);
      const entry = acc.get(r.impl) ?? {
        rounds: 0, wins: 0, podium: 0, scoreSum: 0, totalCost: 0, lastSeen: '', history: [],
      };
      entry.rounds += 1;
      entry.scoreSum += r.score;
      entry.totalCost += cost;
      entry.lastSeen = round.date;
      if (!r.dnf) {
        if (rank === 1) entry.wins += 1;
        if (rank <= 3) entry.podium += 1;
      }
      entry.history.push({ date: round.date, score: r.score, rank, dnf: r.dnf, cost });
      acc.set(r.impl, entry);
    });
  }

  const standings: ModelStanding[] = [];
  for (const [impl, e] of acc.entries()) {
    standings.push({
      impl,
      rounds: e.rounds,
      wins: e.wins,
      podium: e.podium,
      avgScore: e.rounds > 0 ? e.scoreSum / e.rounds : 0,
      totalCost: e.totalCost,
      avgCost: e.rounds > 0 ? e.totalCost / e.rounds : 0,
      winRate: e.rounds > 0 ? e.wins / e.rounds : 0,
      elo: elo[impl] ?? ELO_BASE,
      lastSeen: e.lastSeen,
      history: e.history,
    });
  }
  return standings.sort((a, b) => b.elo - a.elo);
}

const SPARKS = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];
export function sparkline(history: ModelHistoryEntry[]): string {
  if (history.length === 0) return '';
  const scores = history.map(h => h.score);
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  const span = max - min;
  if (span === 0) return SPARKS[4].repeat(scores.length);
  return scores
    .map(s => {
      const idx = Math.round(((s - min) / span) * (SPARKS.length - 1));
      return SPARKS[idx];
    })
    .join('');
}
