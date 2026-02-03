"use client";

import React, { useMemo, useState } from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { useHealth, useOpsStatus, useAdminLogs, useAdminBackfill, useAdminIngestRun, useAdminSummarizeRun } from "@/lib/api/hooks";

function formatAge(ageSec?: number | null) {
  if (ageSec === null || ageSec === undefined) return "—";
  if (ageSec < 60) return `${Math.round(ageSec)}s ago`;
  const mins = Math.round(ageSec / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  return `${hrs}h ago`;
}

function formatTs(ts?: string | null) {
  if (!ts) return "—";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString();
}

function toneFromStatus(status?: string) {
  if (status === "ok") return "good";
  if (status === "fail") return "bad";
  return "neutral";
}

export default function OpsPage() {
  const health = useHealth();
  const ops = useOpsStatus();
  const logs = useAdminLogs();
  const backfill = useAdminBackfill();
  const ingestRun = useAdminIngestRun();
  const summarizeRun = useAdminSummarizeRun();
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [fromDate, setFromDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString().slice(0, 10);
  });
  const [toDate, setToDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [backfillMsg, setBackfillMsg] = useState<string | null>(null);

  const queueTotal = useMemo(() => {
    const q = ops.data?.queues || {};
    if (typeof ops.data?.queues_total === "number") return ops.data?.queues_total;
    return Object.values(q).reduce((acc, v) => acc + (v || 0), 0);
  }, [ops.data?.queues, ops.data?.queues_total]);

  const workerAge = ops.data?.heartbeats?.worker?.age_sec ?? null;
  const daemonAge = ops.data?.heartbeats?.daemon?.age_sec ?? null;
  const workerAlive = workerAge !== null && workerAge < 30;
  const pipelineState = queueTotal > 0 ? (workerAlive ? "processing" : "stalled") : "idle";
  const pipelineTone = pipelineState === "processing" ? "good" : pipelineState === "stalled" ? "bad" : "neutral";
  const workerTone = workerAge === null ? "neutral" : (workerAlive ? "good" : "bad");
  const daemonAlive = daemonAge !== null && daemonAge < 90;
  const daemonTone = daemonAge === null ? "neutral" : (daemonAlive ? "good" : "bad");
  const openaiCheck = health.data?.checks?.find((c: { name?: string }) => c?.name === "openai") as { status?: string; details?: { message?: string; error?: string } } | undefined;

  const quickRange = (days: number) => {
    const d = new Date();
    d.setDate(d.getDate() - days);
    setFromDate(d.toISOString().slice(0, 10));
    setToDate(new Date().toISOString().slice(0, 10));
  };

  return (
    <Shell>
      {ops.isError && (
        <Card title="Ops data unavailable" subtitle="Check API key and backend admin endpoints.">
          <div className="text-sm opacity-80">
            Set <code className="kbd">SENTIMETER_API_KEY</code> in Settings or the top bar, then refresh.
          </div>
        </Card>
      )}

      <PageHeader
        title="Ops"
        subtitle="System health, pipelines, and live logs."
        meta="Use this page to validate ingestion, OpenAI, and background processing."
        actions={(
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={async () => {
                setActionMsg(null);
                try {
                  const res = await ingestRun.mutateAsync(undefined);
                  setActionMsg(`Force ingest: ${res?.pushed ?? 0} pushed from ${res?.sources_polled ?? 0} sources`);
                  ops.refetch();
                } catch (err: any) {
                  setActionMsg(`Ingest failed: ${err?.message ?? "Unknown error"}`);
                }
              }}
              disabled={ingestRun.isPending}
            >
              {ingestRun.isPending ? "Running…" : "Force Ingest"}
            </Button>
            <Button
              onClick={async () => {
                setActionMsg(null);
                try {
                  const res = await summarizeRun.mutateAsync(undefined);
                  setActionMsg(`Force summarize: ${res?.queued ?? 0} queued`);
                  ops.refetch();
                } catch (err: any) {
                  setActionMsg(`Summarize failed: ${err?.message ?? "Unknown error"}`);
                }
              }}
              disabled={summarizeRun.isPending}
            >
              {summarizeRun.isPending ? "Running…" : "Force Summarize"}
            </Button>
            <Button
              variant="ghost"
              onClick={() => { health.refetch(); setActionMsg("Health refreshed. Check OpenAI status above if summarize/clusters fail."); setTimeout(() => setActionMsg(null), 4000); }}
            >
              Test Connection
            </Button>
            <Button
              onClick={() => document.getElementById("backfill")?.scrollIntoView({ behavior: "smooth", block: "start" })}
            >
              Backfill
            </Button>
          </div>
        )}
      />

      {actionMsg && (
        <div className="glass p-3 text-sm text-left">{actionMsg}</div>
      )}

      <Card
        title="System Overview"
        subtitle="Live system status, queue health, and background activity."
        right={<Badge tone={pipelineTone}>{pipelineState.toUpperCase()}</Badge>}
      >
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-sm">
          <div className="glass p-3">
            <div className="text-xs opacity-70">API Health</div>
            <div className="font-semibold">{health.data?.status ?? "unknown"}</div>
            <div className="text-xs opacity-70">as of {formatTs(health.data?.as_of)}</div>
            {openaiCheck?.status === "fail" && (
              <div className="text-xs text-amber-400 mt-1" title={openaiCheck?.details?.error}>
                OpenAI: {openaiCheck?.details?.message || openaiCheck?.details?.error || "invalid"}
              </div>
            )}
          </div>
          <div className="glass p-3">
            <div className="text-xs opacity-70">Database</div>
            <div className="font-semibold">{ops.data?.db?.status ?? "unknown"}</div>
            <div className="text-xs opacity-70">{ops.data?.db?.error ?? "OK"}</div>
          </div>
          <div className="glass p-3">
            <div className="text-xs opacity-70">Redis</div>
            <div className="font-semibold">{ops.data?.redis?.status ?? "unknown"}</div>
            <div className="text-xs opacity-70">{ops.data?.redis?.error ?? "OK"}</div>
          </div>
          <div className="glass p-3">
            <div className="text-xs opacity-70">Background</div>
            <div className="font-semibold">{queueTotal} queued</div>
            <div className="flex items-center gap-2 mt-1">
              <Badge tone={workerTone}>worker {formatAge(workerAge)}</Badge>
              <Badge tone={daemonTone}>daemon {formatAge(daemonAge)}</Badge>
            </div>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-[var(--grid-gap)]">
        <Card className="xl:col-span-7" title="Queue Activity" subtitle="Live backlog + worker heartbeat.">
          {!ops.data ? (
            <Skeleton className="h-[220px]" />
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
              {Object.entries(ops.data?.queues || {}).map(([name, value]) => (
                <div key={name} className="glass p-3">
                  <div className="text-xs opacity-70">{name}</div>
                  <div className="text-lg font-semibold">{value}</div>
                </div>
              ))}
              <div className="glass p-3 col-span-2 md:col-span-3">
                <div className="text-xs opacity-70">Worker last job</div>
                <div className="text-sm">
                  {(ops.data?.heartbeats?.worker as any)?.last_job?.queue ?? "—"}
                </div>
                <div className="text-xs opacity-70">
                  {(ops.data?.heartbeats?.worker as any)?.last_job?.at ? formatTs((ops.data?.heartbeats?.worker as any)?.last_job?.at) : "—"}
                </div>
              </div>
            </div>
          )}
        </Card>

        <Card className="xl:col-span-5" title="System Counts" subtitle="Materialized totals in Postgres.">
          {!ops.data ? (
            <Skeleton className="h-[220px]" />
          ) : (
            <div className="grid grid-cols-2 gap-3 text-sm">
              {Object.entries(ops.data?.counts || {}).map(([name, value]) => (
                <div key={name} className="glass p-3">
                  <div className="text-xs opacity-70">{name}</div>
                  <div className="text-lg font-semibold">{value}</div>
                </div>
              ))}
              <div className="glass p-3 col-span-2">
                <div className="text-xs opacity-70">Latest activity</div>
                <div className="text-sm">article {formatTs((ops.data?.latest as any)?.article_at)}</div>
                <div className="text-sm">cluster {formatTs((ops.data?.latest as any)?.cluster_at)}</div>
                <div className="text-sm">event {formatTs((ops.data?.latest as any)?.event_at)}</div>
              </div>
            </div>
          )}
        </Card>
      </div>

      <Card id="backfill" title="Backfill" subtitle="Queue historical ingest by date range.">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
          <div className="md:col-span-4 flex flex-wrap gap-2 text-xs">
            <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => quickRange(7)}>Last 7 days</Button>
            <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => quickRange(30)}>Last 30 days</Button>
            <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => quickRange(90)}>Last 90 days</Button>
          </div>
          <div>
            <label className="text-xs opacity-70">From</label>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-black/20 border border-white/10 outline-none text-sm"
              autoComplete="off"
            />
          </div>
          <div>
            <label className="text-xs opacity-70">To</label>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-black/20 border border-white/10 outline-none text-sm"
              autoComplete="off"
            />
          </div>
          <div className="md:col-span-2 flex items-center gap-2">
            <Button
              onClick={async () => {
                setBackfillMsg(null);
                try {
                  const res = await backfill.mutateAsync({ from: fromDate, to: toDate });
                  const msg = res?.error
                    ? `Backfill error: ${res.error}`
                    : `Queued ${res?.pushed ?? 0} items from ${res?.from ?? fromDate} to ${res?.to ?? toDate}.`;
                  setBackfillMsg(msg);
                  ops.refetch();
                } catch (err: any) {
                  setBackfillMsg(`Backfill failed: ${err?.message ?? "Unknown error"}`);
                }
              }}
              disabled={backfill.isPending || !fromDate || !toDate}
            >
              {backfill.isPending ? "Running…" : "Run Backfill"}
            </Button>
            <div className="text-xs opacity-70">
              This can take time for large ranges.
            </div>
          </div>
        </div>
        {backfillMsg && (
          <div className="glass p-3 mt-3 text-sm">{backfillMsg}</div>
        )}
      </Card>

      <Card title="Recent Runs" subtitle="Last successful or failed job per pipeline stage.">
        {!ops.data ? (
          <Skeleton className="h-[160px]" />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 text-sm">
            {Object.entries(ops.data?.runs || {}).map(([name, run]) => (
              <div key={name} className="glass p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-semibold">{name}</div>
                  <Badge tone={toneFromStatus((run as any)?.status)}>{(run as any)?.status ?? "unknown"}</Badge>
                </div>
                <div className="text-xs opacity-70 mt-1">start {formatTs((run as any)?.started_at)}</div>
                <div className="text-xs opacity-70">end {formatTs((run as any)?.ended_at)}</div>
                <div className="text-xs opacity-70 mt-1">stats {JSON.stringify((run as any)?.stats || {})}</div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-[var(--grid-gap)]">
        {(["api","worker","daemon"] as const).map((src) => (
          <Card key={src} title={`${src} logs`} subtitle="Tail (latest 200 lines)">
            {!logs.data ? (
              <Skeleton className="h-[220px]" />
            ) : (
              <div className="glass p-3">
                <pre className="text-xs opacity-85 whitespace-pre-wrap max-h-[280px] overflow-auto">
                  {(logs.data as any)?.[src]?.length ? (logs.data as any)[src].join("\n") : "No log lines yet."}
                </pre>
              </div>
            )}
          </Card>
        ))}
      </div>
    </Shell>
  );
}
