import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';
import { seoSite } from '../config/seo';
import { findChampion, uniqueModelCount, totalCost } from '../lib/scoreboard';
import { fmtNum } from '../lib/format';

export async function GET(context: APIContext) {
  const entries = await getCollection('rounds');
  const rounds = entries.sort((a, b) => b.id.localeCompare(a.id));

  return rss({
    title: `${seoSite.name} — rounds`,
    description: seoSite.description,
    site: context.site ?? seoSite.url,
    items: rounds.map((entry) => {
      const r = entry.data;
      const champ = findChampion(r.scoreboard);
      const modelCount = uniqueModelCount(r.samples);
      const cost = totalCost(r.samples);
      const description = `Round ${r.date}: ${modelCount} models on sandbox. Winner ${champ.impl} at ${fmtNum(champ.score, 1)}/30. $${fmtNum(cost, 2)} total spend.`;
      return {
        title: `Round ${r.date} — ${champ.impl}`,
        link: `/round/${r.date}`,
        pubDate: new Date(r.date),
        description,
      };
    }),
    customData: `<language>${seoSite.locale}</language>`,
  });
}
