# knowlton

Monorepo containing the backend API, Vue web app, and shared TypeScript
packages.

## Layout

```
apps/
  api/        FastAPI backend (uv)        → see apps/api/README.md
  web/        Vue 3 + Vite frontend       → see apps/web/README.md
  mobile/     future React Native / Expo app placeholder
packages/
  api-client/ typed HTTP client + token handling → see its README
  shared/     framework-agnostic domain types & pure helpers
```

Dependency direction: `web` → `api-client` → `shared` (and `web` → `shared`).

`apps/api` is a self-contained Python project (its own `pyproject.toml`,
`uv.lock`, and `.venv`). The web app and shared packages form a pnpm workspace
defined in `pnpm-workspace.yaml`.

## Getting started

Backend:

```sh
cd apps/api && uv sync && uv run fastapi dev
```

Web frontend:

```sh
pnpm install     # installs all JS workspace deps
pnpm web         # run the web app (needs the API running)
```

The web app talks to the API at `VITE_API_URL` (default
`http://localhost:8000`), which must match the API's `FRONTEND_ORIGIN` for
credentialed CORS.

Useful root scripts:

```sh
pnpm check      # type-check web/packages and verify generated API types
pnpm build      # production web build
pnpm verify     # check + build + backend tests
pnpm api:types  # regenerate TypeScript API schema types from FastAPI OpenAPI
```
