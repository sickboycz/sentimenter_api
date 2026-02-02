"use client";

import React from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";

export default function ResearchPage() {
  return (
    <Shell>
      <PageHeader
        title="Research"
        subtitle="Event studies, correlation, and calibration."
        meta="This area turns news impact into measurable edge."
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-[var(--grid-gap)]">
        <Card title="Event Study Builder" subtitle="Pick windows and cohorts">
          <div className="text-sm opacity-70">
            Define windows like 30m, 2h, 1d, 3d. Compare outcomes against baselines.
          </div>
        </Card>
        <Card title="Correlation Heatmap" subtitle="Drivers vs sectors">
          <div className="text-sm opacity-70">
            Visualize cross-asset sensitivity to geopolitical and macro drivers.
          </div>
        </Card>
        <Card title="Calibration Curve" subtitle="Predicted vs realized">
          <div className="text-sm opacity-70">
            Track score accuracy over time as the model evolves.
          </div>
        </Card>
      </div>
    </Shell>
  );
}
