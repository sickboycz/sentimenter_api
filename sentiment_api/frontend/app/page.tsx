"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../components/Shell";
import { TickerSpan } from "../components/TickerSpan";
import { apiGet, getDefaultApiKey } from "../lib/api";

export default function OverviewPage() {
  const apiKey = getDefaultApiKey();

  const moodNow = useQuery({
    queryKey: ["moodNow"],
    queryFn: () => apiGet<any>("/v1/mood/now", apiKey),
  });

  const impacts = useQuery({
    queryKey: ["impactsLatest"],
    queryFn: () =>
      apiGet<any>("/v1/impacts/latest?window=6h&limit_tickers=50&limit_sectors=11", apiKey),
  });

  const mood = moodNow.data?.data;
  const data = impacts.data?.data;

  return (
    <Shell>
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="glass p-4 xl:col-span-2">
          <div className="text-sm opacity-75">Mood Now</div>
          <div className="text-2xl font-semibold">
            {mood?.sentiment ?? "—"}
          </div>
          <div className="text-sm opacity-75">
            intraday index: {mood?.index_intraday ?? "—"} • vol: {mood?.news_volatility_intraday ?? "—"}
          </div>
        </div>

        <div className="glass p-4">
          <div className="text-sm opacity-75">Most Affected Market</div>
          <div className="text-lg font-semibold">
            {data?.most_affected_market?.market_id ?? "—"}
          </div>
          <div className="text-sm opacity-75">
            {data?.most_affected_market?.direction ?? ""} • score {Math.round(data?.most_affected_market?.impact_score ?? 0)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="glass p-4">
          <div className="font-semibold mb-2">Top Sector Impacts</div>
          <div className="text-sm opacity-85 space-y-1">
            {(data?.sectors ?? []).slice(0, 12).map((s: any) => (
              <div key={s.sector_id} className="flex justify-between">
                <span>{s.sector_name_en ?? s.sector_id}</span>
                <span className="opacity-75">{s.direction} {Math.round(s.impact_score ?? 0)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass p-4">
          <div className="font-semibold mb-2">Top Ticker Winners / Losers</div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="opacity-70 mb-1">Winners</div>
              {(data?.winners ?? []).slice(0, 15).map((t: any) => (
                <div key={t.symbol ?? t.ticker} className="flex justify-between">
                  <TickerSpan symbol={t.symbol ?? t.ticker} name={t.name} className="cursor-help">
                    {t.symbol ?? t.ticker}
                  </TickerSpan>
                  <span className="opacity-75">+{Math.round(t.impact_score ?? 0)}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="opacity-70 mb-1">Losers</div>
              {(data?.losers ?? []).slice(0, 15).map((t: any) => (
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
      </div>
    </Shell>
  );
}
