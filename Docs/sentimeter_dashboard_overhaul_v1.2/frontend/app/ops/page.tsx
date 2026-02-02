"use client";

import React from "react";
import { Shell } from "../../components/Shell";
import { Card } from "../../components/ui/Card";
import { StatusPill } from "../../components/ui/StatusPill";
import { useHealth, useSources } from "../../lib/api/hooks";

export default function OpsPage() {
  const health = useHealth();
  const sources = useSources();

  const apiStatus = health.data?.data?.status ?? "unknown";
  const sourcesCount = sources.data?.data?.sources?.length ?? 0;

  return (
    <Shell>
      <div className="grid gap-4">
        <Card title="System Health" subtitle="Readiness at a glance.">
          <div className="flex flex-wrap gap-2">
            <StatusPill label="API" status={apiStatus} />
            <StatusPill label="Sources" status={sourcesCount > 0 ? "ok" : "degraded"} />
            <StatusPill label="Prometheus" status="unknown" />
            <StatusPill label="Grafana" status="unknown" />
          </div>

          <div className="mt-4 text-sm opacity-80">
            <div>Prometheus: http://localhost:9090</div>
            <div>Grafana: http://localhost:3001</div>
          </div>
        </Card>

        <Card title="Raw Health Payload">
          <pre className="text-xs opacity-85 overflow-auto">{JSON.stringify(health.data, null, 2)}</pre>
        </Card>

        <Card title="Sources (Registry Snapshot)">
          <pre className="text-xs opacity-85 overflow-auto">{JSON.stringify(sources.data, null, 2)}</pre>
        </Card>
      </div>
    </Shell>
  );
}
