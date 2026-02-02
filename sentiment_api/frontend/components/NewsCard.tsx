import React from "react";
import Link from "next/link";
import { ImpactBadge } from "./ImpactBadge";
import { TickerSpan } from "./TickerSpan";

export function NewsCard({ cluster }: { cluster: any }) {
  return (
    <div className="glass p-4 space-y-2">
      <div className="flex items-start justify-between gap-3">
        <div className="font-semibold leading-snug">{cluster.headline_en}</div>
        <ImpactBadge level={cluster.impact?.impact_level} direction={cluster.impact?.expected_direction} />
      </div>

      <div className="text-sm opacity-85 space-y-1">
        {(cluster.summary_bullets_en ?? []).slice(0, 4).map((b: string, i: number) => (
          <div key={i}>• {b}</div>
        ))}
      </div>

      <div className="text-xs opacity-75 flex flex-wrap gap-2">
        <span>{cluster.source_count} sources</span>
        <span>•</span>
        <span>{(cluster.topics ?? []).slice(0, 4).join(", ")}</span>
      </div>

      <div className="text-xs opacity-85 grid grid-cols-1 md:grid-cols-2 gap-2">
        <div>
          <div className="opacity-70 mb-1">Top Winners</div>
          <div className="flex flex-wrap gap-1">
            {(cluster.top_ticker_winners ?? []).slice(0, 6).map((t: any) => (
              <TickerSpan
                key={t.ticker ?? t.symbol}
                symbol={t.ticker ?? t.symbol}
                name={t.name}
                className="px-2 py-1 rounded-lg bg-white/10 border border-white/10 cursor-help inline-block"
              >
                {t.ticker ?? t.symbol} +{Math.round(t.impact_score)}
              </TickerSpan>
            ))}
          </div>
        </div>
        <div>
          <div className="opacity-70 mb-1">Top Losers</div>
          <div className="flex flex-wrap gap-1">
            {(cluster.top_ticker_losers ?? []).slice(0, 6).map((t: any) => (
              <TickerSpan
                key={t.ticker ?? t.symbol}
                symbol={t.ticker ?? t.symbol}
                name={t.name}
                className="px-2 py-1 rounded-lg bg-white/10 border border-white/10 cursor-help inline-block"
              >
                {t.ticker ?? t.symbol} -{Math.round(t.impact_score)}
              </TickerSpan>
            ))}
          </div>
        </div>
      </div>

      <div className="pt-2">
        <Link href={`/clusters/${cluster.cluster_id}`} className="text-sm underline opacity-90">
          Open details →
        </Link>
      </div>
    </div>
  );
}
