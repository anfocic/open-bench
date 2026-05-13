import { resolve } from 'node:path';
import { repoRoot } from './paths';
import { readJsonOptional } from './io';

interface BenchConfig {
  implementers?: string[];
  slugs?: Record<string, string>;
}

let cache: Record<string, string> | null = null;

export function displaySlug(slug: string | null | undefined): string {
  if (!slug) return '';
  const i = slug.indexOf('/');
  return i === -1 ? slug : slug.slice(i + 1);
}

export function loadSlugs(): Record<string, string> {
  if (cache) return cache;
  const cfg = readJsonOptional<BenchConfig>(resolve(repoRoot, 'bench/config.json'));
  const raw = cfg?.slugs ?? {};
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(raw)) out[k] = displaySlug(v);
  cache = out;
  return cache;
}
