# knowlton

Monorepo containing the backend API and frontends.

## Layout

```
apps/
  api/        FastAPI backend (uv)        → see apps/api/README.md
  web/        web frontend (placeholder)
  mobile/     React Native / Expo app (placeholder)
packages/
  api-client/ typed client generated from the API's OpenAPI schema
  shared/     shared TS types, validation, constants
```

`apps/api` is a self-contained Python project (its own `pyproject.toml`,
`uv.lock`, and `.venv`). The JS frontends and shared packages form a pnpm
workspace defined in `pnpm-workspace.yaml`.

## Getting started

Backend:

```sh
cd apps/api && uv sync && uv run fastapi dev
```

Frontends (once scaffolded):

```sh
pnpm install     # installs all JS workspace deps
pnpm web         # run the web app
pnpm mobile      # run the mobile app
```

Root scripts: `pnpm api` / `pnpm api:test` proxy to the backend.
