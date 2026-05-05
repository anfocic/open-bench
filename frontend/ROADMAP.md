# Roadmap

Backlog of frontend gaps. Live document — edit freely.

Status: `[ ]` todo, `[~]` in progress, `[x]` done, `[-]` skipped.

## P1 — high leverage, ship soon

- [~] **Glossary / scoring legend** — column-header tooltips shipped (central `glossary.ts` + `<Term>` component, applied to leaderboard, scoreboard, compare, model history). Still pending: a dedicated `/scoring` page that walks through the rubric end-to-end for visitors who want the full story instead of one-line tooltips.
- [ ] **Reproduce-it walkthrough** — prominent CTA (`/reproduce` page or top of `/about`) with the minimal "clone, run X, get the same scores" recipe. The whole pitch is open methods; the site never invites verification.

## P2 — polish, ship next

- [ ] **Per-round JSON endpoint** — `/round/[date].json` mirroring the `/dataset.json` shape but scoped to a single round. Researchers fetching one round shouldn't have to download the whole archive. ~10 lines, parallels the existing dataset endpoint.
- [ ] **Empty-state polish for low-round-count pages** — at 1 round, `/changelog` is one entry, sparklines are single bars, ELO swings are degenerate. Either guard trend columns behind a `rounds >= 3` check or show a "round 2 ships {date}" placeholder so pages don't read as undercooked.
- [ ] **iOS / Android touch icons + theme-color** — add `apple-touch-icon.png`, `theme-color` meta, minimal web manifest. Currently only `favicon.svg` exists. ~5 minutes, pure polish.

## P3 — nice to have

- [ ] **Multi-way compare (3+ models)** — current `/compare` is pairwise only. Revisit when the lineup hits ~10+ models and pairwise no longer scales.
- [ ] **Search / filter for models** — same trigger as multi-way compare.
- [ ] **`/round/[date]` → `/compare/x/vs/y` deep links** — clickable scoreboard rows that pre-fill a comparison. Useful once `rounds >= 2`.
- [ ] **Newsletter signup** — only if RSS analytics show < 50 readers after 5 rounds.

## Skipped (no fit)

- [-] **Comments / search / i18n / notifications / PWA** — wrong shape for a static research site. RSS already covers the subscribe use case.
- [-] **Security headers** — no threat model (no auth, forms, user input). HSTS/nosniff acceptable later if free A+ on securityheaders.com matters.
- [-] **Per-impl OG images** — impl pages rarely shared socially.
- [-] **FAQPage JSON-LD** — about page is prose, not Q&A.
- [-] **Google Search Console submission** — user-driven; happens outside repo.
- [-] **A11y deep audit** — basics covered (semantic HTML, focus states); revisit if real users complain. Defer Lighthouse pass until the site gets linked from anywhere with traffic.

## Done

- [x] **SEO foundation** — typed config, JSON-LD, robots.txt, sitemap with priorities (`feat/seo-config-v2`).
- [x] **OG image auto-build** — `astro:build:start` hook regenerates per-round OG.
- [x] **RSS feed** — `/feed.xml` with visible link in footer + `<link rel="alternate">`.
- [x] **/round/ archive index** — listing page with CollectionPage + ItemList JSON-LD.
- [x] **Article JSON-LD + rel=prev/next** — round permalinks now also typed as `Article`.
- [x] **OG dims/alt + twitter handle** — `@folezof`, width/height/alt all wired.
- [x] **Cross-round leaderboard / ELO** — `/leaderboard`, ELO base 1000 K=32, sparkline, sorted by ELO desc.
- [x] **Per-model career page** — `/model/[impl]` with full round history, rank/ELO masthead.
- [x] **Methodology changelog** — `/changelog` timeline. Auto-derives lineup deltas (+ added / − removed) between consecutive rounds. Pulls `specChanges` and `recommendation` from each round's review markdown when not still placeholder text.
- [x] **Public dataset export** — `/dataset.json` (full structured) + `/dataset.csv` (one row per round×impl) + `/dataset` docs page with schema, license, citation. Backs the "open data" claim.
- [x] **Embed widgets** — `/embed/leaderboard`, `/embed/round/[date]`, `/embed/round/latest`. Minimal `EmbedLayout` (no nav/footer chrome, attribution backlink only, `?theme=light|dark` query override, `noindex`, excluded from sitemap). Catalog at `/embed` with live previews + copy-paste iframe snippets.
- [x] **Inline code diff viewer** — already shipped: `/round/[date]/[impl]` renders `diff.patch` inline via shiki under the "diff" tab, no GH round-trip needed.
- [x] **Compare view** — `/compare` matrix picker + `/compare/[a]/vs/[b]` head-to-head pages. Side-by-side ELO/wins/podium/avg/$/round/sparkline cards, summary, per-round table with score and cost deltas. Static-prerendered for all unordered impl pairs.
- [x] **Charts** — pure-SVG `<Bars>` (scoreboard) + `<Scatter>` (cost-vs-quality, log x). Round-data wrappers `<RoundBars date>` / `<RoundScatter date>` plug into round tabs and are MDX-available in writeups. Zero JS.
- [x] **Round retrospective / writeup system** — MDX content collection at `frontend/src/content/notes/`, `/notes/[slug]` permalinks, `<RoundScoreboard>` + `<Stat>` MDX components, per-note OG cards, RSS merged with rounds, BlogPosting JSON-LD, round page callout.
