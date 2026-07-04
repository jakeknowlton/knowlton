# Recipes Backend — Implementation Plan

Backend API for the **food → recipes** subsection. All endpoints are scoped under
`/recipes` (section name `food` stays out of the path, exactly as `home` does for
laundry; the subsection name `recipes` *is* the prefix, like `laundry` in
`/laundry/loads`).

This plan is the output of a design review. The "why" behind each choice lives in
the **Design decisions** section at the bottom; the phases above it are the
build order.

---

## Conventions (inherited from the existing codebase)

- Feature module: `food/recipes/{models,schemas,service,router}.py` + supporting
  modules, aggregated by `food/router.py`, mounted in `main.py`.
- SQLModel tables; integer **Unix timestamps**; `created_by` FK → `user.id`.
- Separate Pydantic `Create` / `Update` / `Read` schemas.
- Thin routers → service layer that raises **domain exceptions**; router maps them
  to `HTTPException`.
- Auth on everything via `get_current_active_user`.
- **SQLite now / Postgres later** → constraints must be dialect-portable; cascade
  via ORM relationships (not DB-engine `ON DELETE`, which SQLite needs a PRAGMA for).
- Per-feature test factories under `tests/food/recipes/`.
- New schemas flow to the frontend via `scripts/generate_ts_types.py`.

---

## Target module layout

```
apps/api/food/
  __init__.py
  router.py                # includes recipes router (no prefix of its own)
  recipes/
    __init__.py
    enums.py               # Unit, Dimension, IngredientCategory, MealType, Course
    quantities.py          # rational parse / reduce / render / scale (fractions.Fraction)
    units.py               # UNIT_META {Unit: (Dimension, base_factor|None)}, convert()
    rendering.py           # step-token grammar + render(text, refs, scale)
    models.py              # Ingredient, IngredientAlias, Tag, RecipeTag,
                           #   Recipe, RecipeIngredient, RecipeStep
    schemas.py             # write + read (base & scaled) models
    service.py             # catalog get-or-create, recipe CRUD, search, scaling
    router.py              # all routes under prefix="/recipes"
apps/api/tests/food/recipes/
  __init__.py
  factories.py
  test_*.py
```

`main.py`: add `from food.router import router as food_router` +
`app.include_router(food_router)`.

---

## Phase 0 — Scaffolding & wiring

- [ ] Create `food/` and `food/recipes/` packages (empty `__init__.py`s).
- [ ] `food/router.py`: `APIRouter()` that `include_router`s the recipes router
      (no prefix), mirroring `home/router.py`.
- [ ] `recipes/router.py`: `APIRouter(prefix="/recipes", tags=["recipes"])`
      (empty for now).
- [ ] Wire `food_router` into `main.py`.
- [ ] `tests/food/recipes/` package + a smoke test hitting `GET /recipes` (empty list).

**Acceptance:** app boots, `GET /recipes` returns `[]`, `pnpm api:test` green.

---

## Phase 1 — Quantity & unit primitives (pure, no DB)

These are pure functions, fully unit-testable before any model exists.

- [ ] `enums.py`:
  - `Dimension(str, Enum)`: `MASS, VOLUME, COUNT, INFORMAL`.
  - `Unit(str, Enum)`: e.g. `GRAM='g', KILOGRAM='kg', OUNCE='oz', POUND='lb',
    MILLILITER='ml', LITER='l', TSP='tsp', TBSP='tbsp', CUP='cup', FLOZ='fl_oz',
    PIECE='piece', CLOVE='clove', SLICE='slice', PINCH='pinch', DASH='dash',
    TO_TASTE='to_taste'`.
  - `IngredientCategory(str, Enum)`: `PRODUCE, DAIRY, MEAT_SEAFOOD, BAKERY,
    PANTRY, CANNED, FROZEN, SPICES, CONDIMENTS, BEVERAGES, SNACKS, BAKING,
    DELI, OTHER`.
  - `MealType(str, Enum)`: `BREAKFAST, LUNCH, DINNER, SNACK, DESSERT`.
  - `Course(str, Enum)`: `APPETIZER, MAIN, SIDE, DRINK, SAUCE`.
- [ ] `units.py`:
  - `UNIT_META: dict[Unit, tuple[Dimension, float | None]]` (base unit per
    dimension: gram for MASS, milliliter for VOLUME, piece for COUNT; INFORMAL
    units have factor `None`).
  - `unit_display(unit, plural: bool) -> str` (e.g. `cup`/`cups`, `to_taste`→"to taste").
  - `convert(value: Fraction, frm: Unit, to: Unit) -> Fraction` — within-dimension
    only; raises `IncompatibleUnitsError` across dimensions or for INFORMAL.
    *(Not used by recipes yet; built here for the grocery feature.)*
- [ ] `quantities.py` (wraps `fractions.Fraction`):
  - `parse_quantity(raw: str) -> Fraction` — accepts `"2"`, `"1 1/2"`, `"3/2"`,
    `"0.5"`. Rejects `<= 0` and zero denominators (`InvalidQuantityError`).
  - `to_columns(q: Fraction) -> tuple[int, int]` — reduced `(num, den)`.
  - `from_columns(num: int, den: int) -> Fraction`.
  - `format_quantity(q: Fraction) -> str` — mixed number, e.g. `9/2` → `"4 1/2"`,
    `1/3` → `"1/3"`, `2/1` → `"2"`.
  - `scale(q: Fraction, factor: Fraction) -> Fraction`.

**Acceptance:** exhaustive unit tests — round-trip parse/format, exact scaling
(`1/3 * 3 == 1`), reduction, conversion within/across dimensions.

---

## Phase 2 — Catalog: Ingredient, IngredientAlias, Tag

**Models (`models.py`):**
- [ ] `Ingredient`: `id`, `name`, `name_normalized` **[UNIQUE]**,
      `category: IngredientCategory | None`, `is_staple: bool = False`, `created_at`.
- [ ] `IngredientAlias`: `id`, `alias_normalized` **[UNIQUE]**,
      `ingredient_id` FK → `Ingredient`.
- [ ] `Tag`: `id`, `name`, `name_normalized` **[UNIQUE]**, `created_at`.

**Service (`service.py`):**
- [ ] `normalize(name) -> str` — lowercase, strip, collapse internal whitespace.
- [ ] `get_or_create_ingredient(session, name, *, category=None, is_staple=False)`
      — match on `name_normalized`, then alias table; create if absent. Handle the
      unique-violation race (catch `IntegrityError`, rollback, re-select).
- [ ] `get_or_create_tag(session, name)`.
- [ ] `search_ingredients(session, q, limit)` / `search_tags(session, q, limit)`
      — prefix/substring match on `name_normalized` for autocomplete.

**Endpoints (`router.py`):**
- [ ] `GET /recipes/ingredients?q=&limit=` → `list[IngredientRead]`.
- [ ] `GET /recipes/tags?q=&limit=` → `list[TagRead]`.

> Catalog **mutation/merge/delete is intentionally out of scope for v1**. Rows are
> created only as a side effect of recipe writes (or the search endpoints' future
> create-on-miss). A used ingredient must never become silently deletable.

**Acceptance:** get-or-create dedups by normalized name and alias; concurrent
create doesn't duplicate; autocomplete returns ranked matches.

---

## Phase 3 — Recipe aggregate models

**Models (`models.py`):**
- [ ] `Recipe`: `id`, `created_at`, `updated_at`, `created_by` FK → `user.id`,
      `version: int = 1`, `name`, `description | None`,
      `prep_time_minutes | None`, `cook_time_minutes | None`, `source | None`,
      `meal_type | None`, `course | None`,
      `yield_quantity_num: int`, `yield_quantity_den: int`, `yield_unit: str`.
- [ ] `RecipeIngredient`: `id`, `recipe_id` FK, `ingredient_id` FK,
      `ref_key: str`, `quantity_num | None`, `quantity_den | None`,
      `unit: Unit | None`, `preparation | None`, `is_optional: bool = False`,
      `section | None`, `position: int`.
      Constraints: **UNIQUE(recipe_id, ref_key)**, **INDEX(ingredient_id)**
      (shared-ingredient search), INDEX(recipe_id).
- [ ] `RecipeStep`: `id`, `recipe_id` FK, `position: int`, `section | None`,
      `text: str` (raw, contains tokens). INDEX(recipe_id).
- [ ] `RecipeTag`: `recipe_id` FK, `tag_id` FK, **PK(recipe_id, tag_id)**.
- [ ] ORM relationships with `cascade="all, delete-orphan"` from `Recipe` to
      `RecipeIngredient`, `RecipeStep`, `RecipeTag` (portable cascade).

**Acceptance:** tables create on SQLite; deleting a `Recipe` removes its children
via ORM cascade.

---

## Phase 4 — Schemas

**Token-aware quantity field:** a Pydantic type that serializes a stored
`(num, den)` to a `{num, den, display}` object and parses an input string via
`parse_quantity`.

- [ ] Writes:
  - `RecipeIngredientWrite`: `ref_key`, `ingredient` (name; get-or-create) or
    `ingredient_id`, `quantity: str | None`, `unit: Unit | None`,
    `preparation | None`, `is_optional`, `section | None`, `position`.
  - `RecipeStepWrite`: `text`, `position`, `section | None`.
  - `RecipeCreate`: scalars + `yield_quantity: str` + `yield_unit` +
    `ingredients: list[RecipeIngredientWrite]` + `steps: list[RecipeStepWrite]` +
    `tags: list[str]`.
  - `RecipeUpdate`: `RecipeCreate` **+ `version: int`** (full-replace).
- [ ] Reads:
  - `IngredientRead`, `TagRead`.
  - `RecipeIngredientRead`: `ref_key`, `ingredient` (`IngredientRead`),
    `quantity_num/den | None`, `quantity_display | None`, `unit | None`,
    `preparation`, `is_optional`, `section`, `position`.
  - `RecipeStepRead`: `position`, `section`, `text_template` (raw, for editing),
    `text_rendered` (tokens resolved at the requested scale).
  - `RecipeRead`: scalars + `version`, `scale` (default `"1"`), `effective_yield`
    (`{quantity_display, unit}`), `ingredients`, `steps`, `tags`.
    A scaled read reuses the same shape with scaled quantities + `scale` set.

---

## Phase 5 — Create (atomic nested write)

`POST /recipes` → `RecipeCreate`. In **one transaction**:
- [ ] Validate `ref_key`s: unique within payload, charset `[a-z0-9_-]`.
- [ ] Validate every step token references a `ref_key` present in `ingredients`
      → else `RecipeValidationError` (`422`).
- [ ] `get_or_create` each ingredient (by `ingredient_id` or name) and each tag.
- [ ] Insert `Recipe` (`created_by` from current user, `version=1`,
      timestamps), then children with their `position`s.
- [ ] Return `RecipeRead` (scale 1).

**Acceptance:** round-trip create→read; bad token → 422; duplicate ref_key → 422;
reused catalog ingredient is not duplicated.

---

## Phase 6 — Read & scaling (compute-on-read)

- [ ] `rendering.py`: token grammar
      `{{ri:<ref_key>}}` | `{{ri:<ref_key>*<n>/<d>}}` | `{{ri:<ref_key>|name}}`
      | `{{ri:<ref_key>|amount}}`. Default renders **amount + name**
      (e.g. `"4 cups flour"`); `|amount` → `"4 cups"`; `|name` → `"flour"`.
      Null-quantity informal units render the unit display (`"to taste"`).
      `render(text, refs, scale) -> str`.
- [ ] `service.get_recipe(session, id, *, to_yield=None, scale=None)`:
  - factor = `Fraction(to_yield)/base_yield` if `to_yield`, else
    `parse_quantity(scale)` if `scale`, else `1`.
  - scale every non-null ingredient quantity by factor; scale `yield_quantity`.
  - build `refs` (ref_key → scaled qty + unit + ingredient name) and render steps.
- [ ] `GET /recipes/{recipe_id}?to_yield=&scale=` → `RecipeRead` (404 if missing).
      `int` path param keeps `/recipes/ingredients|tags|makeable` unambiguous.

**Acceptance:** `?to_yield=6` on a 4-serving recipe yields exact `3/2` scaling in
both ingredient quantities and rendered step text; time/temp literals untouched;
base read unchanged.

---

## Phase 7 — Update (full replace) & delete

- [ ] `PUT /recipes/{recipe_id}` → `RecipeUpdate`. In one transaction:
  - 404 if missing; **`409` if `version` mismatches** current.
  - Same ref_key + token validation as create.
  - Diff children **by `ref_key`** (ingredients) and rebuild steps/tags;
    delete-reinsert is safe because tokens reference `ref_key`, not DB id.
  - Bump `version`, set `updated_at`. Return `RecipeRead`.
- [ ] `DELETE /recipes/{recipe_id}` → `204`; ORM cascade removes children.

**Acceptance:** stale version → 409; removing a still-referenced ingredient line
fails validation (422); successful PUT bumps version; delete cascades.

---

## Phase 8 — Search

- [ ] **Filter** `GET /recipes?ingredient=&ingredient=&meal_type=&course=&tag=&q=`:
  multi `ingredient` = **AND** (`GROUP BY recipe HAVING count(distinct
  ingredient_id) == n`); `meal_type`/`course` equality; `tag` via join; `q` name
  substring. → `list[RecipeRead]` (base scale).
- [ ] **Similar** `GET /recipes/{recipe_id}/similar?limit=`: self-join on shared
  `ingredient_id`, exclude self, order by shared count desc. →
  `[{recipe, shared_count, shared_ingredients}]`.
- [ ] **Makeable** `GET /recipes/makeable?have=&max_missing=N`: per recipe,
  `missing = required (not is_optional) AND non-staple AND ingredient_id NOT IN
  have`; keep where `count(missing) <= N`; annotate each with its missing
  ingredients. (Presence-only — quantities ignored until an inventory model exists.)

**Acceptance:** AND filter excludes partial matches; similar ranks by overlap;
makeable respects staple + optional exclusions and `max_missing`.

---

## Phase 9 — Tests & factories

- [ ] `tests/food/recipes/factories.py`: `make_ingredient`, `make_tag`,
      `make_recipe` (writes directly, like `make_load`) for arranging search state.
- [ ] Coverage: quantities/units (Phase 1), catalog dedup, create/read/scale,
      update/version/delete, all three searches, token validation & rendering.

---

## Phase 10 — Frontend types

- [ ] Run `pnpm api:types` to regenerate `packages/api-client/src/generated.ts`;
      confirm `pnpm api:types:check` is clean. (No client methods in this plan —
      that's a separate frontend task.)

---

## Error → HTTP mapping

| Condition | Status |
|---|---|
| Recipe not found | 404 |
| Bad token ref / duplicate ref_key / invalid quantity / unknown unit | 422 |
| `PUT` version mismatch | 409 |
| (future) delete catalog ingredient in use | 409 |

---

## Design decisions (reference)

| # | Decision |
|---|---|
| 1 | Canonical `Ingredient` catalog + `RecipeIngredient` join (not free-text). |
| 2 | Global shared catalog; open creation, guarded merge/rename (deferred). |
| 3 | Dedup: `name_normalized` UNIQUE + get-or-create + `IngredientAlias`. |
| 4 | Units: `str` enum + in-code dimension/factor map; conversion is pure, used later. |
| 5 | Quantities: rational `num/den` (exact scaling), nullable. |
| 6 | No quantity ranges (range nuance → `preparation` text). |
| 7 | Yield: rational `yield_quantity` + free-text `yield_unit` label. |
| 8 | Instructions: templated steps with tokens → `RecipeIngredient` amounts; time/temp stay literal. |
| 9 | Token integrity: stable `ref_key` + validate-on-write + (subsumed by PUT validation). |
| 10 | Scaling: server-side, compute-on-read (`to_yield`/`scale`); base immutable. |
| 11 | Access: fully shared household-global; keep `created_by`; permissions later. |
| 12 | Sections: lightweight nullable `section` label on ingredients & steps. |
| 13 | `Ingredient.category` enum (nullable) now, for grocery aisle-grouping. |
| 14 | Searches: ingredient filter (AND) + `/similar` + `/makeable`. |
| 15 | Pantry: `is_staple` flag; presence-only; exclude staples + optional. |
| 16 | Categorization: `meal_type`/`course` enums + normalized `Tag` catalog + `RecipeTag`. |
| 17 | Writes: atomic nested `POST` + full-aggregate `PUT` (diff by `ref_key`, one txn). |
| 18 | Concurrency: optimistic `version` + `409`; `updated_at` added. |
| 19 | Delete: hard delete + ORM cascade; catalog delete out of scope. |

## Deferred / future

- Cross-dimension conversion via per-ingredient **density** (cup ↔ g) — for grocery
  aggregation across mixed units.
- Quantity **ranges**; pantry **quantity-awareness** (needs inventory).
- Catalog **merge/rename/delete** (guarded operations).
- Recipe **reference integrity** (FK `RESTRICT` vs snapshot) — decided when meal
  planning references recipes.
- Recipe **images**, **nutrition** (derivable from ingredient data), metric/imperial
  **display preferences**, "nice number" scaled rounding (frontend policy).
- **Seed data** for common ingredients + staples.
