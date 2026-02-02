"use client";

import React, { createContext, useCallback, useContext, useState } from "react";

type TickerDetailContextValue = {
  selectedSymbol: string | null;
  openTickerDetail: (symbol: string) => void;
  closeTickerDetail: () => void;
};

const TickerDetailContext = createContext<TickerDetailContextValue | null>(null);

export function TickerDetailProvider({ children }: { children: React.ReactNode }) {
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const openTickerDetail = useCallback((symbol: string) => setSelectedSymbol(symbol?.trim() || null), []);
  const closeTickerDetail = useCallback(() => setSelectedSymbol(null), []);
  return (
    <TickerDetailContext.Provider value={{ selectedSymbol, openTickerDetail, closeTickerDetail }}>
      {children}
    </TickerDetailContext.Provider>
  );
}

export function useTickerDetail() {
  const ctx = useContext(TickerDetailContext);
  return ctx;
}
