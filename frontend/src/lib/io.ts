import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { resolve } from 'node:path';

export function readOptional(p: string): string | null {
  try {
    return existsSync(p) ? readFileSync(p, 'utf-8') : null;
  } catch {
    return null;
  }
}

export function listDirs(dir: string): string[] {
  try {
    return readdirSync(dir).filter(d => !d.startsWith('.') && statSync(resolve(dir, d)).isDirectory());
  } catch {
    return [];
  }
}

export function readJsonOptional<T>(p: string): T | null {
  const raw = readOptional(p);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}