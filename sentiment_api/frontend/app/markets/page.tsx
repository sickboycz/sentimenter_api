"use client";

import React from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { useImpactMarkets } from "@/lib/api/hooks";

export default function MarketsPage() {
  const markets = useImpactMarkets();

  return (
    <Shell>
      <PageHeader
        title="Markets"
        subtitle="Cross-market impact: where the shock concentrates right now."
        meta="Directional magnitude normalized 0–100."
      />
      {!markets.data ? <Skeleton className="h-[240px]" /> : (
        <Card title="Top Markets" subtitle={`method ${markets.data.methodology_version}`}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            {markets.data.top_markets.map((m: any) => (
              <div key={m.market_id} className="glass p-4">
                {(() => {
                  const mag = Math.max(0, Math.min(1, Number(m.magnitude ?? 0)));
                  const pct = Math.round(mag * 100);
                  return (
                    <>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-semibold">{m.label_en}</div>
                          <div className="text-xs opacity-70">{m.expected_direction} • {m.horizon} • conf {Math.round(Number(m.confidence ?? 0) * 100)}%</div>
                        </div>
                        <div className="text-xs opacity-80">{pct}%</div>
                      </div>
                      <div className="mt-2 h-1.5 rounded-full bg-white/5 overflow-hidden">
                        <div className="h-full bg-[var(--accent-cyan)]/60" style={{ width: `${pct}%` }} />
                      </div>
                      <div className="text-xs opacity-70 mt-2 line-clamp-2">{m.rationale_en}</div>
                    </>
                  );
                })()}
              </div>
            ))}
          </div>
        </Card>
      )}
    </Shell>
  );
}
