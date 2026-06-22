# @knowlton/api-client

Typed client for the backend API, shared by `web` and `mobile` (placeholder).

The FastAPI backend exposes an OpenAPI schema at `/openapi.json`. Generate a
typed client from it so both frontends share types that track the backend.

For example, with [`openapi-typescript`](https://openapi-ts.dev) + `openapi-fetch`:

```sh
# with the API running locally
pnpm --filter @knowlton/api-client exec openapi-typescript \
  http://localhost:8000/openapi.json -o src/schema.d.ts
```

Then export a small wrapper around `openapi-fetch` configured with the base URL.
