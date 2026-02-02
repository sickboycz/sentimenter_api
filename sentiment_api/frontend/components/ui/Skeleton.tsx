import React from "react";
import { cn } from "@/lib/cn";

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div className={cn("skeleton rounded-xl border border-white/10", className)} />
  );
}
