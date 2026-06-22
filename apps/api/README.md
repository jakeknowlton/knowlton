# api

FastAPI backend, managed with [uv](https://docs.astral.sh/uv/).

```sh
cd apps/api
uv sync              # install deps into .venv
cp .env.example .env # then fill in SECRET_KEY (openssl rand -hex 32)
uv run fastapi dev   # serve at http://localhost:8000
uv run pytest        # run tests
```

OpenAPI schema is served at `/openapi.json` — used to generate
`@knowlton/api-client` for the frontends.
