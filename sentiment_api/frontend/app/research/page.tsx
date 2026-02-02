"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../../components/Shell";
import { apiGet, getDefaultApiKey } from "../../lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

export default function ResearchPage() {
  const apiKey = getDefaultApiKey();
  const [from, setFrom] = useState("2025-01-01");
  const [to, setTo] = useState("2025-02-01");
  const [market, setMarket] = useState<"SPY" | "ES">("SPY");

  const eventStudy = useQuery({
    queryKey: ["eventStudy", from, to, market],
    queryFn: () =>
      apiGet<any>(
        `/v1/research/spy/event-study?from=${from}&to=${to}&windows=30m&windows=2h&windows=1d&windows=3d&windows=1w&market=${market}`,
        apiKey
      ),
  });

  const windows = eventStudy.data?.data?.windows ?? eventStudy.data?.data ?? [];
  const marketLabel = eventStudy.data?.data?.market ?? market;
  const chartData = Array.isArray(windows)
    ? windows.map((w: any) => ({
        window: w.window ?? w,
        mean_return: (w.mean_return ?? 0) * 100,
        median_return: (w.median_return ?? 0) * 100,
        hit_rate: (w.hit_rate ?? 0) * 100,
        sample_size: w.sample_size ?? 0,
      }))
    : [];

  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">Research</div>
        <div className="text-sm opacity-75">
          Event studies vs {marketLabel}. Mean/median returns by horizon.
        </div>
      </div>

      <div className="glass p-4 flex flex-wrap gap-4 items-end">
        <label className="flex flex-col gap-1 text-sm">
          <span className="opacity-75">From</span>
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="px-3 py-2 rounded-lg bg-black/20 border border-white/10"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="opacity-75">To</span>
          <input
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="px-3 py-2 rounded-lg bg-black/20 border border-white/10"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="opacity-75">Market</span>
          <select
            value={market}
            onChange={(e) => setMarket(e.target.value as "SPY" | "ES")}
            className="px-3 py-2 rounded-lg bg-black/20 border border-white/10"
          >
            <option value="SPY">SPY</option>
            <option value="ES">ES</option>
          </select>
        </label>
      </div>

      <div className="glass p-4">
        <div className="font-semibold mb-4">Mean Return by Window</div>
        {chartData.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <XAxis dataKey="window" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} tickFormatter={(v) => `${v.toFixed(2)}%`} />
                <Tooltip
                  contentStyle={{ background: "rgba(15,23,42,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
                  formatter={(v: number) => [`${v.toFixed(3)}%`, "Mean Return"]}
                />
                <Bar dataKey="mean_return" radius={4}>
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={chartData[i].mean_return >= 0 ? "#22c55e" : "#ef4444"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="text-sm opacity-70">No event study data for this range.</div>
        )}
      </div>

      <div className="glass p-4 overflow-x-auto">
        <div className="font-semibold mb-2">Event Study Results</div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left opacity-80 border-b border-white/10">
              <th className="py-2 pr-4">Window</th>
              <th className="py-2 pr-4">Mean Return %</th>
              <th className="py-2 pr-4">Median Return %</th>
              <th className="py-2 pr-4">Hit Rate %</th>
              <th className="py-2 pr-4">Sample</th>
            </tr>
          </thead>
          <tbody>
            {chartData.map((r: any) => (
              <tr key={r.window} className="border-b border-white/5">
                <td className="py-2 pr-4">{r.window}</td>
                <td className="py-2 pr-4">{(r.mean_return ?? 0).toFixed(3)}</td>
                <td className="py-2 pr-4">{(r.median_return ?? 0).toFixed(3)}</td>
                <td className="py-2 pr-4">{(r.hit_rate ?? 0).toFixed(1)}</td>
                <td className="py-2 pr-4">{r.sample_size}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
