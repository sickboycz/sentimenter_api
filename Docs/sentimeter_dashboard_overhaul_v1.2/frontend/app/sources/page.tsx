"use client";

import React from "react";
import { Shell } from "../../components/Shell";
import { Card } from "../../components/ui/Card";
import { useSources } from "../../lib/api/hooks";

export default function SourcesPage() {
  const sources = useSources();

  return (
    <Shell>
      <Card title="Sources" subtitle="Registry snapshot + health.">
        <div className="space-y-2 text-sm">
          {(sources.data?.data?.sources ?? []).slice(0, 50).map((s: any) => (
            <div key={s.source_id} className="flex justify-between">
              <span>{s.name}</span>
              <span className="opacity-75">{s.type} • {s.credibility_tier} • {s.license_class}</span>
            </div>
          ))}
        </div>
      </Card>
    </Shell>
  );
}
