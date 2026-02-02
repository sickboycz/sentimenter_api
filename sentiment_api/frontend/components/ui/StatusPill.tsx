"use client";

import React from "react";

function color(status: string): string {
  if (status === "ok") return "text-[var(--good)] border-[var(--good)]/30 bg-[var(--good)]/10";
  if (status === "degraded") return "text-[var(--warn)] border-[var(--warn)]/30 bg-[var(--warn)]/10";
  if (status === "down") return "text-[var(--bad)] border-[var(--bad)]/30 bg-[var(--bad)]/10";
  return "text-white/70 border-white/10 bg-white/5";
}

export function StatusPill({ label, status }: { label: string; status: string }) {
  return (
    <span className={`px-2 py-1 rounded-lg text-xs border font-medium ${color(status)}`}>
      {label}: {status}
    </span>
  );
}
