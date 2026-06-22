# knowlton

Monorepo containing the backend API and frontends.

## Layout

```
apps/
  api/        FastAPI backend (uv)        → see apps/api/README.md
  web/        SvelteKit SPA (Svelte 5)    → see apps/web/README.md
  mobile/     React Native / Expo app (placeholder)
packages/
  api-client/ typed HTTP client + token handling → see its README
  shared/     framework-agnostic domain types & pure helpers
```

Dependency direction: `web` → `api-client` → `shared` (and `web` → `shared`).

`apps/api` is a self-contained Python project (its own `pyproject.toml`,
`uv.lock`, and `.venv`). The JS frontends and shared packages form a pnpm
workspace defined in `pnpm-workspace.yaml`.

## Getting started

Backend:

```sh
cd apps/api && uv sync && uv run fastapi dev
```

Frontends:

```sh
pnpm install     # installs all JS workspace deps
pnpm web         # run the web app (needs the API running)
pnpm mobile      # run the mobile app (placeholder)
```

The web app talks to the API at `VITE_API_URL` (default `http://localhost:8000`),
which must match the API's `FRONTEND_ORIGIN` for credentialed CORS.

Root scripts: `pnpm api` / `pnpm api:test` proxy to the backend.
