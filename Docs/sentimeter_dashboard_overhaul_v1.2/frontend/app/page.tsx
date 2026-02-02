"use client";

import React from "react";
import { Shell } from "../components/Shell";
import { Card } from "../components/ui/Card";
import { useMoodNow, useImpactMarkets, useImpactSectors, useImpactTickers, useClusters } from "../lib/api/hooks";

export default function Overview() {
  const mood = useMoodNow();
  const markets = useImpactMarkets();
  const sectors = useImpactSectors();
  const tickers = useImpactTickers();
  const clusters = useClusters();

  return (
    <Shell>
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Card title="Mood Now" subtitle="Health at first sight.">
          <div className="text-2xl font-semibold">{mood.data?.data?.sentiment ?? "—"}</div>
          <div className="text-sm opacity-70">
            confidence {mood.data?.data?.confidence ?? "—"} • vol {mood.data?.data?.news_volatility_intraday ?? "—"} • volume {mood.data?.data?.news_volume_intraday ?? "—"}
          </div>
        </Card>

        <Card title="Most Affected Markets" subtitle="Cross-market allocation.">
          <div className="space-y-2 text-sm opacity-85">
            {(markets.data?.data?.top_markets ?? []).slice(0, 6).map((m: any) => (
              <div key={m.market_id} className="flex justify-between">
                <span>{m.label_en}</span>
                <span className="opacity-75">{m.expected_direction} • {Math.round(m.magnitude * 100)}%</span>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Winners / Losers" subtitle="Ticker impacts (top).">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="opacity-70 mb-1">Winners</div>
              {(tickers.data?.data?.winners ?? []).slice(0, 10).map((t: any) => (
                <div key={t.symbol} className="flex justify-between">
                  <span>{t.symbol}</span>
                  <span className="opacity-75">+{Math.round(t.expected_return_bps)}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="opacity-70 mb-1">Losers</div>
              {(tickers.data?.data?.losers ?? []).slice(0, 10).map((t: any) => (
                <div key={t.symbol} className="flex justify-between">
                  <span>{t.symbol}</span>
                  <span className="opacity-75">{Math.round(t.expected_return_bps)}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Card title="Sector Heat" subtitle="Where the impact concentrates.">
          <div className="grid grid-cols-2 gap-2 text-sm">
            {(sectors.data?.data?.sectors ?? []).slice(0, 12).map((s: any) => (
              <div key={s.sector_id} className="glass p-3">
                <div className="font-semibold">{s.sector_name_en}</div>
                <div className="text-xs opacity-70">{s.expected_direction} • score {Math.round(s.impact_score)}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Latest Clusters" subtitle="High-signal items (L2+).">
          <div className="space-y-2 text-sm">
            {(clusters.data?.data ?? []).slice(0, 8).map((c: any) => (
              <div key={c.cluster_id} className="glass glass-hover p-3">
                <div className="font-semibold">{c.headline_en}</div>
                <div className="text-xs opacity-70">
                  {c.impact?.impact_level} • {c.impact?.expected_direction} • conf {c.impact?.confidence}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </Shell>
  );
}
