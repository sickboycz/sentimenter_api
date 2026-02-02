# Source Registry

- `source_registry.yaml` — default enabled set for v1.0.
- `source_registry.schema.json` — JSON Schema validator.

Operational notes:
- A source can be disabled immediately by setting `enabled: false` and reloading registry.
- Use packs to disable entire categories (e.g., disable `optional_media_rss` to reduce noise/cost).
- Treat *paid/restricted* sources as metadata-only unless licensed.

- `source_registry_extra_global.yaml` — optional expansion library (disabled by default)
