"use client";

import React from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";

export default function ResearchPage() {
  return (
    <Shell>
      <Card title="Research" subtitle="Event studies, correlation, calibration (UI scaffold).">
        <div className="text-sm opacity-80 space-y-2">
          <div>• Add event-study request builder for windows (30m/2h/1d/3d/1w)</div>
          <div>• Render mean/median/hit-rate table + correlation heatmap</div>
          <div>• Render calibration curve (predicted vs realized) once backend supports it</div>
        </div>
      </Card>
    </Shell>
  );
}
