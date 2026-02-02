"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../../components/Shell";
import { apiGet } from "../../lib/api";

export default function TopicsPage() {
  const apiKey = process.env.NEXT_PUBLIC_API_KEY ?? "";

  const topics = useQuery({
    queryKey: ["topicsIndex"],
    queryFn: () => apiGet<any>("/v1/topics/index?interval=1h&limit=200", apiKey),
    refetchInterval: 60_000,
  });

  return (
    <Shell>
      <div className="glass p-4">
        <div className="text-lg font-semibold mb-2">Topics</div>
        <div className="text-sm opacity-80 mb-4">
          Topic indices (Moodix-inspired): trend + sentiment + news volume.
        </div>

        {topics.isLoading && <div className="opacity-70">Loading…</div>}
        {topics.isError && (
          <div className="text-sm text-red-300">
            Failed to load topics: {(topics.error as any)?.message}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="opacity-70">
              <tr>
                <th className="text-left py-2">ts</th>
                <th className="text-left py-2">topic</th>
                <th className="text-right py-2">index</th>
                <th className="text-left py-2">sentiment</th>
                <th className="text-right py-2">news_volume</th>
              </tr>
            </thead>
            <tbody>
              {(topics.data?.data ?? []).map((row: any) => (
                <tr key={`${row.ts}-${row.topic_id}`} className="border-t border-white/5">
                  <td className="py-2 font-mono text-xs">{row.ts}</td>
                  <td className="py-2">{row.topic_name_en}</td>
                  <td className="py-2 text-right font-mono">{row.index_value?.toFixed?.(3) ?? row.index_value}</td>
                  <td className="py-2">{row.sentiment}</td>
                  <td className="py-2 text-right font-mono">{row.news_volume}</td>
                </tr>
              ))}
              {(topics.data?.data ?? []).length === 0 && (
                <tr>
                  <td className="py-4 opacity-60" colSpan={5}>
                    No topic index points yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
