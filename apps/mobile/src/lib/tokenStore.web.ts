/**
 * Web: the API sets the refresh token as an HttpOnly, SameSite=Strict cookie, so JavaScript
 * (and any injected script) can never read it. Nothing is stored in localStorage/sessionStorage.
 */
export const tokenStore = {
  /** The cookie is invisible to us; always try a refresh and let the API decide. */
  canRestore: async () => true,
  getRefreshToken: async (): Promise<string | null> => null,
  setRefreshToken: async (_token: string | null | undefined) => {},
  clear: async () => {},
};
