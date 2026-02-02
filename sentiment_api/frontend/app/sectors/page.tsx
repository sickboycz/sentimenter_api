"use client";

import React from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { SectorHeatmap } from "@/components/charts/SectorHeatmap";
import { PageHeader } from "@/components/ui/PageHeader";
import { useImpactSectors } from "@/lib/api/hooks";

export default function SectorsPage() {
  const sectors = useImpactSectors();

  return (
    <Shell>
      <PageHeader
        title="Sectors"
        subtitle="Heatmap + rationale by sector."
        meta="Impact scores are normalized 0–100 with directional tags."
      />

      {!sectors.data ? (
        <Skeleton className="h-[240px]" />
      ) : (
        <>
          <Card title="Sector Heatmap" subtitle={`method ${sectors.data?.methodology_version}`}>
            <SectorHeatmap sectors={sectors.data?.sectors} />
          </Card>

          <Card title="Sector Notes" subtitle="Top rationales (compact).">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              {(sectors.data?.sectors ?? []).slice(0, 10).map((s: any) => (
                <div key={s.sector_id} className="glass p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-semibold">{s.sector_name_en}</div>
                    <div className="text-xs opacity-70">{s.expected_direction} • {Math.round(s.impact_score)}</div>
                  </div>
                  <div className="text-xs opacity-70 mt-2 line-clamp-3">{s.rationale_en}</div>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </Shell>
  );
}
