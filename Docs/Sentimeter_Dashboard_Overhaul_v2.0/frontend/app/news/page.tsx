"use client";

import React from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { useClusters } from "@/lib/api/hooks";

export default function NewsPage() {
  const clusters = useClusters();

  return (
    <Shell>
      <Card title="News Feed" subtitle="Clusters with impacts, evidence, and winners/losers preview." />

      {!clusters.data ? (
        <Skeleton className="h-[260px]" />
      ) : (clusters.data.data ?? []).length === 0 ? (
        <Card title="No clusters yet" subtitle="Ingestion is running, but nothing has been clustered yet.">
          <div className="text-sm opacity-80">
            Tip: verify collectors, GDELT availability, and clustering service status.
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {(clusters.data.data ?? []).map((c: any) => (
            <a key={c.cluster_id} href={`/clusters/${c.cluster_id}`} className="glass glass-hover p-4 block">
              <div className="flex items-start justify-between gap-3">
                <div className="font-semibold text-lg">{c.headline_en}</div>
                <Badge tone={c.impact?.expected_direction === "RiskOff" ? "bad" : c.impact?.expected_direction === "RiskOn" ? "good" : "neutral"}>
                  {c.impact?.impact_level} • {c.impact?.expected_direction}
                </Badge>
              </div>

              <div className="text-sm opacity-85 mt-2">
                {(c.summary_bullets_en ?? []).slice(0, 4).map((b: string, i: number) => (
                  <div key={i}>• {b}</div>
                ))}
              </div>

              <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs opacity-85">
                <div>
                  <div className="opacity-70 mb-1">Winners</div>
                  <div className="flex flex-wrap gap-1">
                    {(c.top_tickers_winners ?? []).slice(0, 6).map((t: any) => (
                      <span key={t.symbol} className="px-2 py-1 rounded-lg bg-white/5 border border-white/10">
                        {t.symbol} +{Math.round(t.expected_return_bps)}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="opacity-70 mb-1">Losers</div>
                  <div className="flex flex-wrap gap-1">
                    {(c.top_tickers_losers ?? []).slice(0, 6).map((t: any) => (
                      <span key={t.symbol} className="px-2 py-1 rounded-lg bg-white/5 border border-white/10">
                        {t.symbol} {Math.round(t.expected_return_bps)}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="text-xs opacity-70 mt-2">
                {(c.topics ?? []).slice(0, 6).join(" • ")} • {c.source_count} sources
              </div>
            </a>
          ))}
        </div>
      )}
    </Shell>
  );
}
