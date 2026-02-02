"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../../components/Shell";
import { apiGet, getDefaultApiKey } from "../../lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

export default function TopicsPage() {
  const apiKey = getDefaultApiKey();
  const topics = useQuery({
    queryKey: ["topicsIndex"],
    queryFn: () =>
      apiGet<{ data: Array<{ ts: string; topic_id: string; topic_name_en: string; index_value: number; sentiment: string; news_volume: number }> }>(
        "/v1/topics/index?interval=5m&limit=500",
        apiKey
      ),
  });

  const rows = topics.data?.data ?? [];
  const chartData = rows
    .slice(0, 100)
    .map((r) => ({
      ts: r.ts ? new Date(r.ts).toLocaleTimeString() : "",
      [r.topic_name_en || r.topic_id]: r.index_value,
    }));

  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">Topic Index</div>
        <div className="text-sm opacity-75">
          Mood/topic contribution timeline — v1.2
        </div>
      </div>

      <div className="glass p-4">
        <div className="font-semibold mb-2">Topic Ranking</div>
        <div className="text-sm overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left opacity-75">
                <th className="py-1">Topic</th>
                <th className="py-1">Index</th>
                <th className="py-1">Sentiment</th>
                <th className="py-1">Volume</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 20).map((r: any, i: number) => (
                <tr key={r.topic_id ?? i}>
                  <td className="py-1">{r.topic_name_en ?? r.topic_id ?? "—"}</td>
                  <td className="py-1">{Number(r.index_value ?? 0).toFixed(2)}</td>
                  <td className="py-1">{r.sentiment ?? "—"}</td>
                  <td className="py-1">{r.news_volume ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {chartData.length > 0 && Object.keys(chartData[0] ?? {}).filter((k) => k !== "ts").length > 0 && (
        <div className="glass p-4">
          <div className="font-semibold mb-2">Topic Index Chart</div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="ts" stroke="rgba(255,255,255,0.6)" fontSize={11} />
                <YAxis stroke="rgba(255,255,255,0.6)" fontSize={11} />
                <Tooltip contentStyle={{ background: "rgba(0,0,0,0.8)", border: "1px solid rgba(255,255,255,0.2)" }} />
                <Legend />
                {Object.keys(chartData[0] ?? {}).filter((k) => k !== "ts").slice(0, 3).map((k, i) => (
                  <Line key={k} type="monotone" dataKey={k} stroke={`hsl(${200 + i * 60}, 70%, 60%)`} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {rows.length === 0 && !topics.isLoading && (
        <div className="glass p-4 text-sm opacity-75">No topic data yet. Run ingestion to populate.</div>
      )}
    </Shell>
  );
}
