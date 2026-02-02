"use client";

import React, { createContext, useContext, useState } from "react";

export type Timeframe = "1h" | "6h" | "24h";

const TimeframeContext = createContext<{
  timeframe: Timeframe;
  setTimeframe: (t: Timeframe) => void;
} | null>(null);

export function TimeframeProvider({ children }: { children: React.ReactNode }) {
  const [timeframe, setTimeframe] = useState<Timeframe>("24h");
  return (
    <TimeframeContext.Provider value={{ timeframe, setTimeframe }}>
      {children}
    </TimeframeContext.Provider>
  );
}

export function useTimeframe() {
  const ctx = useContext(TimeframeContext);
  return ctx ?? { timeframe: "24h" as Timeframe, setTimeframe: () => {} };
}
