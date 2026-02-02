"use client";

import React from "react";
import { Shell } from "../../../components/Shell";
import { Card } from "../../../components/ui/Card";
import { useClusterDetail } from "../../../lib/api/hooks";

export default function ClusterDetailPage({ params }: { params: { clusterId: string } }) {
  const detail = useClusterDetail(params.clusterId);
  const c = detail.data?.data?.cluster;

  return (
    <Shell>
      <Card title="Cluster Detail" subtitle={c?.headline_en ?? "—"}>
        <div className="text-xs opacity-70">
          {c?.impact?.impact_level} • {c?.impact?.expected_direction} • conf {c?.impact?.confidence}
        </div>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Card title="Summary" subtitle="What changed / why it matters / what to watch.">
          <div className="space-y-1 text-sm opacity-85">
            {(c?.summary_bullets_en ?? []).map((b: string, i: number) => <div key={i}>• {b}</div>)}
          </div>
          <div className="mt-4 text-sm opacity-85">
            <div className="font-semibold">Why it matters</div>
            <div className="opacity-80">{detail.data?.data?.why_it_matters_en ?? "—"}</div>
          </div>
        </Card>

        <Card title="Evidence" subtitle="Audit trail.">
          <div className="space-y-2 text-sm opacity-85">
            {(detail.data?.data?.evidence ?? []).slice(0, 10).map((e: any, i: number) => (
              <div key={i} className="glass p-3">
                <div className="text-xs opacity-70 break-all">{e.url}</div>
                <div>{e.text_en}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Impacts" subtitle="Markets, sectors, tickers.">
          <div className="text-sm opacity-85 space-y-3">
            <div>
              <div className="opacity-70 text-xs mb-1">Top sectors</div>
              {(c?.top_sectors ?? []).slice(0, 6).map((s: any) => (
                <div key={s.sector_id} className="flex justify-between">
                  <span>{s.sector_name_en}</span>
                  <span className="opacity-75">{s.expected_direction} {Math.round(s.impact_score)}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="opacity-70 text-xs mb-1">Winners</div>
              {(c?.top_tickers_winners ?? []).slice(0, 8).map((t: any) => (
                <div key={t.symbol} className="flex justify-between">
                  <span>{t.symbol}</span>
                  <span className="opacity-75">+{Math.round(t.expected_return_bps)}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="opacity-70 text-xs mb-1">Losers</div>
              {(c?.top_tickers_losers ?? []).slice(0, 8).map((t: any) => (
                <div key={t.symbol} className="flex justify-between">
                  <span>{t.symbol}</span>
                  <span className="opacity-75">{Math.round(t.expected_return_bps)}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>
    </Shell>
  );
}
