"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Crosshair, LockKeyhole, Pause, RadioTower, Shield } from "lucide-react";

import { KpiCard } from "@/components/kpi/kpi-card";
import {
  buildApiUrl,
  type DailyDigestArtifactResponse,
  type DailyDigestPreviewResponse,
  type DailyDigestSeriesPointResponse,
  type DashboardSummaryResponse,
  type ExecutionIntentResponse,
  type LiquidityPointResponse,
  type MarketStreamStatusResponse,
  type OrderBookResponse,
  type UserStreamStatusResponse,
  getBybitUserStreamStatus,
  getDailyDigestPreview,
  getDashboardSummary,
  getExecutionIntents,
  getLiquidityHistory,
  getMarketStreamStatus,
  getOrderbook,
  listDailyDigestArtifacts,
  listDailyDigestRunsFiltered,
  listDailyDigestSeriesFiltered,
  runDailyDigest
} from "@/lib/api";

type DashboardState = {
  summary: DashboardSummaryResponse | null;
  digests: DailyDigestArtifactResponse[];
  digestRuns: DailyDigestArtifactResponse[];
  digestSeries: DailyDigestSeriesPointResponse[];
  marketStream: MarketStreamStatusResponse | null;
  userStream: UserStreamStatusResponse | null;
  orderbook: OrderBookResponse | null;
  liquidityHistory: LiquidityPointResponse[];
  intents: ExecutionIntentResponse[];
  error: string | null;
  updatedAt: string | null;
};

const DIGEST_RANGE_OPTIONS = [7, 30, 90] as const;
const DIGEST_COMPARE_OPTIONS = ["fills", "lineage_alerts", "top_strategy_pnl"] as const;

function Panel({
  title,
  action,
  children,
  className = ""
}: {
  title: string;
  action?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`market-panel scanline rounded ${className}`}>
      <div className="flex h-10 items-center justify-between border-b border-white/10 px-3">
        <h2 className="font-mono text-[11px] uppercase text-secondary">{title}</h2>
        {action ? <span className="font-mono text-[10px] uppercase text-muted">{action}</span> : null}
      </div>
      <div className="p-3">{children}</div>
    </section>
  );
}

function formatNumber(value: number | string | null | undefined, digits = 2) {
  if (value === null || value === undefined) {
    return "--";
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return "--";
  }
  return parsed.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}

function formatCompact(value: number | string | null | undefined) {
  if (value === null || value === undefined) {
    return "--";
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return "--";
  }
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 2
  }).format(parsed);
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "--";
  }
  return new Date(value).toLocaleTimeString("en-GB", {
    hour12: false,
    timeZone: "UTC"
  });
}

function buildSparkPath(points: LiquidityPointResponse[]) {
  if (points.length === 0) {
    return "";
  }
  const values = points
    .map((point) => Number(point.metrics.mid_price ?? point.metrics.best_bid ?? 0))
    .filter((value) => Number.isFinite(value) && value > 0);
  if (values.length === 0) {
    return "";
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || 1;
  return values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * 900;
      const y = 240 - ((value - min) / spread) * 170;
      return `${index === 0 ? "M" : "L"}${x} ${y}`;
    })
    .join(" ");
}

function buildMetricSparkPath(values: number[], width = 320, height = 82) {
  const filtered = values.filter((value) => Number.isFinite(value));
  if (filtered.length === 0) {
    return "";
  }
  const min = Math.min(...filtered);
  const max = Math.max(...filtered);
  const spread = max - min || 1;
  return filtered
    .map((value, index) => {
      const x = (index / Math.max(filtered.length - 1, 1)) * width;
      const y = height - ((value - min) / spread) * Math.max(height - 18, 1);
      return `${index === 0 ? "M" : "L"}${x} ${y}`;
    })
    .join(" ");
}

function buildFlagMarkers(points: DailyDigestSeriesPointResponse[], width = 320, height = 100) {
  if (points.length === 0) {
    return [];
  }
  const anomalyValues = points.map((point) => point.anomaly_score);
  const min = Math.min(...anomalyValues);
  const max = Math.max(...anomalyValues);
  const spread = max - min || 1;
  return points
    .map((point, index) => {
      if (point.anomaly_score <= 0) {
        return null;
      }
      const x = (index / Math.max(points.length - 1, 1)) * width;
      const y = height - ((point.anomaly_score - min) / spread) * Math.max(height - 18, 1);
      const tone = point.anomaly_flags.includes("negative_top_strategy_pnl")
        ? "#ef4444"
        : point.anomaly_flags.includes("high_lineage_alerts")
          ? "#49c6ff"
          : "#f59e0b";
      return { x, y, tone, flags: point.anomaly_flags, reportDate: point.report_date };
    })
    .filter((point): point is { x: number; y: number; tone: string; flags: string[]; reportDate: string } => point !== null);
}

function exportCsv(path: string) {
  window.open(buildApiUrl(path), "_blank", "noopener,noreferrer");
}

function exportDigestSeriesCsv(options: {
  days?: number;
  startAt?: string;
  endAt?: string;
  flaggedOnly?: boolean;
}) {
  const params = new URLSearchParams({ limit: "365" });
  if (options.days) {
    params.set("days", String(options.days));
  }
  if (options.startAt) {
    params.set("start_at", options.startAt);
  }
  if (options.endAt) {
    params.set("end_at", options.endAt);
  }
  if (options.flaggedOnly) {
    params.set("flagged_only", "true");
  }
  window.open(buildApiUrl("/reports/daily-digest/series/export", params), "_blank", "noopener,noreferrer");
}

export default function DashboardPage() {
  const [digestRangeDays, setDigestRangeDays] = useState<(typeof DIGEST_RANGE_OPTIONS)[number]>(30);
  const [digestCompareMetric, setDigestCompareMetric] = useState<(typeof DIGEST_COMPARE_OPTIONS)[number]>("fills");
  const [digestStartAt, setDigestStartAt] = useState("");
  const [digestEndAt, setDigestEndAt] = useState("");
  const [digestFlaggedOnly, setDigestFlaggedOnly] = useState(false);
  const [selectedDigestReportDate, setSelectedDigestReportDate] = useState<string | null>(null);
  const [selectedDigestPreview, setSelectedDigestPreview] = useState<DailyDigestPreviewResponse | null>(null);
  const [selectedDigestPreviewError, setSelectedDigestPreviewError] = useState<string | null>(null);
  const [selectedDigestPreviewLoading, setSelectedDigestPreviewLoading] = useState(false);
  const [state, setState] = useState<DashboardState>({
    summary: null,
    digests: [],
    digestRuns: [],
    digestSeries: [],
    marketStream: null,
    userStream: null,
    orderbook: null,
    liquidityHistory: [],
    intents: [],
    error: null,
    updatedAt: null
  });

  useEffect(() => {
    let active = true;

    const load = async () => {
      const digestSeriesRequest =
        digestStartAt || digestEndAt
          ? listDailyDigestSeriesFiltered({
              startAt: digestStartAt || undefined,
              endAt: digestEndAt || undefined,
              flaggedOnly: digestFlaggedOnly,
              limit: 365
            })
          : listDailyDigestSeriesFiltered({ days: digestRangeDays, flaggedOnly: digestFlaggedOnly, limit: 365 });
      const digestRunsRequest =
        digestStartAt || digestEndAt
          ? listDailyDigestRunsFiltered({
              startAt: digestStartAt || undefined,
              endAt: digestEndAt || undefined,
              flaggedOnly: digestFlaggedOnly,
              limit: 365
            })
          : listDailyDigestRunsFiltered({ days: digestRangeDays, flaggedOnly: digestFlaggedOnly, limit: 365 });
      try {
        const [summaryResult, marketStreamResult, userStreamResult, orderbookResult, liquidityHistoryResult, intentsResult, digestsResult, digestSeriesResult, digestRunsResult] = await Promise.allSettled([
          getDashboardSummary(),
          getMarketStreamStatus(),
          getBybitUserStreamStatus(),
          getOrderbook("BTCUSDT", 7),
          getLiquidityHistory("BTCUSDT", 24),
          getExecutionIntents(8),
          listDailyDigestArtifacts(6),
          digestSeriesRequest,
          digestRunsRequest
        ]);
        if (!active) {
          return;
        }
        if (summaryResult.status !== "fulfilled") {
          throw summaryResult.reason;
        }
        setState({
          summary: summaryResult.value,
          digests: digestsResult.status === "fulfilled" ? digestsResult.value : [],
          digestRuns: digestRunsResult.status === "fulfilled" ? digestRunsResult.value : [],
          digestSeries: digestSeriesResult.status === "fulfilled" ? digestSeriesResult.value : [],
          marketStream: marketStreamResult.status === "fulfilled" ? marketStreamResult.value : null,
          userStream: userStreamResult.status === "fulfilled" ? userStreamResult.value : null,
          orderbook: orderbookResult.status === "fulfilled" ? orderbookResult.value : null,
          liquidityHistory: liquidityHistoryResult.status === "fulfilled" ? liquidityHistoryResult.value : [],
          intents: intentsResult.status === "fulfilled" ? intentsResult.value : [],
          error: null,
          updatedAt: new Date().toISOString()
        });
      } catch (error) {
        if (!active) {
          return;
        }
        setState((current) => ({
          ...current,
          error: error instanceof Error ? error.message : "dashboard load failed",
          updatedAt: new Date().toISOString()
        }));
      }
    };

    void load();
    const timer = window.setInterval(() => {
      void load();
    }, 15000);

    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [digestRangeDays, digestStartAt, digestEndAt, digestFlaggedOnly]);

  useEffect(() => {
    const reportDate =
      selectedDigestReportDate ??
      state.digestRuns[0]?.report_date ??
      null;
    if (!reportDate) {
      setSelectedDigestPreview(null);
      setSelectedDigestPreviewError(null);
      setSelectedDigestPreviewLoading(false);
      return;
    }

    let active = true;
    setSelectedDigestPreviewLoading(true);
    setSelectedDigestPreviewError(null);

    void getDailyDigestPreview(reportDate)
      .then((preview) => {
        if (!active) {
          return;
        }
        setSelectedDigestPreview(preview);
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        setSelectedDigestPreview(null);
        setSelectedDigestPreviewError(error instanceof Error ? error.message : "digest preview load failed");
      })
      .finally(() => {
        if (!active) {
          return;
        }
        setSelectedDigestPreviewLoading(false);
      });

    return () => {
      active = false;
    };
  }, [selectedDigestReportDate, state.digestRuns]);

  const triggerDailyDigest = async () => {
    await runDailyDigest();
    const digestSeriesRequest =
      digestStartAt || digestEndAt
        ? listDailyDigestSeriesFiltered({
            startAt: digestStartAt || undefined,
            endAt: digestEndAt || undefined,
            flaggedOnly: digestFlaggedOnly,
            limit: 365
          })
        : listDailyDigestSeriesFiltered({ days: digestRangeDays, flaggedOnly: digestFlaggedOnly, limit: 365 });
    const digestRunsRequest =
      digestStartAt || digestEndAt
        ? listDailyDigestRunsFiltered({
            startAt: digestStartAt || undefined,
            endAt: digestEndAt || undefined,
            flaggedOnly: digestFlaggedOnly,
            limit: 365
          })
        : listDailyDigestRunsFiltered({ days: digestRangeDays, flaggedOnly: digestFlaggedOnly, limit: 365 });
    const [digests, digestSeries, digestRuns] = await Promise.all([listDailyDigestArtifacts(6), digestSeriesRequest, digestRunsRequest]);
    setState((current) => ({
      ...current,
      digests,
      digestRuns,
      digestSeries,
      updatedAt: new Date().toISOString()
    }));
  };

  const summary = state.summary;
  const marketStream = state.marketStream;
  const userStream = state.userStream;
  const orderbook = state.orderbook;
  const sparkPath = buildSparkPath(state.liquidityHistory);
  const executionCounts = summary?.execution_counts ?? {};
  const activeIntents = (executionCounts.approved ?? 0) + (executionCounts.dispatching ?? 0);
  const utcNow = new Date().toLocaleTimeString("en-GB", { hour12: false, timeZone: "UTC" });
  const digestAlert = summary?.digest_alert ?? null;
  const anomalySparkPath = buildMetricSparkPath(state.digestSeries.map((point) => point.anomaly_score));
  const fillsSparkPath = buildMetricSparkPath(state.digestSeries.map((point) => point.fills_count));
  const lineageSparkPath = buildMetricSparkPath(state.digestSeries.map((point) => point.lineage_alerts_count));
  const topPnlSparkPath = buildMetricSparkPath(
    state.digestSeries.map((point) => Number(point.top_strategy_realized_pnl_usd ?? 0))
  );
  const anomalyOverlayPath = buildMetricSparkPath(state.digestSeries.map((point) => point.anomaly_score), 320, 100);
  const compareOverlayPath =
    digestCompareMetric === "fills"
      ? buildMetricSparkPath(state.digestSeries.map((point) => point.fills_count), 320, 100)
      : digestCompareMetric === "lineage_alerts"
        ? buildMetricSparkPath(state.digestSeries.map((point) => point.lineage_alerts_count), 320, 100)
        : buildMetricSparkPath(state.digestSeries.map((point) => Number(point.top_strategy_realized_pnl_usd ?? 0)), 320, 100);
  const digestCompareConfig =
    digestCompareMetric === "fills"
      ? { label: "Fills", path: fillsSparkPath, tone: "#22f5a5" }
      : digestCompareMetric === "lineage_alerts"
        ? { label: "Lineage Alerts", path: lineageSparkPath, tone: "#49c6ff" }
        : { label: "Top Strategy PnL", path: topPnlSparkPath, tone: "#ef4444" };
  const digestCompareValues =
    digestCompareMetric === "fills"
      ? state.digestSeries.map((point) => point.fills_count)
      : digestCompareMetric === "lineage_alerts"
        ? state.digestSeries.map((point) => point.lineage_alerts_count)
        : state.digestSeries.map((point) => Number(point.top_strategy_realized_pnl_usd ?? 0));
  const avgAnomaly =
    state.digestSeries.length > 0
      ? state.digestSeries.reduce((sum, point) => sum + point.anomaly_score, 0) / state.digestSeries.length
      : 0;
  const avgCompareValue =
    digestCompareValues.length > 0
      ? digestCompareValues.reduce((sum, value) => sum + value, 0) / digestCompareValues.length
      : 0;
  const flaggedDaysCount = state.digestSeries.filter((point) => point.anomaly_score > 0).length;
  const worstTopStrategyPnl =
    state.digestSeries.length > 0
      ? Math.min(...state.digestSeries.map((point) => Number(point.top_strategy_realized_pnl_usd ?? 0)))
      : 0;
  const flagMarkers = buildFlagMarkers(state.digestSeries);
  const zeroFillsDays = state.digestSeries.filter((point) => point.anomaly_flags.includes("zero_fills")).length;
  const negativePnlDays = state.digestSeries.filter((point) => point.anomaly_flags.includes("negative_top_strategy_pnl")).length;
  const highAlertDays = state.digestSeries.filter((point) => point.anomaly_flags.includes("high_lineage_alerts")).length;
  const selectedDigestRun =
    state.digestRuns.find((run) => run.report_date === selectedDigestReportDate) ??
    state.digestRuns[0] ??
    null;

  const riskRows = [
    {
      label: "Market stream",
      status: marketStream?.running ? "RUNNING" : "STOPPED",
      tone: marketStream?.running ? "text-profit" : "text-loss",
      Icon: RadioTower
    },
    {
      label: "Execution venue feed",
      status: userStream?.subscribed ? "SYNCED" : userStream?.running ? "CONNECTING" : "IDLE",
      tone: userStream?.subscribed ? "text-profit" : userStream?.running ? "text-warning" : "text-secondary",
      Icon: RadioTower
    },
    {
      label: "Queue pressure",
      status: `${activeIntents} ACTIVE`,
      tone: activeIntents > 0 ? "text-warning" : "text-profit",
      Icon: Crosshair
    },
    {
      label: "Strategy gate",
      status: summary?.bot_status ?? "UNKNOWN",
      tone: summary?.bot_status === "RUNNING" ? "text-profit" : "text-warning",
      Icon: Shield
    },
    {
      label: "Hard limits",
      status: "IMMUTABLE",
      tone: "text-cyan",
      Icon: LockKeyhole
    },
    {
      label: "Execution sync",
      status: summary?.execution_status ?? "IDLE",
      tone: userStream?.subscribed ? "text-profit" : "text-warning",
      Icon: Pause
    }
  ];

  return (
    <div className="space-y-3">
      <div className="grid gap-3 xl:grid-cols-[1fr_360px]">
        <div className="market-panel rounded px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="font-mono text-[11px] uppercase text-muted">
                Command Deck / {summary?.bot_status ?? "BOOTSTRAP"}
              </div>
              <h1 className="mt-1 text-2xl font-semibold tracking-normal">Execution and Microstructure Deck</h1>
            </div>
            <div className="flex flex-wrap gap-2 font-mono text-[11px]">
              <span className="rounded border border-profit/30 bg-profit/10 px-2 py-1 text-profit">
                MARKET {marketStream?.running ? "ONLINE" : "OFFLINE"}
              </span>
              <span className="rounded border border-cyan/30 bg-cyan/10 px-2 py-1 text-cyan">
                REGIME {summary?.market_regime ?? "UNKNOWN"}
              </span>
              <span className="rounded border border-warning/30 bg-warning/10 px-2 py-1 text-warning">
                EXEC {summary?.execution_status ?? "IDLE"}
              </span>
            </div>
          </div>
          {state.error ? (
            <div className="mt-3 rounded border border-loss/30 bg-loss/10 px-3 py-2 font-mono text-[11px] text-loss">
              {state.error}
            </div>
          ) : null}
        </div>
        <div className="market-panel rounded px-4 py-3">
          <div className="grid grid-cols-3 gap-3 font-mono text-[11px]">
            <div>
              <div className="text-muted">UTC</div>
              <div className="mt-1 text-primary">{utcNow}</div>
            </div>
            <div>
              <div className="text-muted">BTCUSDT SPREAD</div>
              <div className="mt-1 text-profit">
                {formatNumber(summary?.focus_liquidity?.spread_bps, 2)} bps
              </div>
            </div>
            <div>
              <div className="text-muted">UPDATED</div>
              <div className="mt-1 text-warning">{formatTimestamp(state.updatedAt)}</div>
            </div>
          </div>
        </div>
      </div>

      {digestAlert ? (
        <div className="rounded border border-warning/30 bg-warning/10 px-4 py-3 font-mono text-xs text-warning">
          <div className="flex flex-wrap items-center gap-2">
            <AlertTriangle size={14} />
            <span>
              Digest anomaly {digestAlert.report_date}: score {digestAlert.anomaly_score}
            </span>
          </div>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-secondary">
            <span>flags: {digestAlert.anomaly_flags.join(", ")}</span>
            <span>fills: {digestAlert.fills_count}</span>
            <span>alerts: {digestAlert.lineage_alerts_count}</span>
            <span>top: {digestAlert.top_strategy ?? "n/a"}</span>
            <span>pnl: {formatNumber(digestAlert.top_strategy_realized_pnl_usd, 2)} USDT</span>
          </div>
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <KpiCard label="Total Equity" value={`${formatNumber(summary?.equity.net, 2)} ${summary?.equity.currency ?? "USDT"}`} />
        <KpiCard label="Daily Net PnL" value={formatNumber(summary?.daily_pnl.net, 2)} />
        <KpiCard label="Weekly Net PnL" value={formatNumber(summary?.weekly_pnl.net, 2)} />
        <KpiCard label="Exposure" value={`${formatCompact(summary?.exposure_notional)} USDT`} tone={activeIntents > 0 ? "warning" : "neutral"} />
        <KpiCard label="Queue Active" value={String(activeIntents)} tone={activeIntents > 0 ? "warning" : "profit"} />
        <KpiCard
          label="Replacement Alerts"
          value={String(summary?.lineage_summary?.replacement_alerts_count ?? 0)}
          tone={(summary?.lineage_summary?.replacement_alerts_count ?? 0) > 0 ? "warning" : "profit"}
        />
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.15fr_0.85fr_360px]">
        <Panel title="Liquidity / Mid Price Stream" action="btc microstructure">
          <div className="relative h-[292px] overflow-hidden rounded border border-white/10 bg-black/35">
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 900 280" preserveAspectRatio="none">
              {Array.from({ length: 8 }).map((_, index) => (
                <line key={`h-${index}`} x1="0" x2="900" y1={35 + index * 32} y2={35 + index * 32} stroke="rgba(255,255,255,.06)" />
              ))}
              {Array.from({ length: 12 }).map((_, index) => (
                <line key={`v-${index}`} y1="0" y2="280" x1={index * 82} x2={index * 82} stroke="rgba(255,255,255,.045)" />
              ))}
              {sparkPath ? <path d={sparkPath} fill="none" stroke="#22f5a5" strokeWidth="3" /> : null}
              <path d="M0 232 L900 232" stroke="#49c6ff" strokeDasharray="8 8" strokeOpacity="0.5" />
            </svg>
            <div className="absolute left-3 top-3 rounded border border-white/10 bg-black/70 px-3 py-2 font-mono text-[11px]">
              <div className="text-muted">MID / DEPTH SNAPSHOT</div>
              <div className="mt-1 text-profit">
                {formatNumber(orderbook?.metrics.mid_price, 2)} / {formatCompact(orderbook?.metrics.bid_depth_notional_0p5pct)} bid
              </div>
            </div>
          </div>
        </Panel>

        <Panel title="Execution Queue" action="latest intents">
          <div className="overflow-hidden rounded border border-white/10">
            <table className="w-full font-mono text-xs">
              <thead className="bg-white/[0.04] text-muted">
                <tr>
                  <th className="px-2 py-2 text-left font-normal">STRATEGY</th>
                  <th className="px-2 py-2 text-left font-normal">SYMBOL</th>
                  <th className="px-2 py-2 text-right font-normal">STATE</th>
                  <th className="px-2 py-2 text-right font-normal">NOTIONAL</th>
                </tr>
              </thead>
              <tbody>
                {state.intents.map((intent) => (
                  <tr key={intent.id} className="border-t border-white/10">
                    <td className="px-2 py-2 text-primary">{intent.source_strategy}</td>
                    <td className="px-2 py-2 text-secondary">{intent.symbol}</td>
                    <td
                      className={`px-2 py-2 text-right ${
                        intent.status === "executed"
                          ? "text-profit"
                          : intent.status === "failed" || intent.status === "rejected"
                            ? "text-loss"
                            : "text-warning"
                      }`}
                    >
                      {intent.status.toUpperCase()}
                    </td>
                    <td className="px-2 py-2 text-right text-muted">{formatCompact(intent.approved_notional)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Risk Stack" action="live gates">
          <div className="space-y-2 font-mono text-xs">
            {riskRows.map(({ label, status, tone, Icon }) => (
              <div key={label} className="flex items-center justify-between rounded border border-white/10 bg-black/25 px-3 py-2">
                <span className="flex items-center gap-2 text-secondary">
                  <Icon size={14} />
                  {label}
                </span>
                <span className={tone}>{status}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-3 xl:grid-cols-[0.75fr_1fr_0.85fr]">
        <Panel title={`${orderbook?.symbol ?? "BTCUSDT"} Order Book`} action="live top of book">
          <div className="space-y-1 font-mono text-xs">
            {[...(orderbook?.asks ?? []), ...(orderbook?.bids ?? [])].map((level, index) => {
              const side = index < (orderbook?.asks.length ?? 0) ? "ask" : "bid";
              const notional = Number(level.price) * Number(level.quantity);
              return (
                <div
                  key={`${level.price}-${side}`}
                  className={`grid grid-cols-3 rounded px-2 py-1.5 ${
                    side === "ask" ? "bg-loss/10 text-loss" : "bg-profit/10 text-profit"
                  }`}
                >
                  <span>{formatNumber(level.price, 2)}</span>
                  <span className="text-right">{formatNumber(level.quantity, 4)}</span>
                  <span className="text-right">{formatCompact(notional)}</span>
                </div>
              );
            })}
          </div>
        </Panel>

        <Panel title="Spot Balances" action="venue account state">
          <div className="overflow-hidden rounded border border-white/10">
            <table className="w-full font-mono text-xs">
              <thead className="bg-white/[0.04] text-muted">
                <tr>
                  <th className="px-2 py-2 text-left font-normal">ASSET</th>
                  <th className="px-2 py-2 text-right font-normal">TOTAL</th>
                  <th className="px-2 py-2 text-right font-normal">USD</th>
                  <th className="px-2 py-2 text-right font-normal">UPDATED</th>
                </tr>
              </thead>
              <tbody>
                {(summary?.balances ?? []).map((balance) => (
                  <tr key={balance.asset} className="border-t border-white/10">
                    <td className="px-2 py-2 text-primary">{balance.asset}</td>
                    <td className="px-2 py-2 text-right text-secondary">{formatNumber(balance.total, 6)}</td>
                    <td className="px-2 py-2 text-right text-profit">{formatCompact(balance.total_value_usd)}</td>
                    <td className="px-2 py-2 text-right text-muted">{formatTimestamp(balance.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Signal Feed" action="risk veto audit">
          <div className="space-y-2 font-mono text-xs">
            {(summary?.recent_intents ?? []).map((intent) => (
              <div key={intent.id} className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-primary">{intent.source_strategy}</span>
                  <span
                    className={
                      intent.status === "failed" || intent.status === "rejected"
                        ? "text-loss"
                        : intent.status === "executed"
                          ? "text-profit"
                          : "text-warning"
                    }
                  >
                    {intent.status.toUpperCase()}
                  </span>
                </div>
                <div className="mt-1 flex items-center justify-between text-[11px] text-muted">
                  <span>{intent.symbol}</span>
                  <span>{intent.notes ?? formatTimestamp(intent.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Strategy Cohorts" action="fill outcome breakdown">
          <div className="overflow-hidden rounded border border-white/10">
            <table className="w-full font-mono text-xs">
              <thead className="bg-white/[0.04] text-muted">
                <tr>
                  <th className="px-2 py-2 text-left font-normal">STRATEGY</th>
                  <th className="px-2 py-2 text-right font-normal">FILLS</th>
                  <th className="px-2 py-2 text-right font-normal">WIN RATE</th>
                  <th className="px-2 py-2 text-right font-normal">REALIZED</th>
                  <th className="px-2 py-2 text-right font-normal">SLIP COST</th>
                </tr>
              </thead>
              <tbody>
                {(summary?.strategy_breakdown ?? []).map((row) => (
                  <tr key={row.source_strategy} className="border-t border-white/10">
                    <td className="px-2 py-2 text-primary">{row.source_strategy}</td>
                    <td className="px-2 py-2 text-right text-secondary">{row.fills_count}</td>
                    <td className="px-2 py-2 text-right text-cyan">{formatNumber(Number(row.win_rate) * 100, 1)}%</td>
                    <td
                      className={`px-2 py-2 text-right ${
                        Number(row.gross_realized_pnl_usd) >= 0 ? "text-profit" : "text-loss"
                      }`}
                    >
                      {formatNumber(row.gross_realized_pnl_usd, 2)}
                    </td>
                    <td className="px-2 py-2 text-right text-warning">
                      {formatNumber(row.gross_adverse_slippage_cost_usd, 2)}
                    </td>
                  </tr>
                ))}
                {(summary?.strategy_breakdown ?? []).length === 0 ? (
                  <tr className="border-t border-white/10">
                    <td colSpan={5} className="px-2 py-4 text-center text-muted">
                      No attributed fills yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Strategy Notes" action="cohort context">
          <div className="mb-3 flex flex-wrap gap-2 font-mono text-[11px]">
            <button
              type="button"
              onClick={() => exportCsv("/dashboard/summary/strategy-breakdown/export")}
              className="rounded border border-white/10 px-3 py-2 text-primary"
            >
              Export Strategy CSV
            </button>
          </div>
          <div className="grid gap-2 font-mono text-xs">
            {(summary?.strategy_breakdown ?? []).slice(0, 4).map((row) => (
              <div key={`note-${row.source_strategy}`} className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-primary">{row.source_strategy}</span>
                  <span className={Number(row.gross_realized_pnl_usd) >= 0 ? "text-profit" : "text-loss"}>
                    {formatNumber(row.gross_realized_pnl_usd, 2)} USDT
                  </span>
                </div>
                <div className="mt-1 flex items-center justify-between text-[11px] text-muted">
                  <span>{row.chains_count} chains / {row.fills_count} fills</span>
                  <span>{formatNumber(Number(row.win_rate) * 100, 1)}% win</span>
                </div>
                <div className="mt-1 flex items-center justify-between text-[11px] text-muted">
                  <span>slip {formatNumber(row.average_adverse_slippage_bps, 2)} bps</span>
                  <span>underfill {formatCompact(row.gross_underfill_notional_usd)} USDT</span>
                </div>
              </div>
            ))}
            {(summary?.strategy_breakdown ?? []).length === 0 ? (
              <div className="rounded border border-white/10 bg-black/25 px-3 py-4 text-center text-muted">
                Strategy cohorts will appear after attributed execution fills are recorded.
              </div>
            ) : null}
          </div>
        </Panel>
      </div>

      <div className="grid gap-3 xl:grid-cols-[1fr_0.9fr]">
        <Panel title="Lineage Alerts" action="replacement and slippage watch">
          <div className="overflow-hidden rounded border border-white/10">
            <table className="w-full font-mono text-xs">
              <thead className="bg-white/[0.04] text-muted">
                <tr>
                  <th className="px-2 py-2 text-left font-normal">LINEAGE</th>
                  <th className="px-2 py-2 text-left font-normal">STRATEGY</th>
                  <th className="px-2 py-2 text-right font-normal">FILL</th>
                  <th className="px-2 py-2 text-right font-normal">SLIP</th>
                  <th className="px-2 py-2 text-right font-normal">PNL</th>
                </tr>
              </thead>
              <tbody>
                {(summary?.lineage_alerts ?? []).map((alert) => (
                  <tr key={`${alert.root_intent_id}-${alert.latest_intent_id}`} className="border-t border-white/10">
                    <td className="px-2 py-2">
                      <div className="text-primary">{alert.symbol}</div>
                      <div className="text-[11px] text-muted">
                        {alert.root_intent_id} {"->"} {alert.latest_intent_id} / {alert.lineage_size} intents
                      </div>
                    </td>
                    <td className="px-2 py-2 text-secondary">{alert.source_strategy}</td>
                    <td className="px-2 py-2 text-right text-warning">{formatNumber(Number(alert.fill_ratio) * 100, 1)}%</td>
                    <td className="px-2 py-2 text-right text-warning">{formatNumber(alert.slippage_bps, 2)} bps</td>
                    <td className={`px-2 py-2 text-right ${Number(alert.realized_pnl_usd) >= 0 ? "text-profit" : "text-loss"}`}>
                      {formatNumber(alert.realized_pnl_usd, 2)}
                    </td>
                  </tr>
                ))}
                {(summary?.lineage_alerts ?? []).length === 0 ? (
                  <tr className="border-t border-white/10">
                    <td colSpan={5} className="px-2 py-4 text-center text-muted">
                      No active replacement alerts.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Panel>

        <div className="grid gap-3">
          <Panel title="Lineage Summary" action="operator replacement pressure">
            <div className="mb-3 flex flex-wrap gap-2 font-mono text-[11px]">
              <button
                type="button"
                onClick={() => exportCsv("/dashboard/summary/lineage-alerts/export")}
                className="rounded border border-white/10 px-3 py-2 text-primary"
              >
                Export Lineage Alerts CSV
              </button>
            </div>
            <div className="grid gap-2 font-mono text-xs">
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="text-muted">Replacement lineages</div>
                <div className="mt-1 text-xl text-primary">{summary?.lineage_summary?.replacement_lineages_count ?? 0}</div>
              </div>
              <div className="rounded border border-warning/30 bg-warning/10 px-3 py-2">
                <div className="text-warning">Open alerts</div>
                <div className="mt-1 text-xl text-warning">{summary?.lineage_summary?.replacement_alerts_count ?? 0}</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="text-muted">Worst slippage</div>
                <div className="mt-1 text-xl text-secondary">{formatNumber(summary?.lineage_summary?.worst_slippage_bps, 2)} bps</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
                Replacement alerts trigger on fill ratio below 90% or slippage above 5 bps.
              </div>
            </div>
          </Panel>

          <Panel title="Venue Event Alerts" action="bybit reject cancel partial watch">
            <div className="mb-3 grid grid-cols-3 gap-2 font-mono text-[11px]">
              <div className="rounded border border-loss/30 bg-loss/10 px-2 py-2 text-center">
                <div className="text-loss">Rejected</div>
                <div className="mt-1 text-sm text-primary">{summary?.venue_event_summary?.rejected ?? 0}</div>
              </div>
              <div className="rounded border border-warning/30 bg-warning/10 px-2 py-2 text-center">
                <div className="text-warning">Cancelled</div>
                <div className="mt-1 text-sm text-primary">{summary?.venue_event_summary?.cancelled ?? 0}</div>
              </div>
              <div className="rounded border border-cyan/30 bg-cyan/10 px-2 py-2 text-center">
                <div className="text-cyan">Partial</div>
                <div className="mt-1 text-sm text-primary">{summary?.venue_event_summary?.partial ?? 0}</div>
              </div>
            </div>
            <div className="mb-3 flex flex-wrap gap-2 font-mono text-[11px]">
              <button
                type="button"
                onClick={() => exportCsv("/execution/venues/events/export?status_bucket=rejected")}
                className="rounded border border-white/10 px-3 py-2 text-primary"
              >
                Export Rejected CSV
              </button>
              <button
                type="button"
                onClick={() => exportCsv("/execution/venues/events/export?status_bucket=cancelled")}
                className="rounded border border-white/10 px-3 py-2 text-primary"
              >
                Export Cancelled CSV
              </button>
            </div>
            <div className="grid gap-2 font-mono text-xs">
              {(summary?.venue_event_alerts ?? []).map((event) => (
                <div key={event.id} className="rounded border border-white/10 bg-black/25 px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-primary">{event.symbol ?? event.venue}</span>
                    <span
                      className={
                        event.status_bucket === "rejected"
                          ? "text-loss"
                          : event.status_bucket === "cancelled"
                            ? "text-warning"
                            : "text-cyan"
                      }
                    >
                      {event.venue_status}
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted">
                    <span>{event.event_type}</span>
                    <span>{formatTimestamp(event.created_at)}</span>
                  </div>
                  <div className="mt-1 text-[11px] text-secondary">
                    {event.ret_code !== null ? `retCode ${event.ret_code}` : event.reconcile_state}
                    {event.ret_msg ? ` • ${event.ret_msg}` : ""}
                  </div>
                </div>
              ))}
              {(summary?.venue_event_alerts ?? []).length === 0 ? (
                <div className="rounded border border-white/10 bg-black/25 px-3 py-4 text-center text-muted">
                  No recent Bybit venue alerts.
                </div>
              ) : null}
            </div>
          </Panel>
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="Daily Digest" action="scheduled report artifacts">
          <div className="mb-3 flex flex-wrap gap-2 font-mono text-[11px]">
            <button
              type="button"
              onClick={() => void triggerDailyDigest()}
              className="rounded border border-white/10 px-3 py-2 text-primary"
            >
              Run Daily Digest
            </button>
          </div>
          <div className="grid gap-2 font-mono text-xs">
            <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
              Output directory: server-side daily JSON and CSV artifacts.
            </div>
            <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
              Latest artifact count: {state.digests.length}
            </div>
            <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
              Latest top strategy: {summary?.digest_runs?.[0]?.top_strategy ?? "n/a"}
            </div>
            <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
              Latest digest alerts: {summary?.digest_runs?.[0]?.lineage_alerts_count ?? 0}
            </div>
          </div>
        </Panel>

        <Panel title="Recent Digest Artifacts" action="archived reports">
          <div className="space-y-2 font-mono text-xs">
            {state.digests.map((digest) => (
              <div key={digest.report_date} className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-primary">{digest.report_date}</span>
                  <span className="text-muted">{formatTimestamp(digest.generated_at)}</span>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] text-muted">
                  <div>fills: <span className="text-secondary">{digest.fills_count ?? "--"}</span></div>
                  <div>intents: <span className="text-secondary">{digest.intents_count ?? "--"}</span></div>
                  <div>alerts: <span className="text-warning">{digest.lineage_alerts_count ?? "--"}</span></div>
                  <div>
                    top: <span className="text-primary">{digest.top_strategy ?? "n/a"}</span>
                  </div>
                </div>
                {digest.anomaly_score && digest.anomaly_score > 0 ? (
                  <div className="mt-1 text-[11px] text-warning">
                    anomaly score {digest.anomaly_score}: {(digest.anomaly_flags ?? []).join(", ")}
                  </div>
                ) : null}
                {digest.top_strategy_realized_pnl_usd !== null ? (
                  <div className="mt-1 text-[11px] text-secondary">
                    top strategy pnl: {formatNumber(digest.top_strategy_realized_pnl_usd, 2)} USDT
                  </div>
                ) : null}
                <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                  <button
                    type="button"
                    onClick={() => exportCsv(`/reports/daily-digest/download?report_date=${digest.report_date}&artifact=json`)}
                    className="rounded border border-white/10 px-2 py-1 text-secondary"
                  >
                    JSON
                  </button>
                  <button
                    type="button"
                    onClick={() => exportCsv(`/reports/daily-digest/download?report_date=${digest.report_date}&artifact=strategy_csv`)}
                    className="rounded border border-white/10 px-2 py-1 text-secondary"
                  >
                    Strategy CSV
                  </button>
                  <button
                    type="button"
                    onClick={() => exportCsv(`/reports/daily-digest/download?report_date=${digest.report_date}&artifact=lineage_csv`)}
                    className="rounded border border-white/10 px-2 py-1 text-secondary"
                  >
                    Lineage CSV
                  </button>
                </div>
              </div>
            ))}
            {state.digests.length === 0 ? (
              <div className="rounded border border-white/10 bg-black/25 px-3 py-4 text-center text-muted">
                No digest artifacts generated yet.
              </div>
            ) : null}
          </div>
        </Panel>
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.05fr_0.95fr]">
        <Panel title="Digest Trend" action="run log series">
          <div className="mb-3 flex flex-wrap gap-2 font-mono text-[11px]">
            {DIGEST_RANGE_OPTIONS.map((days) => (
              <button
                key={days}
                type="button"
                onClick={() => {
                  setDigestRangeDays(days);
                  setDigestStartAt("");
                  setDigestEndAt("");
                }}
                className={`rounded border px-3 py-2 ${
                  digestRangeDays === days ? "border-cyan/40 bg-cyan/10 text-cyan" : "border-white/10 text-primary"
                }`}
              >
                {days}D
              </button>
            ))}
            <button
              type="button"
              onClick={() =>
                exportDigestSeriesCsv({
                  days: digestStartAt || digestEndAt ? undefined : digestRangeDays,
                  startAt: digestStartAt || undefined,
                  endAt: digestEndAt || undefined,
                  flaggedOnly: digestFlaggedOnly
                })
              }
              className="rounded border border-white/10 px-3 py-2 text-primary"
            >
              Export Series CSV
            </button>
          </div>
          <div className="mb-3 grid gap-2 lg:grid-cols-[1fr_1fr_auto]">
            <input
              type="date"
              value={digestStartAt}
              onChange={(event) => setDigestStartAt(event.target.value)}
              className="rounded border border-white/10 bg-black/25 px-3 py-2 font-mono text-[11px] text-primary outline-none"
            />
            <input
              type="date"
              value={digestEndAt}
              onChange={(event) => setDigestEndAt(event.target.value)}
              className="rounded border border-white/10 bg-black/25 px-3 py-2 font-mono text-[11px] text-primary outline-none"
            />
            <label className="flex items-center gap-2 rounded border border-white/10 bg-black/25 px-3 py-2 font-mono text-[11px] text-secondary">
              <input
                type="checkbox"
                checked={digestFlaggedOnly}
                onChange={(event) => setDigestFlaggedOnly(event.target.checked)}
                className="h-3.5 w-3.5 accent-amber-400"
              />
              flagged only
            </label>
          </div>
          <div className="mb-3 flex flex-wrap gap-2 font-mono text-[11px]">
            {DIGEST_COMPARE_OPTIONS.map((metric) => (
              <button
                key={metric}
                type="button"
                onClick={() => setDigestCompareMetric(metric)}
                className={`rounded border px-3 py-2 ${
                  digestCompareMetric === metric ? "border-warning/40 bg-warning/10 text-warning" : "border-white/10 text-primary"
                }`}
              >
                {metric === "fills" ? "Compare Fills" : metric === "lineage_alerts" ? "Compare Alerts" : "Compare PnL"}
              </button>
            ))}
          </div>
          <div className="grid gap-3 lg:grid-cols-[1.25fr_0.75fr]">
            <div className="rounded border border-white/10 bg-black/25 p-2">
              <div className="mb-2 flex items-center justify-between font-mono text-[11px] uppercase">
                <span className="text-muted">Anomaly vs {digestCompareConfig.label}</span>
                <span className="text-secondary">{digestRangeDays}D window</span>
              </div>
              <svg className="h-28 w-full" viewBox="0 0 320 110" preserveAspectRatio="none">
                <line x1="0" x2="320" y1="100" y2="100" stroke="rgba(255,255,255,.08)" />
                {compareOverlayPath ? (
                  <path d={compareOverlayPath} fill="none" stroke={digestCompareConfig.tone} strokeWidth="2.5" strokeOpacity="0.75" />
                ) : null}
                {anomalyOverlayPath ? (
                  <path d={anomalyOverlayPath} fill="none" stroke="#f59e0b" strokeWidth="3" />
                ) : null}
                {flagMarkers.map((marker) => (
                  <circle
                    key={`${marker.reportDate}-${marker.flags.join("-")}`}
                    cx={marker.x}
                    cy={marker.y}
                    r="3.5"
                    fill={marker.tone}
                    className="cursor-pointer"
                    onClick={() => setSelectedDigestReportDate(marker.reportDate)}
                  >
                    <title>{`${marker.reportDate}: ${marker.flags.join(", ")}`}</title>
                  </circle>
                ))}
              </svg>
              <div className="mt-2 flex flex-wrap gap-3 font-mono text-[10px] text-muted">
                <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-amber-400" />zero fills</span>
                <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-red-500" />negative pnl</span>
                <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-cyan-400" />high alerts</span>
              </div>
            </div>
            <div className="grid gap-3">
              <div className="grid gap-2">
                <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
                  <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                    <div className="text-muted">Avg anomaly</div>
                    <div className="mt-1 text-warning">{formatNumber(avgAnomaly, 2)}</div>
                  </div>
                  <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                    <div className="text-muted">Flagged days</div>
                    <div className="mt-1 text-primary">{flaggedDaysCount}</div>
                  </div>
                  <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                    <div className="text-muted">Avg {digestCompareConfig.label}</div>
                    <div className="mt-1 text-secondary">{formatNumber(avgCompareValue, 2)}</div>
                  </div>
                  <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                    <div className="text-muted">Worst top pnl</div>
                    <div className={`${worstTopStrategyPnl >= 0 ? "mt-1 text-profit" : "mt-1 text-loss"}`}>
                      {formatNumber(worstTopStrategyPnl, 2)}
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 font-mono text-[11px]">
                  <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                    <div className="text-muted">Zero fills</div>
                    <div className="mt-1 text-warning">{zeroFillsDays}</div>
                  </div>
                  <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                    <div className="text-muted">Neg pnl</div>
                    <div className="mt-1 text-loss">{negativePnlDays}</div>
                  </div>
                  <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                    <div className="text-muted">High alerts</div>
                    <div className="mt-1 text-cyan">{highAlertDays}</div>
                  </div>
                </div>
              </div>
              {[
                { label: "Anomaly", path: anomalySparkPath, tone: "#f59e0b" },
                digestCompareConfig
              ].map((item) => (
                <div key={item.label} className="rounded border border-white/10 bg-black/25 p-2">
                  <div className="mb-2 font-mono text-[11px] uppercase text-muted">{item.label}</div>
                  <svg className="h-20 w-full" viewBox="0 0 320 86" preserveAspectRatio="none">
                    <line x1="0" x2="320" y1="82" y2="82" stroke="rgba(255,255,255,.08)" />
                    {item.path ? <path d={item.path} fill="none" stroke={item.tone} strokeWidth="3" /> : null}
                  </svg>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        <Panel title="Digest Run Log" action="latest daily series">
          <div className="overflow-hidden rounded border border-white/10">
            <table className="w-full font-mono text-xs">
              <thead className="bg-white/[0.04] text-muted">
                <tr>
                  <th className="px-2 py-2 text-left font-normal">DATE</th>
                  <th className="px-2 py-2 text-right font-normal">SCORE</th>
                  <th className="px-2 py-2 text-right font-normal">FILLS</th>
                  <th className="px-2 py-2 text-right font-normal">ALERTS</th>
                  <th className="px-2 py-2 text-right font-normal">TOP PNL</th>
                </tr>
              </thead>
              <tbody>
                {[...state.digestSeries].reverse().slice(0, 7).map((row) => (
                  <tr
                    key={row.report_date}
                    className={`cursor-pointer border-t border-white/10 ${
                      selectedDigestRun?.report_date === row.report_date ? "bg-white/[0.04]" : ""
                    }`}
                    onClick={() => setSelectedDigestReportDate(row.report_date)}
                  >
                    <td className="px-2 py-2 text-primary">{row.report_date}</td>
                    <td className={`px-2 py-2 text-right ${row.anomaly_score > 0 ? "text-warning" : "text-profit"}`}>
                      {row.anomaly_score}
                    </td>
                    <td className="px-2 py-2 text-right text-secondary">{row.fills_count}</td>
                    <td className="px-2 py-2 text-right text-cyan">{row.lineage_alerts_count}</td>
                    <td className="px-2 py-2 text-right">
                      <div
                        className={`${
                          Number(row.top_strategy_realized_pnl_usd ?? 0) >= 0 ? "text-profit" : "text-loss"
                        }`}
                      >
                        {formatNumber(row.top_strategy_realized_pnl_usd, 2)}
                      </div>
                      {row.anomaly_flags.length > 0 ? (
                        <div className="mt-1 text-[10px] text-warning">{row.anomaly_flags.join(", ")}</div>
                      ) : null}
                    </td>
                  </tr>
                ))}
                {state.digestSeries.length === 0 ? (
                  <tr className="border-t border-white/10">
                    <td colSpan={5} className="px-2 py-4 text-center text-muted">
                      No digest run history yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      <Panel title="Digest Day Detail" action="selected run detail">
        {selectedDigestRun ? (
          <div className="grid gap-3 lg:grid-cols-[0.85fr_1.15fr]">
            <div className="grid gap-2 font-mono text-xs">
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="text-muted">Report date</div>
                <div className="mt-1 text-primary">{selectedDigestRun.report_date}</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="text-muted">Generated</div>
                <div className="mt-1 text-secondary">{formatTimestamp(selectedDigestRun.generated_at)}</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="text-muted">Top strategy</div>
                <div className="mt-1 text-primary">{selectedDigestRun.top_strategy ?? "n/a"}</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="text-muted">Top pnl</div>
                <div
                  className={`mt-1 ${
                    Number(selectedDigestRun.top_strategy_realized_pnl_usd ?? 0) >= 0 ? "text-profit" : "text-loss"
                  }`}
                >
                  {formatNumber(selectedDigestRun.top_strategy_realized_pnl_usd, 2)} USDT
                </div>
              </div>
            </div>
            <div className="grid gap-2 font-mono text-xs">
              <div className="grid grid-cols-3 gap-2">
                <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                  <div className="text-muted">Fills</div>
                  <div className="mt-1 text-secondary">{selectedDigestRun.fills_count ?? 0}</div>
                </div>
                <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                  <div className="text-muted">Intents</div>
                  <div className="mt-1 text-secondary">{selectedDigestRun.intents_count ?? 0}</div>
                </div>
                <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                  <div className="text-muted">Alerts</div>
                  <div className="mt-1 text-warning">{selectedDigestRun.lineage_alerts_count ?? 0}</div>
                </div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="text-muted">Anomaly score</div>
                <div className="mt-1 text-warning">{selectedDigestRun.anomaly_score ?? 0}</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="text-muted">Anomaly flags</div>
                <div className="mt-1 text-secondary">
                  {selectedDigestRun.anomaly_flags && selectedDigestRun.anomaly_flags.length > 0
                    ? selectedDigestRun.anomaly_flags.join(", ")
                    : "none"}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => exportCsv(`/reports/daily-digest/download?report_date=${selectedDigestRun.report_date}&artifact=json`)}
                  className="rounded border border-white/10 px-3 py-2 text-primary"
                >
                  Open JSON
                </button>
                <button
                  type="button"
                  onClick={() => exportCsv(`/reports/daily-digest/download?report_date=${selectedDigestRun.report_date}&artifact=strategy_csv`)}
                  className="rounded border border-white/10 px-3 py-2 text-primary"
                >
                  Strategy CSV
                </button>
                <button
                  type="button"
                  onClick={() => exportCsv(`/reports/daily-digest/download?report_date=${selectedDigestRun.report_date}&artifact=lineage_csv`)}
                  className="rounded border border-white/10 px-3 py-2 text-primary"
                >
                  Lineage CSV
                </button>
              </div>
            </div>
            <div className="grid gap-3 lg:col-span-2">
              <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
                <div className="rounded border border-white/10 bg-black/25 p-3">
                  <div className="mb-2 flex items-center justify-between font-mono text-[11px] uppercase">
                    <span className="text-muted">Strategy Breakdown Preview</span>
                    <span className="text-secondary">
                      {selectedDigestPreviewLoading ? "loading" : `${selectedDigestPreview?.strategy_breakdown.length ?? 0} rows`}
                    </span>
                  </div>
                  {selectedDigestPreviewError ? (
                    <div className="rounded border border-loss/30 bg-loss/10 px-3 py-2 text-xs text-loss">
                      {selectedDigestPreviewError}
                    </div>
                  ) : selectedDigestPreview && selectedDigestPreview.strategy_breakdown.length > 0 ? (
                    <div className="overflow-hidden rounded border border-white/10">
                      <table className="w-full font-mono text-xs">
                        <thead className="bg-white/[0.04] text-muted">
                          <tr>
                            <th className="px-2 py-2 text-left font-normal">STRATEGY</th>
                            <th className="px-2 py-2 text-right font-normal">FILLS</th>
                            <th className="px-2 py-2 text-right font-normal">WIN</th>
                            <th className="px-2 py-2 text-right font-normal">PNL</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedDigestPreview.strategy_breakdown.slice(0, 5).map((row) => (
                            <tr key={`preview-strategy-${row.source_strategy}`} className="border-t border-white/10">
                              <td className="px-2 py-2 text-primary">{row.source_strategy}</td>
                              <td className="px-2 py-2 text-right text-secondary">{row.fills_count}</td>
                              <td className="px-2 py-2 text-right text-cyan">{formatNumber(Number(row.win_rate) * 100, 1)}%</td>
                              <td
                                className={`px-2 py-2 text-right ${
                                  Number(row.gross_realized_pnl_usd) >= 0 ? "text-profit" : "text-loss"
                                }`}
                              >
                                {formatNumber(row.gross_realized_pnl_usd, 2)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="rounded border border-white/10 bg-black/25 px-3 py-4 text-center text-muted">
                      No strategy rows for this digest.
                    </div>
                  )}
                </div>

                <div className="rounded border border-white/10 bg-black/25 p-3">
                  <div className="mb-2 flex items-center justify-between font-mono text-[11px] uppercase">
                    <span className="text-muted">Lineage Alerts Preview</span>
                    <span className="text-secondary">
                      {selectedDigestPreviewLoading ? "loading" : `${selectedDigestPreview?.lineage_alerts.length ?? 0} rows`}
                    </span>
                  </div>
                  {selectedDigestPreviewError ? (
                    <div className="rounded border border-loss/30 bg-loss/10 px-3 py-2 text-xs text-loss">
                      {selectedDigestPreviewError}
                    </div>
                  ) : selectedDigestPreview && selectedDigestPreview.lineage_alerts.length > 0 ? (
                    <div className="space-y-2">
                      {selectedDigestPreview.lineage_alerts.slice(0, 4).map((row) => (
                        <div key={`preview-lineage-${row.root_intent_id}-${row.latest_intent_id}`} className="rounded border border-white/10 bg-black/25 px-3 py-2 font-mono text-xs">
                          <div className="flex items-center justify-between">
                            <span className="text-primary">{row.symbol}</span>
                            <span className="text-warning">{formatNumber(Number(row.fill_ratio) * 100, 1)}%</span>
                          </div>
                          <div className="mt-1 flex items-center justify-between text-[11px] text-muted">
                            <span>{row.source_strategy}</span>
                            <span>{formatNumber(row.slippage_bps, 2)} bps</span>
                          </div>
                          <div className="mt-1 flex items-center justify-between text-[11px]">
                            <span className="text-muted">
                              {row.root_intent_id} {"->"} {row.latest_intent_id} / {row.lineage_size} intents
                            </span>
                            <span className={Number(row.realized_pnl_usd) >= 0 ? "text-profit" : "text-loss"}>
                              {formatNumber(row.realized_pnl_usd, 2)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded border border-white/10 bg-black/25 px-3 py-4 text-center text-muted">
                      No lineage alerts for this digest.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded border border-white/10 bg-black/25 px-3 py-4 text-center font-mono text-xs text-muted">
            No digest run selected.
          </div>
        )}
      </Panel>

      <Panel title="Critical Audit Stream" action="operator notes">
          <div className="grid gap-2 font-mono text-xs lg:grid-cols-4">
          <div className="rounded border border-warning/30 bg-warning/10 px-3 py-2 text-warning">
            <AlertTriangle size={14} className="mb-2" />
            User stream requires valid Bybit credentials, Unified account setup, and explicit live transport enablement before sync starts.
          </div>
          <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
            Market stream symbols: {(marketStream?.symbols ?? ["BTCUSDT"]).join(", ")}
          </div>
          <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
            Venue sync: {userStream?.subscribed ? "account balances synchronized" : "user stream not subscribed yet"}.
          </div>
          <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
            Latest queue counts: executed {executionCounts.executed ?? 0}, failed {executionCounts.failed ?? 0}, queued {executionCounts.queued ?? 0}.
          </div>
          <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
            BTC depth 0.5%: bid {formatCompact(summary?.focus_liquidity?.bid_depth_notional)} / ask {formatCompact(summary?.focus_liquidity?.ask_depth_notional)}.
          </div>
        </div>
      </Panel>
    </div>
  );
}
