"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../../components/Shell";
import { apiGet, getDefaultApiKey } from "../../lib/api";

export default function OpsPage() {
  const apiKey = getDefaultApiKey();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<any>("/v1/health", apiKey),
  });

  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">Ops</div>
        <div className="text-sm opacity-75">System health and links to Prometheus/Grafana.</div>
      </div>

      <div className="glass p-4">
        <div className="font-semibold mb-2">API Health</div>
        <pre className="text-xs opacity-85 overflow-auto">{JSON.stringify(health.data, null, 2)}</pre>
      </div>

      <div className="glass p-4 text-sm opacity-85">
        <div>Prometheus: http://localhost:9090</div>
        <div>Grafana: http://localhost:3001</div>
      </div>
    </Shell>
  );
}
