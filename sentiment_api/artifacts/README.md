# Artifacts — universe seed data (in git)

These CSVs are copied from `registry/` so they are always available for seeding universes (sectors, industries, S&P 500, Nasdaq-100) without depending on an external registry path.

- **sp500.csv** — S&P 500 constituents (semicolon-separated)
- **nasdaq100.csv** — Nasdaq-100 constituents (semicolon-separated)
- **sectors.csv** — GICS-like sectors
- **industries.csv** — GICS industries (sector_id, industry_id, name)

Used by `refresh_universes()` when `registry/` does not contain the CSVs (e.g. in Docker when only `source_registry.yaml` is mounted). Scripts and install flow may copy these into a volume or use this path directly.

Do not ignore these files in `.gitignore`; they are part of the repo for a clean install.
