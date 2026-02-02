"use client";

import React from "react";
import { Shell } from "../../components/Shell";
import { Card } from "../../components/ui/Card";
import { useImpactMarkets } from "../../lib/api/hooks";

export default function MarketsPage() {
  const markets = useImpactMarkets();

  return (
    <Shell>
      <Card title="Markets" subtitle="Which markets are most affected right now.">
        <div className="space-y-2 text-sm opacity-85">
          {(markets.data?.data?.top_markets ?? []).map((m: any) => (
            <div key={m.market_id} className="flex justify-between">
              <span>{m.label_en}</span>
              <span className="opacity-75">{m.expected_direction} • {Math.round(m.magnitude * 100)}%</span>
            </div>
          ))}
        </div>
      </Card>
    </Shell>
  );
}
