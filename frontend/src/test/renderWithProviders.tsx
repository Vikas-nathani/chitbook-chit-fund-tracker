import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render } from '@testing-library/react';
import { LanguageProvider } from '../i18n';
import { ToastProvider } from '../toast';

export function renderWithProviders(ui: ReactElement, initialEntries: string[] = ['/']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <LanguageProvider>
        <ToastProvider>{ui}</ToastProvider>
      </LanguageProvider>
    </MemoryRouter>,
  );
}
