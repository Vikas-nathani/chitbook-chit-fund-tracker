import { Platform } from 'react-native';

/**
 * API origin, read at build time from EXPO_PUBLIC_API_BASE_URL (.env at the repo root).
 * Empty = same origin (the web build is served by nginx, which proxies /api to the API).
 */
export const API_BASE_URL = (process.env.EXPO_PUBLIC_API_BASE_URL ?? '').replace(/\/$/, '');

/** "web": refresh token lives in an HttpOnly cookie. "mobile": in the Keychain/Keystore. */
export const CLIENT_TYPE: 'web' | 'mobile' = Platform.OS === 'web' ? 'web' : 'mobile';

export const DEVICE_NAME =
  Platform.OS === 'web' ? 'Web browser' : Platform.OS === 'ios' ? 'iPhone / iPad app' : 'Android app';
