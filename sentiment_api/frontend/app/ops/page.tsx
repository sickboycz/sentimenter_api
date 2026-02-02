"use client";

import React, { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Shell } from "../../components/Shell";
import { apiGet, getDefaultApiKey } from "../../lib/api";

const LOG_SOURCES = ["api", "worker", "daemon"] as const;
type LogSource = (typeof LOG_SOURCES)[number];

const SOURCE_LABELS: Record<LogSource, string> = {
  api: "API",
  worker: "Worker",
  daemon: "Daemon",
};

const SOURCE_COLORS: Record<LogSource, string> = {
  api: "border-l-4 border-l-sky-500 bg-sky-500/10",
  worker: "border-l-4 border-l-emerald-500 bg-emerald-500/10",
  daemon: "border-l-4 border-l-amber-500 bg-amber-500/10",
};

const TAIL = 50;

export default function OpsPage() {
  const apiKey = getDefaultApiKey();
  const [selected, setSelected] = useState<Set<LogSource>>(new Set(LOG_SOURCES));

  const sourcesList = Array.from(selected);
  const sourcesParam = sourcesList.length > 0 ? sourcesList.map((s) => `sources=${encodeURIComponent(s)}`).join("&") : "";
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<any>("/v1/health", apiKey),
  });
  const logs = useQuery({
    queryKey: ["admin-logs", sourcesParam],
    queryFn: () =>
      apiGet<{ data: Record<LogSource, string[]> }>(
        `/v1/admin/logs?tail=${TAIL}&${sourcesParam}`,
        apiKey
      ),
    enabled: selected.size > 0 && !!apiKey,
  });

  const toggle = useCallback((src: LogSource) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(src)) next.delete(src);
      else next.add(src);
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelected(new Set(LOG_SOURCES));
  }, []);

  const selectNone = useCallback(() => {
    setSelected(new Set());
  }, []);

  const refetchLogs = useCallback(() => {
    logs.refetch();
  }, [logs]);

  return (
    <Shell>
      <div className="glass p-4">
        <div className="font-semibold">Ops</div>
        <div className="text-sm opacity-75">System health and logs.</div>
      </div>

      <div className="glass p-4">
        <div className="font-semibold mb-2">API Health</div>
        <pre className="text-xs opacity-85 overflow-auto max-h-48 rounded-lg bg-black/20 p-2">
          {health.data != null ? JSON.stringify(health.data, null, 2) : (health.isLoading ? "Loading…" : "—")}
        </pre>
      </div>

      <div className="glass p-4">
        <div className="flex flex-wrap items-center gap-3 mb-3">
          <span className="font-semibold">Logs</span>
          <span className="text-sm opacity-75">(last {TAIL} lines)</span>
          <div className="flex items-center gap-4">
            {LOG_SOURCES.map((src) => (
              <label key={src} className="flex items-center gap-2 cursor-pointer text-sm">
                <input
                  type="checkbox"
                  checked={selected.has(src)}
                  onChange={() => toggle(src)}
                  className="rounded border-white/30 bg-black/20"
                />
                {SOURCE_LABELS[src]}
              </label>
            ))}
            <button
              type="button"
              onClick={selectAll}
              className="text-xs px-2 py-1 rounded bg-white/10 hover:bg-white/15"
            >
              All
            </button>
            <button
              type="button"
              onClick={selectNone}
              className="text-xs px-2 py-1 rounded bg-white/10 hover:bg-white/15"
            >
              None
            </button>
            <button
              type="button"
              onClick={refetchLogs}
              disabled={selected.size === 0 || logs.isFetching}
              className="text-xs px-3 py-1.5 rounded bg-sky-600 hover:bg-sky-500 disabled:opacity-50 disabled:pointer-events-none"
            >
              {logs.isFetching ? "Refreshing…" : "Refresh"}
            </button>
          </div>
        </div>

        {selected.size === 0 ? (
          <div className="text-sm opacity-60 py-8 text-center rounded-lg border border-dashed border-white/20">
            Select at least one source (API, Worker, Daemon) and click Refresh.
          </div>
        ) : logs.data && "data" in logs.data && typeof logs.data.data === "object" ? (
          <div className="space-y-3">
            {(LOG_SOURCES as readonly string[]).map((src) => {
              if (!selected.has(src as LogSource)) return null;
              const lines = (logs.data as { data: Record<string, string[]> }).data[src] ?? [];
              return (
                <div
                  key={src}
                  className={`rounded-lg overflow-hidden ${SOURCE_COLORS[src as LogSource]}`}
                >
                  <div className="px-3 py-1.5 text-xs font-medium opacity-90 border-b border-white/10">
                    {SOURCE_LABELS[src as LogSource]}
                  </div>
                  <div className="p-2 max-h-64 overflow-auto font-mono text-xs leading-relaxed whitespace-pre break-all">
                    {lines.length === 0 ? (
                      <span className="opacity-60">No log lines yet.</span>
                    ) : (
                      lines.map((line, i) => (
                        <div key={i} className="hover:bg-white/5 px-1 -mx-1 rounded">
                          {line || " "}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : logs.isLoading || logs.isFetching ? (
          <div className="text-sm opacity-60 py-8 text-center">Loading logs…</div>
        ) : logs.error ? (
          <div className="text-sm text-red-300 py-4 rounded-lg bg-red-500/10 border border-red-500/30">
            Failed to load logs. Check API key and CORS.
          </div>
        ) : null}
      </div>

      <div className="glass p-4 text-sm opacity-85">
        <div>Prometheus: http://localhost:9090</div>
        <div>Grafana: http://localhost:3001</div>
      </div>
    </Shell>
  );
}
