export interface MetaJson {
  task: string;
  model: string;
  slug: string;
  started_at: string;
  ended_at?: string;
  base_commit?: string;
  test_exit_code: number | null;
  sandbox_py_loc?: number;
  opencode_version?: string;
  model_slug?: string;
  cost_usd: number | null;
  tokens_total: number | null;
  input_tokens?: number;
  output_tokens?: number;
  cache_read_tokens?: number;
  model_wall_clock_seconds: number | null;
  harness?: string;
  session_id?: string;
}

export interface Run {
  model: string;
  round: string;
  sample: number;
  wallSec: number | null;
  costUsd: number | null;
  tokensTotal: number | null;
  inputTokens: number | null;
  outputTokens: number | null;
  cacheReadTokens: number | null;
  loc: number | null;
  testExitCode: number | null;
  modelSlug: string | null;
}

export interface ScoreboardEntry {
  impl: string;
  hardFail: boolean;
  specAll: number | null;
  specExpert: number | null;
  specPeer: number | null;
  qualityAll: number | null;
  qualityExpert: number | null;
  qualityPeer: number | null;
  tests: string;
  verdict: string;
}

export interface JudgeRankingEntry {
  judge: string;
  first: string;
  second: string;
  third: string;
}

export interface SelfBiasEntry {
  impl: string;
  selfSpec: number | null;
  peerMedSpec: number | null;
  deltaSpec: number | null;
  selfQual: number | null;
  peerMedQual: number | null;
  deltaQual: number | null;
}

export interface AgreementEntry {
  impl: string;
  minSpec: number | null;
  maxSpec: number | null;
  range: number | null;
  stdev: number | null;
  judges: string;
}

export interface JudgeScore {
  judge: string;
  tier: 'self' | 'peer' | 'expert';
  hardFail: boolean;
  spec: number | null;
  quality: number | null;
  verdict: string;
  note: string;
}

export interface PerImplDetail {
  impl: string;
  runPath: string;
  scores: JudgeScore[];
  hiddenTests: { name: string; passed: boolean }[];
}

export interface CostEfficiencyEntry {
  impl: string;
  modelSlug: string;
  loc: number | null;
  wallClock: string;
  tokens: number | null;
  costUsd: number | null;
  testsPassed: string;
  costPerTest: string;
}

export interface JudgingCostEntry {
  judge: string;
  tier: string;
  harness: string;
  model: string;
  wallClock: string;
  tokens: string;
  costUsd: string;
}

export interface Round {
  date: string;
  samples: Run[];
  scoreboard: ScoreboardEntry[];
  judgeRanking: JudgeRankingEntry[];
  selfBias: SelfBiasEntry[];
  agreement: AgreementEntry[];
  perImplDetail: PerImplDetail[];
  costEfficiency: CostEfficiencyEntry[];
  judgingCost: JudgingCostEntry[];
  crossModelObservations: string | null;
  recommendation: string | null;
  specChanges: string | null;
}

export interface Config {
  implementers: string[];
  expert_judges: string[];
  harness: string;
  slugs: Record<string, string>;
}
