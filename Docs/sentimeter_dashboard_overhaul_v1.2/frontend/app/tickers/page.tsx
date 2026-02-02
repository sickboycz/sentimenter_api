"use client";

import React from "react";
import { Shell } from "../../components/Shell";
import { Card } from "../../components/ui/Card";
import { useImpactTickers } from "../../lib/api/hooks";

export default function TickersPage() {
  const tickers = useImpactTickers();

  return (
    <Shell>
      <Card title="Tickers" subtitle="Winners/Losers across the configured universes.">
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 text-sm">
          <div className="glass p-4">
            <div className="font-semibold mb-2">Winners</div>
            {(tickers.data?.data?.winners ?? []).slice(0, 40).map((t: any) => (
              <div key={t.symbol} className="flex justify-between">
                <span>{t.symbol}</span>
                <span className="opacity-75">+{Math.round(t.expected_return_bps)} • {Math.round(t.confidence * 100)}%</span>
              </div>
            ))}
          </div>
          <div className="glass p-4">
            <div className="font-semibold mb-2">Losers</div>
            {(tickers.data?.data?.losers ?? []).slice(0, 40).map((t: any) => (
              <div key={t.symbol} className="flex justify-between">
                <span>{t.symbol}</span>
                <span className="opacity-75">{Math.round(t.expected_return_bps)} • {Math.round(t.confidence * 100)}%</span>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </Shell>
  );
}
