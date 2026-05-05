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

function parseCostPerImpl(md) {
  const section = extractSection(md, 'Cost & efficiency');
  const lines = section.split('\n').filter(l => l.trim().startsWith('|'));
  const out = {};
  for (const line of lines.slice(2)) {
    const cols = line.split('|').slice(1, -1).map(c => c.trim());
    const impl = cols[0];
    const price = cols[5]?.replace(/^\$/, '');
    const n = Number(price);
    if (impl && !isNaN(n)) out[impl] = n;
  }
  return out;
}

function parseFrontmatter(src) {
  const m = src.match(/^---\n([\s\S]*?)\n---/);
  if (!m) return null;
  const out = {};
  for (const line of m[1].split('\n')) {
    const kv = line.match(/^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$/);
    if (!kv) continue;
    let v = kv[2].trim();
    if (v === 'true') out[kv[1]] = true;
    else if (v === 'false') out[kv[1]] = false;
    else if (v === 'null' || v === '~' || v === '') out[kv[1]] = null;
    else if (/^-?\d+(\.\d+)?$/.test(v)) out[kv[1]] = Number(v);
    else out[kv[1]] = v.replace(/^['"]|['"]$/g, '');
  }
  return out;
}

function loadNotes() {
  const dir = resolve(FRONTEND, 'src/content/notes');
  let files;
  try { files = readdirSync(dir); } catch { return []; }
  return files
    .filter(f => f.endsWith('.mdx'))
    .map(f => {
      const slug = f.replace(/\.mdx$/, '');
      const md = readFileSync(resolve(dir, f), 'utf-8');
      const fm = parseFrontmatter(md);
      if (!fm || !fm.title) return null;
      return { slug, ...fm };
    })
    .filter(Boolean);
}

function noteCard(note) {
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
              { type: 'div', props: { style: { fontSize: 26, color: BLUE, letterSpacing: 1, textTransform: 'uppercase' }, children: 'open-bench / writeup' } },
              { type: 'div', props: { style: { fontSize: 60, fontWeight: 700, lineHeight: 1.15, letterSpacing: -1.5, marginTop: 8 }, children: note.title } },
            ],
          },
        },
        {
          type: 'div',
          props: {
            style: { fontSize: 28, color: MUTED, lineHeight: 1.4, maxWidth: 980 },
            children: note.summary,
          },
        },
        {
          type: 'div',
          props: {
            style: { display: 'flex', gap: 24, fontSize: 24, color: MUTED, alignItems: 'baseline' },
            children: [
              { type: 'div', props: { style: { color: GOLD }, children: note.author ?? 'fole' } },
              { type: 'div', props: { children: '·' } },
              { type: 'div', props: { children: note.publishedAt ?? '' } },
              note.round && { type: 'div', props: { children: '·' } },
              note.round && { type: 'div', props: { children: `round ${note.round}` } },
            ].filter(Boolean),
          },
        },
      ],
    },
  };
}

const ELO_BASE = 1000;
const ELO_K = 32;

function computeElo(rounds) {
  const elo = {};
  const sorted = [...rounds].sort((a, b) => a.date.localeCompare(b.date));
  for (const round of sorted) {
    const ranked = [...round.scoreboard].sort((a, b) => b.composite - a.composite);
    for (const r of ranked) if (elo[r.impl] === undefined) elo[r.impl] = ELO_BASE;
    const updates = {};
    for (let i = 0; i < ranked.length; i++) {
      for (let j = i + 1; j < ranked.length; j++) {
        const a = ranked[i], b = ranked[j];
        const ea = 1 / (1 + Math.pow(10, (elo[b.impl] - elo[a.impl]) / 400));
        const eb = 1 - ea;
        const sa = a.composite === b.composite ? 0.5 : 1;
        const sb = a.composite === b.composite ? 0.5 : 0;
        updates[a.impl] = (updates[a.impl] ?? 0) + ELO_K * (sa - ea);
        updates[b.impl] = (updates[b.impl] ?? 0) + ELO_K * (sb - eb);
      }
    }
    for (const [impl, delta] of Object.entries(updates)) elo[impl] += delta;
  }
  return elo;
}

function computeStandings(rounds) {
  const elo = computeElo(rounds);
  const acc = {};
  const sorted = [...rounds].sort((a, b) => a.date.localeCompare(b.date));
  for (const round of sorted) {
    const ranked = [...round.scoreboard].sort((a, b) => b.composite - a.composite);
    ranked.forEach((r, idx) => {
      if (!acc[r.impl]) acc[r.impl] = { rounds: 0, wins: 0, totalCost: 0, history: [] };
      acc[r.impl].rounds += 1;
      if (idx === 0) acc[r.impl].wins += 1;
      acc[r.impl].totalCost += r.cost ?? 0;
      acc[r.impl].history.push(r.composite);
    });
  }
  return Object.entries(acc)
    .map(([impl, e]) => ({
      impl,
      elo: elo[impl] ?? ELO_BASE,
      rounds: e.rounds,
      wins: e.wins,
      totalCost: e.totalCost,
      avgCost: e.rounds > 0 ? e.totalCost / e.rounds : 0,
      history: e.history,
    }))
    .sort((a, b) => b.elo - a.elo);
}

function sparkText(history) {
  if (!history.length) return '';
  const SPARKS = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];
  const min = Math.min(...history);
  const max = Math.max(...history);
  const span = max - min;
  if (span === 0) return SPARKS[4].repeat(history.length);
  return history
    .map(s => SPARKS[Math.round(((s - min) / span) * (SPARKS.length - 1))])
    .join('');
}

function modelCard(standing) {
  const elo = Math.round(standing.elo);
  const rec = standing.rounds === 1 ? '1 round' : `${standing.rounds} rounds`;
  const wins = standing.wins === 1 ? '1 win' : `${standing.wins} wins`;
  const dollars = `$${standing.avgCost.toFixed(3)}/round`;
  const spark = sparkText(standing.history);
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
            style: { display: 'flex', flexDirection: 'column', gap: 6 },
            children: [
              { type: 'div', props: { style: { fontSize: 26, color: BLUE, letterSpacing: 1, textTransform: 'uppercase' }, children: 'open-bench / model' } },
              { type: 'div', props: { style: { fontSize: 84, fontWeight: 700, letterSpacing: -2, marginTop: 6 }, children: standing.impl } },
            ],
          },
        },
        {
          type: 'div',
          props: {
            style: { display: 'flex', alignItems: 'baseline', gap: 28 },
            children: [
              { type: 'div', props: { style: { fontSize: 36, color: MUTED }, children: 'elo' } },
              { type: 'div', props: { style: { fontSize: 96, fontWeight: 700, color: GOLD, letterSpacing: -2 }, children: String(elo) } },
              spark && { type: 'div', props: { style: { fontSize: 56, color: BLUE, marginLeft: 18, letterSpacing: -2 }, children: spark } },
            ].filter(Boolean),
          },
        },
        {
          type: 'div',
          props: {
            style: { display: 'flex', gap: 36, fontSize: 28, color: MUTED },
            children: [
              { type: 'div', props: { children: rec } },
              { type: 'div', props: { children: wins } },
              { type: 'div', props: { children: dollars } },
            ],
          },
        },
      ],
    },
  };
}

function leaderboardCard(standings) {
  const top = standings.slice(0, 5);
  const maxElo = Math.max(...top.map(s => s.elo), 1100);
  const minElo = Math.min(...top.map(s => s.elo), 900);
  const span = Math.max(maxElo - minElo, 1);
  return {
    type: 'div',
    props: {
      style: {
        width: 1200, height: 630, display: 'flex', flexDirection: 'column',
        background: BG, color: FG, padding: '56px 80px', fontFamily: 'Inter', gap: 24,
      },
      children: [
        {
          type: 'div',
          props: {
            style: { display: 'flex', flexDirection: 'column', gap: 4 },
            children: [
              { type: 'div', props: { style: { fontSize: 26, color: BLUE, letterSpacing: 1, textTransform: 'uppercase' }, children: 'open-bench / leaderboard' } },
              { type: 'div', props: { style: { fontSize: 64, fontWeight: 700, letterSpacing: -1.5 }, children: 'standings' } },
            ],
          },
        },
        {
          type: 'div',
          props: {
            style: { display: 'flex', flexDirection: 'column', gap: 14, marginTop: 8 },
            children: top.map((s, i) => {
              const w = 280 + Math.round(((s.elo - minElo) / span) * 600);
              return {
                type: 'div',
                props: {
                  style: { display: 'flex', alignItems: 'center', gap: 18 },
                  children: [
                    { type: 'div', props: { style: { width: 64, fontSize: 36, fontWeight: 700, color: i === 0 ? GOLD : MUTED }, children: `#${i + 1}` } },
                    { type: 'div', props: { style: { width: 280, fontSize: 36, fontWeight: 700, color: i === 0 ? GOLD : FG }, children: s.impl } },
                    {
                      type: 'div',
                      props: {
                        style: { width: w, height: 32, background: i === 0 ? GOLD : '#3a3a3a' },
                        children: '',
                      },
                    },
                    { type: 'div', props: { style: { fontSize: 30, color: MUTED, marginLeft: 8 }, children: String(Math.round(s.elo)) } },
                  ],
                },
              };
            }),
          },
        },
      ],
    },
  };
}

function loadRounds() {
  const dir = resolve(REPO, 'results/reviews');
  const files = readdirSync(dir).filter(f => /^sandbox-\d{4}-\d{2}-\d{2}\.md$/.test(f));
  return files.map(f => {
    const date = f.replace(/^sandbox-/, '').replace(/\.md$/, '');
    const md = readFileSync(resolve(dir, f), 'utf-8');
    const scoreboardRaw = parseScoreboard(extractSection(md, 'Scoreboard'));
    const costByImpl = parseCostPerImpl(md);
    const scoreboard = scoreboardRaw.map(s => ({ ...s, cost: costByImpl[s.impl] ?? 0 }));
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

export async function generateOg() {
  mkdirSync(OG_DIR, { recursive: true });
  const fontReg = readFileSync(resolve(FRONTEND, 'og-assets/inter-regular.woff'));
  const fontBold = readFileSync(resolve(FRONTEND, 'og-assets/inter-bold.woff'));
  const fonts = [
    { name: 'Inter', data: fontReg, weight: 400, style: 'normal' },
    { name: 'Inter', data: fontBold, weight: 700, style: 'normal' },
  ];

  const renderOne = async (tree, outPath) => {
    const svg = await satori(tree, { width: 1200, height: 630, fonts });
    const png = new Resvg(svg).render().asPng();
    writeFileSync(outPath, png);
    console.log(`[og] wrote ${outPath}`);
  };

  let count = 0;
  const rounds = loadRounds();
  for (const round of rounds) {
    await renderOne(card(round), resolve(OG_DIR, `round-${round.date}.png`));
    count += 1;
  }

  const notes = loadNotes().filter(n => !n.draft && !n.ogImageOverride);
  for (const note of notes) {
    await renderOne(noteCard(note), resolve(OG_DIR, `note-${note.slug}.png`));
    count += 1;
  }

  if (rounds.length > 0) {
    const standings = computeStandings(rounds);
    await renderOne(leaderboardCard(standings), resolve(OG_DIR, 'leaderboard.png'));
    count += 1;
    for (const s of standings) {
      await renderOne(modelCard(s), resolve(OG_DIR, `model-${s.impl}.png`));
      count += 1;
    }
  }

  if (count === 0) console.warn('[og] no rounds or notes found, skipping');
  return count;
}

const isCli = import.meta.url === `file://${process.argv[1]}`;
if (isCli) {
  const n = await generateOg();
  if (n === 0) process.exit(1);
}
