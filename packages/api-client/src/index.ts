import { createAuth, type AuthClient } from "./auth";
import { createHttp } from "./http";
import { createLaundry, type LaundryClient } from "./laundry";
import { createTokenStore } from "./token-store";

export interface ApiClientConfig {
  /** Base URL of the backend, e.g. "http://localhost:8000". */
  baseUrl: string;
}

export interface ApiClient {
  auth: AuthClient;
  laundry: LaundryClient;
}

/**
 * Construct an API client. Each client owns its own in-memory access token, so
 * the returned instance is the single source of truth for the session.
 */
export function createApiClient(config: ApiClientConfig): ApiClient {
  const tokens = createTokenStore();
  const http = createHttp(config.baseUrl, tokens);
  return {
    auth: createAuth(config.baseUrl, http, tokens),
    laundry: createLaundry(http),
  };
}

export { ApiError } from "./errors";
export type { AuthClient } from "./auth";
export type { LaundryClient } from "./laundry";
export type * from "./generated";
