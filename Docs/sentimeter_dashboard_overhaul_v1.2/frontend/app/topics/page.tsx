"use client";

import React from "react";
import { Shell } from "../../components/Shell";
import { Card } from "../../components/ui/Card";
import { useTopicsIndex } from "../../lib/api/hooks";

export default function TopicsPage() {
  const topics = useTopicsIndex();

  return (
    <Shell>
      <Card title="Topics" subtitle="Topic indices (Moodix-style).">
        <div className="text-sm opacity-85 space-y-1">
          {(topics.data?.data?.points ?? []).slice(0, 30).map((p: any, i: number) => (
            <div key={i} className="flex justify-between">
              <span>{p.topic_name_en}</span>
              <span className="opacity-75">{p.sentiment} • {Math.round(p.index_value)}</span>
            </div>
          ))}
        </div>
      </Card>
    </Shell>
  );
}
