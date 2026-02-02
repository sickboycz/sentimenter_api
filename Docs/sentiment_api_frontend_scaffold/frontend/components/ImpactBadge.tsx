import React from "react";

export function ImpactBadge({ level, direction }: { level: string; direction: string }) {
  const dir = direction ?? "Unknown";
  return (
    <span className="px-2 py-1 rounded-lg text-xs bg-white/10 border border-white/10">
      {level} • {dir}
    </span>
  );
}
