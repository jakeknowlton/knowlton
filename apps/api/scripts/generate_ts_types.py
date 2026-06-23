from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


API_ROOT = Path(__file__).resolve().parents[1]
HTTP_METHODS = {"delete", "get", "patch", "post", "put"}


def schema_ref(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def collect_refs(schema: dict[str, Any]) -> list[str]:
    refs: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str):
                refs.append(schema_ref(ref))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schema)
    return refs


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def array_type(item_type: str) -> str:
    if " | " in item_type:
        return f"({item_type})[]"
    return f"{item_type}[]"


def object_type(schema: dict[str, Any], level: int) -> str:
    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        return "Record<string, unknown>"

    indent = "  " * level
    child_indent = "  " * (level + 1)
    required = set(schema.get("required", []))
    lines = ["{"]

    for name, child_schema in properties.items():
        optional = "" if name in required else "?"
        lines.append(
            f"{child_indent}{json.dumps(name)}{optional}: "
            f"{ts_type(child_schema, level + 1)};"
        )

    lines.append(f"{indent}}}")
    return "\n".join(lines)


def ts_type(schema: dict[str, Any], level: int = 0) -> str:
    if "$ref" in schema:
        return schema_ref(schema["$ref"])

    if "anyOf" in schema:
        return " | ".join(unique([ts_type(item, level) for item in schema["anyOf"]]))

    if "oneOf" in schema:
        return " | ".join(unique([ts_type(item, level) for item in schema["oneOf"]]))

    if "enum" in schema:
        return " | ".join(json.dumps(item) for item in schema["enum"])

    schema_type = schema.get("type")

    if isinstance(schema_type, list):
        return " | ".join(
            unique([ts_type({**schema, "type": item}, level) for item in schema_type])
        )

    if schema_type == "null":
        return "null"
    if schema_type == "string":
        return "string"
    if schema_type in {"integer", "number"}:
        return "number"
    if schema_type == "boolean":
        return "boolean"
    if schema_type == "array":
        return array_type(ts_type(schema.get("items", {}), level))
    if schema_type == "object":
        return object_type(schema, level)

    return "unknown"


def render(openapi: dict[str, Any]) -> str:
    schemas = openapi["components"]["schemas"]
    public_schemas = public_schema_names(openapi)
    lines = [
        "// Generated from apps/api OpenAPI schema by scripts/generate_ts_types.py.",
        "// Do not edit by hand.",
        "",
    ]

    for name in public_schemas:
        lines.append(f"export type {name} = {ts_type(schemas[name])};")

    lines.append("")
    return "\n".join(lines)


def add_schema_refs(
    names: list[str],
    seen: set[str],
    schema: dict[str, Any] | None,
) -> None:
    if schema is None:
        return
    for name in collect_refs(schema):
        if name not in seen:
            seen.add(name)
            names.append(name)


def public_schema_names(openapi: dict[str, Any]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()

    for path_item in openapi["paths"].values():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue

            request_content = operation.get("requestBody", {}).get("content", {})
            add_schema_refs(
                names,
                seen,
                request_content.get("application/json", {}).get("schema"),
            )

            for status_code, response in operation.get("responses", {}).items():
                if not status_code.startswith("2"):
                    continue
                response_content = response.get("content", {})
                add_schema_refs(
                    names,
                    seen,
                    response_content.get("application/json", {}).get("schema"),
                )

    schemas = openapi["components"]["schemas"]
    index = 0
    while index < len(names):
        add_schema_refs(names, seen, schemas[names[index]])
        index += 1

    return names


def load_openapi() -> dict[str, Any]:
    os.environ.setdefault("SECRET_KEY", "openapi-generation-only")
    os.chdir(API_ROOT)
    sys.path.insert(0, str(API_ROOT))

    from main import app

    return app.openapi()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate TypeScript component types from the FastAPI OpenAPI schema.",
    )
    parser.add_argument("output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    content = render(load_openapi())

    if args.check:
        if not output.exists() or output.read_text() != content:
            print(f"{output} is out of date; run `pnpm api:types`.")
            return 1
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
