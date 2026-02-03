"use client";

import React, { useMemo, useState } from "react";
import { StatusPill } from "./ui/StatusPill";
import { Badge } from "./ui/Badge";
import { useHealth, useStatus, useOpsStatus } from "@/lib/api/hooks";

export function Topbar() {
  const health = useHealth();
  const status = useStatus();
  const ops = useOpsStatus(true);

  const [tf, setTf] = useState<"1h" | "6h" | "24h">("24h");
  const [q, setQ] = useState("");

  const apiStatus = health.data?.status ?? "unknown";
  const ingestionStatus = status.data?.ingestion ?? "unknown";
  const allocationStatus = status.data?.allocation ?? "unknown";
  const researchStatus = status.data?.research ?? "unknown";

  const authStatus = useMemo(() => {
    if (ops.isError && (ops.error as any)?.status === 401) return "down";
    return apiStatus === "ok" ? "ok" : "unknown";
  }, [apiStatus, ops.isError, ops.error]);

  const pills = useMemo(() => {
    return [
      { label: "API", status: apiStatus },
      { label: "Auth", status: authStatus },
      { label: "Ingestion", status: ingestionStatus },
      { label: "Allocation", status: allocationStatus },
      { label: "Research", status: researchStatus }
    ];
  }, [apiStatus, authStatus, ingestionStatus, allocationStatus, researchStatus]);

  const queueTotal = useMemo(() => {
    const q = ops.data?.queues || {};
    if (typeof ops.data?.queues_total === "number") return ops.data?.queues_total;
    return Object.values(q).reduce((acc, v) => acc + (v || 0), 0);
  }, [ops.data?.queues, ops.data?.queues_total]);

  const workerAge = ops.data?.heartbeats?.worker?.age_sec ?? null;
  const workerAlive = workerAge !== null && workerAge < 30;
  const activityTone = !ops.data || ops.isError
    ? "neutral"
    : queueTotal > 0 && !workerAlive
      ? "bad"
      : queueTotal > 0
        ? "good"
        : "neutral";
  const activityLabel = !ops.data || ops.isError ? "unknown" : (queueTotal > 0 ? `${queueTotal} queued` : "idle");
  const workerLabel = workerAge === null ? "—" : `${Math.round(workerAge)}s`;
  const dotClass = activityTone === "good"
    ? "bg-[var(--good)]"
    : activityTone === "bad"
      ? "bg-[var(--bad)]"
      : "bg-white/40";
  const dotPulse = activityTone === "good" ? "animate-pulse" : "";

  return (
    <div className="glass-strong p-2 sm:p-3 flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-2">
          <div className="font-display font-semibold text-sm sm:text-base">Sentimeter</div>
          <div className="text-xs opacity-60 hidden lg:block">Dashboard</div>
          <div className="text-[11px] opacity-50 hidden xl:block">API status at a glance</div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {pills.map((p) => (
            <StatusPill key={p.label} label={p.label} status={p.status} />
          ))}
        </div>

        <div className="flex-1" />

        <Badge tone={activityTone} className="whitespace-nowrap">
          <span className="inline-flex items-center gap-2">
            <span className={`inline-block w-2 h-2 rounded-full ${dotClass} ${dotPulse}`} />
            <span>Activity</span>
            <span className="opacity-70">•</span>
            <span>{activityLabel}</span>
            <span className="opacity-70">•</span>
            <span>worker {workerLabel}</span>
          </span>
        </Badge>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="glass p-1 flex gap-1 shrink-0">
          {(["1h","6h","24h"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTf(t)}
              className={`px-2 py-1 rounded-lg text-xs ${tf===t ? "bg-white/10" : "opacity-70 hover:bg-white/5"}`}
              title="Timeframe (UI state only)"
            >
              {t}
            </button>
          ))}
        </div>

        <div className="flex-1 min-w-[160px] max-w-[320px]">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search clusters, tickers…"
            className="w-full px-3 py-2 rounded-xl bg-black/20 border border-white/10 outline-none focus:border-white/25"
            autoComplete="off"
          />
        </div>
      </div>
    </div>
  );
}
