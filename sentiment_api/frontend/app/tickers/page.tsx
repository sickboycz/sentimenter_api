"use client";

import React from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/Table";
import { useImpactTickers } from "@/lib/api/hooks";

export default function TickersPage() {
  const tickers = useImpactTickers();

  return (
    <Shell>
      <Card title="Tickers" subtitle="Winners/Losers with explainable rationale." />

      {!tickers.data ? (
        <Skeleton className="h-[260px]" />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-[var(--grid-gap)]">
          <Card title="Winners" subtitle={`method ${tickers.data?.methodology_version}`}>
            <Table>
              <THead>
                <TR hover={false}>
                  <TH>Ticker</TH>
                  <TH className="text-right">bps</TH>
                  <TH className="text-right">conf</TH>
                </TR>
              </THead>
              <TBody>
                {(tickers.data?.winners ?? []).slice(0, 25).map((t: any) => (
                  <TR key={t.symbol}>
                    <TD className="font-medium">{t.symbol}</TD>
                    <TD className="text-right">+{Math.round(t.expected_return_bps)}</TD>
                    <TD className="text-right opacity-80">{Math.round(t.confidence * 100)}%</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </Card>

          <Card title="Losers" subtitle="Highest negative impact">
            <Table>
              <THead>
                <TR hover={false}>
                  <TH>Ticker</TH>
                  <TH className="text-right">bps</TH>
                  <TH className="text-right">conf</TH>
                </TR>
              </THead>
              <TBody>
                {(tickers.data?.losers ?? []).slice(0, 25).map((t: any) => (
                  <TR key={t.symbol}>
                    <TD className="font-medium">{t.symbol}</TD>
                    <TD className="text-right">{Math.round(t.expected_return_bps)}</TD>
                    <TD className="text-right opacity-80">{Math.round(t.confidence * 100)}%</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </Card>
        </div>
      )}
    </Shell>
  );
}
