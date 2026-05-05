import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = fileURLToPath(new URL('..', import.meta.url));

export default defineConfig({
  site: 'https://openbenchmark.dev',
  trailingSlash: 'never',
  integrations: [sitemap()],
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
