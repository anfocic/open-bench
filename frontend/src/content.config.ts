import { defineCollection } from 'astro:content';
import { roundsLoader } from './lib/loader';
import { RoundSchema } from './data/types';

export const collections = {
  rounds: defineCollection({
    loader: roundsLoader,
    schema: RoundSchema,
  }),
};