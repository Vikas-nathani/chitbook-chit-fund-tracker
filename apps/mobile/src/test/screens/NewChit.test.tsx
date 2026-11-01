import { fireEvent, screen, waitFor } from '@testing-library/react-native';

import { api } from '@/api/endpoints';
import NewChitScreen from '@/app/chits/new';
import { renderWithProviders } from '@/test/renderWithProviders';

jest.mock('expo-router', () => ({ router: { replace: jest.fn(), push: jest.fn() } }));
jest.mock('@/api/endpoints', () => ({ api: { createChit: jest.fn() } }));

const createChit = api.createChit as jest.Mock;

describe('New chit screen', () => {
  beforeEach(() => {
    createChit.mockReset();
    createChit.mockResolvedValue({ id: 42, name: 'Family chit' });
  });

  it('sends one member per person with their shares and the suggested per-share amount', async () => {
    await renderWithProviders(<NewChitScreen />);
    await fireEvent.changeText(screen.getByLabelText('Chit name'), 'Family chit');
    await fireEvent.changeText(screen.getByLabelText('Chit amount (₹)'), '500000');
    await fireEvent.changeText(screen.getByLabelText('Number of months'), '20');
    await fireEvent.changeText(screen.getByLabelText('Member name'), 'Ramesh');
    await fireEvent.changeText(screen.getByLabelText('Shares'), '2');

    await fireEvent.press(screen.getByText('Save chit'));

    await waitFor(() => expect(createChit).toHaveBeenCalledTimes(1));
    const payload = createChit.mock.calls[0][0];
    expect(payload.members).toEqual([{ name: 'Ramesh', shares: 2, startMonth: undefined }]);
    expect(payload.perShareAmount).toBe(25000);
  });

  it('validates before calling the API', async () => {
    await renderWithProviders(<NewChitScreen />);
    await fireEvent.press(screen.getByText('Save chit'));
    expect(screen.getByText('Enter a chit name.')).toBeTruthy();
    expect(createChit).not.toHaveBeenCalled();
  });

  it('adds another member row', async () => {
    await renderWithProviders(<NewChitScreen />);
    expect(screen.getAllByLabelText('Member name')).toHaveLength(1);
    await fireEvent.press(screen.getByText('+ Add member'));
    expect(screen.getAllByLabelText('Member name')).toHaveLength(2);
  });

  it('shows the escalation percent only after the toggle is on', async () => {
    await renderWithProviders(<NewChitScreen />);
    expect(screen.queryByLabelText('Increase by')).toBeNull();
    await fireEvent.press(screen.getByText("Increase a member's payment after they take the chit"));
    expect(screen.getByLabelText('Increase by')).toBeTruthy();
  });
});
