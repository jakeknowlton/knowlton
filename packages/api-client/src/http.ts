import { toApiError } from './errors';
import type { TokenStore } from './token-store';

export interface Http {
  /** Perform a JSON request, transparently refreshing on a 401 once. */
  request<T>(path: string, init?: RequestInit): Promise<T>;
  /**
   * Exchange the refresh cookie for a new access token. Returns whether a
   * session is now active. Safe to call concurrently — calls are coalesced.
   */
  refresh(): Promise<boolean>;
}

export function createHttp(baseUrl: string, tokens: TokenStore): Http {
  // A single in-flight refresh shared by all callers. The refresh token rotates
  // on every use (the server invalidates the old one), so two parallel refresh
  // attempts would race and one would spend an already-dead token. Coalescing
  // guarantees the cookie is exchanged exactly once per burst of 401s.
  let inFlight: Promise<boolean> | null = null;

  async function doRefresh(): Promise<boolean> {
    let response: Response;
    try {
      response = await fetch(`${baseUrl}/auth/refresh`, {
        method: 'POST',
        credentials: 'include', // send the HttpOnly refresh cookie
      });
    } catch {
      // Network failure / CORS / server down: treat as no session so callers
      // (e.g. the startup restore) resolve to anonymous instead of hanging.
      tokens.set(null);
      return false;
    }
    if (!response.ok) {
      tokens.set(null);
      return false;
    }
    const data = (await response.json()) as { access_token: string };
    tokens.set(data.access_token);
    return true;
  }

  function refresh(): Promise<boolean> {
    inFlight ??= doRefresh().finally(() => {
      inFlight = null;
    });
    return inFlight;
  }

  async function send(path: string, init: RequestInit): Promise<Response> {
    const headers = new Headers(init.headers);
    const token = tokens.get();
    if (token) headers.set('Authorization', `Bearer ${token}`);
    if (init.body !== undefined && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
    return fetch(`${baseUrl}${path}`, {
      ...init,
      headers,
      credentials: 'include',
    });
  }

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    let response = await send(path, init);

    // The access token may have expired; try one refresh + replay.
    if (response.status === 401) {
      const refreshed = await refresh();
      if (refreshed) response = await send(path, init);
    }

    if (!response.ok) throw await toApiError(response);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  return { request, refresh };
}
