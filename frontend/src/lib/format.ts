export function fmtSec(sec: number | null): string {
  if (sec === null || sec === undefined) return '—';
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  if (m === 0) return `${s}s`;
  return `${m}m${s}s`;
}

export function fmtCost(usd: number | null): string {
  if (usd === null || usd === undefined) return '—';
  if (usd < 0.001) return `$${usd.toFixed(5)}`;
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  if (usd < 1) return `$${usd.toFixed(3)}`;
  return `$${usd.toFixed(2)}`;
}

export function fmtTok(n: number | null): string {
  if (n === null || n === undefined) return '—';
  if (n < 1000) return `${n}`;
  if (n < 1000000) return `${(n / 1000).toFixed(n % 1000 === 0 ? 0 : 1)}k`;
  return `${(n / 1000000).toFixed(1)}M`;
}

export function fmtNum(n: number | null | undefined, decimals = 0): string {
  if (n === null || n === undefined) return '—';
  return n.toFixed(decimals);
}

export function fmtOr(n: number | null, decimals: number, fallback = '—'): string {
  return n !== null && n !== undefined ? n.toFixed(decimals) : fallback;
}

export function passFailIcon(exitCode: number | null): string {
  if (exitCode === 0) return '✓';
  if (exitCode !== null) return '✗';
  return '—';
}

export function passFailClass(exitCode: number | null, variant: 'pill' | 'cell' = 'cell'): string {
  const passed = exitCode === 0;
  if (exitCode === null) return '';
  return variant === 'pill'
    ? `pill ${passed ? 'pill-green' : 'pill-red'}`
    : passed ? 'win' : 'fail';
}

export function fmtDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m || !d) return iso;
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${months[m - 1]} ${d}, ${y}`;
}
