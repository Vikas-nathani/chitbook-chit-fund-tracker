/**
 * HTTP client for the ChitBook API.
 *
 * - Sends the in-memory access token as `Authorization: Bearer ...`.
 * - When the API answers 401 AUTH_TOKEN_EXPIRED, refreshes once (single-flight: concurrent
 *   requests share one refresh, so a rotated token is never presented twice) and retries.
 * - If the refresh fails, the session has ended: tokens are cleared and the app is told.
 */
import { API_BASE_URL, CLIENT_TYPE } from '@/lib/config';
import { tokenStore } from '@/lib/tokenStore';

import type { ApiErrorBody, TokenResponse } from './types';

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: unknown = null,
    public requestId: string | null = null,
  ) {
    super(message);
  }
}

/** status 0 = the server could not be reached at all */
export const NETWORK_ERROR = 'NETWORK_ERROR';

let accessToken: string | null = null;
let refreshing: Promise<TokenResponse | null> | null = null;
let onSessionEnded: () => void = () => {};

export function setSessionEndedHandler(handler: () => void) {
  onSessionEnded = handler;
}

/** Stores a fresh token pair: access token in memory, refresh token in the secure store. */
export async function applyTokens(tokens: TokenResponse) {
  accessToken = tokens.accessToken;
  await tokenStore.setRefreshToken(tokens.refreshToken);
}

export async function clearTokens() {
  accessToken = null;
  await tokenStore.clear();
}

async function send(path: string, init: RequestInit, withAuth: boolean): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (withAuth && accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  try {
    return await fetch(`${API_BASE_URL}${path}`, { ...init, headers, credentials: 'include' });
  } catch {
    throw new ApiError(0, NETWORK_ERROR, 'Cannot reach the server');
  }
}

async function toError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as ApiErrorBody;
    const e = body.error;
    return new ApiError(res.status, e.code, e.message, e.details, e.requestId);
  } catch {
    return new ApiError(res.status, 'UNKNOWN', `Request failed (${res.status})`);
  }
}

/** Exchanges the refresh token for a new pair. Returns null when the session is over. */
export function refreshSession(): Promise<TokenResponse | null> {
  refreshing ??= (async () => {
    try {
      const refreshToken = await tokenStore.getRefreshToken();
      if (CLIENT_TYPE === 'mobile' && !refreshToken) return null;
      const res = await send(
        '/api/v1/auth/refresh',
        {
          method: 'POST',
          headers: CLIENT_TYPE === 'web' ? { 'X-Chitbook-Client': 'web' } : undefined,
          body: JSON.stringify({ client: CLIENT_TYPE, refreshToken: refreshToken ?? undefined }),
        },
        false,
      );
      if (!res.ok) {
        if (res.status === 401) await clearTokens();
        return null;
      }
      const tokens = (await res.json()) as TokenResponse;
      await applyTokens(tokens);
      return tokens;
    } catch {
      return null; // offline: keep the stored token and try again later
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

/** Calls the API and returns parsed JSON (undefined for 204). Throws ApiError on failure. */
export async function request<T>(path: string, init: RequestInit = {}, withAuth = true): Promise<T> {
  let res = await send(path, init, withAuth);

  if (res.status === 401 && withAuth) {
    const err = await toError(res.clone());
    if (err.code === 'AUTH_TOKEN_EXPIRED' && (await refreshSession())) {
      res = await send(path, init, withAuth);
    } else if (err.code.startsWith('AUTH_')) {
      await clearTokens();
      onSessionEnded();
      throw err;
    }
  }

  if (!res.ok) throw await toError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });
