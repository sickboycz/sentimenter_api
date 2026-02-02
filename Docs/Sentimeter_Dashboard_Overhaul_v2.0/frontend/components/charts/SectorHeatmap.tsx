"use client";

import React from "react";
import { cn } from "@/lib/cn";

function toneColor(dir: string, score: number) {
  const s = Math.max(0, Math.min(100, score));
  if (dir === "RiskOn") return `rgba(70,220,160,${0.10 + (s/100)*0.25})`;
  if (dir === "RiskOff") return `rgba(255,95,110,${0.10 + (s/100)*0.25})`;
  return "rgba(255,255,255,0.06)";
}

export function SectorHeatmap({ sectors }: { sectors: any[] }) {
  const items = sectors.slice(0, 11);
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2">
      {items.map((s) => (
        <div
          key={s.sector_id}
          className={cn("rounded-xl border border-white/10 p-3 glass-hover")}
          style={{ background: toneColor(s.expected_direction, s.impact_score) }}
          title={s.rationale_en}
        >
          <div className="text-sm font-semibold">{s.sector_name_en}</div>
          <div className="text-xs opacity-70">
            {s.expected_direction} • score {Math.round(s.impact_score)} • conf {Math.round((s.confidence ?? 0)*100)}%
          </div>
        </div>
      ))}
    </div>
  );
}
