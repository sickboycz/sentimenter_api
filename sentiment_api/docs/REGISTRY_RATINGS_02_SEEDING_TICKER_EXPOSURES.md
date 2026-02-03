# Seeding ticker_exposures.csv (initial template)

Your engine needs per-ticker exposure magnitudes in [0..1] for each channel.

The correct deterministic seeding rule is:

1) Determine ticker's sector_id and industry_id (from your Security Master DB).
2) Start with sector default exposures:
   exposure[t][k] = abs(beta_sector[sector_id][k]) clipped to [0..1]
3) If industry_id exists and beta_industry has an override:
   exposure[t][k] = max(exposure[t][k], abs(beta_industry[industry_id][k]))
   (This makes industries "more sensitive" than sector base when appropriate.)
4) Optional: apply ticker-specific manual overrides for special cases (e.g., NVDA trade_controls).

This package includes:
- registry/llm_asset_targeting/sector_default_exposures.yaml (ready)
- registry/llm_asset_targeting/beta_industry.yaml (industry betas)
- registry/llm_asset_targeting/ticker_exposures_template.csv (all tickers, exposures baseline=0.20 until sector_id known)
- registry/llm_asset_targeting/ticker_exposures_seed_example.csv (how the filled version looks)

Production implementation:
- run `uv run python scripts/seed_exposures.py` (exports ticker_exposures.csv)
- or update DB exposures table directly via a daily job.
