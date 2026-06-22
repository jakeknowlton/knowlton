/**
 * Holds the access token in memory only.
 *
 * Deliberately not localStorage/sessionStorage: a token sitting in web storage
 * is readable by any injected script (XSS) and persists on disk. Keeping it in a
 * closure variable means it lives only for the page's lifetime and vanishes on
 * reload — at which point the HttpOnly refresh cookie silently mints a new one.
 *
 * The refresh token itself is never handled here: the browser stores it as an
 * HttpOnly cookie that JavaScript cannot read.
 */

export type AuthListener = (authenticated: boolean) => void;

export interface TokenStore {
  get(): string | null;
  set(token: string | null): void;
  isAuthenticated(): boolean;
  subscribe(listener: AuthListener): () => void;
}

export function createTokenStore(): TokenStore {
  let accessToken: string | null = null;
  const listeners = new Set<AuthListener>();

  function setToken(token: string | null): void {
    const wasAuthenticated = accessToken !== null;
    accessToken = token;
    // Notify only when the authenticated/anonymous state actually flips, so a
    // routine token rotation doesn't churn subscribers.
    if (wasAuthenticated !== (accessToken !== null)) {
      for (const listener of listeners) listener(accessToken !== null);
    }
  }

  return {
    get: () => accessToken,
    set: setToken,
    isAuthenticated: () => accessToken !== null,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
