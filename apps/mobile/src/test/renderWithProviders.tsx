import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react-native';
import type { ReactElement } from 'react';

import { ToastProvider } from '@/components/Toast';
import { LanguageProvider } from '@/i18n';

/** Renders a screen with the same providers as the app (minus auth and navigation). Await it. */
export function renderWithProviders(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <LanguageProvider>
        <ToastProvider>{ui}</ToastProvider>
      </LanguageProvider>
    </QueryClientProvider>,
  );
}
