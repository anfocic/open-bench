export const seoSite = {
  name: 'open-bench',
  url: 'https://openbenchmark.dev',
  defaultOgImage: '/og-default.png',
  defaultOgImageAlt: 'open-bench — weekly LLM coding battle royale',
  ogImageWidth: 1200,
  ogImageHeight: 630,
  twitterHandle: '@folezof',
  locale: 'en',
  brand: 'open-bench',
  brandSuffix: ' · open-bench',
  description: 'Weekly battle royale benchmark for open-weight coding LLMs. Hidden tests, peer review, cost and wall-clock tracked.',
  keywords: [
    'LLM benchmark',
    'coding benchmark',
    'open-weight models',
    'AI model comparison',
    'code generation benchmark',
    'LLM leaderboard',
  ],
} as const;

export type JsonLdKey =
  | 'organization'
  | 'website'
  | 'datasetSite'
  | 'datasetRound'
  | 'roundArticle'
  | 'aboutPage'
  | 'leaderboard'
  | 'softwareSourceCode'
  | 'techArticle'
  | 'breadcrumb'
  | 'collectionPage'
  | 'roundList'
  | 'leaderboardCumulative'
  | 'blog'
  | 'blogPosting';

export interface StaticPageSeo {
  readonly title: string;
  readonly description: string;
  readonly ogImage: string;
  readonly ogImageAlt?: string;
  readonly jsonLd: readonly JsonLdKey[];
}

export interface TemplateSeo {
  readonly titleTpl: string;
  readonly descTpl: string;
  readonly ogTpl: string;
  readonly ogAltTpl?: string;
  readonly ogType: 'website' | 'article';
  readonly jsonLd: readonly JsonLdKey[];
}

export const seoPages = {
  home: {
    title: 'open-bench — a benchmark harness for coding LLMs',
    description: 'open-bench is the engine: a SPEC, a hidden test suite, an agent loop, peer judges, and the full artifact set committed back to the repo. Model Royale is the flagship consumer.',
    ogImage: '/og-default.png',
    jsonLd: ['organization', 'website', 'datasetSite'],
  },
  about: {
    title: 'About · open-bench',
    description: 'Why open-bench exists: a coding-LLM benchmark harness built around real agent loops, hidden tests, peer review, and committed artifacts.',
    ogImage: '/og-default.png',
    jsonLd: ['organization', 'aboutPage'],
  },
  modelRoyale: {
    title: 'Model Royale · open-bench',
    description: 'Model Royale: weekly elimination-style coding tournament between selected open-source coding models, run on the open-bench harness. Lineup, rules, current task, lineage.',
    ogImage: '/og-default.png',
    jsonLd: ['organization', 'website'],
  },
  roundIndex: {
    title: 'Rounds · open-bench',
    description: 'Every round of open-bench, newest first. Weekly LLM coding battle royale archive — winners, scoreboards, full artifacts.',
    ogImage: '/og-default.png',
    jsonLd: ['organization', 'collectionPage', 'roundList'],
  },
  leaderboard: {
    title: 'Leaderboard · open-bench',
    description: 'Cumulative standings across every round. ELO, win rate, podium count, cost per round.',
    ogImage: '/og/leaderboard.png',
    jsonLd: ['organization', 'collectionPage', 'leaderboardCumulative'],
  },
  dataset: {
    title: 'Dataset · open-bench',
    description: 'Download open-bench rounds as JSON or CSV. Schema, license, citation.',
    ogImage: '/og-default.png',
    jsonLd: ['organization', 'datasetSite'],
  },
  changelog: {
    title: 'Methodology changelog · open-bench',
    description: 'What changed and when: spec edits, lineup additions and eliminations, rubric tweaks. Round-to-round comparability, made auditable.',
    ogImage: '/og-default.png',
    jsonLd: ['organization', 'collectionPage'],
  },
  notesIndex: {
    title: 'Writeups · open-bench',
    description: 'Round retrospectives, model behaviour notes, and post-mortems from open-bench.',
    ogImage: '/og-default.png',
    jsonLd: ['organization', 'collectionPage', 'blog'],
  },
  compareIndex: {
    title: 'Compare models · open-bench',
    description: 'Pick any two models and compare them head-to-head: ELO, scores per round, win/loss record, total spend.',
    ogImage: '/og-default.png',
    jsonLd: ['organization', 'collectionPage'],
  },
} as const satisfies Record<string, StaticPageSeo>;

export type StaticPageKey = keyof typeof seoPages;

export const seoTemplates = {
  round: {
    titleTpl: 'Round {date}{winnerSuffix}{brandSuffix}',
    descTpl: 'Round {date}: {modelCount} models on {task}. Winner {winner} at {score}/30. {modelCount} models, ${cost} spend.',
    ogTpl: '/og/round-{date}.png',
    ogAltTpl: 'open-bench round {date} — winner {winner}',
    ogType: 'article',
    jsonLd: ['organization', 'datasetRound', 'roundArticle', 'leaderboard', 'breadcrumb'],
  },
  impl: {
    titleTpl: '{impl} · round {date}{brandSuffix}',
    descTpl: 'Full artifacts (code, diff, hidden tests, transcript) for {impl} in round {date}.',
    ogTpl: '/og/round-{date}.png',
    ogAltTpl: 'open-bench round {date} — {impl} artifacts',
    ogType: 'article',
    jsonLd: ['organization', 'softwareSourceCode', 'breadcrumb'],
  },
  model: {
    titleTpl: '{impl} · model career{brandSuffix}',
    descTpl: '{impl} on open-bench: {rounds} round{roundSuffix}, {wins} win{winSuffix}, ELO {elo}, ${totalCost} total spend.',
    ogTpl: '/og/model-{impl}.png',
    ogAltTpl: 'open-bench — {impl} model career',
    ogType: 'article',
    jsonLd: ['organization', 'breadcrumb'],
  },
  note: {
    titleTpl: '{title}{brandSuffix}',
    descTpl: '{summary}',
    ogTpl: '/og/note-{slug}.png',
    ogAltTpl: 'open-bench writeup — {title}',
    ogType: 'article',
    jsonLd: ['organization', 'blogPosting', 'breadcrumb'],
  },
  compare: {
    titleTpl: '{a} vs {b}{brandSuffix}',
    descTpl: '{a} (ELO {aElo}) vs {b} (ELO {bElo}) head-to-head: {commonRounds} shared round{commonSuffix}, {aWins}-{bWins}-{ties} record.',
    ogTpl: '/og-default.png',
    ogAltTpl: 'open-bench compare — {a} vs {b}',
    ogType: 'website',
    jsonLd: ['organization', 'breadcrumb'],
  },
  task: {
    titleTpl: '{task} task{brandSuffix}',
    descTpl: 'Full spec, prompt, and rubric for the {task} task — the contract every model is judged against.',
    ogTpl: '/og-default.png',
    ogType: 'article',
    jsonLd: ['organization', 'techArticle', 'breadcrumb'],
  },
} as const satisfies Record<string, TemplateSeo>;

export type TemplateKey = keyof typeof seoTemplates;
