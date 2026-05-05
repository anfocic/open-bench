#!/usr/bin/env node
import { mkdirSync, readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(__dirname, '..');
const REPO = resolve(FRONTEND, '..');
const OG_DIR = resolve(FRONTEND, 'public/og');
const FONT_REG = readFileSync(resolve(FRONTEND, 'og-assets/inter-regular.woff'));
const FONT_BOLD = readFileSync(resolve(FRONTEND, 'og-assets/inter-bold.woff'));

mkdirSync(OG_DIR, { recursive: true });

const BG = '#0d1117';
const FG = '#e6edf3';
const MUTED = '#8b949e';
const BLUE = '#58a6ff';
const GOLD = '#d29922';

function extractSection(md, heading) {
  const sections = md.split(/\n(?=## )/);
  for (const s of sections) if (s.startsWith(`## ${heading}`)) return s.replace(/^## .+\n?/, '').trim();
  return '';
}

function parseScoreboard(section) {
  const lines = section.split('\n').filter(l => l.trim().startsWith('|'));
  if (lines.length < 3) return [];
  return lines.slice(2).map(line => {
    const cols = line.split('|').slice(1, -1).map(c => c.trim());
    if (cols.length < 10) return null;
    const num = (s) => { const c = s.replace(/,/g, ''); const n = Number(c); return isNaN(n) ? null : n; };
    const specPeer = num(cols[4]);
    const qualityPeer = num(cols[7]);
    const composite = (specPeer ?? 0) + (qualityPeer ?? 0);
    return { impl: cols[0], composite };
  }).filter(Boolean);
}

function parseTotalCost(md) {
  const section = extractSection(md, 'Cost & efficiency');
  const lines = section.split('\n').filter(l => l.trim().startsWith('|'));
  let total = 0;
  for (const line of lines.slice(2)) {
    const cols = line.split('|').slice(1, -1).map(c => c.trim());
    const price = cols[5]?.replace(/^\$/, '');
    const n = Number(price);
    if (!isNaN(n)) total += n;
  }
  return total;
}

function loadRounds() {
  const dir = resolve(REPO, 'results/reviews');
  const files = readdirSync(dir).filter(f => /^sandbox-\d{4}-\d{2}-\d{2}\.md$/.test(f));
  return files.map(f => {
    const date = f.replace(/^sandbox-/, '').replace(/\.md$/, '');
    const md = readFileSync(resolve(dir, f), 'utf-8');
    const scoreboard = parseScoreboard(extractSection(md, 'Scoreboard'));
    const totalCost = parseTotalCost(md);
    return { date, scoreboard, totalCost };
  });
}

function card(round) {
  const sorted = [...round.scoreboard].sort((a, b) => b.composite - a.composite);
  const top = sorted[0];
  const champion = top?.impl ?? '—';
  const score = top?.composite ? `${top.composite.toFixed(1)} / 30` : '';
  const modelCount = round.scoreboard.length;
  const totalCost = round.totalCost.toFixed(2);

  return {
    type: 'div',
    props: {
      style: {
        width: 1200, height: 630, display: 'flex', flexDirection: 'column',
        background: BG, color: FG, padding: '64px 80px', fontFamily: 'Inter',
        justifyContent: 'space-between',
      },
      children: [
        {
          type: 'div',
          props: {
            style: { display: 'flex', flexDirection: 'column', gap: 8 },
            children: [
              { type: 'div', props: { style: { fontSize: 28, color: MUTED, letterSpacing: -0.5 }, children: 'open-bench' } },
              { type: 'div', props: { style: { fontSize: 72, fontWeight: 700, letterSpacing: -1.5 }, children: `Round ${round.date}` } },
            ],
          },
        },
        {
          type: 'div',
          props: {
            style: { display: 'flex', flexDirection: 'column', gap: 12 },
            children: [
              { type: 'div', props: { style: { fontSize: 36, color: MUTED }, children: 'Winner' } },
              {
                type: 'div',
                props: {
                  style: { display: 'flex', alignItems: 'baseline', gap: 24 },
                  children: [
                    { type: 'div', props: { style: { fontSize: 64, fontWeight: 700, color: GOLD }, children: champion } },
                    score && { type: 'div', props: { style: { fontSize: 32, color: BLUE }, children: score } },
                  ].filter(Boolean),
                },
              },
            ],
          },
        },
        {
          type: 'div',
          props: {
            style: { display: 'flex', gap: 48, fontSize: 26, color: MUTED },
            children: [
              { type: 'div', props: { children: `${modelCount} models` } },
              { type: 'div', props: { children: `$${totalCost} total` } },
            ],
          },
        },
      ],
    },
  };
}

const rounds = loadRounds();
if (rounds.length === 0) { console.error('No rounds found.'); process.exit(1); }

for (const round of rounds) {
  const svg = await satori(card(round), {
    width: 1200, height: 630,
    fonts: [
      { name: 'Inter', data: FONT_REG, weight: 400, style: 'normal' },
      { name: 'Inter', data: FONT_BOLD, weight: 700, style: 'normal' },
    ],
  });
  const png = new Resvg(svg).render().asPng();
  const out = resolve(OG_DIR, `round-${round.date}.png`);
  writeFileSync(out, png);
  console.log(`wrote ${out}`);
}
