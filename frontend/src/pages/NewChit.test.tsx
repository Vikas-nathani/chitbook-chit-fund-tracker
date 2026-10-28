import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../test/renderWithProviders';
import { NewChit } from './NewChit';
import { api } from '../api';

vi.mock('../api', () => ({
  api: {
    createChit: vi.fn(),
  },
}));

describe('NewChit', () => {
  beforeEach(() => {
    vi.mocked(api.createChit).mockReset();
    vi.mocked(api.createChit).mockResolvedValue({ id: 42, name: 'Family chit' } as never);
  });

  it('submits one member row per person with shares, not one row per share', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NewChit />);

    await user.type(screen.getByLabelText(/chit name/i), 'Family chit');
    await user.type(screen.getByPlaceholderText('100000'), '500000');
    await user.type(screen.getByPlaceholderText('10'), '20');

    const nameInput = screen.getByPlaceholderText('Member name');
    await user.type(nameInput, 'Ramesh');
    const sharesInput = screen.getAllByRole('spinbutton').find((el) => el.closest('.member-row-shares'))!;
    await user.clear(sharesInput);
    await user.type(sharesInput, '2');

    await user.click(screen.getByText('Save chit'));

    await waitFor(() => expect(api.createChit).toHaveBeenCalledTimes(1));
    const payload = vi.mocked(api.createChit).mock.calls[0][0];
    expect(payload.members).toHaveLength(1);
    expect(payload.members[0]).toMatchObject({ name: 'Ramesh', shares: 2 });
  });

  it('adding a member row adds another name field', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NewChit />);

    expect(screen.getAllByPlaceholderText('Member name')).toHaveLength(1);
    await user.click(screen.getByText('+ Add member'));
    expect(screen.getAllByPlaceholderText('Member name')).toHaveLength(2);
  });

  it('shows a shares badge in the preview when a member holds more than one share', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NewChit />);

    await user.type(screen.getByPlaceholderText('Member name'), 'Ramesh');
    const sharesInput = screen.getAllByRole('spinbutton').find((el) => el.closest('.member-row-shares')) as HTMLInputElement;
    await user.clear(sharesInput);
    await user.type(sharesInput, '3');

    expect(await screen.findByText('×3')).toBeInTheDocument();
  });

  it('hides the escalation percent field until the toggle is enabled', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NewChit />);

    expect(screen.queryByText('Increase by')).not.toBeInTheDocument();
    await user.click(screen.getByLabelText(/increase a member's payment/i));
    expect(await screen.findByText('Increase by')).toBeInTheDocument();
  });
});
