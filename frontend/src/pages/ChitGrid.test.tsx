import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LanguageProvider } from '../i18n';
import { ToastProvider } from '../toast';
import { ChitGrid } from './ChitGrid';
import { api, type Chit } from '../api';
import { currentMonth } from '../format';

vi.mock('../api', () => ({
  api: {
    getChit: vi.fn(),
    addMember: vi.fn(),
    updateChit: vi.fn(),
    savePayout: vi.fn(),
    deletePayout: vi.fn(),
    deleteChit: vi.fn(),
  },
}));

function addMonths(yearMonth: string, n: number): string {
  const [y, m] = yearMonth.split('-').map(Number);
  const total = y * 12 + (m - 1) + n;
  return `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, '0')}`;
}

function buildChit(): Chit {
  const start = currentMonth();
  const month2 = addMonths(start, 1);
  const month3 = addMonths(start, 2);
  return {
    id: 1,
    name: 'Family chit',
    totalAmount: 500000,
    months: 3,
    startMonth: start,
    commissionPercent: 5,
    perShareAmount: 25000,
    escalationEnabled: false,
    escalationPercent: 1,
    members: [
      { id: 1, name: 'Ramesh', shares: 1, startMonth: start, amounts: [25000, 25000, 25000], paid: [false, false, false] },
      { id: 2, name: 'LateJoiner', shares: 1, startMonth: month2, amounts: [null, 25000, 25000], paid: [false, false, false] },
    ],
    payouts: [],
    monthSummaries: [
      { month: 1, calendarMonth: start, due: 25000, collected: 0, pending: 25000, payout: null, pnl: null, isDue: true },
      { month: 2, calendarMonth: month2, due: 50000, collected: 0, pending: 50000, payout: null, pnl: null, isDue: false },
      { month: 3, calendarMonth: month3, due: 50000, collected: 0, pending: 50000, payout: null, pnl: null, isDue: false },
    ],
    createdAt: '2026-01-01T00:00:00',
    updatedAt: '2026-01-01T00:00:00',
  };
}

function renderGrid() {
  const router = createMemoryRouter([{ path: '/chits/:id', element: <ChitGrid /> }], { initialEntries: ['/chits/1'] });
  return render(
    <LanguageProvider>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </LanguageProvider>,
  );
}

describe('ChitGrid month view', () => {
  beforeEach(() => {
    vi.mocked(api.getChit).mockReset();
    vi.mocked(api.getChit).mockResolvedValue(buildChit());
    vi.mocked(api.addMember).mockReset();
  });

  it('only shows members whose start month has arrived for the displayed month', async () => {
    renderGrid();

    await screen.findByText('Ramesh');
    // LateJoiner starts next month, so is not shown for the current (first) month
    expect(screen.queryByText('LateJoiner')).not.toBeInTheDocument();
  });

  it('moving to the next month reveals a member who joins then', async () => {
    const user = userEvent.setup();
    renderGrid();

    await screen.findByText('Ramesh');
    expect(screen.queryByText('LateJoiner')).not.toBeInTheDocument();

    await user.click(screen.getByLabelText('Next month'));

    expect(await screen.findByText('LateJoiner')).toBeInTheDocument();
    expect(screen.getByText('Ramesh')).toBeInTheDocument();
  });

  it('adding a member calls the API with the right payload', async () => {
    const user = userEvent.setup();
    const chit = buildChit();
    vi.mocked(api.addMember).mockResolvedValue(chit);
    renderGrid();

    await screen.findByText('Ramesh');
    await user.click(screen.getByText('+ Add member'));

    await user.type(screen.getByLabelText('Member name'), 'Priya');
    const sharesInput = screen.getByLabelText('Shares');
    await user.clear(sharesInput);
    await user.type(sharesInput, '2');

    await user.click(screen.getByText('Add member'));

    await waitFor(() => expect(api.addMember).toHaveBeenCalledTimes(1));
    const [calledChitId, payload] = vi.mocked(api.addMember).mock.calls[0];
    expect(calledChitId).toBe(1);
    expect(payload).toMatchObject({ name: 'Priya', shares: 2 });
  });
});
