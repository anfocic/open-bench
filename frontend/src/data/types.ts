import { z } from 'zod';

// --- Zod schemas ---

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

export const JudgeRankingEntrySchema = z.object({
  judge: z.string(),
  first: z.string(),
  second: z.string(),
  third: z.string(),
});

export const SelfBiasEntrySchema = z.object({
  impl: z.string(),
  selfSpec: z.number().nullable(),
  peerMedSpec: z.number().nullable(),
  deltaSpec: z.number().nullable(),
  selfQual: z.number().nullable(),
  peerMedQual: z.number().nullable(),
  deltaQual: z.number().nullable(),
});

export const AgreementEntrySchema = z.object({
  impl: z.string(),
  minSpec: z.number().nullable(),
  maxSpec: z.number().nullable(),
  range: z.number().nullable(),
  stdev: z.number().nullable(),
  judges: z.string(),
});

export const JudgeScoreSchema = z.object({
  judge: z.string(),
  tier: z.enum(['self', 'peer', 'expert']),
  hardFail: z.boolean(),
  spec: z.number().nullable(),
  quality: z.number().nullable(),
  verdict: z.string(),
  note: z.string(),
});

const HiddenTestSchema = z.object({
  name: z.string(),
  passed: z.boolean(),
});

export const PerImplDetailSchema = z.object({
  impl: z.string(),
  runPath: z.string(),
  scores: z.array(JudgeScoreSchema),
  hiddenTests: z.array(HiddenTestSchema),
});

export const CostEfficiencyEntrySchema = z.object({
  impl: z.string(),
  modelSlug: z.string(),
  loc: z.number().nullable(),
  wallClock: z.string(),
  tokens: z.number().nullable(),
  costUsd: z.number().nullable(),
  testsPassed: z.string(),
  costPerTest: z.string(),
});

export const JudgingCostSchema = z.object({
  judge: z.string(),
  tier: z.string(),
  harness: z.string(),
  model: z.string(),
  wallClock: z.string(),
  tokens: z.string(),
  costUsd: z.string(),
});

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

// --- Inferred types (same names as before) ---

export type Run = z.infer<typeof RunSchema>;
export type ScoreboardEntry = z.infer<typeof ScoreboardEntrySchema>;
export type JudgeRankingEntry = z.infer<typeof JudgeRankingEntrySchema>;
export type SelfBiasEntry = z.infer<typeof SelfBiasEntrySchema>;
export type AgreementEntry = z.infer<typeof AgreementEntrySchema>;
export type JudgeScore = z.infer<typeof JudgeScoreSchema>;
export type PerImplDetail = z.infer<typeof PerImplDetailSchema>;
export type CostEfficiencyEntry = z.infer<typeof CostEfficiencyEntrySchema>;
export type JudgingCostEntry = z.infer<typeof JudgingCostSchema>;
export type Round = z.infer<typeof RoundSchema>;

// --- Non-collection schemas & types ---

export const MetaJsonSchema = z.object({
  task: z.string(),
  model: z.string(),
  slug: z.string(),
  started_at: z.string(),
  ended_at: z.string().optional(),
  base_commit: z.string().optional(),
  test_exit_code: z.number().nullable(),
  sandbox_py_loc: z.number().optional(),
  opencode_version: z.string().optional(),
  model_slug: z.string().optional(),
  cost_usd: z.number().nullable(),
  tokens_total: z.number().nullable(),
  input_tokens: z.number().optional(),
  output_tokens: z.number().optional(),
  cache_read_tokens: z.number().optional(),
  model_wall_clock_seconds: z.number().nullable(),
  harness: z.string().optional(),
  session_id: z.string().optional(),
});

export type MetaJson = z.infer<typeof MetaJsonSchema>;

export const ConfigSchema = z.object({
  implementers: z.array(z.string()),
  expert_judges: z.array(z.string()),
  harness: z.string(),
  slugs: z.record(z.string(), z.string()),
});

export type Config = z.infer<typeof ConfigSchema>;

export const RunIndexSchema = z.object({
  model: z.string(),
  date: z.string(),
  sample: z.number(),
  runPath: z.string(),
});

export type RunIndex = z.infer<typeof RunIndexSchema>;