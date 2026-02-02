import React from "react";
import { cn } from "@/lib/cn";

export function Badge({
  children,
  tone = "neutral",
  className = ""
}: {
  children: React.ReactNode;
  tone?: "neutral"|"good"|"warn"|"bad";
  className?: string;
}) {
  const cls = tone === "good"
    ? "text-[var(--good)] border-[var(--good)]/25 bg-[var(--good)]/10"
    : tone === "warn"
    ? "text-[var(--warn)] border-[var(--warn)]/25 bg-[var(--warn)]/10"
    : tone === "bad"
    ? "text-[var(--bad)] border-[var(--bad)]/25 bg-[var(--bad)]/10"
    : "text-white/70 border-white/10 bg-white/5";
  return (
    <span className={cn("px-2 py-1 rounded-lg text-[10px] uppercase tracking-wide border", cls, className)}>
      {children}
    </span>
  );
}
