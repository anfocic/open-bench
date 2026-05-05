import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';
import { fileURLToPath } from 'node:url';
import { generateOg } from './scripts/gen-og.mjs';

const REPO_ROOT = fileURLToPath(new URL('..', import.meta.url));

const ogIntegration = {
  name: 'open-bench-og',
  hooks: {
    'astro:build:start': async ({ logger }) => {
      const n = await generateOg();
      logger.info(`generated ${n} OG image${n === 1 ? '' : 's'}`);
    },
  },
};

const dateFromRoundUrl = (url) => {
  const m = url.match(/\/round\/(\d{4}-\d{2}-\d{2})(?:\/|$)/);
  return m ? new Date(m[1]) : null;
};

export default defineConfig({
  site: 'https://openbenchmark.dev',
  trailingSlash: 'never',
  integrations: [
    ogIntegration,
    mdx(),
    sitemap({
      filter: (page) => !page.includes('/embed'),
      serialize(item) {
        const u = item.url;
        const roundDate = dateFromRoundUrl(u);
        if (roundDate) {
          item.lastmod = roundDate.toISOString();
          item.changefreq = u.includes('/round/') && !u.match(/\/round\/[^/]+$/) ? 'monthly' : 'weekly';
          item.priority = u.match(/\/round\/[^/]+$/) ? 0.8 : 0.5;
          return item;
        }
        if (u === 'https://openbenchmark.dev/' || u === 'https://openbenchmark.dev') {
          item.changefreq = 'weekly';
          item.priority = 1.0;
        } else if (u.endsWith('/model-royale')) {
          item.changefreq = 'weekly';
          item.priority = 0.9;
        } else if (u.endsWith('/round')) {
          item.changefreq = 'weekly';
          item.priority = 0.7;
        } else if (u.endsWith('/leaderboard')) {
          item.changefreq = 'weekly';
          item.priority = 0.9;
        } else if (u.includes('/model/')) {
          item.changefreq = 'weekly';
          item.priority = 0.6;
        } else if (u.endsWith('/notes')) {
          item.changefreq = 'weekly';
          item.priority = 0.8;
        } else if (u.includes('/notes/')) {
          item.changefreq = 'monthly';
          item.priority = 0.7;
        } else if (u.endsWith('/dataset')) {
          item.changefreq = 'weekly';
          item.priority = 0.8;
        } else if (u.endsWith('/changelog')) {
          item.changefreq = 'weekly';
          item.priority = 0.6;
        } else if (u.endsWith('/about')) {
          item.changefreq = 'yearly';
          item.priority = 0.3;
        } else if (u.includes('/task/')) {
          item.changefreq = 'monthly';
          item.priority = 0.4;
        }
        return item;
      },
    }),
  ],
  build: { format: 'directory' },
  vite: {
    server: {
      watch: {
        ignored: [
          `!${REPO_ROOT}/results/reviews/**`,
          `!${REPO_ROOT}/builds/**/meta.json`,
          `!${REPO_ROOT}/bench/config.json`,
        ],
      },
    },
  },
});
