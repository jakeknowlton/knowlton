import type { LaundryLoad, LaundryStatus, User } from "@knowlton/shared";

// Re-export the domain types so consumers can import everything API-shaped from
// one place, while the canonical definitions stay in @knowlton/shared.
export type { LaundryLoad, LaundryStatus, User };

export interface Credentials {
  username: string;
  password: string;
}

/** The login/refresh response. Note: no refresh token — it lives in a cookie. */
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface LaundryLoadCreate {
  label?: string | null;
}

export interface LaundryLoadUpdate {
  status?: LaundryStatus;
  label?: string | null;
  washer_duration_minutes?: number;
  dryer_duration_minutes?: number;
}
