"use client";

import React from "react";
import { Shell } from "../../components/Shell";
import { Card } from "../../components/ui/Card";

export default function ResearchPage() {
  return (
    <Shell>
      <Card title="Research" subtitle="Event studies & correlation UI.">
        <div className="text-sm opacity-80">
          Implement charts/tables consuming /v1/research/spy/event-study and related endpoints.
          This scaffold is intentionally minimal; the design system + error handling + contracts are the core deliverables.
        </div>
      </Card>
    </Shell>
  );
}
