/**
 * Unsaved edits on the chit screen, and live money figures that include them.
 * Pure functions (no React) so the rules are unit-tested in gridDraft.test.ts.
 * Money rules match the API (docs/domain/simple-chits.md):
 *   due = sum of entries, collected = sum of paid entries, pending = max(due - collected, 0),
 *   P/L = collected - payout (only when a payout is recorded).
 */
import type { Chit, Payout, UpdateChitInput } from '@/api/types';
import { formatNumber, round2 } from '@/lib/format';

export const MAX_COMMISSION = 20;

export interface Draft {
  /** amount text per "memberId:month", as typed */
  amounts: Record<string, string>;
  /** paid tick per "memberId:month" */
  paid: Record<string, boolean>;
  totalAmount: string | null;
  commission: string | null;
}

export const emptyDraft = (): Draft => ({ amounts: {}, paid: {}, totalAmount: null, commission: null });

export const cellKey = (memberId: number, month: number) => `${memberId}:${month}`;

/** '' counts as 0; anything else must be a non-negative number (commas allowed). null = invalid. */
export function parseAmount(text: string): number | null {
  const cleaned = text.replace(/,/g, '').trim();
  if (cleaned === '') return 0;
  const n = Number(cleaned);
  return Number.isFinite(n) && n >= 0 ? round2(n) : null;
}

function member(chit: Chit, memberId: number) {
  return chit.members.find((m) => m.id === memberId);
}

export const serverAmount = (chit: Chit, memberId: number, month: number) =>
  member(chit, memberId)?.amounts[month - 1] ?? 0;
export const serverPaid = (chit: Chit, memberId: number, month: number) =>
  member(chit, memberId)?.paid[month - 1] ?? false;

export function cellText(chit: Chit, draft: Draft, memberId: number, month: number): string {
  const key = cellKey(memberId, month);
  return key in draft.amounts ? draft.amounts[key]! : formatNumber(serverAmount(chit, memberId, month));
}

export const cellValue = (chit: Chit, draft: Draft, memberId: number, month: number) =>
  parseAmount(cellText(chit, draft, memberId, month)) ?? 0;

export function cellPaid(chit: Chit, draft: Draft, memberId: number, month: number): boolean {
  const key = cellKey(memberId, month);
  return key in draft.paid ? draft.paid[key]! : serverPaid(chit, memberId, month);
}

/** Members who have joined by the given month (late joiners have no entry before they start). */
export function membersInMonth(chit: Chit, month: number) {
  const calendar = chit.monthSummaries[month - 1]?.calendarMonth ?? chit.startMonth;
  return chit.members.filter((m) => m.startMonth <= calendar);
}

// ---------------------------------------------------------------- edits

export function editAmount(chit: Chit, draft: Draft, memberId: number, month: number, text: string): Draft {
  const key = cellKey(memberId, month);
  const amounts = { ...draft.amounts };
  const parsed = parseAmount(text);
  // Typing the original value back clears the edit
  if (parsed !== null && text.trim() !== '' && parsed === serverAmount(chit, memberId, month)) delete amounts[key];
  else amounts[key] = text;
  return { ...draft, amounts };
}

export function setPaid(chit: Chit, draft: Draft, cells: { memberId: number; month: number }[], paid: boolean): Draft {
  const next = { ...draft.paid };
  for (const { memberId, month } of cells) {
    const key = cellKey(memberId, month);
    if (paid === serverPaid(chit, memberId, month)) delete next[key];
    else next[key] = paid;
  }
  return { ...draft, paid: next };
}

// ---------------------------------------------------------------- derived state

export interface DraftStatus {
  dirtyCount: number;
  hasErrors: boolean;
  totalChanged: boolean;
  commissionChanged: boolean;
  totalInvalid: boolean;
  commissionInvalid: boolean;
}

export function draftStatus(chit: Chit, draft: Draft): DraftStatus {
  const invalidCells = Object.values(draft.amounts).filter((text) => parseAmount(text) === null).length;
  const total = draft.totalAmount === null ? chit.totalAmount : Number(draft.totalAmount);
  const totalInvalid = draft.totalAmount !== null && !(total > 0);
  const totalChanged = draft.totalAmount !== null && total !== chit.totalAmount;
  const commission = draft.commission === null ? chit.commissionPercent : Number(draft.commission);
  const commissionInvalid =
    draft.commission !== null && !(draft.commission.trim() !== '' && commission >= 0 && commission <= MAX_COMMISSION);
  const commissionChanged = draft.commission !== null && commission !== chit.commissionPercent;
  const cells = new Set([...Object.keys(draft.amounts), ...Object.keys(draft.paid)]).size;
  return {
    dirtyCount: cells + (totalChanged ? 1 : 0) + (commissionChanged ? 1 : 0),
    hasErrors: invalidCells > 0 || totalInvalid || commissionInvalid,
    totalChanged,
    commissionChanged,
    totalInvalid,
    commissionInvalid,
  };
}

export function toUpdateInput(chit: Chit, draft: Draft): UpdateChitInput {
  const status = draftStatus(chit, draft);
  const keys = new Set([...Object.keys(draft.amounts), ...Object.keys(draft.paid)]);
  return {
    totalAmount: status.totalChanged ? Number(draft.totalAmount) : undefined,
    commissionPercent: status.commissionChanged ? Number(draft.commission) : undefined,
    entries: [...keys].map((key) => {
      const [memberId, month] = key.split(':').map(Number) as [number, number];
      return {
        memberId,
        month,
        amount: key in draft.amounts ? (parseAmount(draft.amounts[key]!) ?? 0) : undefined,
        paid: key in draft.paid ? draft.paid[key] : undefined,
      };
    }),
  };
}

export interface MonthMoney {
  month: number;
  calendarMonth: string;
  due: number;
  collected: number;
  pending: number;
  paidCount: number;
  memberCount: number;
  allPaid: boolean;
  payout: Payout | null;
  pnl: number | null;
  isDue: boolean;
}

export interface ChitMoney {
  months: MonthMoney[];
  rowTotals: Record<number, number>;
  collected: number;
  pending: number;
  paidOut: number;
  profit: number;
}

/** Live figures for the whole chit, including unsaved edits. */
export function computeMoney(chit: Chit, draft: Draft): ChitMoney {
  const payoutByMonth = new Map(chit.payouts.map((p) => [p.month, p]));
  const rowTotals: Record<number, number> = {};
  const months: MonthMoney[] = chit.monthSummaries.map((summary) => {
    const month = summary.month;
    let due = 0;
    let collected = 0;
    let paidCount = 0;
    const present = membersInMonth(chit, month);
    for (const m of present) {
      const v = cellValue(chit, draft, m.id, month);
      due += v;
      rowTotals[m.id] = round2((rowTotals[m.id] ?? 0) + v);
      if (cellPaid(chit, draft, m.id, month)) {
        collected += v;
        paidCount++;
      }
    }
    const payout = payoutByMonth.get(month) ?? null;
    return {
      month,
      calendarMonth: summary.calendarMonth,
      due: round2(due),
      collected: round2(collected),
      pending: round2(Math.max(due - collected, 0)),
      paidCount,
      memberCount: present.length,
      allPaid: present.length > 0 && paidCount === present.length,
      payout,
      pnl: payout ? round2(collected - payout.amount) : null,
      isDue: summary.isDue,
    };
  });
  const sum = (f: (m: MonthMoney) => number) => round2(months.reduce((a, m) => a + f(m), 0));
  return {
    months,
    rowTotals,
    collected: sum((m) => m.collected),
    pending: sum((m) => (m.isDue ? m.pending : 0)),
    paidOut: sum((m) => m.payout?.amount ?? 0),
    profit: sum((m) => m.pnl ?? 0),
  };
}

/** Suggested payout: the chit amount minus the owner's commission. */
export const suggestedPayout = (chit: Chit) => round2(chit.totalAmount * (1 - chit.commissionPercent / 100));

/** Escalation each payout adds to the taker's later months (preview only; the API applies it). */
export const escalationBump = (chit: Chit) =>
  chit.escalationEnabled ? round2((chit.totalAmount * chit.escalationPercent) / 100) : 0;
