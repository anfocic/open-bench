import { getCollection } from 'astro:content';

export const ROYALE_TASK = 'sandbox';

export async function getRoyaleRounds() {
  const entries = await getCollection('rounds');
  return entries.filter(e => e.data.task === ROYALE_TASK);
}
