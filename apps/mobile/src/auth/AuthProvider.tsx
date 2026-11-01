/**
 * Session state for the whole app.
 *
 * Start-up: try to restore the session by refreshing (phones: refresh token from the
 * Keychain/Keystore; web: HttpOnly cookie). Sign-in stores the new token pair; sign-out
 * revokes the session on the server and wipes local tokens.
 */
import { useQueryClient } from '@tanstack/react-query';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { applyTokens, clearTokens, refreshSession, setSessionEndedHandler } from '@/api/client';
import { api } from '@/api/endpoints';
import type { SignupInput, User } from '@/api/types';
import { tokenStore } from '@/lib/tokenStore';

type Status = 'restoring' | 'signedOut' | 'signedIn';

interface AuthValue {
  status: Status;
  user: User | null;
  signIn: (username: string, password: string) => Promise<void>;
  signUp: (input: SignupInput) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<Status>('restoring');
  const [user, setUser] = useState<User | null>(null);

  const endLocally = useCallback(() => {
    setUser(null);
    setStatus('signedOut');
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    setSessionEndedHandler(endLocally);
    (async () => {
      const tokens = (await tokenStore.canRestore()) ? await refreshSession() : null;
      if (tokens) {
        setUser(tokens.user);
        setStatus('signedIn');
      } else {
        setStatus('signedOut');
      }
    })();
  }, [endLocally]);

  const signIn = useCallback(async (username: string, password: string) => {
    const tokens = await api.login(username.trim(), password);
    await applyTokens(tokens);
    setUser(tokens.user);
    setStatus('signedIn');
  }, []);

  const signUp = useCallback(
    async (input: SignupInput) => {
      await api.register(input);
      await signIn(input.username, input.password);
    },
    [signIn],
  );

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // offline or already revoked: still sign out locally
    }
    await clearTokens();
    endLocally();
  }, [endLocally]);

  const value = useMemo(() => ({ status, user, signIn, signUp, signOut }), [status, user, signIn, signUp, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
