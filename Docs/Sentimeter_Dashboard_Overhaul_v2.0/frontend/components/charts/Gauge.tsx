"use client";

import React from "react";

export function Gauge({
  value,
  label,
  sublabel
}: {
  value: number; // -1..+1
  label: string;
  sublabel?: string;
}) {
  const v = Math.max(-1, Math.min(1, value));
  const pct = (v + 1) / 2; // 0..1
  const angle = -90 + pct * 180;

  return (
    <div className="relative">
      <div className="flex items-center justify-between">
        <div className="text-sm opacity-70">{label}</div>
        <div className="text-xs opacity-60">{sublabel ?? ""}</div>
      </div>

      <div className="mt-3 relative h-[120px]">
        <svg viewBox="0 0 200 120" className="w-full h-full">
          <defs>
            <linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor="rgba(255,95,110,1)" />
              <stop offset="0.5" stopColor="rgba(255,195,80,1)" />
              <stop offset="1" stopColor="rgba(70,220,160,1)" />
            </linearGradient>
          </defs>
          <path d="M20 110 A80 80 0 0 1 180 110" stroke="rgba(255,255,255,0.08)" strokeWidth="18" fill="none" />
          <path d="M20 110 A80 80 0 0 1 180 110" stroke="url(#gaugeGrad)" strokeWidth="10" fill="none" strokeLinecap="round" />
          <circle cx="100" cy="110" r="6" fill="rgba(255,255,255,0.65)" />
          <g transform={`rotate(${angle} 100 110)`}>
            <line x1="100" y1="110" x2="165" y2="110" stroke="rgba(230,234,242,0.9)" strokeWidth="3" strokeLinecap="round" />
          </g>
        </svg>

        <div className="absolute inset-x-0 bottom-0 text-center">
          <div className="text-2xl font-semibold">
            {v > 0.25 ? "RiskOn" : v < -0.25 ? "RiskOff" : "Neutral"}
          </div>
          <div className="text-xs opacity-70">score {v.toFixed(2)}</div>
        </div>
      </div>
    </div>
  );
}
