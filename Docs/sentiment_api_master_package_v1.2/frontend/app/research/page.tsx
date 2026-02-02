"use client";

import React from "react";
import { Shell } from "../../components/Shell";

export default function ResearchPage() {
  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">Research</div>
        <div className="text-sm opacity-75">
          Event studies and correlations (SPY/ES). Implement charts calling /v1/research/spy/event-study.
        </div>
      </div>

      <div className="glass p-4">
        <div className="text-sm opacity-85">
          Recommended UI blocks:
          <div>• event study result table (windows)</div>
          <div>• heatmap: topic × horizon median_return</div>
          <div>• calibration curves: predicted vs realized move</div>
        </div>
      </div>
    </Shell>
  );
}
