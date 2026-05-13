import { getRoyaleRounds } from '../../../lib/royale';
import { roundsToRows, SCHEMA_VERSION } from '../../../lib/dataset';

export const prerender = true;

export async function getStaticPaths() {
  const entries = await getRoyaleRounds();
  return entries.map(e => ({ params: { date: e.data.date }, props: { round: e.data } }));
}

export async function GET({ props }: { props: { round: import('../../data/types').Round } }) {
  const { round } = props;
  const flat = roundsToRows([round]);
  const body = {
    meta: {
      generated_at: new Date().toISOString(),
      schema_version: SCHEMA_VERSION,
      license: 'MIT',
      source: `https://openbenchmark.dev/round/${round.date}`,
      round: round.date,
      rows: flat.length,
    },
    round,
    flat,
  };
  return new Response(JSON.stringify(body, null, 2), {
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'public, max-age=300',
    },
  });
}
