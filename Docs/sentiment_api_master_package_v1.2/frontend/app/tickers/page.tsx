"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../../components/Shell";
import { apiGet } from "../../lib/api";

export default function TickersPage() {
  const apiKey = "";
  const impactSummary = useQuery({
    queryKey: ["impactSummary"],
    queryFn: () => apiGet<any>("/v1/impact/summary?universe=all&limit=100", apiKey),
  });

  const winners = impactSummary.data?.data?.top_ticker_winners ?? [];
  const losers = impactSummary.data?.data?.top_ticker_losers ?? [];

  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">Tickers</div>
        <div className="text-sm opacity-75">
          Winners/losers derived from latest news impacts (SP500 + Nasdaq Composite).
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="glass p-4">
          <div className="font-semibold mb-2">Top Winners</div>
          <div className="space-y-1 text-sm">
            {winners.slice(0, 50).map((t: any) => (
              <div key={t.ticker} className="flex justify-between">
                <span>{t.ticker}</span>
                <span className="opacity-75">+{Math.round(t.impact_score)} • {t.impact_level}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass p-4">
          <div className="font-semibold mb-2">Top Losers</div>
          <div className="space-y-1 text-sm">
            {losers.slice(0, 50).map((t: any) => (
              <div key={t.ticker} className="flex justify-between">
                <span>{t.ticker}</span>
                <span className="opacity-75">-{Math.round(t.impact_score)} • {t.impact_level}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Shell>
  );
}
