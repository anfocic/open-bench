import type { MetaJson, Run, ScoreboardEntry, SelfBiasEntry, JudgeRankingEntry, AgreementEntry, JudgeScore, PerImplDetail, CostEfficiencyEntry, JudgingCostEntry } from '../data/types';

// --- parseMeta ---

export function parseMeta(json: unknown): Run | null {
  if (!json || typeof json !== 'object') return null;
  const m = json as Record<string, unknown>;
  if (typeof m.model !== 'string' || typeof m.slug !== 'string') return null;

  const slug = m.slug as string;
  const dateMatch = slug.match(/(\d{4}-\d{2}-\d{2})/);
  const date = dateMatch ? dateMatch[1] : '';
  const sampleMatch = slug.match(/-r(\d+)$/);
  const sample = sampleMatch ? parseInt(sampleMatch[1], 10) : 1;

  return {
    model: m.model as string,
    round: date,
    sample,
    wallSec: typeof m.model_wall_clock_seconds === 'number' ? m.model_wall_clock_seconds : null,
    costUsd: typeof m.cost_usd === 'number' ? m.cost_usd : null,
    tokensTotal: typeof m.tokens_total === 'number' ? m.tokens_total : null,
    inputTokens: typeof m.input_tokens === 'number' ? m.input_tokens : null,
    outputTokens: typeof m.output_tokens === 'number' ? m.output_tokens : null,
    cacheReadTokens: typeof m.cache_read_tokens === 'number' ? m.cache_read_tokens : null,
    loc: typeof m.sandbox_py_loc === 'number' ? m.sandbox_py_loc : null,
    testExitCode: typeof m.test_exit_code === 'number' ? m.test_exit_code : null,
    modelSlug: typeof m.model_slug === 'string' ? m.model_slug : null,
  };
}

// --- parseReview ---

function parseTableRow(line: string): string[] {
  return line.split('|').slice(1, -1).map(c => c.trim());
}

function parseTableSection<T>(section: string, minCols: number, mapFn: (cols: string[]) => T | null): T[] {
  const lines = section.split('\n').filter(l => l.trim().startsWith('|'));
  if (lines.length < 3) return [];
  return lines.slice(2).map(line => {
    const cols = parseTableRow(line);
    if (cols.length < minCols) return null;
    return mapFn(cols);
  }).filter((e): e is T => e !== null);
}

function parseScoreboard(section: string): ScoreboardEntry[] {
  return parseTableSection(section, 10, cols => ({
    impl: cols[0],
    hardFail: cols[1] === 'pass',
    specAll: parseNum(cols[2]),
    specExpert: parseNum(cols[3]),
    specPeer: parseNum(cols[4]),
    qualityAll: parseNum(cols[5]),
    qualityExpert: parseNum(cols[6]),
    qualityPeer: parseNum(cols[7]),
    tests: cols[8],
    verdict: cols[9],
  }));
}

function parseJudgeRanking(section: string): JudgeRankingEntry[] {
  return parseTableSection(section, 4, cols => ({
    judge: cols[0],
    first: cols[1] || '',
    second: cols[2] || '',
    third: cols[3] || '',
  }));
}

function parseSelfBias(section: string): SelfBiasEntry[] {
  return parseTableSection(section, 7, cols => ({
    impl: cols[0],
    selfSpec: parseNum(cols[1]),
    peerMedSpec: parseNum(cols[2]),
    deltaSpec: parseNum(cols[3]),
    selfQual: parseNum(cols[4]),
    peerMedQual: parseNum(cols[5]),
    deltaQual: parseNum(cols[6]),
  }));
}

function parseAgreement(section: string): AgreementEntry[] {
  return parseTableSection(section, 6, cols => ({
    impl: cols[0],
    minSpec: parseNum(cols[1]),
    maxSpec: parseNum(cols[2]),
    range: parseNum(cols[3]),
    stdev: parseNum(cols[4]),
    judges: cols[5],
  }));
}

function parseCostEfficiency(section: string): CostEfficiencyEntry[] {
  return parseTableSection(section, 8, cols => ({
    impl: cols[0],
    modelSlug: cols[1],
    loc: parseNum(cols[2]),
    wallClock: cols[3],
    tokens: parseNum(cols[4]),
    costUsd: parsePrice(cols[5]),
    testsPassed: cols[6],
    costPerTest: cols[7],
  }));
}

function parseJudgingCost(section: string): JudgingCostEntry[] {
  return parseTableSection(section, 7, cols => ({
    judge: cols[0],
    tier: cols[1],
    harness: cols[2],
    model: cols[3],
    wallClock: cols[4],
    tokens: cols[5],
    costUsd: cols[6],
  }));
}

function parsePerImplDetail(section: string): PerImplDetail[] {
  const results: PerImplDetail[] = [];
  const blocks = section.split(/\n(?=### )/);
  for (const block of blocks) {
    const headerMatch = block.match(/^### (.+)/m);
    if (!headerMatch) continue;
    const impl = headerMatch[1].trim();
    const runMatch = block.match(/Run: `(.+?)`/);
    const runPath = runMatch ? runMatch[1] : '';

    const tableLines = block.split('\n').filter(l => l.trim().startsWith('|'));
    const scores: JudgeScore[] = [];
    if (tableLines.length >= 3) {
      for (const line of tableLines.slice(2)) {
        const cols = parseTableRow(line);
        if (cols.length < 7) continue;
        const tier = cols[1] as 'self' | 'peer' | 'expert';
        scores.push({
          judge: cols[0],
          tier,
          hardFail: cols[2] === 'pass',
          spec: parseNum(cols[3]),
          quality: parseNum(cols[4]),
          verdict: cols[5],
          note: cols[6] || '',
        });
      }
    }

    const testLines = block.split('\n').filter(l => /^- `/.test(l.trim()));
    const hiddenTests = testLines.map(l => {
      const m = l.match(/`(.+?)`\s*[—–-]+\s*(PASSED|FAILED)/);
      if (m) return { name: m[1], passed: m[2] === 'PASSED' };
      return null;
    }).filter((t): t is { name: string; passed: boolean } => t !== null);

    results.push({ impl, runPath, scores, hiddenTests });
  }
  return results;
}

export function parseNum(s: string): number | null {
  const cleaned = s.trim().replace(/^—+$/, '').replace(/,/g, '');
  if (!cleaned || cleaned === '—' || cleaned === '' || cleaned === '–') return null;
  const n = Number(cleaned);
  return isNaN(n) ? null : n;
}

export function parsePrice(s: string): number | null {
  const cleaned = s.trim().replace(/^\$/, '');
  if (!cleaned || cleaned === '—') return null;
  const n = Number(cleaned);
  return isNaN(n) ? null : n;
}

function extractSection(content: string, heading: string): string {
  const sections = content.split(/\n(?=## )/);
  for (const section of sections) {
    if (section.startsWith(`## ${heading}`)) {
      return section.replace(/^## .+\n?/, '').trim();
    }
  }
  return '';
}

export interface ParsedReview {
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

function sectionPresent(content: string, heading: string): boolean {
  return content.split(/\n(?=## )/).some(s => s.startsWith(`## ${heading}`));
}

export function parseReview(markdown: string): ParsedReview {
  const result: ParsedReview = {
    scoreboard: parseScoreboard(extractSection(markdown, 'Scoreboard')),
    judgeRanking: parseJudgeRanking(extractSection(markdown, 'Per-judge ranking')),
    selfBias: parseSelfBias(extractSection(markdown, 'Self-bias')),
    agreement: parseAgreement(extractSection(markdown, 'Inter-judge agreement')),
    perImplDetail: parsePerImplDetail(extractSection(markdown, 'Per-implementation detail')),
    costEfficiency: parseCostEfficiency(extractSection(markdown, 'Cost & efficiency')),
    judgingCost: parseJudgingCost(extractSection(markdown, 'Judging cost')),
    crossModelObservations: extractSection(markdown, 'Cross-model observations') || null,
    recommendation: extractSection(markdown, 'Recommendation') || null,
    specChanges: extractSection(markdown, 'Spec changes') || null,
  };

  const required: [string, keyof ParsedReview][] = [
    ['Scoreboard', 'scoreboard'],
    ['Per-judge ranking', 'judgeRanking'],
    ['Self-bias', 'selfBias'],
    ['Inter-judge agreement', 'agreement'],
    ['Per-implementation detail', 'perImplDetail'],
    ['Cost & efficiency', 'costEfficiency'],
  ];
  for (const [heading, key] of required) {
    if (sectionPresent(markdown, heading) && (result[key] as unknown[]).length === 0) {
      throw new Error(
        `parseReview: section "## ${heading}" present but parser produced 0 rows. ` +
        `Aggregator format likely drifted — update parse.ts.`
      );
    }
  }
  return result;
}