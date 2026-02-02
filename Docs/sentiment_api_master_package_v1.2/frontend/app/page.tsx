"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../components/Shell";
import { apiGet } from "../lib/api";

export default function OverviewPage() {
  // In a real app: load from localStorage or a secure proxy.
  const apiKey = "";

  const moodNow = useQuery({
    queryKey: ["moodNow"],
    queryFn: () => apiGet<any>("/v1/mood/now", apiKey),
  });

  const impactSummary = useQuery({
    queryKey: ["impactSummary"],
    queryFn: () => apiGet<any>("/v1/impact/summary", apiKey),
  });

  const mood = moodNow.data?.data;
  const summary = impactSummary.data?.data;

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
            {(summary?.top_markets?.[0]?.market ?? "—")}
          </div>
          <div className="text-sm opacity-75">
            {(summary?.top_markets?.[0]?.direction ?? "")} • score {(summary?.top_markets?.[0]?.impact_score ?? "—")}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="glass p-4">
          <div className="font-semibold mb-2">Top Sector Impacts</div>
          <div className="text-sm opacity-85 space-y-1">
            {(summary?.top_sectors ?? []).slice(0, 12).map((s: any) => (
              <div key={s.sector_id} className="flex justify-between">
                <span>{s.sector_name_en}</span>
                <span className="opacity-75">{s.direction} {Math.round(s.impact_score)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass p-4">
          <div className="font-semibold mb-2">Top Ticker Winners / Losers</div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="opacity-70 mb-1">Winners</div>
              {(summary?.top_ticker_winners ?? []).slice(0, 15).map((t: any) => (
                <div key={t.ticker} className="flex justify-between">
                  <span>{t.ticker}</span>
                  <span className="opacity-75">+{Math.round(t.impact_score)}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="opacity-70 mb-1">Losers</div>
              {(summary?.top_ticker_losers ?? []).slice(0, 15).map((t: any) => (
                <div key={t.ticker} className="flex justify-between">
                  <span>{t.ticker}</span>
                  <span className="opacity-75">-{Math.round(t.impact_score)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Shell>
  );
}
