/** A failed API response, carrying the HTTP status and a human-readable detail. */
export class ApiError extends Error {
  declare readonly status: number;
  declare readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

/** Build an ApiError from a non-OK Response, extracting FastAPI's `detail`. */
export async function toApiError(response: Response): Promise<ApiError> {
  let detail = response.statusText || 'Request failed';
  try {
    const body: unknown = await response.json();
    const raw = isRecord(body) ? body.detail : undefined;
    if (typeof raw === 'string') {
      detail = raw;
    } else if (Array.isArray(raw)) {
      // FastAPI validation errors arrive as a list of { msg, loc, ... }.
      detail = (raw as unknown[])
        .map((item) =>
          isRecord(item) && typeof item.msg === 'string' ? item.msg : '',
        )
        .filter(Boolean)
        .join(', ');
    }
  } catch {
    // Non-JSON body; keep the status text.
  }
  return new ApiError(response.status, detail);
}
