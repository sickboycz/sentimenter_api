"use client";

import React, { useMemo } from "react";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { PageHeader } from "@/components/ui/PageHeader";
import { Gauge } from "@/components/charts/Gauge";
import { LineChartCard } from "@/components/charts/LineChartCard";
import { BarChartCard } from "@/components/charts/BarChartCard";
import { AreaChartCard } from "@/components/charts/AreaChartCard";
import { SectorHeatmap } from "@/components/charts/SectorHeatmap";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/Table";
import { useMoodNow, useIntradayIndex, useImpactMarkets, useImpactSectors, useImpactTickers, useClusters } from "@/lib/api/hooks";

function fmtPct(x: number) {
  return `${Math.round(x * 100)}%`;
}

function CardContent({
  isLoading,
  isError,
  error,
  onRetry,
  children,
  loadingFallback,
}: {
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  onRetry: () => void;
  children: React.ReactNode;
  loadingFallback: React.ReactNode;
}) {
  if (isError) {
    const msg = error instanceof Error ? error.message : "Request failed";
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-6 text-center">
        <p className="text-sm opacity-80">{msg}</p>
        <Button variant="ghost" onClick={onRetry}>Retry</Button>
      </div>
    );
  }
  if (isLoading) return <>{loadingFallback}</>;
  return <>{children}</>;
}

export default function OverviewPage() {
  const mood = useMoodNow();
  const intraday = useIntradayIndex();
  const markets = useImpactMarkets();
  const sectors = useImpactSectors();
  const tickers = useImpactTickers();
  const clusters = useClusters();

  const gaugeValue = useMemo(() => {
    const s = mood.data?.sentiment;
    if (!s) return 0;
    if (s === "RiskOn") return 0.6;
    if (s === "RiskOff") return -0.6;
    if (s === "Neutral") return 0.0;
    return 0.0;
  }, [mood.data?.sentiment]);

  const lineData = useMemo(() => {
    return (intraday.data ?? []).map((p: any) => ({
      t: p.ts.slice(11,16),
      idx: p.index_value,
      vol: p.news_volatility
    }));
  }, [intraday.data]);

  const bars = useMemo(() => {
    // derive a simple volume bar series from intraday
    const pts = (intraday.data ?? []).slice(-24);
    return pts.map((p: any) => ({ t: p.ts.slice(11,16), v: p.news_volume }));
  }, [intraday.data]);

  return (
    <Shell>
      <PageHeader
        title="Overview"
        subtitle="Real-time macro + geopolitical sentiment with market impact context."
        meta="Auto-refreshes every 10–30s depending on panel."
        actions={<Badge tone="good">Live</Badge>}
      />

      {/* Row 1 */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-[var(--grid-gap)]">
        <Card className="xl:col-span-4" title="Sentiment Indicator" subtitle="Health at first sight." right={
          <Badge tone={mood.data?.sentiment === "RiskOff" ? "bad" : mood.data?.sentiment === "RiskOn" ? "good" : "neutral"}>
            {mood.data?.sentiment ?? "—"}
          </Badge>
        }>
          <CardContent
            isLoading={mood.isLoading}
            isError={mood.isError}
            error={mood.error}
            onRetry={() => mood.refetch()}
            loadingFallback={<Skeleton className="h-[210px]" />}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Gauge value={gaugeValue} label="Mood" sublabel={`confidence ${fmtPct(mood.data?.confidence ?? 0)}`} />
              <div className="space-y-2">
                <div className="glass p-3">
                  <div className="text-xs opacity-70">Intraday Index</div>
                  <div className="text-xl font-semibold">{(mood.data?.index_intraday ?? 0).toFixed(2)}</div>
                  <div className="text-xs opacity-70">vol {mood.data?.news_volatility_intraday?.toFixed(2)} • volume {mood.data?.news_volume_intraday}</div>
                </div>
                <div className="glass p-3">
                  <div className="text-xs opacity-70">Risk Vector</div>
                  <div className="text-xs opacity-75">
                    geo {(mood.data?.risk_vector?.geopolitical_risk ?? 0).toFixed(2)} • energy {(mood.data?.risk_vector?.energy_supply_risk ?? 0).toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="xl:col-span-5" title="Intraday Sentiment Index" subtitle="Index vs volatility pressure.">
          <CardContent
            isLoading={intraday.isLoading}
            isError={intraday.isError}
            error={intraday.error}
            onRetry={() => intraday.refetch()}
            loadingFallback={<Skeleton className="h-[210px]" />}
          >
            {lineData.length ? (
              <LineChartCard data={lineData} xKey="t" yKey="idx" y2Key="vol" height={210} />
            ) : (
              <div className="flex items-center justify-center h-[210px] text-sm opacity-60">No index data yet</div>
            )}
          </CardContent>
        </Card>

        <Card className="xl:col-span-3" title="Market Impacts" subtitle="Where the shock concentrates.">
          <CardContent
            isLoading={markets.isLoading}
            isError={markets.isError}
            error={markets.error}
            onRetry={() => markets.refetch()}
            loadingFallback={<Skeleton className="h-[210px]" />}
          >
            <div className="space-y-2 text-sm">
              {(markets.data?.top_markets ?? []).slice(0, 6).map((m: any) => (
                <div key={m.market_id} className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold">{m.label_en}</div>
                    <div className="text-xs opacity-70">{m.expected_direction} • {m.horizon}</div>
                  </div>
                  <div className="text-xs opacity-75">{Math.round(m.magnitude * 100)}%</div>
                </div>
              ))}
              <div className="text-xs opacity-60 mt-2">method {markets.data?.methodology_version}</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 2 */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-[var(--grid-gap)]">
        <Card className="xl:col-span-4" title="Top News Events" subtitle="Volume proxy (last ~24m).">
          <CardContent
            isLoading={intraday.isLoading}
            isError={intraday.isError}
            error={intraday.error}
            onRetry={() => intraday.refetch()}
            loadingFallback={<Skeleton className="h-[180px]" />}
          >
            {bars.length ? (
              <BarChartCard data={bars} xKey="t" yKey="v" height={180} />
            ) : (
              <div className="flex items-center justify-center h-[180px] text-sm opacity-60">No volume data yet</div>
            )}
          </CardContent>
        </Card>

        <Card className="xl:col-span-4" title="Sector Sentiment Performance" subtitle="Ranked heat (top).">
          <CardContent
            isLoading={sectors.isLoading}
            isError={sectors.isError}
            error={sectors.error}
            onRetry={() => sectors.refetch()}
            loadingFallback={<Skeleton className="h-[180px]" />}
          >
            <Table>
              <THead>
                <TR hover={false}>
                  <TH>Sector</TH>
                  <TH className="text-right">Dir</TH>
                  <TH className="text-right">Score</TH>
                  <TH className="text-right">Conf</TH>
                </TR>
              </THead>
              <TBody>
                {(sectors.data?.sectors ?? []).slice(0, 8).map((s: any) => (
                  <TR key={s.sector_id}>
                    <TD className="font-medium">{s.sector_name_en}</TD>
                    <TD className="text-right opacity-80">{s.expected_direction}</TD>
                    <TD className="text-right">{Math.round(s.impact_score)}</TD>
                    <TD className="text-right opacity-80">{fmtPct(s.confidence)}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="xl:col-span-4" title="Sector Heatmap" subtitle="At-a-glance concentration.">
          <CardContent
            isLoading={sectors.isLoading}
            isError={sectors.isError}
            error={sectors.error}
            onRetry={() => sectors.refetch()}
            loadingFallback={<Skeleton className="h-[180px]" />}
          >
            <SectorHeatmap sectors={sectors.data?.sectors ?? []} />
          </CardContent>
        </Card>
      </div>

      {/* Row 3 */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-[var(--grid-gap)]">
        <Card className="xl:col-span-7" title="Sector Impact Trend" subtitle="Impact pressure (demo series).">
          <CardContent
            isLoading={intraday.isLoading}
            isError={intraday.isError}
            error={intraday.error}
            onRetry={() => intraday.refetch()}
            loadingFallback={<Skeleton className="h-[220px]" />}
          >
            {lineData.length ? (
              <AreaChartCard data={lineData} xKey="t" yKey="idx" height={220} />
            ) : (
              <div className="flex items-center justify-center h-[220px] text-sm opacity-60">No trend data yet</div>
            )}
          </CardContent>
        </Card>

        <Card className="xl:col-span-5" title="Top Gainers & Losers" subtitle="Ticker impacts (latest).">
          <CardContent
            isLoading={tickers.isLoading}
            isError={tickers.isError}
            error={tickers.error}
            onRetry={() => tickers.refetch()}
            loadingFallback={<Skeleton className="h-[220px]" />}
          >
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-xs opacity-70 mb-2">Winners</div>
                {(tickers.data?.winners ?? []).slice(0, 10).map((t: any) => (
                  <div key={t.symbol} className="flex justify-between">
                    <span className="font-medium">{t.symbol}</span>
                    <span className="opacity-80">+{Math.round(t.expected_return_bps ?? 0)}</span>
                  </div>
                ))}
              </div>
              <div>
                <div className="text-xs opacity-70 mb-2">Losers</div>
                {(tickers.data?.losers ?? []).slice(0, 10).map((t: any) => (
                  <div key={t.symbol} className="flex justify-between">
                    <span className="font-medium">{t.symbol}</span>
                    <span className="opacity-80">{Math.round(t.expected_return_bps ?? 0)}</span>
                  </div>
                ))}
              </div>
              <div className="col-span-2 text-xs opacity-60 mt-2">method {tickers.data?.methodology_version}</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Row 4 */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-[var(--grid-gap)]">
        <Card className="xl:col-span-12" title="Latest High-Impact Clusters" subtitle="Evidence-first, drilldown on click.">
          <CardContent
            isLoading={clusters.isLoading}
            isError={clusters.isError}
            error={clusters.error}
            onRetry={() => clusters.refetch()}
            loadingFallback={<Skeleton className="h-[180px]" />}
          >
            {(clusters.data ?? []).length === 0 ? (
              <div className="flex items-center justify-center h-[180px] text-sm opacity-60">No clusters yet</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {(clusters.data ?? []).slice(0, 6).map((c: any) => (
                  <a key={c.cluster_id} href={`/clusters/${c.cluster_id}`} className="glass glass-hover p-4 block">
                    <div className="flex items-start justify-between gap-3">
                      <div className="font-semibold leading-snug">{c.headline_en}</div>
                      <Badge tone={c.impact?.expected_direction === "RiskOff" ? "bad" : c.impact?.expected_direction === "RiskOn" ? "good" : "neutral"}>
                        {c.impact?.impact_level} • {c.impact?.expected_direction}
                      </Badge>
                    </div>
                    <div className="text-sm opacity-85 mt-2">
                      {(c.summary_bullets_en ?? []).slice(0, 3).map((b: string, i: number) => (
                        <div key={i}>• {b}</div>
                      ))}
                    </div>
                    <div className="text-xs opacity-70 mt-2">
                      {c.source_count} sources • conf {fmtPct(c.impact?.confidence ?? 0)}
                    </div>
                  </a>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Shell>
  );
}
