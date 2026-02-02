"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../../components/Shell";
import { apiGet } from "../../lib/api";

export default function MarketsPage() {
  const apiKey = "";

  const impactSummary = useQuery({
    queryKey: ["impactSummary"],
    queryFn: () => apiGet<any>("/v1/impact/summary?universe=all", apiKey),
  });

  const top = impactSummary.data?.data?.top_markets ?? [];

  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">Markets</div>
        <div className="text-sm opacity-75">
          Which market basket is affected most (SP500 vs NASDAQ_COMP) based on latest clusters.
        </div>
      </div>

      <div className="glass p-4">
        <div className="font-semibold mb-2">Top Market Impacts</div>
        <div className="space-y-2">
          {top.map((m: any, i: number) => (
            <div key={i} className="flex justify-between">
              <span>
                {m.market} ({m.universe})
              </span>
              <span className="opacity-75">
                {m.direction} • {Math.round(m.impact_score)} • {m.impact_level}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}
