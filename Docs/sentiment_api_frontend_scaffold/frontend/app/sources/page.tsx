"use client";

import React from "react";
import { Shell } from "../../components/Shell";

export default function SourcesPage() {
  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">Sources</div>
        <div className="text-sm opacity-75">
          Source registry + ingestion status should be surfaced here.
          Implement endpoint: /v1/sources and (optional) /v1/sources/status.
        </div>
      </div>

      <div className="glass p-4 text-sm opacity-85">
        Recommended tables:
        <div>• sources list with enabled, tier, license</div>
        <div>• ingestion lag p95, last fetch time</div>
        <div>• failure count last 1h</div>
      </div>
    </Shell>
  );
}
