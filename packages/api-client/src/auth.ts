import { toApiError } from "./errors";
import type { Http } from "./http";
import type { TokenStore } from "./token-store";
import type { Credentials, TokenResponse, User } from "./types";

export interface AuthClient {
  register(credentials: Credentials): Promise<User>;
  login(credentials: Credentials): Promise<void>;
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
      return http.request<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify(credentials),
      });
    },

    async login(credentials) {
      // The token endpoint expects OAuth2 form encoding, not JSON, and needs no
      // access token — so it bypasses the JSON request helper.
      const response = await fetch(`${baseUrl}/auth/token`, {
        method: "POST",
        credentials: "include", // receive the Set-Cookie refresh token
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
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
      const query = options?.allDevices ? "?all_devices=true" : "";
      try {
        await fetch(`${baseUrl}/auth/logout${query}`, {
          method: "POST",
          credentials: "include",
        });
      } finally {
        // Drop the local session even if the network call fails.
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
