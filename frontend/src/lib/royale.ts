import { getCollection } from 'astro:content';

// Tasks that are part of the Model Royale tournament (vs standalone
// benchmarks). Round 1 = `sandbox` (Build), round 2 = `break-sandbox`
// (Break). `ROYALE_TASK` stays the canonical default for callers that
// need a single fallback task name.
export const ROYALE_TASK = 'sandbox';
export const ROYALE_TASKS = new Set(['sandbox', 'break-sandbox']);

export function isRoyaleTask(task: string): boolean {
  return ROYALE_TASKS.has(task);
}

export async function getRoyaleRounds() {
  const entries = await getCollection('rounds');
  return entries.filter(e => isRoyaleTask(e.data.task));
}
