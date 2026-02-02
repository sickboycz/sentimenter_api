"use client";

import React from "react";
import { Shell } from "../../components/Shell";
import { Card } from "../../components/ui/Card";
import { useClusters } from "../../lib/api/hooks";

export default function NewsFeed() {
  const clusters = useClusters();

  return (
    <Shell>
      <Card title="News Feed" subtitle="Clusters with impacts, evidence, and winners/losers.">
        <div className="text-sm opacity-70">
          Filters + virtualization are required for production scale. (Implement next.)
        </div>
      </Card>

      <div className="grid gap-4">
        {(clusters.data?.data ?? []).map((c: any) => (
          <div key={c.cluster_id} className="glass p-4 space-y-2">
            <div className="flex items-start justify-between gap-3">
              <div className="font-semibold">{c.headline_en}</div>
              <div className="text-xs opacity-70">{c.impact?.impact_level} • {c.impact?.expected_direction}</div>
            </div>
            <div className="text-sm opacity-85">
              {(c.summary_bullets_en ?? []).slice(0, 4).map((b: string, i: number) => (
                <div key={i}>• {b}</div>
              ))}
            </div>
            <div className="text-xs opacity-70">
              {c.source_count} sources • {c.topics?.slice(0, 4).join(", ")}
            </div>
          </div>
        ))}
      </div>
    </Shell>
  );
}
