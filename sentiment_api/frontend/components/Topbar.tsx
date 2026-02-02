"use client";

import React, { useEffect, useMemo, useState } from "react";
import { StatusPill } from "./ui/StatusPill";
import { Button } from "./ui/Button";
import { useHealth, useSources, useImpactTickers } from "@/lib/api/hooks";

function getApiKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("SENTIMETER_API_KEY") || "";
}

export function Topbar() {
  const health = useHealth();
  const sources = useSources();
  const tickers = useImpactTickers();

  const apiStatus = health.data?.status ?? "unknown";
  const ingestionStatus = (sources.data?.sources?.length ?? 0) > 0 ? "ok" : "unknown";
  const allocationStatus = (tickers.data?.winners?.length ?? 0) > 0 ? "ok" : "unknown";

  const [tf, setTf] = useState<"1h" | "6h" | "24h">("24h");
  const [q, setQ] = useState("");
  const [key, setKey] = useState("");

  useEffect(() => setKey(getApiKey()), []);

  const pills = useMemo(() => {
    return [
      { label: "API", status: apiStatus },
      { label: "Ingestion", status: ingestionStatus },
      { label: "Allocation", status: allocationStatus },
      { label: "Research", status: "unknown" }
    ];
  }, [apiStatus, ingestionStatus, allocationStatus]);

  const saveKey = () => {
    localStorage.setItem("SENTIMETER_API_KEY", key.trim());
    window.location.reload();
  };

  return (
    <div className="glass-strong p-3 flex items-center gap-3">
      <div className="flex items-center gap-2">
        <div className="font-semibold">Sentimeter Dashboard</div>
        <div className="text-xs opacity-60">API status at a glance</div>
      </div>

      <div className="flex items-center gap-2 ml-3">
        {pills.map((p) => (
          <StatusPill key={p.label} label={p.label} status={p.status} />
        ))}
      </div>

      <div className="flex-1" />

      <div className="flex items-center gap-2">
        <div className="glass p-1 flex gap-1">
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

        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search clusters, tickers…"
          className="w-[360px] px-3 py-2 rounded-xl bg-black/20 border border-white/10 outline-none"
        />

        <div className="flex items-center gap-2 ml-2">
          <div className="text-xs opacity-70">API Key</div>
          <input
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="paste key"
            className="w-[220px] px-3 py-2 rounded-xl bg-black/20 border border-white/10 outline-none text-sm"
            type="password"
          />
          <Button onClick={saveKey} className="px-3">Apply</Button>
        </div>
      </div>
    </div>
  );
}
