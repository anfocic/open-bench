export function withViewTransition(fn: () => void): void {
  const doc = document as Document & { startViewTransition?: (cb: () => void) => void };
  if (doc.startViewTransition) doc.startViewTransition(fn);
  else fn();
}