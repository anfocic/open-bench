import { resolve } from 'node:path';

// Astro guarantees CWD is the frontend/ dir during build/dev.
// Repo root is one level up.
export const repoRoot = resolve(process.cwd(), '..');