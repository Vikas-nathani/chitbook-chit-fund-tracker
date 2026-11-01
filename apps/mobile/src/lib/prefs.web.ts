/** Non-secret preferences (UI language) in the browser. Never used for tokens. */
export const prefs = {
  get: async (key: string): Promise<string | null> => {
    try {
      return window.localStorage.getItem(`chitbook.pref.${key}`);
    } catch {
      return null;
    }
  },
  set: async (key: string, value: string) => {
    try {
      window.localStorage.setItem(`chitbook.pref.${key}`, value);
    } catch {
      // storage unavailable (private mode): the choice lasts for this visit
    }
  },
};
