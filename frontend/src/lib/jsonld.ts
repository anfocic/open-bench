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

function roundArticle(d: { round: RoundLite; canonicalPath: string; ogImage?: string }): Json {
  const r = d.round;
  const image = d.ogImage ? url(d.ogImage) : url(`/og/round-${r.date}.png`);
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: `open-bench round ${r.date} — ${r.winner} wins`,
    datePublished: r.date,
    author: { '@type': 'Organization', name: seoSite.name, url: seoSite.url },
    publisher: { '@type': 'Organization', name: seoSite.name, url: seoSite.url, logo: url('/favicon.svg') },
    image,
    mainEntityOfPage: url(d.canonicalPath),
    description: `Round ${r.date}: ${r.modelCount} models on ${r.task}. Winner ${r.winner} at ${r.winnerScore}/30.`,
  };
}

function collectionPage(d: { canonicalPath: string }): Json {
  return {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: 'open-bench rounds',
    url: url(d.canonicalPath),
    description: 'Every round of open-bench, newest first.',
    isPartOf: { '@type': 'WebSite', name: seoSite.name, url: seoSite.url },
  };
}

function blog(d: { notes: { slug: string; title: string; publishedAt: string }[]; canonicalPath: string }): Json {
  return {
    '@context': 'https://schema.org',
    '@type': 'Blog',
    name: 'open-bench writeups',
    url: url(d.canonicalPath),
    description: 'Round retrospectives, model behaviour notes, and post-mortems from open-bench.',
    publisher: { '@type': 'Organization', name: seoSite.name, url: seoSite.url },
    blogPost: d.notes.map((n) => ({
      '@type': 'BlogPosting',
      headline: n.title,
      url: url(`/notes/${n.slug}`),
      datePublished: n.publishedAt,
    })),
  };
}

function blogPosting(d: { note: { title: string; summary: string; publishedAt: string; author: string; slug: string }; canonicalPath: string; ogImage?: string }): Json {
  const image = d.ogImage ? url(d.ogImage.startsWith('http') ? d.ogImage.slice(seoSite.url.length) : d.ogImage) : url(`/og/note-${d.note.slug}.png`);
  return {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: d.note.title,
    description: d.note.summary,
    datePublished: d.note.publishedAt,
    dateModified: d.note.publishedAt,
    author: { '@type': 'Person', name: d.note.author },
    publisher: { '@type': 'Organization', name: seoSite.name, url: seoSite.url, logo: url('/favicon.svg') },
    image,
    mainEntityOfPage: url(d.canonicalPath),
  };
}

function leaderboardCumulative(d: { standings: { impl: string; elo: number }[]; canonicalPath: string }): Json {
  return {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: 'open-bench cumulative standings',
    url: url(d.canonicalPath),
    numberOfItems: d.standings.length,
    itemListOrder: 'https://schema.org/ItemListOrderDescending',
    itemListElement: d.standings.map((s, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: s.impl,
      url: url(`/model/${s.impl}`),
    })),
  };
}

function roundList(d: { rounds: { date: string; winner: string }[] }): Json {
  return {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    name: 'open-bench rounds',
    numberOfItems: d.rounds.length,
    itemListOrder: 'https://schema.org/ItemListOrderDescending',
    itemListElement: d.rounds.map((r, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: `Round ${r.date} — ${r.winner}`,
      url: url(`/round/${r.date}`),
    })),
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
  roundArticle: (d) => roundArticle(d as never),
  aboutPage: (d) => aboutPage(d as never),
  leaderboard: (d) => leaderboard(d as never),
  softwareSourceCode: (d) => softwareSourceCode(d as never),
  techArticle: (d) => techArticle(d as never),
  breadcrumb: (d) => breadcrumb(d as never),
  collectionPage: (d) => collectionPage(d as never),
  roundList: (d) => roundList(d as never),
  leaderboardCumulative: (d) => leaderboardCumulative(d as never),
  blog: (d) => blog(d as never),
  blogPosting: (d) => blogPosting(d as never),
};

export function buildJsonLd(keys: readonly JsonLdKey[], data: Record<string, unknown> = {}): Json[] {
  return keys.map((k) => builders[k](data as Json));
}
