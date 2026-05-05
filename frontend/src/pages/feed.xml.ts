import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';
import { seoSite } from '../config/seo';
import { findChampion, uniqueModelCount, totalCost } from '../lib/scoreboard';
import { fmtNum } from '../lib/format';

interface FeedItem {
  title: string;
  link: string;
  pubDate: Date;
  description: string;
  sortKey: string;
  tieBreak: number;
}

export async function GET(context: APIContext) {
  const roundEntries = await getCollection('rounds');
  const noteEntries = await getCollection('notes', n => !n.data.draft);

  const items: FeedItem[] = [];

  for (const entry of roundEntries) {
    const r = entry.data;
    const champ = findChampion(r.scoreboard);
    const modelCount = uniqueModelCount(r.samples);
    const cost = totalCost(r.samples);
    items.push({
      title: `Round ${r.date} — ${champ.impl}`,
      link: `/round/${r.date}`,
      pubDate: new Date(r.date),
      description: `Round ${r.date}: ${modelCount} models on sandbox. Winner ${champ.impl} at ${fmtNum(champ.score, 1)}/30. $${fmtNum(cost, 2)} total spend.`,
      sortKey: r.date,
      tieBreak: 0,
    });
  }

  for (const entry of noteEntries) {
    const n = entry.data;
    items.push({
      title: n.title,
      link: `/notes/${entry.id}`,
      pubDate: new Date(n.publishedAt),
      description: n.summary,
      sortKey: n.publishedAt,
      tieBreak: 1,
    });
  }

  items.sort((a, b) => {
    const k = b.sortKey.localeCompare(a.sortKey);
    return k !== 0 ? k : b.tieBreak - a.tieBreak;
  });

  return rss({
    title: `${seoSite.name} — rounds & writeups`,
    description: seoSite.description,
    site: context.site ?? seoSite.url,
    items: items.map(({ title, link, pubDate, description }) => ({ title, link, pubDate, description })),
    customData: `<language>${seoSite.locale}</language>`,
  });
}
