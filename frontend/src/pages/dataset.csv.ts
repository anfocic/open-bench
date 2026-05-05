import { getCollection } from 'astro:content';
import { roundsToRows, rowsToCsv } from '../lib/dataset';

export const prerender = true;

export async function GET() {
  const entries = await getCollection('rounds');
  const rounds = entries.sort((a, b) => a.id.localeCompare(b.id)).map(e => e.data);
  const csv = rowsToCsv(roundsToRows(rounds));
  return new Response(csv + '\n', {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Cache-Control': 'public, max-age=300',
    },
  });
}
