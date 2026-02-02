"use client";

import React, { useEffect, useState } from "react";
import { apiGet, getDefaultApiKey } from "../lib/api";

export function CompanyDetailModal({
  symbol,
  onClose,
}: {
  symbol: string | null;
  onClose: () => void;
}) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const apiKey = getDefaultApiKey();

  useEffect(() => {
    if (!symbol) {
      setData(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    apiGet<{ data: Record<string, unknown> }>(`/v1/tickers/${encodeURIComponent(symbol)}/detail`, apiKey)
      .then((res) => setData(res.data || {}))
      .catch((e) => {
        setError(e?.message || "Failed to load company detail");
        setData(null);
      })
      .finally(() => setLoading(false));
  }, [symbol, apiKey]);

  if (!symbol) return null;

  const summary = (data?.summary as Record<string, unknown>) || {};
  const price = (data?.price as Record<string, unknown>) || {};
  const statistics = (data?.statistics as Record<string, unknown>) || {};
  const earnings = (data?.earnings as unknown[]) || [];

  const fmt = (v: unknown): string => {
    if (v == null) return "—";
    if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString() : v.toFixed(2);
    return String(v);
  };

  const section = (title: string, children: React.ReactNode) => (
    <div className="space-y-1">
      <div className="text-sm opacity-75">{title}</div>
      <div className="text-sm opacity-90">{children}</div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className="glass max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl p-4 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="font-semibold">{symbol}</div>
            {summary.longName != null ? (
              <div className="text-sm opacity-75">{String(summary.longName)}</div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-2 text-sm opacity-75 hover:opacity-100"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {loading && (
          <div className="text-sm opacity-75 py-8">Loading…</div>
        )}
        {error && (
          <div className="text-sm opacity-90 text-red-300 py-2">{error}</div>
        )}

        {!loading && !error && data && (
          <>
            {summary.longBusinessSummary != null ? section("Summary", <p className="leading-relaxed">{String(summary.longBusinessSummary)}</p>) : null}

            {(summary.sector != null || summary.industry != null || summary.website != null || summary.fullTimeEmployees != null) ? section(
              "Company",
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1 opacity-85">
                {summary.sector != null ? <><dt className="opacity-75">Sector</dt><dd>{String(summary.sector)}</dd></> : null}
                {summary.industry != null ? <><dt className="opacity-75">Industry</dt><dd>{String(summary.industry)}</dd></> : null}
                {summary.website != null ? <><dt className="opacity-75">Website</dt><dd><a href={String(summary.website)} target="_blank" rel="noopener noreferrer" className="underline opacity-90">{String(summary.website)}</a></dd></> : null}
                {summary.fullTimeEmployees != null ? <><dt className="opacity-75">Employees</dt><dd>{fmt(summary.fullTimeEmployees)}</dd></> : null}
              </dl>
            ) : null}

            {(price.regularMarketPrice != null || price.previousClose != null || price.volume != null) ? section(
              "Price",
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1 opacity-85">
                {price.regularMarketPrice != null ? <><dt className="opacity-75">Price</dt><dd>{fmt(price.regularMarketPrice)} {price.currency != null ? String(price.currency) : null}</dd></> : null}
                {price.previousClose != null ? <><dt className="opacity-75">Previous Close</dt><dd>{fmt(price.previousClose)}</dd></> : null}
                {price.dayLow != null ? <><dt className="opacity-75">Day Range</dt><dd>{fmt(price.dayLow)} – {fmt(price.dayHigh)}</dd></> : null}
                {price.volume != null ? <><dt className="opacity-75">Volume</dt><dd>{fmt(price.volume)}</dd></> : null}
                {price.marketCap != null ? <><dt className="opacity-75">Market Cap</dt><dd>{fmt(price.marketCap)}</dd></> : null}
              </dl>
            ) : null}

            {(statistics.trailingPE != null || statistics.trailingEps != null || statistics.beta != null) ? section(
              "Statistics",
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1 opacity-85">
                {statistics.trailingPE != null ? <><dt className="opacity-75">P/E</dt><dd>{fmt(statistics.trailingPE)}</dd></> : null}
                {statistics.trailingEps != null ? <><dt className="opacity-75">EPS</dt><dd>{fmt(statistics.trailingEps)}</dd></> : null}
                {statistics.dividendYield != null ? <><dt className="opacity-75">Div Yield</dt><dd>{fmt(statistics.dividendYield)}</dd></> : null}
                {statistics.beta != null ? <><dt className="opacity-75">Beta</dt><dd>{fmt(statistics.beta)}</dd></> : null}
                {statistics.profitMargins != null ? <><dt className="opacity-75">Profit Margin</dt><dd>{fmt(statistics.profitMargins)}</dd></> : null}
              </dl>
            ) : null}

            {earnings.length > 0 ? section(
              "Earnings",
              <div className="space-y-1">
                {(earnings as Array<Record<string, unknown>>).slice(0, 8).map((row, i) => (
                  <div key={i} className="flex justify-between opacity-85 text-sm">
                    <span>{fmt(row.date)}</span>
                    <span>Est. {fmt(row.eps_estimate)} / Reported {fmt(row.reported_eps)}</span>
                  </div>
                ))}
              </div>
            ) : null}

            <div className="text-xs opacity-60 pt-2">Data from Yahoo Finance, on demand.</div>
          </>
        )}
      </div>
    </div>
  );
}
