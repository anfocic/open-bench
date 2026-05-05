import type { ScoreboardEntry, SelfBiasEntry, JudgeRankingEntry, AgreementEntry, JudgeScore, PerImplDetail, CostEfficiencyEntry, JudgingCostEntry } from '../data/types';

function parseTableRow(line: string): string[] {
  return line.split('|').slice(1, -1).map(c => c.trim());
}

function parseScoreboard(section: string): ScoreboardEntry[] {
  const lines = section.split('\n').filter(l => l.trim().startsWith('|'));
  if (lines.length < 3) return [];
  const dataLines = lines.slice(2);
  return dataLines.map(line => {
    const cols = parseTableRow(line);
    if (cols.length < 10) return null;
    return {
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
    };
  }).filter((e): e is ScoreboardEntry => e !== null);
}

function parseJudgeRanking(section: string): JudgeRankingEntry[] {
  const lines = section.split('\n').filter(l => l.trim().startsWith('|'));
  if (lines.length < 3) return [];
  const dataLines = lines.slice(2);
  return dataLines.map(line => {
    const cols = parseTableRow(line);
    if (cols.length < 4) return null;
    return {
      judge: cols[0],
      first: cols[1] || '',
      second: cols[2] || '',
      third: cols[3] || '',
    };
  }).filter((e): e is JudgeRankingEntry => e !== null);
}

function parseSelfBias(section: string): SelfBiasEntry[] {
  const lines = section.split('\n').filter(l => l.trim().startsWith('|'));
  if (lines.length < 3) return [];
  const dataLines = lines.slice(2);
  return dataLines.map(line => {
    const cols = parseTableRow(line);
    if (cols.length < 7) return null;
    return {
      impl: cols[0],
      selfSpec: parseNum(cols[1]),
      peerMedSpec: parseNum(cols[2]),
      deltaSpec: parseNum(cols[3]),
      selfQual: parseNum(cols[4]),
      peerMedQual: parseNum(cols[5]),
      deltaQual: parseNum(cols[6]),
    };
  }).filter((e): e is SelfBiasEntry => e !== null);
}

function parseAgreement(section: string): AgreementEntry[] {
  const lines = section.split('\n').filter(l => l.trim().startsWith('|'));
  if (lines.length < 3) return [];
  const dataLines = lines.slice(2);
  return dataLines.map(line => {
    const cols = parseTableRow(line);
    if (cols.length < 6) return null;
    return {
      impl: cols[0],
      minSpec: parseNum(cols[1]),
      maxSpec: parseNum(cols[2]),
      range: parseNum(cols[3]),
      stdev: parseNum(cols[4]),
      judges: cols[5],
    };
  }).filter((e): e is AgreementEntry => e !== null);
}

function parseCostEfficiency(section: string): CostEfficiencyEntry[] {
  const lines = section.split('\n').filter(l => l.trim().startsWith('|'));
  if (lines.length < 3) return [];
  const dataLines = lines.slice(2);
  return dataLines.map(line => {
    const cols = parseTableRow(line);
    if (cols.length < 8) return null;
    return {
      impl: cols[0],
      modelSlug: cols[1],
      loc: parseNum(cols[2]),
      wallClock: cols[3],
      tokens: parseNum(cols[4]),
      costUsd: parsePrice(cols[5]),
      testsPassed: cols[6],
      costPerTest: cols[7],
    };
  }).filter((e): e is CostEfficiencyEntry => e !== null);
}

function parseJudgingCost(section: string): JudgingCostEntry[] {
  const lines = section.split('\n').filter(l => l.trim().startsWith('|'));
  if (lines.length < 3) return [];
  const dataLines = lines.slice(2);
  return dataLines.map(line => {
    const cols = parseTableRow(line);
    if (cols.length < 7) return null;
    return {
      judge: cols[0],
      tier: cols[1],
      harness: cols[2],
      model: cols[3],
      wallClock: cols[4],
      tokens: cols[5],
      costUsd: cols[6],
    };
  }).filter((e): e is JudgingCostEntry => e !== null);
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

function parseNum(s: string): number | null {
  const cleaned = s.trim().replace(/^—+$/, '').replace(/,/g, '');
  if (!cleaned || cleaned === '—' || cleaned === '' || cleaned === '–') return null;
  const n = Number(cleaned);
  return isNaN(n) ? null : n;
}

function parsePrice(s: string): number | null {
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
        `Aggregator format likely drifted — update parse-review.ts.`
      );
    }
  }
  return result;
}
