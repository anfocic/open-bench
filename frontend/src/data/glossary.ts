export const glossary = {
  elo: 'Cumulative ELO rating across rounds. Base 1000, K=32. Hard-failed runs excluded from updates.',
  podium: 'Rounds finished in the top 3 by composite peer-judged score.',
  avg: 'Mean composite score (specPeer + qualityPeer) per round, out of 30.',
  costPerRound: 'Mean implementer cost in USD per round.',
  trend: 'Sparkline of composite score across rounds — oldest on the left, newest on the right.',

  total: 'Composite peer-judged score: spec (/15) + quality (/15).',
  spec: 'Peer-judged spec adherence, out of 15. How well the implementation meets SPEC.md.',
  qual: 'Peer-judged code quality, out of 15. Style, structure, idiomatic use of the language.',
  build: 'Whether the implementation builds and runs without crashing. Hard-failed builds are excluded from rankings.',
  tests: 'Hidden tests run after the model finishes. Tests are not visible to the implementer.',
  verdict: 'Reviewer recommendation: ship, fix-then-ship, cleanup, or skip.',

  deltaScore: 'Score difference (model A minus model B) for that round. Positive favours A.',
  deltaCost: 'Cost difference (model A minus model B). Negative means A was cheaper.',
  winner: 'Higher composite score in that round, or the non-DNF model if one hard-failed.',

  score: 'Composite peer-judged score for the round, out of 30.',
  rank: 'Final rank within that round. Hard-failed runs sort to the bottom.',
} as const;

export type GlossaryKey = keyof typeof glossary;
