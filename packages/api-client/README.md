# @knowlton/api-client

Typed client for the backend API. Owns HTTP and token handling so frontend code
does not duplicate the security-critical parts.

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
  generated.ts    generated request/response shapes
  errors.ts       ApiError + FastAPI detail extraction
```

## Generated types

Request and response shapes come from FastAPI's OpenAPI schema:

```sh
pnpm api:types
```

`src/generated.ts` is generated. Keep hand-written code in the small client
modules (`auth.ts`, `http.ts`, `laundry.ts`) so transport and token handling stay
easy to read.

The generator discovers public types from JSON request bodies and successful
JSON responses in the OpenAPI paths, then includes any referenced component
schemas. Form-only internals and validation-error schemas stay out of the
client surface.
