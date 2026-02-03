"""Security master: DB-backed ticker allowlist (universe_memberships + securities)."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from sentiment_api.db.pool import acquire


@dataclass(frozen=True)
class TickerInfo:
    symbol: str
    sector_id: str
    company_name: str
    universe: str  # sp500 | nasdaq100 | nasdaq_comp


class SecurityMaster:
    """Interface to ticker universe and metadata (DB-backed in production)."""

    async def is_allowed(self, symbol: str) -> bool:
        raise NotImplementedError

    async def get(self, symbol: str) -> Optional[TickerInfo]:
        raise NotImplementedError

    async def by_sector(self, sector_id: str, limit: int) -> List[TickerInfo]:
        raise NotImplementedError

    async def all_symbols(self) -> Set[str]:
        raise NotImplementedError


class DBSecurityMaster(SecurityMaster):
    """DB-backed: queries universe_memberships and securities."""

    async def is_allowed(self, symbol: str) -> bool:
        sym = symbol.strip().upper()
        async with acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1 FROM universe_memberships um
                WHERE um.symbol = $1
                  AND (um.effective_to IS NULL OR um.effective_to >= current_date)
                LIMIT 1
                """,
                sym,
            )
        return row is not None

    async def get(self, symbol: str) -> Optional[TickerInfo]:
        sym = symbol.strip().upper()
        async with acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT s.symbol, COALESCE(s.sector_id, 'UNKNOWN') as sector_id, COALESCE(s.name, s.symbol) as company_name,
                       COALESCE(um.universe_id::text, 'unknown') as universe
                FROM securities s
                LEFT JOIN (
                    SELECT DISTINCT ON (symbol) symbol, universe_id
                    FROM universe_memberships
                    WHERE effective_from <= current_date AND (effective_to IS NULL OR effective_to >= current_date)
                    ORDER BY symbol, effective_from DESC
                ) um ON um.symbol = s.symbol
                WHERE s.symbol = $1
                """,
                sym,
            )
        if not row:
            return None
        return TickerInfo(
            symbol=row["symbol"],
            sector_id=str(row["sector_id"]).upper(),
            company_name=str(row["company_name"]),
            universe=str(row["universe"]),
        )

    async def by_sector(self, sector_id: str, limit: int) -> List[TickerInfo]:
        sid = sector_id.strip().upper()
        async with acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT s.symbol, COALESCE(s.sector_id, 'UNKNOWN') as sector_id, COALESCE(s.name, s.symbol) as company_name,
                       COALESCE(um.universe_id, 'unknown') as universe
                FROM securities s
                JOIN universe_memberships um ON um.symbol = s.symbol
                  AND um.effective_from <= current_date AND (um.effective_to IS NULL OR um.effective_to >= current_date)
                WHERE UPPER(COALESCE(s.sector_id, '')) = $1
                ORDER BY s.symbol
                LIMIT $2
                """,
                sid,
                limit,
            )
        return [
            TickerInfo(
                symbol=r["symbol"],
                sector_id=str(r["sector_id"]).upper(),
                company_name=str(r["company_name"]),
                universe=str(r["universe"]),
            )
            for r in rows
        ]

    async def all_symbols(self) -> Set[str]:
        async with acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT um.symbol FROM universe_memberships um
                WHERE (um.effective_to IS NULL OR um.effective_to >= current_date)
                """
            )
        return {r["symbol"] for r in rows}


class CSVSecurityMaster(SecurityMaster):
    """CSV-backed for tests (uses ticker_exposures or registry CSVs)."""

    def __init__(self, sp500_csv: str = "", nasdaq_csv: str = "", exposures_csv: str = "") -> None:
        self._m: Dict[str, TickerInfo] = {}
        self._sector_index: Dict[str, List[TickerInfo]] = {}
        if sp500_csv:
            self._load_csv(sp500_csv, universe="sp500")
        if nasdaq_csv:
            self._load_csv(nasdaq_csv, universe="nasdaq_comp")
        if exposures_csv:
            self._load_exposures(exposures_csv)
        for info in self._m.values():
            self._sector_index.setdefault(info.sector_id, []).append(info)

    def _load_csv(self, path: str, universe: str) -> None:
        p = Path(path)
        if not p.exists():
            return
        content = p.read_text(encoding="utf-8")
        lines = [l for l in content.splitlines() if l.strip()]
        if not lines:
            return
        delim = ";" if ";" in lines[0] else ","
        r = csv.DictReader(lines, delimiter=delim)
        for row in r:
            sym = (row.get("symbol") or row.get("Symbol") or "").strip().upper()
            if not sym:
                parts = list(row.values()) if row else []
                if len(parts) >= 3:
                    sym = str(parts[-1]).strip().upper()
            if not sym or sym in ("SYMBOL", "SECTOR_ID"):
                continue
            sector = (row.get("sector_id") or "UNKNOWN").strip().upper()
            name = (row.get("company_name") or row.get("Company") or sym).strip()
            self._m[sym] = TickerInfo(symbol=sym, sector_id=sector, company_name=name, universe=universe)

    def _load_exposures(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            return
        with open(p, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                sym = (row.get("symbol") or "").strip().upper()
                if not sym:
                    continue
                sector = (row.get("sector_id") or "UNKNOWN").strip().upper()
                universe = (row.get("universe") or "unknown").strip()
                self._m[sym] = TickerInfo(symbol=sym, sector_id=sector, company_name=sym, universe=universe)

    async def is_allowed(self, symbol: str) -> bool:
        return symbol.strip().upper() in self._m

    async def get(self, symbol: str) -> Optional[TickerInfo]:
        return self._m.get(symbol.strip().upper())

    async def by_sector(self, sector_id: str, limit: int) -> List[TickerInfo]:
        arr = self._sector_index.get(sector_id.strip().upper(), [])
        arr2 = sorted(arr, key=lambda x: x.symbol)
        return arr2[:limit]

    async def all_symbols(self) -> Set[str]:
        return set(self._m.keys())
