"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
// TODO: Add virtualization (e.g. react-window) when clusters > 50 to avoid UI freeze on large payloads.
import { Shell } from "../../components/Shell";
import { apiGet, getDefaultApiKey } from "../../lib/api";
import { NewsCard } from "../../components/NewsCard";

export default function NewsPage() {
  const apiKey = getDefaultApiKey();

  const clusters = useQuery({
    queryKey: ["clusters"],
    queryFn: () =>
      apiGet<any>("/v1/news/clusters?min_impact_level=L2&include_source_urls=false&limit=50", apiKey),
  });

  const list = clusters.data?.data ?? [];

  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">News Clusters</div>
        <div className="text-sm opacity-70">Latest clusters with impacts (sectors + tickers).</div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {list.map((c: any) => (
          <NewsCard key={c.cluster_id} cluster={c} />
        ))}
      </div>
    </Shell>
  );
}
