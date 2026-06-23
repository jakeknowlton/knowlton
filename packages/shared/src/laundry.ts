/**
 * Laundry domain model and pure helpers, shared by every frontend.
 *
 * This module intentionally holds no I/O — only the shapes that mirror the API
 * and the framework-agnostic logic for interpreting them (status ordering,
 * labels, countdowns). The HTTP transport lives in `@knowlton/api-client`.
 */

export type LaundryStatus = 'dirty' | 'washing' | 'drying' | 'folding' | 'done';

/** Statuses in the order a load naturally progresses through them. */
export const LAUNDRY_STATUSES: readonly LaundryStatus[] = [
  'dirty',
  'washing',
  'drying',
  'folding',
  'done',
] as const;

const STATUS_LABELS: Record<LaundryStatus, string> = {
  dirty: 'Dirty',
  washing: 'Washing',
  drying: 'Drying',
  folding: 'Folding',
  done: 'Done',
};

export function statusLabel(status: LaundryStatus): string {
  return STATUS_LABELS[status];
}

/** Statuses that occupy a machine and therefore carry a finish countdown. */
export function machineFor(status: LaundryStatus): 'washer' | 'dryer' | null {
  if (status === 'washing') return 'washer';
  if (status === 'drying') return 'dryer';
  return null;
}

export interface LaundryLoad {
  id: number;
  created_at: number; // unix seconds
  created_by: number;
  label: string | null;
  status: LaundryStatus;
  washer_finish: number | null; // unix seconds
  dryer_finish: number | null; // unix seconds
}

/**
 * Seconds remaining until a finish timestamp, or null when there is none.
 * Clamped at zero so callers never show negative time.
 */
export function remainingSeconds(
  finish: number | null,
  nowMs: number = Date.now(),
): number | null {
  if (finish === null) return null;
  return Math.max(0, finish - Math.floor(nowMs / 1000));
}

/** Format a non-negative second count as "M:SS". */
export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
