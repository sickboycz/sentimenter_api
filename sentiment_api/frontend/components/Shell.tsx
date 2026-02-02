import React from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex">
      <Sidebar />
      <main className="flex-1 p-4 lg:p-6 space-y-4">
        <Topbar />
        {children}
      </main>
    </div>
  );
}
