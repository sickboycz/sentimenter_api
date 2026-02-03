"use client";

import React from "react";
import Link from "next/link";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/Table";
import { PageHeader } from "@/components/ui/PageHeader";
import { useClusterDetail } from "@/lib/api/hooks";

function useImpacts(detail: ReturnType<typeof useClusterDetail>) {
  const sectorImpacts = detail.data?.sector_impacts ?? [];
  const tickerImpacts = detail.data?.ticker_impacts ?? [];
  const winners = tickerImpacts.filter((t: { direction: string }) => t.direction === "Up");
  const losers = tickerImpacts.filter((t: { direction: string }) => t.direction === "Down");
  return { sectorImpacts, winners, losers };
}

export default function ClusterDetailPage({ params }: { params: { clusterId: string } }) {
  const detail = useClusterDetail(params.clusterId, true, { includeAssetImpacts: true, includeAnalogs: true });
  const c = detail.data?.cluster;
  const { sectorImpacts, winners, losers } = useImpacts(detail);
  const historicalAnalogs = detail.data?.historical_analogs ?? [];

  return (
    <Shell>
      {!detail.data ? (
        <Skeleton className="h-[260px]" />
      ) : (
        <>
          <PageHeader
            title={c?.headline_en ?? "Cluster"}
            subtitle={`${c?.impact?.impact_level ?? ""} • ${c?.impact?.expected_direction ?? ""} • conf ${Math.round((c?.impact?.confidence ?? 0) * 100)}%`}
            meta={`cluster ${c?.cluster_id ?? ""} • ${c?.source_count ?? 0} sources`}
            actions={
              <Badge tone={c?.impact?.expected_direction === "RiskOff" ? "bad" : c?.impact?.expected_direction === "RiskOn" ? "good" : "neutral"}>
                {c?.impact?.impact_level} • {c?.impact?.expected_direction}
              </Badge>
            }
          />

          <Card title="Summary" subtitle="Key bullets distilled from evidence.">
            <div className="text-sm opacity-85">
              {(c?.summary_bullets_en ?? []).length > 0 ? (
                (c?.summary_bullets_en ?? []).map((b: string, i: number) => (
                  <div key={i}>• {b}</div>
                ))
              ) : (
                <div className="opacity-70">No summary bullets yet.</div>
              )}
            </div>
          </Card>

          <div className="grid grid-cols-1 xl:grid-cols-12 gap-[var(--grid-gap)]">
            <Card className="xl:col-span-6" title="Evidence" subtitle="Audit trail (snippets).">
              <div className="space-y-2 text-sm opacity-85">
                {(detail.data?.evidence ?? []).length > 0 ? (
                  (detail.data?.evidence ?? []).slice(0, 12).map((e: { url: string; text_en: string }, i: number) => (
                    <div key={i} className="glass p-3">
                      <a className="text-xs opacity-70 break-all hover:underline" href={e.url} target="_blank" rel="noreferrer">
                        {e.url}
                      </a>
                      <div className="mt-1">{e.text_en}</div>
                    </div>
                  ))
                ) : (
                  <div className="opacity-70">No evidence yet.</div>
                )}
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
                      {sectorImpacts.length > 0 ? (
                        sectorImpacts.slice(0, 8).map((s: { sector_id: string; sector_name_en: string; direction: string; impact_score: number }) => (
                          <TR key={s.sector_id}>
                            <TD className="font-medium">{s.sector_name_en}</TD>
                            <TD className="text-right opacity-80">{s.direction}</TD>
                            <TD className="text-right">{Math.round(s.impact_score)}</TD>
                          </TR>
                        ))
                      ) : (
                        <TR><TD colSpan={3} className="opacity-70">No sector impacts.</TD></TR>
                      )}
                    </TBody>
                  </Table>
                </div>

                <div>
                  <div className="text-xs opacity-70 mb-2">Winners / Losers</div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <div className="opacity-70 mb-1">Winners</div>
                      {winners.length > 0 ? (
                        winners.slice(0, 10).map((t: { symbol: string; impact_score?: number; expected_return_bps?: number }) => (
                          <div key={t.symbol} className="flex justify-between">
                            <span className="font-medium">{t.symbol}</span>
                            <span className="opacity-80">+{Math.round(t.expected_return_bps ?? t.impact_score ?? 0)}</span>
                          </div>
                        ))
                      ) : (
                        <div className="opacity-70">—</div>
                      )}
                    </div>
                    <div>
                      <div className="opacity-70 mb-1">Losers</div>
                      {losers.length > 0 ? (
                        losers.slice(0, 10).map((t: { symbol: string; impact_score?: number; expected_return_bps?: number }) => (
                          <div key={t.symbol} className="flex justify-between">
                            <span className="font-medium">{t.symbol}</span>
                            <span className="opacity-80">{Math.round(t.expected_return_bps ?? -(t.impact_score ?? 0))}</span>
                          </div>
                        ))
                      ) : (
                        <div className="opacity-70">—</div>
                      )}
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

          {historicalAnalogs.length > 0 && (
            <Card title="Historically Similar Clusters" subtitle="Embedding-similar past clusters.">
              <div className="space-y-2">
                {historicalAnalogs.slice(0, 10).map((a: { cluster_id: string; similarity: number; label_en: string; date: string }) => (
                  <Link key={a.cluster_id} href={`/clusters/${a.cluster_id}`} className="block glass p-3 hover:opacity-90 transition">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium truncate flex-1">{a.label_en || a.cluster_id}</span>
                      <span className="opacity-70 text-xs whitespace-nowrap ml-2">sim {(a.similarity * 100).toFixed(1)}% • {a.date}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </Shell>
  );
}
