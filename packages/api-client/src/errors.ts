/** A failed API response, carrying the HTTP status and a human-readable detail. */
export class ApiError extends Error {
  declare readonly status: number;
  declare readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** Build an ApiError from a non-OK Response, extracting FastAPI's `detail`. */
export async function toApiError(response: Response): Promise<ApiError> {
  let detail = response.statusText || "Request failed";
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      detail = body.detail;
    } else if (Array.isArray(body?.detail)) {
      // FastAPI validation errors arrive as a list of { msg, loc, ... }.
      detail = body.detail
        .map((item: { msg?: string }) => item.msg)
        .filter(Boolean)
        .join(", ");
    }
  } catch {
    // Non-JSON body; keep the status text.
  }
  return new ApiError(response.status, detail);
}
