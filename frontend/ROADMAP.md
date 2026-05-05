# Roadmap

Backlog of frontend gaps. Live document — edit freely.

Status: `[ ]` todo, `[~]` in progress, `[x]` done, `[-]` skipped.

## Next session

**Outstanding PRs (need review + merge before any new work)**
- [ ] PR #19 — embed widgets (`/embed/leaderboard`, `/embed/round/[date]`, `/embed/round/latest`, `/embed` catalog). Stacked on #20.
- [ ] PR #20 — bug sweep on compare + embed code (perf, dedup, dead-code cleanup). Stacked on #21.
- [ ] PR #21 — view transitions + header/footer cleanup + glossary tooltips + four quick wins (per-round JSON, skip-link, theme-color, round/impl tab transition). Bundles a lot; consider splitting if you want narrower review.

**Code to ship next** (do these in order)
- [ ] **Logo decision** — pick a direction (sparkline-in-brackets `[▂▅█]` is my pick: zero new asset pipeline, themes natively, ties to scoreboard vocabulary). Unblocks `apple-touch-icon.png` and the OG default mark.
- [ ] **`/scoring` page** — long-form rubric walkthrough. Tooltips already cover the one-liners; this is the "I want the full story" landing. Closes the P1 glossary item.
- [ ] **Reproduce-it walkthrough** — `/reproduce` page or top-of-`/about` section. "Open methods" is the pitch but the site never invites verification. P1.
- [ ] **Empty-state polish** — guard trend columns and sparklines behind `rounds >= 3`; show a "round 2 ships {date}" placeholder on `/changelog`. P2.
- [ ] **`apple-touch-icon.png`** — once the logo lands. Finishes the P2 touch-icons item.

**Decisions blocking** (no code can move without these)
- [ ] **Logo direction** — sparkline-in-brackets / terminal prompt / monogram / something else.
- [ ] **Round 2 date** — half the new pages (`/changelog`, ELO trend, sparklines, per-round compare) only get interesting at round 2+.
- [ ] **Domain status** — confirm `openbenchmark.dev` is registered + pointed at CF Pages. Canonicals everywhere assume yes.
- [ ] **Twitter handle** — confirm `@folezof` is the right one. Wired into every OG card.
- [ ] **Embed license wording** — "MIT, attribution appreciated" on `/embed` — happy with that copy?

**fole spot-checks** (validate the merged work in a real browser)
- [ ] `/compare` matrix → click 2-3 pairs, sanity-check the numbers and per-round deltas.
- [ ] `/embed` (after #19 merges) → drop a snippet into a scratch HTML file, verify dark + light hosts, try `?theme=light|dark`.
- [ ] Glossary tooltips (after #21 merges) → hover headers on `/leaderboard` and round scoreboard, check copy reads right.
- [ ] View transitions (after #21 merges) → `/leaderboard` → `/model/glm` should morph the model name into the masthead.
- [ ] Skip-to-content (after #21 merges) → tab on any page, "skip to content" should pop in at top-left.

## P1 — high leverage, ship soon

- [ ] **Glossary / scoring legend** — column-header tooltips done on PR #21 (central `glossary.ts` + `<Term>` component, applied to leaderboard, scoreboard, compare, model history). Still pending: dedicated `/scoring` page that walks through the rubric end-to-end.
- [ ] **Reproduce-it walkthrough** — `/reproduce` page or prominent section on `/about` with the minimal "clone, run X, get the same scores" recipe. The whole pitch is open methods; the site never invites verification.

## P2 — polish, ship next

- [ ] **Per-round JSON endpoint** — `/round/[date].json` mirroring the `/dataset.json` shape but scoped to a single round. Shipped on PR #21; lands when that merges.
- [ ] **Empty-state polish for low-round-count pages** — at 1 round, `/changelog` is one entry, sparklines are single bars, ELO swings are degenerate. Either guard trend columns behind a `rounds >= 3` check or show a "round 2 ships {date}" placeholder so pages don't read as undercooked.
- [ ] **iOS / Android touch icons + theme-color** — `theme-color` meta + `site.webmanifest` shipped on PR #21. Still pending: `apple-touch-icon.png` (needs a PNG, blocked on logo decision).

## P3 — nice to have

- [ ] **Inline code diff viewer** — replace "GH link" with rendered diff per impl. (Already shipped via shiki on `/round/[date]/[impl]`; mark done once verified.)
- [ ] **Embed widget** — iframe-able latest scoreboard for blog posts. Shipped on PR #19.
- [ ] **Multi-way compare (3+ models)** — current `/compare` is pairwise only. Revisit when the lineup hits ~10+ models.
- [ ] **Search / filter for models** — same trigger as multi-way compare.
- [ ] **`/round/[date]` → `/compare/x/vs/y` deep links** — clickable scoreboard rows that pre-fill a comparison. Useful once `rounds >= 2`.
- [ ] **Newsletter signup** — only if RSS analytics show < 50 readers after 5 rounds.

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
- [x] **Compare view** — `/compare` matrix picker + `/compare/[a]/vs/[b]` head-to-head pages. Side-by-side ELO/wins/podium/avg/$/round/sparkline cards, summary, per-round table with score and cost deltas. Static-prerendered for all unordered impl pairs.
- [x] **Charts** — pure-SVG `<Bars>` (scoreboard) + `<Scatter>` (cost-vs-quality, log x). Round-data wrappers `<RoundBars date>` / `<RoundScatter date>` plug into round tabs and are MDX-available in writeups. Zero JS.
- [x] **Round retrospective / writeup system** — MDX content collection at `frontend/src/content/notes/`, `/notes/[slug]` permalinks, `<RoundScoreboard>` + `<Stat>` MDX components, per-note OG cards, RSS merged with rounds, BlogPosting JSON-LD, round page callout.
