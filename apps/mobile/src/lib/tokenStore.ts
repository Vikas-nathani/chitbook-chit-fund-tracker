/**
 * Refresh-token storage on phones: iOS Keychain / Android Keystore via expo-secure-store.
 * The short-lived access token is never persisted; it lives in memory only (api/client.ts).
 * Web uses tokenStore.web.ts instead (HttpOnly cookie, nothing readable by JavaScript).
 */
import * as SecureStore from 'expo-secure-store';

const KEY = 'chitbook.refreshToken';
const OPTIONS: SecureStore.SecureStoreOptions = {
  // Readable only while the device is unlocked, and never restored onto another device
  keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
};

export const tokenStore = {
  /** Phones must have a stored token to restore a session. */
  canRestore: async () => (await SecureStore.getItemAsync(KEY, OPTIONS)) !== null,
  getRefreshToken: () => SecureStore.getItemAsync(KEY, OPTIONS),
  setRefreshToken: (token: string | null | undefined) =>
    token ? SecureStore.setItemAsync(KEY, token, OPTIONS) : SecureStore.deleteItemAsync(KEY, OPTIONS),
  clear: () => SecureStore.deleteItemAsync(KEY, OPTIONS),
};
