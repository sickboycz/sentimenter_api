"use client";

import React from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/Table";
import { useClusterDetail } from "@/lib/api/hooks";

export default function ClusterDetailPage({ params }: { params: { clusterId: string } }) {
  const detail = useClusterDetail(params.clusterId);
  const c = detail.data?.cluster;

  return (
    <Shell>
      {!detail.data ? (
        <Skeleton className="h-[260px]" />
      ) : (
        <>
          <Card
            title={c?.headline_en ?? "Cluster"}
            subtitle={`${c?.impact?.impact_level ?? ""} • ${c?.impact?.expected_direction ?? ""} • conf ${Math.round((c?.impact?.confidence ?? 0) * 100)}%`}
            right={
              <Badge tone={c?.impact?.expected_direction === "RiskOff" ? "bad" : c?.impact?.expected_direction === "RiskOn" ? "good" : "neutral"}>
                {c?.impact?.impact_level} • {c?.impact?.expected_direction}
              </Badge>
            }
          >
            <div className="text-sm opacity-85">
              {(c?.summary_bullets_en ?? []).map((b: string, i: number) => (
                <div key={i}>• {b}</div>
              ))}
            </div>
          </Card>

          <div className="grid grid-cols-1 xl:grid-cols-12 gap-[var(--grid-gap)]">
            <Card className="xl:col-span-6" title="Evidence" subtitle="Audit trail (snippets).">
              <div className="space-y-2 text-sm opacity-85">
                {(detail.data?.evidence ?? []).slice(0, 12).map((e: any, i: number) => (
                  <div key={i} className="glass p-3">
                    <div className="text-xs opacity-70 break-all">{e.url}</div>
                    <div className="mt-1">{e.text_en}</div>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="xl:col-span-6" title="Impacts" subtitle="Markets • Sectors • Tickers.">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="text-xs opacity-70 mb-2">Top sectors</div>
                  <Table>
                    <THead>
                      <TR hover={false}>
                        <TH>Sector</TH>
                        <TH className="text-right">Dir</TH>
                        <TH className="text-right">Score</TH>
                      </TR>
                    </THead>
                    <TBody>
                      {(c?.top_sectors ?? []).slice(0, 8).map((s: any) => (
                        <TR key={s.sector_id}>
                          <TD className="font-medium">{s.sector_name_en}</TD>
                          <TD className="text-right opacity-80">{s.expected_direction}</TD>
                          <TD className="text-right">{Math.round(s.impact_score)}</TD>
                        </TR>
                      ))}
                    </TBody>
                  </Table>
                </div>

                <div>
                  <div className="text-xs opacity-70 mb-2">Winners / Losers</div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <div className="opacity-70 mb-1">Winners</div>
                      {(c?.top_tickers_winners ?? []).slice(0, 10).map((t: any) => (
                        <div key={t.symbol} className="flex justify-between">
                          <span className="font-medium">{t.symbol}</span>
                          <span className="opacity-80">+{Math.round(t.expected_return_bps)}</span>
                        </div>
                      ))}
                    </div>
                    <div>
                      <div className="opacity-70 mb-1">Losers</div>
                      {(c?.top_tickers_losers ?? []).slice(0, 10).map((t: any) => (
                        <div key={t.symbol} className="flex justify-between">
                          <span className="font-medium">{t.symbol}</span>
                          <span className="opacity-80">{Math.round(t.expected_return_bps)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-4 text-sm opacity-80">
                <div className="font-semibold">Why it matters</div>
                <div className="opacity-80">{detail.data?.why_it_matters_en ?? "—"}</div>
              </div>
            </Card>
          </div>
        </>
      )}
    </Shell>
  );
}
