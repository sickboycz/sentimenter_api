"""Fetch company details from Yahoo Finance via yfinance (no storage)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any


def _fetch_yahoo_sync(symbol: str) -> dict[str, Any]:
    """Synchronous fetch using yfinance. Run in thread pool."""
    import yfinance as yf

    sym = (symbol or "").strip().upper()
    if not sym:
        return {"error": "Missing symbol"}

    try:
        ticker = yf.Ticker(sym)
    except Exception as e:
        return {"error": str(e)}

    out: dict[str, Any] = {"symbol": sym, "summary": {}, "price": {}, "statistics": {}, "earnings": []}

    # --- Summary (company info) ---
    try:
        info = ticker.info or {}
        if isinstance(info, dict):
            for k in (
                "longBusinessSummary",
                "sector",
                "industry",
                "website",
                "fullTimeEmployees",
                "longName",
                "shortName",
                "address1",
                "city",
                "state",
                "zip",
                "country",
            ):
                if k in info and info[k] is not None:
                    out["summary"][k] = info[k]
    except Exception:
        pass

    # --- Price (current, previous close, day range) ---
    try:
        info = getattr(ticker, "info", None) or {}
        if isinstance(info, dict):
            for k in (
                "regularMarketPrice",
                "previousClose",
                "open",
                "dayLow",
                "dayHigh",
                "fiftyTwoWeekLow",
                "fiftyTwoWeekHigh",
                "volume",
                "averageVolume",
                "marketCap",
                "currency",
            ):
                if k in info and info[k] is not None:
                    out["price"][k] = info[k]
        # Fallback: history
        if not out["price"].get("regularMarketPrice"):
            hist = ticker.history(period="5d")
            if hist is not None and not hist.empty:
                last = hist.iloc[-1]
                out["price"]["regularMarketPrice"] = float(last.get("Close", 0))
                out["price"]["previousClose"] = float(hist.iloc[-2].get("Close", 0)) if len(hist) >= 2 else None
                out["price"]["open"] = float(last.get("Open", 0))
                out["price"]["dayLow"] = float(last.get("Low", 0))
                out["price"]["dayHigh"] = float(last.get("High", 0))
                out["price"]["volume"] = int(last.get("Volume", 0))
    except Exception:
        pass

    # --- Statistics (key stats like P/E, EPS, etc.) ---
    try:
        info = getattr(ticker, "info", None) or {}
        if isinstance(info, dict):
            for k in (
                "trailingPE",
                "forwardPE",
                "trailingEps",
                "forwardEps",
                "dividendYield",
                "beta",
                "profitMargins",
                "operatingMargins",
                "returnOnEquity",
                "returnOnAssets",
                "revenueGrowth",
                "earningsGrowth",
                "targetMeanPrice",
                "recommendationKey",
                "numberOfAnalystOpinions",
            ):
                if k in info and info[k] is not None:
                    out["statistics"][k] = info[k]
    except Exception:
        pass

    # --- Earnings (dates) ---
    try:
        ed = ticker.get_earnings_dates(limit=12)
        if ed is not None and not ed.empty:
            ed = ed.head(12)
            for idx in ed.index:
                row = ed.loc[idx]
                out["earnings"].append({
                    "date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
                    "eps_estimate": float(row.get("eps_estimate", 0)) if row.get("eps_estimate") is not None else None,
                    "reported_eps": float(row.get("reported_eps", 0)) if row.get("reported_eps") is not None else None,
                    "surprise_pct": float(row.get("surprise_pct", 0)) if row.get("surprise_pct") is not None else None,
                })
    except Exception:
        pass

    return out


async def get_company_detail(symbol: str) -> dict[str, Any]:
    """Fetch company detail from Yahoo Finance (run yfinance in thread)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_yahoo_sync, symbol)
