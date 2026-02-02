"use client";

import React from "react";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from "recharts";

export function AreaChartCard({
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
        <AreaChart data={data}>
          <XAxis dataKey={xKey} hide />
          <YAxis hide domain={["auto","auto"]} />
          <Tooltip
            contentStyle={{ background: "rgba(10,14,22,0.92)", border: "1px solid rgba(255,255,255,0.10)", borderRadius: 12 }}
            labelStyle={{ color: "rgba(230,234,242,0.7)" }}
          />
          <Area type="monotone" dataKey={yKey} stroke="rgba(180,120,255,0.9)" fill="rgba(180,120,255,0.20)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
