"use client";

import React, { useMemo, useState } from "react";
import { StatusPill } from "./ui/StatusPill";
import { useHealth } from "../lib/api/hooks";

export function Topbar() {
  const health = useHealth();
  const apiStatus = health.data?.data?.status ?? "unknown";

  const [q, setQ] = useState("");
  const [tf, setTf] = useState<"1h" | "6h" | "24h">("24h");

  const pills = useMemo(() => {
    return [
      { label: "API", status: apiStatus },
      { label: "Ingestion", status: "unknown" },
      { label: "Allocation", status: "unknown" },
      { label: "Research", status: "unknown" },
    ];
  }, [apiStatus]);

  return (
    <div className="glass p-3 flex items-center gap-3">
      <div className="font-semibold">Sentimeter Dashboard</div>

      <div className="flex items-center gap-2 ml-2">
        {pills.map((p) => (
          <StatusPill key={p.label} label={p.label} status={p.status} />
        ))}
      </div>

      <div className="flex-1" />

      <div className="flex items-center gap-2">
        <div className="glass p-1 flex gap-1">
          {(["1h", "6h", "24h"] as const).map((t) => (
            <button
              key={t}
              className={`px-2 py-1 rounded-lg text-xs ${tf === t ? "bg-white/10" : "opacity-70"}`}
              onClick={() => setTf(t)}
              title="Timeframe (frontend-only state)"
            >
              {t}
            </button>
          ))}
        </div>

        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search clusters, tickers, topics…"
          className="w-[420px] max-w-full px-3 py-2 rounded-xl bg-black/20 border border-white/10 outline-none"
        />
        <button className="px-3 py-2 rounded-xl bg-white/10 hover:bg-white/15 border border-white/10 text-sm">
          Search
        </button>
      </div>
    </div>
  );
}
