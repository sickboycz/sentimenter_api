"use client";

import React from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";

export function BarChartCard({
  data,
  xKey,
  yKey,
  height = 160
}: {
  data: any[];
  xKey: string;
  yKey: string;
  height?: number;
}) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <XAxis dataKey={xKey} hide />
          <YAxis hide />
          <Tooltip
            contentStyle={{ background: "rgba(10,14,22,0.92)", border: "1px solid rgba(255,255,255,0.10)", borderRadius: 12 }}
            labelStyle={{ color: "rgba(230,234,242,0.7)" }}
          />
          <Bar dataKey={yKey} fill="rgba(255,190,90,0.85)" radius={[8,8,2,2]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
