// Generated from apps/api OpenAPI schema by scripts/generate_ts_types.py.
// Do not edit by hand.

export type TokenResponse = {
  "access_token": string;
  "token_type"?: string;
};
export type UserCreate = {
  "username": string;
  "password": string;
};
export type UserRead = {
  "username": string;
  "id": number;
  "disabled": boolean;
};
export type LaundryLoadRead = {
  "id": number;
  "created_at": number;
  "created_by": number;
  "label": string | null;
  "status": LaundryStatus;
  "washer_finish": number | null;
  "dryer_finish": number | null;
};
export type LaundryLoadCreate = {
  "label"?: string | null;
};
export type LaundryLoadUpdate = {
  "status"?: LaundryStatus | null;
  "label"?: string | null;
  "washer_duration_minutes"?: number | null;
  "dryer_duration_minutes"?: number | null;
};
export type LaundryStatus = "dirty" | "washing" | "drying" | "folding" | "done";
