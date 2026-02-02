"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../../components/Shell";
import { apiGet, getDefaultApiKey } from "../../lib/api";

export default function SectorsPage() {
  const apiKey = getDefaultApiKey();
  const impacts = useQuery({
    queryKey: ["impactsLatest"],
    queryFn: () =>
      apiGet<any>("/v1/impacts/latest?window=6h&limit_tickers=0&limit_sectors=11", apiKey),
  });

  const top = impacts.data?.data?.sectors ?? [];

  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">Sectors (SP500)</div>
        <div className="text-sm opacity-75">Sector heat list based on latest news allocation.</div>
      </div>

      <div className="glass p-4">
        <div className="font-semibold mb-2">Sector Impacts</div>
        <div className="text-sm opacity-85 space-y-1">
          {top.map((s: any) => (
            <div key={s.sector_id} className="flex justify-between">
              <span>{s.sector_name_en ?? s.sector_id}</span>
              <span className="opacity-75">
                {s.direction} • {Math.round(s.impact_score ?? 0)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}
