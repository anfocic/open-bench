import { seoSite } from '../config/seo';
import type { JsonLdKey } from '../config/seo';

type Json = Record<string, unknown>;

export interface BreadcrumbItem {
  name: string;
  path: string;
}

export interface ScoreboardLite {
  impl: string;
  score: number;
}

export interface RoundLite {
  date: string;
  modelCount: number;
  cost: number;
  winner: string;
  winnerScore: number;
  task: string;
  scoreboard: ScoreboardLite[];
}

const url = (path: string) => seoSite.url + (path.startsWith('/') ? path : '/' + path);

function organization(): Json {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: seoSite.name,
    url: seoSite.url,
    logo: url('/favicon.svg'),
    description: seoSite.description,
  };
}

function website(): Json {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: seoSite.name,
    url: seoSite.url,
    description: seoSite.description,
    inLanguage: seoSite.locale,
  };
}

function datasetSite(): Json {
  return {
    '@context': 'https://schema.org',
    '@type': 'Dataset',
    name: 'open-bench results',
    description: seoSite.description,
    url: seoSite.url,
    keywords: [...seoSite.keywords],
    isAccessibleForFree: true,
    license: 'https://opensource.org/licenses/MIT',
    creator: { '@type': 'Organization', name: seoSite.name, url: seoSite.url },
  };
}

function datasetRound(d: { round: RoundLite; canonicalPath: string }): Json {
  const r = d.round;
  return {
    '@context': 'https://schema.org',
    '@type': 'Dataset',
    name: `open-bench round ${r.date}`,
    description: `Round ${r.date}: ${r.modelCount} models on ${r.task}. Winner ${r.winner} at ${r.winnerScore}/30.`,
    url: url(d.canonicalPath),
    datePublished: r.date,
    keywords: [...seoSite.keywords, r.task, r.winner],
    isAccessibleForFree: true,
    creator: { '@type': 'Organization', name: seoSite.name, url: seoSite.url },
  };
}

function leaderboard(d: { round: RoundLite; canonicalPath: string }): Json {
  const r = d.round;
  return {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: `open-bench leaderboard — round ${r.date}`,
    url: url(d.canonicalPath),
    numberOfItems: r.scoreboard.length,
    itemListOrder: 'https://schema.org/ItemListOrderDescending',
    itemListElement: r.scoreboard.map((row, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: row.impl,
      url: url(`/round/${r.date}/${row.impl}`),
    })),
  };
}

function aboutPage(d: { canonicalPath: string }): Json {
  return {
    '@context': 'https://schema.org',
    '@type': 'AboutPage',
    name: 'About open-bench',
    url: url(d.canonicalPath),
    description: seoPagesAboutDescription,
  };
}

const seoPagesAboutDescription =
  'How the open-bench harness works: identical SPEC.md, identical sandbox, identical budget. Hidden pytest gate, peer + expert review, self-bias measured.';

function softwareSourceCode(d: { impl: string; date: string; canonicalPath: string }): Json {
  return {
    '@context': 'https://schema.org',
    '@type': 'SoftwareSourceCode',
    name: `${d.impl} — open-bench round ${d.date}`,
    url: url(d.canonicalPath),
    programmingLanguage: 'Python',
    codeRepository: seoSite.url,
    creator: { '@type': 'Organization', name: d.impl },
    isPartOf: { '@type': 'Dataset', name: `open-bench round ${d.date}`, url: url(`/round/${d.date}`) },
  };
}

function techArticle(d: { task: string; canonicalPath: string }): Json {
  return {
    '@context': 'https://schema.org',
    '@type': 'TechArticle',
    headline: `${d.task} task — open-bench`,
    url: url(d.canonicalPath),
    inLanguage: seoSite.locale,
    publisher: { '@type': 'Organization', name: seoSite.name, url: seoSite.url },
  };
}

function breadcrumb(d: { trail: BreadcrumbItem[] }): Json {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: d.trail.map((item, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: item.name,
      item: url(item.path),
    })),
  };
}

const builders: Record<JsonLdKey, (data: Json) => Json> = {
  organization: () => organization(),
  website: () => website(),
  datasetSite: () => datasetSite(),
  datasetRound: (d) => datasetRound(d as never),
  aboutPage: (d) => aboutPage(d as never),
  leaderboard: (d) => leaderboard(d as never),
  softwareSourceCode: (d) => softwareSourceCode(d as never),
  techArticle: (d) => techArticle(d as never),
  breadcrumb: (d) => breadcrumb(d as never),
};

export function buildJsonLd(keys: readonly JsonLdKey[], data: Record<string, unknown> = {}): Json[] {
  return keys.map((k) => builders[k](data as Json));
}
