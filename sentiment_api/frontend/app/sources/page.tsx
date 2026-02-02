"use client";

import React from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/Table";
import { useSources } from "@/lib/api/hooks";

export default function SourcesPage() {
  const sources = useSources();

  return (
    <Shell>
      <Card title="Sources" subtitle="Enabled sources with credibility tier and license class." />
      {!sources.data ? (
        <Skeleton className="h-[260px]" />
      ) : (
        <Card title="Registry" subtitle="Snapshot from /v1/sources">
          <Table>
            <THead>
              <TR hover={false}>
                <TH>source_id</TH>
                <TH>name</TH>
                <TH>type</TH>
                <TH>credibility</TH>
                <TH>license</TH>
              </TR>
            </THead>
            <TBody>
              {(sources.data?.sources ?? []).slice(0, 200).map((s: any) => (
                <TR key={s.source_id}>
                  <TD className="font-mono text-xs">{s.source_id}</TD>
                  <TD className="font-medium">{s.name}</TD>
                  <TD className="opacity-80">{s.type}</TD>
                  <TD className="opacity-80">{s.credibility_tier}</TD>
                  <TD className="opacity-80">{s.license_class}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </Card>
      )}
    </Shell>
  );
}
