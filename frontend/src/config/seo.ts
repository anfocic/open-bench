export const seoSite = {
  name: 'open-bench',
  url: 'https://openbenchmark.dev',
  defaultOgImage: '/og-default.png',
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
  | 'aboutPage'
  | 'leaderboard'
  | 'softwareSourceCode'
  | 'techArticle'
  | 'breadcrumb';

export interface StaticPageSeo {
  readonly title: string;
  readonly description: string;
  readonly ogImage: string;
  readonly jsonLd: readonly JsonLdKey[];
}

export interface TemplateSeo {
  readonly titleTpl: string;
  readonly descTpl: string;
  readonly ogTpl: string;
  readonly ogType: 'website' | 'article';
  readonly jsonLd: readonly JsonLdKey[];
}

export const seoPages = {
  home: {
    title: 'open-bench — weekly LLM coding battle royale',
    description: 'Every week, every major coding LLM gets the same blank repo and the same SPEC.md. Hidden tests gate. Models judge each other. Cost and wall-clock tracked. Loser is eliminated.',
    ogImage: '/og-default.png',
    jsonLd: ['organization', 'website', 'datasetSite'],
  },
  about: {
    title: 'About · open-bench',
    description: 'How the open-bench harness works: identical SPEC.md, identical sandbox, identical budget. Hidden pytest gate, peer + expert review, self-bias measured, cheapest run wins ties.',
    ogImage: '/og-default.png',
    jsonLd: ['organization', 'aboutPage'],
  },
} as const satisfies Record<string, StaticPageSeo>;

export type StaticPageKey = keyof typeof seoPages;

export const seoTemplates = {
  round: {
    titleTpl: 'Round {date}{winnerSuffix}{brandSuffix}',
    descTpl: 'Round {date}: {modelCount} models on {task}. Winner {winner} at {score}/30. {modelCount} models, ${cost} spend.',
    ogTpl: '/og/round-{date}.png',
    ogType: 'article',
    jsonLd: ['organization', 'datasetRound', 'leaderboard', 'breadcrumb'],
  },
  impl: {
    titleTpl: '{impl} · round {date}{brandSuffix}',
    descTpl: 'Full artifacts (code, diff, hidden tests, transcript) for {impl} in round {date}.',
    ogTpl: '/og/round-{date}.png',
    ogType: 'article',
    jsonLd: ['organization', 'softwareSourceCode', 'breadcrumb'],
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
