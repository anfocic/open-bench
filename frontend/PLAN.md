# Plan: Migrate to Astro Content Layer with Zod Schemas

## Goal

Replace the hand-rolled `loadRounds()` filesystem crawl with an Astro Content Layer custom loader. Migrate all types to Zod schemas for runtime validation. Keep component props unchanged. Pass minimal props in dynamic routes.

## Context

The current frontend reads data from outside its directory:
- `../../builds/` — model implementation directories with `meta.json` files
- `../../results/reviews/` — markdown review files with embedded data tables
- `../../bench/config.json` — static config for the model lineup

The current data pipeline spans three files:
- `src/data/rounds.ts` — walks filesystem, groups runs by date, loads reviews
- `src/lib/parse-meta.ts` — parses `meta.json` into `Run` objects
- `src/lib/parse-review.ts` — parses markdown tables into structured review data

## Approach: Custom Loader (Approach A)

Use Astro Content Layer with a custom `Loader` that reads data in-place from `builds/` and `results/`. No file copying or pre-build sync step.

Why not Approach B (pre-build sync)? Because the data lives outside `frontend/` and we want to keep the monorepo layout intact. A custom loader avoids duplicating data and keeps the source of truth in one place.

## Files

| Action | Path | Notes |
|---|---|---|
| **NEW** | `src/content.config.ts` | Collection definitions. Single `rounds` collection with custom loader + Zod schema. |
| **NEW** | `src/lib/loader.ts` | Custom `Loader` implementation. Encapsulates all current logic from `rounds.ts`, `parse-review.ts`, and `parse-meta.ts`. |
| **DELETE** | `src/data/rounds.ts` | Replaced by `getCollection('rounds')`. |
| **DELETE** | `src/lib/parse-review.ts` | Logic moves into `loader.ts`. |
| **DELETE** | `src/lib/parse-meta.ts` | Logic moves into `loader.ts`. |
| **REFACTOR** | `src/data/types.ts` | Convert interfaces to Zod schemas; export inferred types with identical names so components need no changes. |
| **REFACTOR** | `src/pages/index.astro` | Use `getCollection('rounds')` for round data. Keep direct `config.json` read for the lineup table (not a collection). |
| **REFACTOR** | `src/pages/round/[date].astro` | `getStaticPaths` returns `{ date }` params + `{ roundId }` props only. Page body calls `getEntry('rounds', roundId)` to hydrate full data. |
| **UNCHANGED** | All components (`Scoreboard`, `RunsTable`, `RoundCard`, etc.) | Receive same typed props. No edits. |
| **UNCHANGED** | `src/lib/format.ts`, layouts, styles | No changes needed. |

## Schema Design

Convert all interfaces in `types.ts` to Zod schemas. Export inferred types with identical names.

```ts
import { z } from 'astro:content';

export const RunSchema = z.object({
  model: z.string(),
  round: z.string(),
  sample: z.number(),
  wallSec: z.number().nullable(),
  costUsd: z.number().nullable(),
  tokensTotal: z.number().nullable(),
  inputTokens: z.number().nullable(),
  outputTokens: z.number().nullable(),
  cacheReadTokens: z.number().nullable(),
  loc: z.number().nullable(),
  testExitCode: z.number().nullable(),
  modelSlug: z.string().nullable(),
});

export const ScoreboardEntrySchema = z.object({
  impl: z.string(),
  hardFail: z.boolean(),
  specAll: z.number().nullable(),
  specExpert: z.number().nullable(),
  specPeer: z.number().nullable(),
  qualityAll: z.number().nullable(),
  qualityExpert: z.number().nullable(),
  qualityPeer: z.number().nullable(),
  tests: z.string(),
  verdict: z.string(),
});

// JudgeRankingEntry, SelfBiasEntry, AgreementEntry,
// JudgeScore, PerImplDetail, CostEfficiencyEntry, JudgingCostEntry
// ... (same pattern: z.object with .nullable() for optional numbers)

export const RoundSchema = z.object({
  date: z.string(),
  samples: z.array(RunSchema),
  scoreboard: z.array(ScoreboardEntrySchema),
  judgeRanking: z.array(JudgeRankingEntrySchema),
  selfBias: z.array(SelfBiasEntrySchema),
  agreement: z.array(AgreementEntrySchema),
  perImplDetail: z.array(PerImplDetailSchema),
  costEfficiency: z.array(CostEfficiencyEntrySchema),
  judgingCost: z.array(JudgingCostSchema),
  crossModelObservations: z.string().nullable(),
  recommendation: z.string().nullable(),
  specChanges: z.string().nullable(),
});

export type Run = z.infer<typeof RunSchema>;
export type ScoreboardEntry = z.infer<typeof ScoreboardEntrySchema>;
// ... all other types
export type Round = z.infer<typeof RoundSchema>;
```

## Loader Implementation (`lib/loader.ts`)

The loader is a standard Astro Content Layer `Loader` object with a `load` method.

```ts
import type { Loader } from 'astro:content';
import { readdirSync, readFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '../../..'); // repo root

const roundsLoader: Loader = {
  name: 'rounds',
  load: async ({ store }) => {
    // 1. Walk builds/ → read meta.json
    // 2. Parse with parseMeta logic (slug regex for date/sample)
    // 3. Group runs by round date
    // 4. For each date, read results/reviews/sandbox-{date}.md
    // 5. Parse markdown tables with parseReview logic
    // 6. Construct Round object
    // 7. store.set({ id: date, data: round })
    //
    // Path resolution uses ROOT (repo root) not process.cwd()
  },
};

export default roundsLoader;
```

Key logic preserved exactly:
- `parseMeta`: JSON parse + regex extract date/sample from slug
- `parseReview`: All markdown table parsers (scoreboard, judge ranking, self-bias, agreement, cost efficiency, judging cost, per-impl detail)
- `parseNum` / `parsePrice`: Null-safe number parsing
- Null handling: empty/— strings → `null`

## `content.config.ts`

```ts
import { defineCollection } from 'astro:content';
import roundsLoader from './lib/loader';
import { RoundSchema } from './data/types';

export const collections = {
  rounds: defineCollection({
    loader: roundsLoader,
    schema: RoundSchema,
  }),
};
```

## Page Migrations

### `pages/index.astro`

```ts
import { getCollection } from 'astro:content';

const rounds = await getCollection('rounds');
// rounds is sorted by loader; rounds[0] is latest
// rounds[0].id === '2025-05-01'
// rounds[0].data === full Round object
```

The lineup table still reads `bench/config.json` directly with `readFileSync`. This single config file does not warrant a collection.

### `pages/round/[date].astro`

```ts
import { getCollection, getEntry } from 'astro:content';

export async function getStaticPaths() {
  const rounds = await getCollection('rounds');
  return rounds.map(r => ({
    params: { date: r.id },
    props: { roundId: r.id },
  }));
}

const { roundId } = Astro.props;
const round = await getEntry('rounds', roundId);
if (!round) return Astro.redirect('/404');
// round.data is the full Zod-validated Round
```

Props are minimal (`roundId` string). Full data is fetched in page body. Template changes are minimal: replace `round` with `round.data` in expressions.

## Dependencies

Add `zod` to `frontend/package.json` (Astro re-exports it as `astro:content`, but we use it directly in `types.ts`).

```json
{
  "dependencies": {
    "zod": "^3.23.0"
  }
}
```

Actually: Astro 5 includes Zod via `astro:content`. We can import `z` from `astro:content` without adding a separate dependency. Verify before adding.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Loader path resolution fragile if CWD changes | Compute `ROOT` relative to `import.meta.url` of the loader file, never `process.cwd()`. |
| Dev server does not reload when bench data changes | Register watched file paths explicitly in the loader. Astro Content Layer supports file watching for loaders. |
| Zod schema drift when bench output changes | Build fails loudly with clear validation error. Easier to debug than silent runtime `undefined`. |
| Types imported by 10 components | Keep `export type` aliases with identical names. Zero component churn. |

## Verification

1. `cd frontend && npm run build` — completes without Zod validation errors.
2. `npm run preview` — homepage shows latest round card.
3. Navigate to a round page — all tables render with correct data.
4. Spot-check: scoreboard totals, champion calculation, cost formatting match current output.

## Future Considerations

- **Multiple tasks**: The `rounds` collection uses `id: date` which assumes one task. If multiple tasks run on the same date, change `id` to `{task}-{date}`.
- **Dev watching**: If the loader watches `builds/` and `results/`, new bench runs trigger auto-reload in dev. Implement if desired.
- **Split repos**: If frontend moves to its own repo, replace the custom loader with a file-based collection and add a pre-build sync step to copy JSON/markdown artifacts into `src/content/rounds/`.

## Decision Log

- **Custom loader vs pre-build sync**: Custom loader wins because data lives outside `frontend/` and we want no duplication.
- **Keep `config.json` as direct read**: It is a single static file, not repeated content. A collection would be overkill.
- **Minimal props in `[date].astro`**: Pass `roundId` only; fetch full data with `getEntry()`. Keeps props small and follows Astro collection patterns.
- **Zod schemas in `types.ts`**: Replaces interfaces with schemas + inferred types. Components import the same type names with zero changes.
