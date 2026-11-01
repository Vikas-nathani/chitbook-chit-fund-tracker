/**
 * Root layout: providers + navigation.
 * Signed-in screens and signed-out screens are separated with Stack.Protected, so a signed-out
 * user can never reach chit screens and is sent to /login (and the reverse after signing in).
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { ApiError } from '@/api/client';
import { AuthProvider, useAuth } from '@/auth/AuthProvider';
import { ToastProvider } from '@/components/Toast';
import { Loading } from '@/components/ui';
import { LanguageProvider, useI18n } from '@/i18n';
import { colors } from '@/theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // Retry only network problems and server errors, never 4xx answers
      retry: (count, error) => count < 2 && (!(error instanceof ApiError) || error.status === 0 || error.status >= 500),
    },
  },
});

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <LanguageProvider>
          <AuthProvider>
            <ToastProvider>
              <StatusBar style="dark" />
              <RootNavigator />
            </ToastProvider>
          </AuthProvider>
        </LanguageProvider>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}

function RootNavigator() {
  const { status } = useAuth();
  const { t } = useI18n();
  if (status === 'restoring') return <Loading />;
  const signedIn = status === 'signedIn';

  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.bg },
        headerShadowVisible: false,
        headerTintColor: colors.primary,
        headerTitleStyle: { color: colors.text },
        contentStyle: { backgroundColor: colors.bg },
      }}
    >
      <Stack.Protected guard={signedIn} redirectTo="/login">
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="chits/new" options={{ title: t('newChit.title') }} />
        <Stack.Screen name="chits/[id]" options={{ title: '' }} />
      </Stack.Protected>
      <Stack.Protected guard={!signedIn} redirectTo="/">
        <Stack.Screen name="login" options={{ headerShown: false }} />
        <Stack.Screen name="signup" options={{ title: t('signup.title') }} />
      </Stack.Protected>
    </Stack>
  );
}
