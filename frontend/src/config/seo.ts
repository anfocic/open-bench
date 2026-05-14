export const seoSite = {
  name: 'open-bench',
  url: 'https://openbenchmark.dev',
  defaultOgImage: '/og-default.png',
  defaultOgImageAlt: 'open-bench — a transparent benchmark for coding LLMs',
  ogImageWidth: 1200,
  ogImageHeight: 630,
  twitterHandle: '@folezof',
  locale: 'en',
  brand: 'open-bench',
  brandSuffix: ' · open-bench',
  description: 'A transparent benchmark for coding LLMs. Real agent loops, hidden tests, full artifacts — every diff, transcript, and cost committed.',
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
    description: 'open-bench is the engine: a SPEC, a hidden test suite, an agent loop, and the full artifact set committed back to the repo. A set of standalone, transparent benchmarks for coding LLMs.',
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
    title: 'Model Royale (retired) · open-bench',
    description: 'Model Royale was the first format on open-bench — a weekly elimination tournament between coding models. It is paused: it surfaced the methodology problems it was meant to. open-bench is now a set of standalone benchmarks.',
    ogImage: '/og-default.png',
    jsonLd: ['organization', 'website'],
  },
  dataset: {
    title: 'Dataset · open-bench',
    description: 'Download open-bench rounds as JSON or CSV. Schema, license, citation.',
    ogImage: '/og-default.png',
    jsonLd: ['organization', 'datasetSite'],
  },
  notesIndex: {
    title: 'Writeups · open-bench',
    description: 'Benchmark retrospectives, model behaviour notes, and post-mortems from open-bench.',
    ogImage: '/og-default.png',
    jsonLd: ['organization', 'collectionPage', 'blog'],
  },
  benchmarks: {
    title: 'Benchmarks · open-bench',
    description: 'Every task in the open-bench corpus. Each one is a SPEC plus a hidden test suite — the contract models are graded against.',
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
