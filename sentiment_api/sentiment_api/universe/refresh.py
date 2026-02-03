"""Universe constituents refresh (idempotent). Loads from registry CSV files."""

import asyncio
import csv
from datetime import date
from pathlib import Path

from sentiment_api.config import get_settings
from sentiment_api.db.pool import init_pool, acquire
from sentiment_api.db.universe_repo import (
    seed_sectors,
    seed_industries,
    upsert_universe,
    upsert_security,
    upsert_universe_membership,
)


def _load_sp500(registry_dir: Path) -> list[tuple[str, str]]:
    """Load (name, symbol) from registry/sp500.csv. Semicolon-separated; first column rank, then Company, Symbol."""
    path = registry_dir / "sp500.csv"
    rows: list[tuple[str, str]] = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(";")
            if len(parts) >= 3 and parts[1] and parts[2]:
                name, symbol = parts[1].strip(), parts[2].strip()
                if symbol and name:
                    rows.append((name, symbol))
            elif len(parts) == 2 and parts[0] and parts[1] and not parts[0].isdigit():
                # header or alternate format
                continue
    return rows


def _load_nasdaq100(registry_dir: Path) -> list[tuple[str, str]]:
    """Load (name, symbol) from registry/nasdaq100.csv. Semicolon-separated; header Company;Symbol."""
    path = registry_dir / "nasdaq100.csv"
    rows: list[tuple[str, str]] = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        first = True
        for row in reader:
            if len(row) >= 2 and row[0].strip() and row[1].strip():
                if first and row[0].lower() == "company" and row[1].lower() == "symbol":
                    first = False
                    continue
                name, symbol = row[0].strip(), row[1].strip()
                if symbol and name:
                    rows.append((name, symbol))
            first = False
    return rows


async def refresh_universes() -> str:
    """Refresh sectors and universe constituents from registry CSVs. Dedupes by symbol; stores index via universe_memberships."""
    settings = get_settings()
    await init_pool(settings.database_url)

    # Resolve dir for universe CSVs: registry (parent of source_registry_path), then artifacts, then registry/
    root = Path(__file__).resolve().parent.parent.parent
    base = Path(settings.source_registry_path).parent
    if not (base / "sp500.csv").exists() and not (base / "nasdaq100.csv").exists():
        base = root / "artifacts"
    if not (base / "sp500.csv").exists() and not (base / "nasdaq100.csv").exists():
        base = root / "registry"

    sp500_rows = _load_sp500(base)
    nasdaq100_rows = _load_nasdaq100(base)

    # Dedupe: symbol -> name (first seen wins; sp500 loaded first so sp500 name preferred for overlaps)
    symbol_to_name: dict[str, str] = {}
    for name, symbol in sp500_rows:
        if symbol and symbol not in symbol_to_name:
            symbol_to_name[symbol] = name
    for name, symbol in nasdaq100_rows:
        if symbol and symbol not in symbol_to_name:
            symbol_to_name[symbol] = name

    async with acquire() as conn:
        n_sectors = await seed_sectors(conn, base)
        n_industries = await seed_industries(conn, base)
        await upsert_universe(conn, "sp500", "S&P 500", "csv", "S&P 500 constituents (registry/sp500.csv)")
        await upsert_universe(conn, "nasdaq100", "Nasdaq-100", "csv", "Nasdaq-100 constituents (registry/nasdaq100.csv)")
        # Optional: keep legacy universe for backward compat
        await upsert_universe(conn, "nasdaq_composite", "Nasdaq Composite", "seed", "Legacy; use nasdaq100 for Nasdaq-100")

        eff = date.today()
        for symbol, name in symbol_to_name.items():
            await upsert_security(conn, symbol, name, sector_id="unknown", exchange=None)

        for _name, symbol in sp500_rows:
            if symbol:
                await upsert_universe_membership(conn, "sp500", symbol, eff)
        for _name, symbol in nasdaq100_rows:
            if symbol:
                await upsert_universe_membership(conn, "nasdaq100", symbol, eff)

    parts = [f"sectors {n_sectors}", f"industries {n_industries}" if n_industries else None, f"sp500 {len(sp500_rows)}", f"nasdaq100 {len(nasdaq100_rows)}", f"→ {len(symbol_to_name)} unique securities"]
    return "Refreshed " + ", ".join(p for p in parts if p)


def run_refresh() -> None:
    """Synchronous entry point for CLI."""
    msg = asyncio.run(refresh_universes())
    print(msg)
