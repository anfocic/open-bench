# Roadmap

Backlog of frontend gaps. Live document — edit freely.

Status: `[ ]` todo, `[~]` in progress, `[x]` done, `[-]` skipped.

## P1 — high leverage, ship soon

- [~] **Cross-round leaderboard / ELO** — `/leaderboard` with cumulative W/podium/avg/ELO. Brand promise is "battle royale", but every round is currently an island.
- [~] **Per-model career page** — `/model/[impl]`. Career view: every round played, score history, cost trend. Natural deep-link target.
- [ ] **Round retrospective / writeup** — markdown blog per round under `frontend/src/pages/round/[date]/notes.astro` (or a `posts/` collection). Tables don't go viral; narrative does.

## P2 — polish, ship next

- [ ] **Charts** — cost-vs-quality scatter plot, scoreboard bars. Site is wall-of-tables; one good chart = 10x shareability on HN/Twitter.
- [ ] **Methodology changelog** — `/changelog` listing SPEC and rubric changes per round. Trust signal: "what's comparable round-to-round".
- [ ] **Public dataset export** — `/dataset.csv` and `/dataset.json` endpoints. Backs the "open data" claim. Researchers want to cite + reanalyze.

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
