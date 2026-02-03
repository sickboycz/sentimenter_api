#!/usr/bin/env python3
"""Seed ticker_exposures.csv from sector_default_exposures and beta_industry.

Deterministic rule (see docs/REGISTRY_RATINGS_02_SEEDING_TICKER_EXPOSURES.md):
1) exposure[t][k] = abs(beta_sector[sector_id][k]) clipped to [0..1]
2) If industry_id exists: exposure[t][k] = max(exposure[t][k], abs(beta_industry[industry_id][k]))
3) Optional: ticker-specific overrides

Usage:
  uv run python scripts/seed_exposures.py
  # Output: registry/llm_asset_targeting/ticker_exposures.csv

Requires: sector_default_exposures.yaml, beta_industry.yaml, ticker_exposures_template.csv
"""

import asyncio
import csv
import sys
from pathlib import Path

import yaml

CHANNELS = [
    "rates", "inflation", "growth", "liquidity", "credit_stress",
    "geopolitics", "energy_supply", "trade_controls", "regulation", "risk_appetite",
]


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    reg_dir = root / "registry" / "llm_asset_targeting"

    sector_path = reg_dir / "sector_default_exposures.yaml"
    industry_path = reg_dir / "beta_industry.yaml"
    template_path = reg_dir / "ticker_exposures_template.csv"
    industry_to_sector_path = reg_dir / "industry_to_sector.csv"
    out_path = reg_dir / "ticker_exposures.csv"

    if not sector_path.exists():
        print(f"Missing {sector_path}", file=sys.stderr)
        return 1
    if not template_path.exists():
        print(f"Missing {template_path}", file=sys.stderr)
        return 1

    sector_cfg = yaml.safe_load(sector_path.read_text()) or {}
    sector_defaults = sector_cfg.get("sector_default_exposures") or {}

    industry_betas: dict = {}
    if industry_path.exists():
        ind_cfg = yaml.safe_load(industry_path.read_text()) or {}
        for ind_id, ind_data in (ind_cfg.get("industries") or {}).items():
            beta = ind_data.get("beta") or {}
            industry_betas[ind_id] = {k: _clip(abs(float(v))) for k, v in beta.items() if k in CHANNELS}

    industry_to_sector: dict[str, str] = {}
    if industry_to_sector_path.exists():
        with industry_to_sector_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ind_id = (row.get("industry_id") or "").strip()
                sec_id = (row.get("sector_id") or "").strip().upper()
                if ind_id and sec_id:
                    industry_to_sector[ind_id] = sec_id

    rows_out: list[dict] = []
    with template_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = [c for c in reader.fieldnames or []]
        for row in reader:
            sym = (row.get("symbol") or "").strip().upper()
            if not sym:
                continue
            sector_id = (row.get("sector_id") or "").strip().upper() or None
            industry_id = (row.get("industry_id") or "").strip() or None
            universe = (row.get("universe") or "sp500").strip()

            if not sector_id and industry_id:
                sector_id = industry_to_sector.get(industry_id)

            exposures: dict[str, float] = {}
            if sector_id and sector_id in sector_defaults:
                base = sector_defaults[sector_id]
                for k in CHANNELS:
                    exposures[k] = _clip(float(base.get(k, 0.2)))
            else:
                for k in CHANNELS:
                    exposures[k] = 0.2

            if industry_id and industry_id in industry_betas:
                for k in CHANNELS:
                    ind_val = industry_betas[industry_id].get(k, 0.0)
                    exposures[k] = max(exposures[k], ind_val)

            out_row: dict = {
                "symbol": sym,
                "universe": universe,
                "sector_id": sector_id or "",
                "industry_id": industry_id or "",
            }
            out_row.update(exposures)
            rows_out.append(out_row)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["symbol", "universe", "sector_id", "industry_id"] + CHANNELS)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Wrote {len(rows_out)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
