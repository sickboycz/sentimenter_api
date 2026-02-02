"use client";

import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSSE } from "../lib/useSSE";

const client = new QueryClient();

function SSEBridge() {
  useSSE(true);
  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={client}>
      <SSEBridge />
      {children}
    </QueryClientProvider>
  );
}
