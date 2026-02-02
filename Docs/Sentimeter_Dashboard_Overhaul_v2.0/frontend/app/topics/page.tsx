"use client";

import React, { useMemo } from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { LineChartCard } from "@/components/charts/LineChartCard";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/Table";
import { useTopicsIndex } from "@/lib/api/hooks";

export default function TopicsPage() {
  const topics = useTopicsIndex();

  const series = useMemo(() => {
    const pts = topics.data?.data?.points ?? [];
    // compress: show last 60 points
    return pts.slice(-60).map((p: any) => ({ t: p.ts.slice(11,16), v: p.index_value }));
  }, [topics.data]);

  return (
    <Shell>
      <Card title="Topics" subtitle="Topic indices (Moodix-style) — what drives the tape." />

      {!topics.data ? (
        <Skeleton className="h-[260px]" />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-[var(--grid-gap)]">
          <Card className="xl:col-span-7" title="Topic Index (last points)" subtitle="Aggregate view (demo line).">
            <LineChartCard data={series} xKey="t" yKey="v" height={220} />
          </Card>

          <Card className="xl:col-span-5" title="Top Topic Points" subtitle="Recent measurements (table).">
            <Table>
              <THead>
                <TR hover={false}>
                  <TH>Topic</TH>
                  <TH className="text-right">sentiment</TH>
                  <TH className="text-right">value</TH>
                  <TH className="text-right">vol</TH>
                </TR>
              </THead>
              <TBody>
                {(topics.data.data.points ?? []).slice(-15).reverse().map((p: any, i: number) => (
                  <TR key={i}>
                    <TD className="font-medium">{p.topic_name_en}</TD>
                    <TD className="text-right opacity-80">{p.sentiment}</TD>
                    <TD className="text-right">{Math.round(p.index_value * 100) / 100}</TD>
                    <TD className="text-right opacity-80">{p.news_volume}</TD>
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
