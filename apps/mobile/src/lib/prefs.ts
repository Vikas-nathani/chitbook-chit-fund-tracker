/** Small non-secret preferences (UI language). Phones: secure store; web: prefs.web.ts. */
import * as SecureStore from 'expo-secure-store';

export const prefs = {
  get: (key: string) => SecureStore.getItemAsync(`chitbook.pref.${key}`),
  set: (key: string, value: string) => SecureStore.setItemAsync(`chitbook.pref.${key}`, value),
};
