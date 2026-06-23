# web

Vue 3 + TypeScript + Vite frontend for Knowlton.

```sh
pnpm web
pnpm --filter web check
pnpm --filter web build
```

The API base URL comes from `VITE_API_URL` and defaults to
`http://localhost:8000`. The backend must allow the same origin through its
`FRONTEND_ORIGIN` setting because auth uses credentialed refresh-cookie
requests.

Source layout:

```
src/
  app/                  app boot and session shell
  auth/
    components/         login/register UI
  home/
    laundry/
      components/       laundry UI
      composables/      laundry data, mutations, and timer state
  shared/
    api/                API client singleton
    errors/             cross-feature error helpers
```

Domain sections should mirror the backend (`home`, then later `food` and
`goals`). Inside each section, files are grouped by function.
