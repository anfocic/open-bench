import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
import { roundsLoader } from './lib/loader';
import { RoundSchema } from './data/types';

const dateString = z.preprocess(
  (v) => v instanceof Date ? v.toISOString().slice(0, 10) : v,
  z.string(),
);

const NoteSchema = z.object({
  title: z.string(),
  summary: z.string(),
  publishedAt: dateString,
  round: dateString.nullable().default(null),
  author: z.string().default('fole'),
  draft: z.boolean().default(false),
  ogImageOverride: z.string().nullable().default(null),
});

export const collections = {
  rounds: defineCollection({
    loader: roundsLoader,
    schema: RoundSchema,
  }),
  notes: defineCollection({
    loader: glob({ pattern: '**/*.mdx', base: './src/content/notes' }),
    schema: NoteSchema,
  }),
};
