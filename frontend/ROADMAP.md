# Roadmap

Backlog of frontend gaps. Live document — edit freely.

Status: `[ ]` todo, `[~]` in progress, `[x]` done, `[-]` skipped.

## P1 — high leverage, ship soon

_(empty — all P1 items shipped; see Done section)_

## P2 — polish, ship next

<!-- Charts: shipped, see Done. -->

<!-- Methodology changelog: shipped, see Done. -->
<!-- Dataset export: shipped, see Done. -->

## P3 — nice to have

- [ ] **Compare view** — two impls or two rounds side-by-side. Power-user feature.
- [ ] **Inline code diff viewer** — replace "GH link" with rendered diff per impl.
- [ ] **Embed widget** — iframe-able latest scoreboard for blog posts.

## Skipped (no fit)

- [-] **Comments / search / i18n / notifications / PWA** — wrong shape for a static research site. RSS already covers the subscribe use case.
- [-] **Security headers** — no threat model (no auth, forms, user input). HSTS/nosniff acceptable later if free A+ on securityheaders.com matters.
- [-] **Per-impl OG images** — impl pages rarely shared socially.
- [-] **FAQPage JSON-LD** — about page is prose, not Q&A.
- [-] **Google Search Console submission** — user-driven; happens outside repo.
- [-] **A11y deep audit** — basics covered (semantic HTML, focus states); revisit if real users complain.

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
- [x] **Charts** — pure-SVG `<Bars>` (scoreboard) + `<Scatter>` (cost-vs-quality, log x). Round-data wrappers `<RoundBars date>` / `<RoundScatter date>` plug into round tabs and are MDX-available in writeups. Zero JS.
- [x] **Round retrospective / writeup system** — MDX content collection at `frontend/src/content/notes/`, `/notes/[slug]` permalinks, `<RoundScoreboard>` + `<Stat>` MDX components, per-note OG cards, RSS merged with rounds, BlogPosting JSON-LD, round page callout.
