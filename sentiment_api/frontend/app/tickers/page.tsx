"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
// TODO: Add virtualization (e.g. react-window) when winners/losers > 50 to avoid UI freeze on large payloads.
import { Shell } from "../../components/Shell";
import { TickerSpan } from "../../components/TickerSpan";
import { apiGet, getDefaultApiKey } from "../../lib/api";

export default function TickersPage() {
  const apiKey = getDefaultApiKey();
  const impacts = useQuery({
    queryKey: ["impactsLatest"],
    queryFn: () =>
      apiGet<any>("/v1/impacts/latest?window=6h&limit_tickers=100", apiKey),
  });

  const winners = impacts.data?.data?.winners ?? [];
  const losers = impacts.data?.data?.losers ?? [];

  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">Tickers</div>
        <div className="text-sm opacity-75">
          Winners/losers derived from latest news impacts (S&P 500 + Nasdaq-100). Hover over a ticker for company name.
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="glass p-4">
          <div className="font-semibold mb-2">Top Winners</div>
          <div className="space-y-1 text-sm">
            {winners.slice(0, 50).map((t: any) => (
              <div key={t.symbol ?? t.ticker} className="flex justify-between">
                <TickerSpan symbol={t.symbol ?? t.ticker} name={t.name} className="cursor-help">
                  {t.symbol ?? t.ticker}
                </TickerSpan>
                <span className="opacity-75">+{Math.round(t.impact_score ?? 0)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass p-4">
          <div className="font-semibold mb-2">Top Losers</div>
          <div className="space-y-1 text-sm">
            {losers.slice(0, 50).map((t: any) => (
              <div key={t.symbol ?? t.ticker} className="flex justify-between">
                <TickerSpan symbol={t.symbol ?? t.ticker} name={t.name} className="cursor-help">
                  {t.symbol ?? t.ticker}
                </TickerSpan>
                <span className="opacity-75">-{Math.round(t.impact_score ?? 0)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Shell>
  );
}
