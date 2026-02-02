"use client";

import React, { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, CheckCircle, AlertCircle, XCircle, RefreshCw, Server } from "lucide-react";

const API_KEY_STORAGE = "sentiment_api_key";

type HealthStatus = "ok" | "degraded" | "down";

function HealthPill({
  status,
  coreOk,
  coreTotal,
  onRefresh,
  isRefetching,
}: {
  status: HealthStatus;
  coreOk: number;
  coreTotal: number;
  onRefresh?: () => void;
  isRefetching?: boolean;
}) {
  const config = {
    ok: {
      icon: CheckCircle,
      label: "Healthy",
      className: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40 ring-emerald-400/20",
      dot: "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]",
    },
    degraded: {
      icon: AlertCircle,
      label: "Degraded",
      className: "bg-amber-500/20 text-amber-300 border-amber-500/40",
      dot: "bg-amber-400",
    },
    down: {
      icon: XCircle,
      label: "Down",
      className: "bg-red-500/20 text-red-300 border-red-500/40",
      dot: "bg-red-400",
    },
  };
  const c = config[status];
  const Icon = c.icon;
  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium shadow-sm ${c.className} ${status === "ok" ? "ring-2 ring-inset" : ""}`}
      title={`API core checks: ${coreOk}/${coreTotal} (postgres, redis, registry, artifacts)`}
    >
      <Server className="h-3.5 w-3.5 opacity-80" aria-hidden />
      <span className={`relative flex h-2 w-2 shrink-0 ${status === "ok" ? "animate-pulse" : ""}`}>
        <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${c.dot}`} />
        <span className={`relative inline-flex rounded-full h-2 w-2 ${c.dot}`} />
      </span>
      <Icon className="h-3.5 w-3.5 shrink-0" />
      <span>{c.label}</span>
      <span className="opacity-70 tabular-nums">{coreOk}/{coreTotal}</span>
      {onRefresh && (
        <button
          type="button"
          onClick={onRefresh}
          disabled={isRefetching}
          className="ml-0.5 p-0.5 rounded hover:bg-white/10 transition-opacity disabled:opacity-50"
          title="Refresh health"
          aria-label="Refresh health"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRefetching ? "animate-spin" : ""}`} />
        </button>
      )}
    </div>
  );
}

export function Topbar() {
  const queryClient = useQueryClient();
  const [apiKey, setApiKeyState] = useState("");
  const [reveal, setReveal] = useState(false);

  const health = useQuery({
    queryKey: ["health-topbar"],
    queryFn: async () => {
      const base = typeof window !== "undefined" && !process.env.NEXT_PUBLIC_API_BASE_URL
        ? `${window.location.protocol}//${window.location.hostname}:8080`
        : (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080");
      const res = await fetch(`${base}/v1/health`, { cache: "no-store" });
      if (!res.ok) throw new Error("Health check failed");
      return res.json() as Promise<{ status: HealthStatus; checks: Array<{ name: string; status: string }> }>;
    },
    refetchInterval: 30_000,
    retry: 1,
    staleTime: 20_000,
  });

  const coreNames = ["postgres", "redis", "registry", "artifacts"];
  const coreChecks = health.data?.checks?.filter((c) => coreNames.includes(c.name)) ?? [];
  const coreOk = coreChecks.filter((c) => c.status === "ok").length;
  const coreTotal = coreChecks.length;
  const status = (health.data?.status as HealthStatus) ?? (health.isError ? "down" : "degraded");

  useEffect(() => {
    if (typeof window !== "undefined") {
      setApiKeyState(localStorage.getItem(API_KEY_STORAGE) ?? "");
    }
  }, []);

  const handleKeyChange = (v: string) => {
    setApiKeyState(v);
    if (typeof window !== "undefined") {
      if (v) localStorage.setItem(API_KEY_STORAGE, v);
      else localStorage.removeItem(API_KEY_STORAGE);
    }
  };

  const handleApply = () => {
    queryClient.invalidateQueries();
  };

  return (
    <header className="glass border-b border-white/5 px-4 py-3 flex items-center gap-4 flex-wrap">
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center justify-center h-9 w-9 rounded-lg bg-white/5 border border-white/10 shrink-0">
          <Activity className="h-5 w-5 text-emerald-400/90" aria-hidden />
        </div>
        <div className="min-w-0">
          <span className="font-semibold text-white/95 block truncate">Sentimeter Dashboard</span>
          <span className="text-xs text-white/50">API status at a glance</span>
        </div>
      </div>
      <div className="h-8 w-px bg-white/10 shrink-0" aria-hidden />
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-white/50 uppercase tracking-wider hidden sm:inline">API</span>
        {health.isLoading ? (
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-white/20 text-xs text-white/60">
            <span className="h-2 w-2 rounded-full bg-white/50 animate-pulse" />
            Checking…
          </div>
        ) : (
          <HealthPill
            status={status}
            coreOk={coreOk}
            coreTotal={coreTotal || 4}
            onRefresh={() => health.refetch()}
            isRefetching={health.isFetching}
          />
        )}
      </div>
      <div className="flex-1 min-w-0" />
      <form
        className="flex items-center gap-2 text-sm opacity-80"
        onSubmit={(e) => {
          e.preventDefault();
          handleApply();
        }}
      >
        <label htmlFor="topbar-api-key">API Key</label>
        <input
          id="topbar-api-key"
          type={reveal ? "text" : "password"}
          value={apiKey}
          onChange={(e) => handleKeyChange(e.target.value)}
          placeholder="Set for authenticated endpoints"
          autoComplete="off"
          className="w-48 px-3 py-1.5 rounded-lg bg-black/20 border border-white/10 outline-none text-sm"
        />
        <button
          type="button"
          onClick={() => setReveal(!reveal)}
          className="text-xs opacity-70 hover:opacity-100"
        >
          {reveal ? "Hide" : "Show"}
        </button>
        <button
          type="submit"
          className="px-2 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-xs"
        >
          Apply
        </button>
      </form>
    </header>
  );
}
