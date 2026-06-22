# @knowlton/api-client

Typed client for the backend API, shared by `web` and `mobile`. Owns all HTTP
and token handling so every frontend gets the security-critical parts right.

```ts
import { createApiClient } from "@knowlton/api-client";

const api = createApiClient({ baseUrl: "http://localhost:8000" });

await api.auth.register({ username, password });
await api.auth.login({ username, password });
await api.auth.restore();             // revive session from the refresh cookie
const loads = await api.laundry.list();
```

## Token handling

- The **access token** lives only in memory (`token-store.ts`) and is sent as a
  `Bearer` header. Never persisted, so XSS cannot exfiltrate it from storage.
- The **refresh token** is never touched by JS — it is an `HttpOnly` cookie set
  by the backend. Requests use `credentials: "include"` so the browser attaches
  it automatically.
- `http.ts` retries a single request once on `401`, refreshing first. Concurrent
  401s share **one** in-flight refresh (`inFlight`), so the server-rotated
  refresh token is exchanged exactly once.

```
src/
  index.ts        createApiClient(); wires the pieces together
  token-store.ts  in-memory access token + auth-state subscription
  http.ts         fetch wrapper with coalesced refresh-and-retry on 401
  auth.ts         register / login / logout / restore
  laundry.ts      load CRUD
  types.ts        request/response shapes (re-exports domain types from shared)
  errors.ts       ApiError + FastAPI detail extraction
```

## Types

Domain types come from `@knowlton/shared` and are re-exported here alongside the
request/response shapes. These are currently hand-written to match the backend.
They could later be generated from the API's OpenAPI schema (e.g. with
`openapi-typescript`) and swapped in behind this same surface.
