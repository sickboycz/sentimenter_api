"use client";

import React, { useState } from "react";

export function Topbar() {
  const [q, setQ] = useState("");

  return (
    <div className="glass p-3 flex items-center gap-3">
      <div className="font-semibold">Sentimeter Dashboard</div>
      <div className="flex-1" />
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
  );
}
