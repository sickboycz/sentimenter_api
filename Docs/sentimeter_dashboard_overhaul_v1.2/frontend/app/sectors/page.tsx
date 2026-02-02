"use client";

import React from "react";
import { Shell } from "../../components/Shell";
import { Card } from "../../components/ui/Card";
import { useImpactSectors } from "../../lib/api/hooks";

export default function SectorsPage() {
  const sectors = useImpactSectors();

  return (
    <Shell>
      <Card title="Sectors" subtitle="Heat + drilldown entrypoint.">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
          {(sectors.data?.data?.sectors ?? []).slice(0, 22).map((s: any) => (
            <div key={s.sector_id} className="glass p-3">
              <div className="font-semibold">{s.sector_name_en}</div>
              <div className="text-xs opacity-70">{s.expected_direction} • {Math.round(s.impact_score)} • conf {s.confidence}</div>
              <div className="text-xs opacity-70 mt-2 line-clamp-2">{s.rationale_en}</div>
            </div>
          ))}
        </div>
      </Card>
    </Shell>
  );
}
