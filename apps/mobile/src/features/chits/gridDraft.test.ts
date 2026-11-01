import { makeChit } from '@/test/fixtures';

import {
  computeMoney,
  draftStatus,
  editAmount,
  emptyDraft,
  membersInMonth,
  parseAmount,
  setPaid,
  suggestedPayout,
  toUpdateInput,
} from './gridDraft';

describe('parseAmount', () => {
  it('accepts grouped numbers and blanks', () => {
    expect(parseAmount('25,000')).toBe(25000);
    expect(parseAmount('')).toBe(0);
    expect(parseAmount('12.345')).toBe(12.35);
  });
  it('rejects negatives and text', () => {
    expect(parseAmount('-1')).toBeNull();
    expect(parseAmount('abc')).toBeNull();
  });
});

describe('membersInMonth', () => {
  it('excludes late joiners before their start month', () => {
    const chit = makeChit();
    expect(membersInMonth(chit, 1).map((m) => m.name)).toEqual(['Asha']);
    expect(membersInMonth(chit, 2).map((m) => m.name)).toEqual(['Asha', 'Bala']);
  });
});

describe('computeMoney', () => {
  it('matches the server figures with no edits', () => {
    const money = computeMoney(makeChit(), emptyDraft());
    expect(money.months.map((m) => m.due)).toEqual([1000, 2000, 2000]);
    expect(money.collected).toBe(1000);
    expect(money.pending).toBe(4000);
    expect(money.paidOut).toBe(900);
    expect(money.profit).toBe(100);
  });

  it('includes unsaved ticks and amounts', () => {
    const chit = makeChit();
    let draft = setPaid(chit, emptyDraft(), [{ memberId: 11, month: 2 }], true);
    draft = editAmount(chit, draft, 10, 2, '1,500');
    const month2 = computeMoney(chit, draft).months[1]!;
    expect(month2.due).toBe(2500);
    expect(month2.collected).toBe(1000);
    expect(month2.paidCount).toBe(1);
  });
});

describe('draft bookkeeping', () => {
  it('typing the original value back clears the edit', () => {
    const chit = makeChit();
    const edited = editAmount(chit, emptyDraft(), 10, 1, '2000');
    expect(draftStatus(chit, edited).dirtyCount).toBe(1);
    const reverted = editAmount(chit, edited, 10, 1, '1,000');
    expect(draftStatus(chit, reverted).dirtyCount).toBe(0);
  });

  it('flags invalid cells and commission', () => {
    const chit = makeChit();
    const draft = { ...editAmount(chit, emptyDraft(), 10, 1, 'abc'), commission: '25' };
    const status = draftStatus(chit, draft);
    expect(status.hasErrors).toBe(true);
    expect(status.commissionInvalid).toBe(true);
  });

  it('builds the PATCH body with only changed fields', () => {
    const chit = makeChit();
    let draft = setPaid(chit, emptyDraft(), [{ memberId: 10, month: 2 }], true);
    draft = { ...draft, totalAmount: '3500' };
    expect(toUpdateInput(chit, draft)).toEqual({
      totalAmount: 3500,
      commissionPercent: undefined,
      entries: [{ memberId: 10, month: 2, amount: undefined, paid: true }],
    });
  });
});

it('suggests payout = amount minus commission', () => {
  expect(suggestedPayout(makeChit())).toBe(2850);
});
