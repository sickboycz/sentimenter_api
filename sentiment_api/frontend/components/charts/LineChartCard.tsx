"use client";

import React from "react";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from "recharts";

export function LineChartCard({
  data,
  xKey,
  yKey,
  y2Key,
  height = 160
}: {
  data: any[];
  xKey: string;
  yKey: string;
  y2Key?: string;
  height?: number;
}) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <XAxis dataKey={xKey} hide />
          <YAxis hide domain={["auto","auto"]} />
          <Tooltip
            contentStyle={{ background: "rgba(10,14,22,0.92)", border: "1px solid rgba(255,255,255,0.10)", borderRadius: 12 }}
            labelStyle={{ color: "rgba(230,234,242,0.7)" }}
          />
          <Line type="monotone" dataKey={yKey} stroke="rgba(90,180,255,0.95)" strokeWidth={2} dot={false} />
          {y2Key ? <Line type="monotone" dataKey={y2Key} stroke="rgba(255,95,110,0.85)" strokeWidth={2} dot={false} /> : null}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
