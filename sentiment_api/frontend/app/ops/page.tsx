"use client";

import React from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { useHealth } from "@/lib/api/hooks";

export default function OpsPage() {
  const health = useHealth();

  return (
    <Shell>
      <Card title="Ops" subtitle="System health and logs.">
        <div className="text-sm opacity-70">Health is instant; logs panel can be wired to a backend tail endpoint.</div>
      </Card>

      {!health.data ? (
        <Skeleton className="h-[240px]" />
      ) : (
        <Card title="API Health" subtitle="Raw payload (debug).">
          <pre className="text-xs opacity-85 overflow-auto">{JSON.stringify(health.data, null, 2)}</pre>
        </Card>
      )}

      <Card title="Logs" subtitle="Wire to /v1/logs later.">
        <div className="text-sm opacity-70">
          This scaffold keeps the UI consistent; implement a backend logs endpoint or proxy to docker logs.
        </div>
      </Card>
    </Shell>
  );
}
