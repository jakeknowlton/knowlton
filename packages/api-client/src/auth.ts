import { toApiError } from './errors';
import type { TokenResponse, UserCreate, UserRead } from './generated';
import type { Http } from './http';
import type { TokenStore } from './token-store';

export interface AuthClient {
  register(credentials: UserCreate): Promise<UserRead>;
  login(credentials: UserCreate): Promise<void>;
  logout(options?: { allDevices?: boolean }): Promise<void>;
  /** Revive a session from the refresh cookie on startup. */
  restore(): Promise<boolean>;
  isAuthenticated(): boolean;
  /** Subscribe to authenticated/anonymous transitions (e.g. session expiry). */
  subscribe(listener: (authenticated: boolean) => void): () => void;
}

export function createAuth(
  baseUrl: string,
  http: Http,
  tokens: TokenStore,
): AuthClient {
  return {
    register(credentials) {
      return http.request<UserRead>('/auth/register', {
        method: 'POST',
        body: JSON.stringify(credentials),
      });
    },

    async login(credentials) {
      // The token endpoint expects OAuth2 form encoding, not JSON, and needs no
      // access token — so it bypasses the JSON request helper.
      const response = await fetch(`${baseUrl}/auth/token`, {
        method: 'POST',
        credentials: 'include', // receive the Set-Cookie refresh token
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          username: credentials.username,
          password: credentials.password,
        }),
      });
      if (!response.ok) throw await toApiError(response);
      const data = (await response.json()) as TokenResponse;
      tokens.set(data.access_token);
    },

    async logout(options) {
      const query = options?.allDevices ? '?all_devices=true' : '';
      try {
        await fetch(`${baseUrl}/auth/logout${query}`, {
          method: 'POST',
          credentials: 'include',
        });
      } catch {
        // Local logout should succeed even when the server cannot be reached.
      } finally {
        tokens.set(null);
      }
    },

    restore() {
      return http.refresh();
    },

    isAuthenticated: tokens.isAuthenticated,
    subscribe: tokens.subscribe,
  };
}
