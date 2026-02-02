"use client";

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../../../components/Shell";
import { apiGet } from "../../../lib/api";
import { ImpactBadge } from "../../../components/ImpactBadge";

export default function ClusterDetailPage({ params }: { params: { clusterId: string } }) {
  const apiKey = "";
  const { clusterId } = params;

  const detail = useQuery({
    queryKey: ["clusterDetail", clusterId],
    queryFn: () =>
      apiGet<any>(
        `/v1/news/clusters/${clusterId}?include_articles=true&include_evidence=true&include_analogs=true`,
        apiKey
      ),
  });

  const c = detail.data?.data?.cluster;

  return (
    <Shell>
      <div className="glass p-4 space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div className="text-xl font-semibold">{c?.headline_en ?? "—"}</div>
          <ImpactBadge level={c?.impact?.impact_level} direction={c?.impact?.expected_direction} />
        </div>
        <div className="opacity-80 text-sm">
          {(c?.summary_bullets_en ?? []).map((b: string, i: number) => (
            <div key={i}>• {b}</div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="glass p-4 xl:col-span-2">
          <div className="font-semibold mb-2">Evidence</div>
          <div className="space-y-2 text-sm opacity-85">
            {(detail.data?.data?.evidence ?? []).slice(0, 12).map((e: any, i: number) => (
              <div key={i} className="glass p-3">
                <div className="text-xs opacity-70 break-all">{e.url}</div>
                <div>{e.text_en}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="glass p-4">
          <div className="font-semibold mb-2">Ticker Impact</div>

          <div className="text-xs opacity-70 mb-1">Winners</div>
          <div className="space-y-1 text-sm">
            {(detail.data?.data?.ticker_impacts ?? [])
              .filter((x: any) => x.direction === "RiskOn")
              .slice(0, 15)
              .map((t: any) => (
                <div key={t.ticker} className="flex justify-between">
                  <span>{t.ticker}</span>
                  <span className="opacity-75">+{Math.round(t.impact_score)}</span>
                </div>
              ))}
          </div>

          <div className="text-xs opacity-70 mt-4 mb-1">Losers</div>
          <div className="space-y-1 text-sm">
            {(detail.data?.data?.ticker_impacts ?? [])
              .filter((x: any) => x.direction === "RiskOff")
              .slice(0, 15)
              .map((t: any) => (
                <div key={t.ticker} className="flex justify-between">
                  <span>{t.ticker}</span>
                  <span className="opacity-75">-{Math.round(t.impact_score)}</span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </Shell>
  );
}
