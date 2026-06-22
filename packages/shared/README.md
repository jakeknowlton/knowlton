# @knowlton/shared

Framework-agnostic domain model shared by `web` and `mobile`: types and pure
helpers, no I/O.

```
src/
  laundry.ts   LaundryStatus, LaundryLoad, status ordering/labels, countdowns
  user.ts      User
  index.ts
```

Keep HTTP/transport concerns in `@knowlton/api-client`; keep anything that's
just data shapes or pure logic here. The package is consumed as TypeScript
source (no build step) via its `exports` map.
