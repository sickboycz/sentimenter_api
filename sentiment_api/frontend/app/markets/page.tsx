"use client";

import React from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { useImpactMarkets } from "@/lib/api/hooks";

export default function MarketsPage() {
  const markets = useImpactMarkets();

  return (
    <Shell>
      <Card title="Markets" subtitle="Cross-market impact: what moves most right now." />
      {!markets.data ? <Skeleton className="h-[240px]" /> : (
        <Card title="Top Markets" subtitle={`method ${markets.data.methodology_version}`}>
          <div className="space-y-2 text-sm">
            {markets.data.top_markets.map((m: any) => (
              <div key={m.market_id} className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-semibold">{m.label_en}</div>
                  <div className="text-xs opacity-70">{m.expected_direction} • {m.horizon} • conf {Math.round(m.confidence*100)}%</div>
                  <div className="text-xs opacity-70 line-clamp-2">{m.rationale_en}</div>
                </div>
                <div className="text-xs opacity-80">{Math.round(m.magnitude * 100)}%</div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </Shell>
  );
}
