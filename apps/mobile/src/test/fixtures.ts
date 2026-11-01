import type { Chit } from '@/api/types';

/** 3-month chit (2020-01..03, all months due): A pays 1000/month from month 1, B joins in month 2. */
export function makeChit(overrides: Partial<Chit> = {}): Chit {
  return {
    id: 1,
    name: 'Test chit',
    totalAmount: 3000,
    months: 3,
    startMonth: '2020-01',
    commissionPercent: 5,
    perShareAmount: 1000,
    escalationEnabled: false,
    escalationPercent: 1,
    members: [
      { id: 10, name: 'Asha', shares: 1, startMonth: '2020-01', amounts: [1000, 1000, 1000], paid: [true, false, false] },
      { id: 11, name: 'Bala', shares: 1, startMonth: '2020-02', amounts: [null, 1000, 1000], paid: [false, false, false] },
    ],
    payouts: [{ month: 1, memberId: 10, memberName: 'Asha', amount: 900, paidOn: '2020-01-31' }],
    monthSummaries: [
      { month: 1, calendarMonth: '2020-01', due: 1000, collected: 1000, pending: 0, payout: 900, pnl: 100, isDue: true },
      { month: 2, calendarMonth: '2020-02', due: 2000, collected: 0, pending: 2000, payout: null, pnl: null, isDue: true },
      { month: 3, calendarMonth: '2020-03', due: 2000, collected: 0, pending: 2000, payout: null, pnl: null, isDue: true },
    ],
    createdAt: '2020-01-01T10:00:00+05:30',
    updatedAt: '2020-01-01T10:00:00+05:30',
    ...overrides,
  };
}
