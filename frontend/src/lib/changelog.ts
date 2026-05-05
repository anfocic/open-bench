import type { Round } from '../data/types';

export interface ChangelogEntry {
  date: string;
  roundNumber: number;
  lineup: string[];
  added: string[];
  removed: string[];
  specChanges: string | null;
  recommendation: string | null;
}

function isPlaceholder(s: string | null): boolean {
  if (!s) return true;
  return s.trim().startsWith('(human reviewer fills');
}

export function buildChangelog(rounds: Round[]): ChangelogEntry[] {
  const sorted = [...rounds].sort((a, b) => a.date.localeCompare(b.date));
  return sorted.map((r, i) => {
    const lineup = r.scoreboard.map(e => e.impl).sort();
    const prev = i > 0 ? new Set(sorted[i - 1].scoreboard.map(e => e.impl)) : null;
    const curr = new Set(lineup);
    const added = prev ? lineup.filter(x => !prev.has(x)) : [];
    const removed = prev ? [...prev].filter(x => !curr.has(x)).sort() : [];
    return {
      date: r.date,
      roundNumber: i + 1,
      lineup,
      added,
      removed,
      specChanges: isPlaceholder(r.specChanges) ? null : r.specChanges,
      recommendation: isPlaceholder(r.recommendation) ? null : r.recommendation,
    };
  });
}
