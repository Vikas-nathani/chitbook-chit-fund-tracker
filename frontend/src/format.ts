import { intlLocale } from './i18n';

// Amounts always use en-IN digits and grouping (₹2,50,000), in both languages
const rupee = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

const plain = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 });

export const formatRupees = (value: number) => rupee.format(Number.isFinite(value) ? value : 0);
export const formatNumber = (value: number) => plain.format(Number.isFinite(value) ? value : 0);

/** "+₹12,500" / "−₹8,500" / "₹0" for P/L figures. */
export function formatSignedRupees(value: number): string {
  if (!Number.isFinite(value) || value === 0) return formatRupees(0);
  return `${value > 0 ? '+' : '−'}${formatRupees(Math.abs(value))}`;
}

/** Compact Indian units for chart axes: ₹950, ₹12K, ₹2.5L, ₹1.2Cr. */
export function formatCompactRupees(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? '−' : '';
  const trim = (n: number) => String(Number(n.toFixed(n >= 10 ? 0 : 1)));
  if (abs >= 1e7) return `${sign}₹${trim(abs / 1e7)}Cr`;
  if (abs >= 1e5) return `${sign}₹${trim(abs / 1e5)}L`;
  if (abs >= 1e3) return `${sign}₹${trim(abs / 1e3)}K`;
  return `${sign}₹${Math.round(abs)}`;
}

export const formatPercent = (ratio: number | null) => (ratio === null ? '–' : `${Math.round(ratio * 100)}%`);

export function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** "Sep 26" from a calendar month "2026-09". */
export function calendarLabel(yearMonth: string): string {
  return monthLabel(yearMonth, 1);
}

/** Rounds to paise, avoiding floating point noise like 33333.330000000004. */
export const round2 = (value: number) => Math.round(value * 100) / 100;

export function currentMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

/** Date for the 1-based month `index` of a chit starting at `startMonth` (yyyy-MM). */
function monthDate(startMonth: string, index: number): Date {
  const [y, m] = startMonth.split('-').map(Number);
  return new Date(y, m - 1 + (index - 1), 1);
}

/** "Nov 26" / "నవం 26" in the current UI language (digits stay 0-9). */
export function monthLabel(startMonth: string, index: number): string {
  const d = monthDate(startMonth, index);
  return `${d.toLocaleString(intlLocale(), { month: 'short' })} ${String(d.getFullYear()).slice(2)}`;
}

/** "Nov 2026 – Aug 2027" */
export function periodLabel(startMonth: string, months: number): string {
  const fmt = (d: Date) => `${d.toLocaleString(intlLocale(), { month: 'short' })} ${d.getFullYear()}`;
  return `${fmt(monthDate(startMonth, 1))} – ${fmt(monthDate(startMonth, months))}`;
}

/** Month name only ("Nov" / "నవం") for a calendar month "2026-11". */
export function monthShortName(yearMonth: string): string {
  return monthDate(yearMonth, 1).toLocaleString(intlLocale(), { month: 'short' });
}

/** 1-based index of today's month within the chit (0 = not started, > months = finished). */
export function currentMonthIndex(startMonth: string): number {
  const [y, m] = startMonth.split('-').map(Number);
  const now = new Date();
  return (now.getFullYear() - y) * 12 + (now.getMonth() + 1 - m) + 1;
}

const AVATAR_COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f97316', '#10b981', '#06b6d4', '#f59e0b', '#3b82f6'];

export function avatarColor(name: string): string {
  let hash = 0;
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

/** Split into user-perceived characters, so Telugu letters keep their vowel signs (రవి -> ర, వి). */
function graphemes(text: string): string[] {
  const Segmenter = (Intl as unknown as { Segmenter?: new (l: string, o: object) => { segment(s: string): Iterable<{ segment: string }> } })
    .Segmenter;
  if (Segmenter) return [...new Segmenter('und', { granularity: 'grapheme' }).segment(text)].map((s) => s.segment);
  return [...text];
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  // Non-Latin scripts get a single letter; two Telugu letters don't fit the small avatar
  const latin = /^[A-Za-z]/.test(parts[0]);
  const first = graphemes(parts[0]);
  const letters = !latin
    ? first[0]
    : parts.length === 1
      ? first.slice(0, 2).join('')
      : first[0] + graphemes(parts[parts.length - 1])[0];
  return letters.toUpperCase();
}
