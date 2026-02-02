"use client";

import React from "react";
import { TickerDetailProvider, useTickerDetail } from "../contexts/TickerDetailContext";
import { CompanyDetailModal } from "./CompanyDetailModal";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

function ShellInner({ children }: { children: React.ReactNode }) {
  const { selectedSymbol, closeTickerDetail } = useTickerDetail() ?? {};
  return (
    <>
      <div className="min-h-screen flex">
        <Sidebar />
        <div className="flex-1 p-4 md:p-6 space-y-4">
          <Topbar />
          {children}
        </div>
      </div>
      <CompanyDetailModal symbol={selectedSymbol ?? null} onClose={closeTickerDetail ?? (() => {})} />
    </>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <TickerDetailProvider>
      <ShellInner>{children}</ShellInner>
    </TickerDetailProvider>
  );
}
