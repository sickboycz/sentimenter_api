import React from "react";
import { Badge } from "./Badge";
import { cn } from "@/lib/cn";

export function PageHeader({
  title,
  subtitle,
  kicker,
  meta,
  actions,
  className = ""
}: {
  title: string;
  subtitle?: string;
  kicker?: string;
  meta?: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("glass-strong p-3 md:p-4 relative overflow-hidden", className)}>
      <div className="pointer-events-none absolute -top-24 -right-20 h-48 w-48 rounded-full bg-[var(--accent-cyan)]/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-20 -left-16 h-40 w-40 rounded-full bg-[var(--accent-amber)]/10 blur-3xl" />
      <div className="relative">
        <div className="flex flex-wrap items-center gap-3 justify-between">
          <div>
            {kicker && <Badge tone="neutral" className="mb-2">{kicker}</Badge>}
            <div className="font-display text-lg md:text-xl tracking-tight">{title}</div>
            {subtitle && <div className="text-xs opacity-70 mt-1">{subtitle}</div>}
            {meta && <div className="text-xs opacity-60 mt-2">{meta}</div>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      </div>
    </section>
  );
}
