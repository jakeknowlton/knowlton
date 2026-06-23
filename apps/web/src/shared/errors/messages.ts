import { ApiError } from '@knowlton/api-client';

export function errorMessage(
  error: unknown,
  fallback = 'Request failed',
): string {
  return error instanceof ApiError ? error.detail : fallback;
}
