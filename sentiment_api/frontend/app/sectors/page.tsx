"use client";

import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../../components/Shell";
import { apiGet, getDefaultApiKey } from "../../lib/api";
import { TickerSpan } from "../../components/TickerSpan";

type Sector = { sector_id: string; sector_name_en?: string; direction: string; impact_score: number };
type Ticker = { symbol?: string; ticker?: string; name?: string; sector_id?: string; direction?: string; impact_score?: number };

export default function SectorsPage() {
  const apiKey = getDefaultApiKey();
  const [expandedSector, setExpandedSector] = useState<string | null>(null);

  const impacts = useQuery({
    queryKey: ["impactsLatest", "sectors-with-tickers"],
    queryFn: () =>
      apiGet<any>("/v1/impacts/latest?window=6h&limit_tickers=100&limit_sectors=11", apiKey),
  });

  const data = impacts.data?.data;
  const sectors = (data?.sectors ?? []) as Sector[];
  const winners = (data?.winners ?? []) as Ticker[];
  const losers = (data?.losers ?? []) as Ticker[];

  const tickersBySector = useMemo(() => {
    const map = new Map<string, Ticker[]>();
    const all = [...(data?.winners ?? []), ...(data?.losers ?? [])] as Ticker[];
    for (const t of all) {
      const sid = t.sector_id ?? "unknown";
      if (!map.has(sid)) map.set(sid, []);
      map.get(sid)!.push(t);
    }
    for (const arr of map.values()) {
      arr.sort((a, b) => (b.impact_score ?? 0) - (a.impact_score ?? 0));
    }
    return map;
  }, [data?.winners, data?.losers]);

  const maxAbs = useMemo(() => {
    const secs = (data?.sectors ?? []) as Sector[];
    if (secs.length === 0) return 1;
    return Math.max(...secs.map((s) => Math.abs(s.impact_score ?? 0)), 1);
  }, [data?.sectors]);

  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">Sectors (SP500)</div>
        <div className="text-sm opacity-75">
          Heatmap of sector impacts from latest news. Click a sector for drilldown (top tickers).
        </div>
      </div>

      <div className="glass p-4">
        <div className="font-semibold mb-3">Sector Heatmap</div>
        <div className="space-y-2">
          {sectors.map((s) => {
            const score = s.impact_score ?? 0;
            const isUp = (s.direction ?? "").toLowerCase().includes("up") || score >= 0;
            const pct = Math.min(100, (Math.abs(score) / maxAbs) * 100);
            const barColor = isUp ? "var(--good)" : "var(--bad)";
            const expanded = expandedSector === s.sector_id;
            const tickers = tickersBySector.get(s.sector_id ?? "") ?? [];

            return (
              <div key={s.sector_id} className="rounded-lg border border-white/10 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setExpandedSector(expanded ? null : s.sector_id ?? null)}
                  className="w-full text-left px-3 py-2 flex items-center justify-between hover:bg-white/5 transition-colors relative"
                >
                  <span
                    className="absolute left-0 top-0 bottom-0 rounded-l-lg opacity-30"
                    style={{ width: `${pct}%`, backgroundColor: barColor }}
                    aria-hidden
                  />
                  <span className="relative z-10 font-medium">{s.sector_name_en ?? s.sector_id}</span>
                  <span className={`relative z-10 text-sm ${isUp ? "text-[var(--good)]" : "text-[var(--bad)]"}`}>
                    {s.direction} • {Math.round(score)}
                  </span>
                </button>
                {expanded && tickers.length > 0 && (
                  <div className="px-3 py-2 border-t border-white/10 bg-black/20 text-sm space-y-1">
                    <div className="font-medium opacity-80 mb-2">Top tickers in sector</div>
                    {tickers.slice(0, 10).map((t) => (
                      <div key={t.symbol ?? t.ticker ?? ""} className="flex justify-between">
                        <TickerSpan symbol={t.symbol ?? t.ticker ?? "?"} name={t.name} />
                        <span className={t.direction === "up" ? "text-[var(--good)]" : "text-[var(--bad)]"}>
                          {t.direction === "up" ? "+" : "-"}{Math.round(t.impact_score ?? 0)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </Shell>
  );
}
