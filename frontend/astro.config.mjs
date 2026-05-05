import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = fileURLToPath(new URL('..', import.meta.url));

const dateFromRoundUrl = (url) => {
  const m = url.match(/\/round\/(\d{4}-\d{2}-\d{2})(?:\/|$)/);
  return m ? new Date(m[1]) : null;
};

export default defineConfig({
  site: 'https://openbenchmark.dev',
  trailingSlash: 'never',
  integrations: [
    sitemap({
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
