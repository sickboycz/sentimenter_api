import React from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex">
      <Sidebar />
      <main className="flex-1 p-3 lg:p-4">
        <div className="relative max-w-[1080px] w-full mx-auto space-y-3">
          <div className="pointer-events-none absolute -top-24 -right-20 h-56 w-56 rounded-full bg-[var(--accent-violet)]/10 blur-3xl" />
          <Topbar />
          {children}
        </div>
      </main>
    </div>
  );
}
