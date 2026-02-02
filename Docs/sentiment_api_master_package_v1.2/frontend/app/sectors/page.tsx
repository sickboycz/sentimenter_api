"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../../components/Shell";
import { apiGet } from "../../lib/api";

export default function SectorsPage() {
  const apiKey = "";
  const impactSummary = useQuery({
    queryKey: ["impactSummary"],
    queryFn: () => apiGet<any>("/v1/impact/summary?universe=sp500", apiKey),
  });

  const top = impactSummary.data?.data?.top_sectors ?? [];

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
              <span>{s.sector_name_en}</span>
              <span className="opacity-75">
                {s.direction} • {Math.round(s.impact_score)} • {s.impact_level}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}
