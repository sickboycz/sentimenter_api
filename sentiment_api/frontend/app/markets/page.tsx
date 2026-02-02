"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../../components/Shell";
import { apiGet, getDefaultApiKey } from "../../lib/api";

export default function MarketsPage() {
  const apiKey = getDefaultApiKey();

  const impacts = useQuery({
    queryKey: ["impactsLatest"],
    queryFn: () =>
      apiGet<any>("/v1/impacts/latest?window=6h&limit_sectors=0", apiKey),
  });

  const top = impacts.data?.data?.markets ?? [];

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
            <div key={m.market_id ?? i} className="flex justify-between">
              <span>{m.market_id}</span>
              <span className="opacity-75">
                {m.direction} • {Math.round(m.impact_score ?? 0)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}
