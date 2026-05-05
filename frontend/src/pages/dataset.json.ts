import { getCollection } from 'astro:content';
import { roundsToDataset } from '../lib/dataset';

export const prerender = true;

export async function GET() {
  const entries = await getCollection('rounds');
  const rounds = entries.sort((a, b) => a.id.localeCompare(b.id)).map(e => e.data);
  const dataset = roundsToDataset(rounds);
  return new Response(JSON.stringify(dataset, null, 2), {
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'public, max-age=300',
    },
  });
}
