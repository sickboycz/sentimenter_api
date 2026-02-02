"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, RefreshCw } from "lucide-react";
import { StatusPill } from "./ui/StatusPill";
import { useTimeframe } from "../contexts/TimeframeContext";

const API_KEY_STORAGE = "sentiment_api_key";

type HealthStatus = "ok" | "degraded" | "down";

export function Topbar() {
  const queryClient = useQueryClient();
  const [apiKey, setApiKeyState] = useState("");
  const [reveal, setReveal] = useState(false);

  const statusQuery = useQuery({
    queryKey: ["status-topbar"],
    queryFn: async () => {
      const base = typeof window !== "undefined" && !process.env.NEXT_PUBLIC_API_BASE_URL
        ? `${window.location.protocol}//${window.location.hostname}:8080`
        : (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080");
      const res = await fetch(`${base}/v1/status`, { cache: "no-store" });
      if (!res.ok) throw new Error("Status check failed");
      return res.json() as Promise<{ api: string; ingestion: string; allocation: string; research: string }>;
    },
    refetchInterval: 30_000,
    retry: 1,
    staleTime: 20_000,
  });

  const status = statusQuery.data;
  const apiStatus = (status?.api as HealthStatus) ?? (statusQuery.isError ? "down" : "degraded");
  const { timeframe, setTimeframe } = useTimeframe();
  const [q, setQ] = useState("");

  const pills = useMemo(
    () => [
      { label: "API", status: apiStatus },
      { label: "Ingestion", status: (status?.ingestion ?? "unknown") as string },
      { label: "Allocation", status: (status?.allocation ?? "unknown") as string },
      { label: "Research", status: (status?.research ?? "unknown") as string },
    ],
    [apiStatus, status?.ingestion, status?.allocation, status?.research]
  );

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
      <div className="flex items-center gap-2 shrink-0 flex-wrap">
        {pills.map((p) => (
          <StatusPill
            key={p.label}
            label={p.label}
            status={p.label === "API" && statusQuery.isLoading ? "unknown" : p.status}
          />
        ))}
        <button
          type="button"
          onClick={() => statusQuery.refetch()}
          disabled={statusQuery.isFetching}
          className="ml-0.5 p-1 rounded opacity-70 hover:opacity-100 disabled:opacity-50"
          title="Refresh API health"
          aria-label="Refresh API health"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${statusQuery.isFetching ? "animate-spin" : ""}`} />
        </button>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <div className="glass p-1 flex gap-1">
          {(["1h", "6h", "24h"] as const).map((t) => (
            <button
              key={t}
              type="button"
              className={`px-2 py-1 rounded-lg text-xs ${timeframe === t ? "bg-white/10" : "opacity-70 hover:opacity-100"}`}
              onClick={() => setTimeframe(t)}
              title={`Timeframe: ${t}`}
              aria-pressed={timeframe === t}
            >
              {t}
            </button>
          ))}
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search clusters, tickers…"
          className="w-64 max-w-full px-3 py-2 rounded-xl bg-black/20 border border-white/10 outline-none text-sm hidden md:block"
          aria-label="Global search"
        />
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
