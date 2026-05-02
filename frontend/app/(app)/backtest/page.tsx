"use client";

import { useEffect, useState } from "react";

import {
  type BacktestOverviewResponse,
  type BacktestRunResponse,
  type BacktestWalkForwardResponse,
  type DashboardSummaryResponse,
  type SpotExecutionFillSummaryResponse,
  getBacktestOverview,
  getDashboardSummary,
  getBacktestRuns,
  getExecutionFillSummary,
  runBacktest,
  runBacktestWalkForward,
} from "@/lib/api";

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="market-panel rounded">
      <div className="flex h-10 items-center border-b border-white/10 px-3">
        <h2 className="font-mono text-[11px] uppercase text-secondary">{title}</h2>
      </div>
      <div className="p-3">{children}</div>
    </section>
  );
}

function formatNumber(value: string | number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "--";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "--";
  return parsed.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export default function BacktestPage() {
  const [summary, setSummary] = useState<SpotExecutionFillSummaryResponse | null>(null);
  const [dashboard, setDashboard] = useState<DashboardSummaryResponse | null>(null);
  const [runs, setRuns] = useState<BacktestRunResponse[]>([]);
  const [overview, setOverview] = useState<BacktestOverviewResponse | null>(null);
  const [walkForward, setWalkForward] = useState<BacktestWalkForwardResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [timeframe, setTimeframe] = useState("1m");
  const [limit, setLimit] = useState("240");
  const [strategyName, setStrategyName] = useState("buy_and_hold");
  const [resultStrategyFilter, setResultStrategyFilter] = useState("all");
  const [resultTimeframeFilter, setResultTimeframeFilter] = useState("all");
  const [walkForwardLookback, setWalkForwardLookback] = useState("720");
  const [walkForwardTrain, setWalkForwardTrain] = useState("240");
  const [walkForwardTest, setWalkForwardTest] = useState("60");
  const [walkForwardStep, setWalkForwardStep] = useState("60");

  const loadRuns = async (symbolFilter?: string) => {
    setRuns(await getBacktestRuns(12, symbolFilter));
  };

  const loadOverview = async (nextSymbol?: string, nextStrategy?: string, nextTimeframe?: string) => {
    setOverview(
      await getBacktestOverview({
        symbol: nextSymbol ?? symbol,
        strategyName: nextStrategy ?? resultStrategyFilter,
        timeframe: nextTimeframe ?? resultTimeframeFilter,
        limit: 120,
      }),
    );
  };

  useEffect(() => {
    let active = true;
    void Promise.allSettled([
      getExecutionFillSummary(undefined, 250, 20),
      getDashboardSummary(),
      getBacktestRuns(12),
      getBacktestOverview({ symbol: "BTCUSDT", limit: 120 }),
    ]).then(([summaryResult, dashboardResult, runsResult, overviewResult]) => {
      if (!active) return;
      if (summaryResult.status === "fulfilled") setSummary(summaryResult.value);
      if (dashboardResult.status === "fulfilled") setDashboard(dashboardResult.value);
      if (runsResult.status === "fulfilled") setRuns(runsResult.value);
      if (overviewResult.status === "fulfilled") setOverview(overviewResult.value);
    });
    return () => {
      active = false;
    };
  }, []);

  const readiness = [
    { label: "Live fills available", ok: (summary?.fills_count ?? 0) > 0 },
    { label: "Strategy cohorts available", ok: (summary?.strategy_breakdown.length ?? 0) > 0 },
    { label: "Lineage outcomes available", ok: (dashboard?.lineage_alerts.length ?? 0) >= 0 },
    { label: "Execution cost analytics available", ok: summary !== null },
    { label: "Backtest engine implemented", ok: true },
    { label: "Walk-forward implemented", ok: walkForward !== null },
    { label: "Monte Carlo implemented", ok: false },
  ];

  const filteredRuns = runs.filter(
    (run) =>
      run.symbol === symbol &&
      (resultStrategyFilter === "all" || run.strategy_name === resultStrategyFilter) &&
      (resultTimeframeFilter === "all" || run.timeframe === resultTimeframeFilter),
  );
  const symbolRuns = runs.filter((run) => run.symbol === symbol);
  const numericMetric = (value: unknown) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  };
  const aggregate = (values: Array<number | null>, mode: "avg" | "max" | "min") => {
    const filtered = values.filter((value): value is number => value !== null);
    if (filtered.length === 0) return null;
    if (mode === "avg") return filtered.reduce((sum, value) => sum + value, 0) / filtered.length;
    if (mode === "max") return Math.max(...filtered);
    return Math.min(...filtered);
  };
  const averageReturnPct = aggregate(filteredRuns.map((run) => numericMetric(run.summary_payload.return_pct)), "avg");
  const averageRangePct = aggregate(filteredRuns.map((run) => numericMetric(run.summary_payload.average_range_pct)), "avg");
  const bestReturnPct = aggregate(filteredRuns.map((run) => numericMetric(run.summary_payload.return_pct)), "max");
  const worstReturnPct = aggregate(filteredRuns.map((run) => numericMetric(run.summary_payload.return_pct)), "min");
  const strategyCounts = filteredRuns.reduce<Record<string, number>>((acc, run) => {
    acc[run.strategy_name] = (acc[run.strategy_name] ?? 0) + 1;
    return acc;
  }, {});
  const availableStrategies = Array.from(new Set(symbolRuns.map((run) => run.strategy_name))).sort();
  const availableTimeframes = Array.from(new Set(symbolRuns.map((run) => run.timeframe))).sort();
  const sortedComparisonRuns = [...filteredRuns].sort((left, right) => {
    const leftReturn = numericMetric(left.summary_payload.return_pct) ?? Number.NEGATIVE_INFINITY;
    const rightReturn = numericMetric(right.summary_payload.return_pct) ?? Number.NEGATIVE_INFINITY;
    return rightReturn - leftReturn;
  });
  const groupRuns = (keyBuilder: (run: BacktestRunResponse) => string) =>
    Object.entries(
      filteredRuns.reduce<Record<string, BacktestRunResponse[]>>((acc, run) => {
        const key = keyBuilder(run);
        acc[key] = acc[key] ?? [];
        acc[key].push(run);
        return acc;
      }, {}),
    )
      .map(([key, group]) => {
        const returns = group.map((run) => numericMetric(run.summary_payload.return_pct));
        const ranges = group.map((run) => numericMetric(run.summary_payload.average_range_pct));
        return {
          key,
          runs: group.length,
          avgReturn: aggregate(returns, "avg"),
          bestReturn: aggregate(returns, "max"),
          worstReturn: aggregate(returns, "min"),
          avgRange: aggregate(ranges, "avg"),
          avgBars: aggregate(group.map((run) => run.sample_size), "avg"),
        };
      })
      .sort((left, right) => (right.avgReturn ?? Number.NEGATIVE_INFINITY) - (left.avgReturn ?? Number.NEGATIVE_INFINITY));
  const normalizeGroupRows = (
    rows:
      | BacktestOverviewResponse["strategy_groups"]
      | Array<{
          key: string;
          runs: number;
          avgReturn: number | null;
          bestReturn: number | null;
          worstReturn: number | null;
          avgRange: number | null;
          avgBars: number | null;
        }>,
  ) =>
    rows.map((row) =>
      "group_key" in row
        ? {
            key: row.group_key,
            runs: row.runs_count,
            avgReturn: Number(row.average_return_pct),
            bestReturn: Number(row.best_return_pct),
            worstReturn: Number(row.worst_return_pct),
            avgRange: Number(row.average_range_pct),
            avgBars: Number(row.average_sample_size),
          }
        : row,
    );
  const strategySummaryRows = normalizeGroupRows(overview?.strategy_groups ?? groupRuns((run) => run.strategy_name));
  const timeframeSummaryRows = normalizeGroupRows(overview?.timeframe_groups ?? groupRuns((run) => run.timeframe));
  const latestRun = sortedComparisonRuns[0] ?? null;

  return (
    <div className="space-y-3">
      <div className="market-panel rounded px-4 py-3">
        <div className="font-mono text-[11px] uppercase text-muted">Backtest Center</div>
        <h1 className="mt-1 text-2xl font-semibold">Research Readiness and Live Proxy</h1>
        <p className="mt-1 text-sm text-secondary">
          The true backtest engine is still pending. This page now shows what is already usable for research calibration from live execution data instead of a placeholder.
        </p>
      </div>

      <div className="grid gap-3 xl:grid-cols-3">
        <Panel title="Run Backtest">
          <div className="space-y-3">
            <div className="rounded border border-white/10 bg-black/20 px-3 py-2 text-sm text-secondary">
              Minimal backend run is now active. It persists backtest runs and computes a simple buy-and-hold or range probe summary from the current candle set.
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              <button
                type="button"
                onClick={() => {
                  setSymbol("BTCUSDT");
                  setTimeframe("1m");
                  setLimit("240");
                  setStrategyName("buy_and_hold");
                }}
                className="h-10 rounded border border-white/10 bg-black/20 px-3 font-mono text-xs text-secondary"
              >
                BTC SCALP PRESET
              </button>
              <button
                type="button"
                onClick={() => {
                  setSymbol("ETHUSDT");
                  setTimeframe("5m");
                  setLimit("360");
                  setStrategyName("range_probe");
                }}
                className="h-10 rounded border border-white/10 bg-black/20 px-3 font-mono text-xs text-secondary"
              >
                ETH RANGE PRESET
              </button>
              <button
                type="button"
                onClick={() => {
                  setSymbol("SOLUSDT");
                  setTimeframe("15m");
                  setLimit("480");
                  setStrategyName("buy_and_hold");
                }}
                className="h-10 rounded border border-white/10 bg-black/20 px-3 font-mono text-xs text-secondary"
              >
                SOL SWING PRESET
              </button>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                value={symbol}
                onChange={(event) => setSymbol(event.target.value.toUpperCase())}
                className="h-10 rounded border border-white/10 bg-black/20 px-3 text-primary"
                placeholder="BTCUSDT"
              />
              <select
                value={timeframe}
                onChange={(event) => setTimeframe(event.target.value)}
                className="h-10 rounded border border-white/10 bg-black/20 px-3 text-primary"
              >
                <option value="1m">1m</option>
                <option value="5m">5m</option>
                <option value="15m">15m</option>
                <option value="1h">1h</option>
              </select>
              <input
                value={limit}
                onChange={(event) => setLimit(event.target.value)}
                className="h-10 rounded border border-white/10 bg-black/20 px-3 text-primary"
                placeholder="240"
              />
              <select
                value={strategyName}
                onChange={(event) => setStrategyName(event.target.value)}
                className="h-10 rounded border border-white/10 bg-black/20 px-3 text-primary"
              >
                <option value="buy_and_hold">buy_and_hold</option>
                <option value="range_probe">range_probe</option>
              </select>
            </div>
            <button
              type="button"
              disabled={loading}
              onClick={() => {
                setLoading(true);
                void runBacktest({
                  symbol,
                  timeframe,
                  limit: Number(limit) || 240,
                  strategy_name: strategyName,
                  notes: `run from backtest page: ${symbol} ${timeframe}`,
                })
                  .then(async () => {
                    await loadRuns(symbol);
                    await loadOverview(symbol, resultStrategyFilter, resultTimeframeFilter);
                  })
                  .finally(() => setLoading(false));
              }}
              className="h-11 w-full rounded border border-profit/30 bg-profit/10 font-mono text-xs text-profit disabled:opacity-60"
            >
              {loading ? "RUNNING..." : `RUN ${symbol} ${timeframe} ${strategyName}`}
            </button>
            <button
              type="button"
              onClick={() => {
                void loadRuns(symbol);
                void loadOverview(symbol, resultStrategyFilter, resultTimeframeFilter);
              }}
              className="h-10 w-full rounded border border-white/10 bg-black/20 font-mono text-xs text-secondary"
            >
              REFRESH {symbol} RUNS
            </button>
          </div>
        </Panel>

        <Panel title="Readiness Matrix">
          <div className="space-y-2 font-mono text-xs">
            {readiness.map((item) => (
              <div key={item.label} className="flex items-center justify-between rounded border border-white/10 bg-black/25 px-3 py-2">
                <span className="text-secondary">{item.label}</span>
                <span className={item.ok ? "text-profit" : "text-warning"}>{item.ok ? "READY" : "PENDING"}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Live Proxy Metrics">
          {summary ? (
            <div className="space-y-2 font-mono text-xs">
              <Metric label="Fills" value={String(summary.fills_count)} />
              <Metric label="Chains" value={String(summary.chains_count)} />
              <Metric label="Win rate" value={formatNumber(summary.win_rate, 2)} />
              <Metric label="Gross pnl" value={formatNumber(summary.gross_realized_pnl_usd, 2)} />
              <Metric label="Adverse cost" value={formatNumber(summary.gross_adverse_slippage_cost_usd, 2)} />
              <Metric label="Avg hold" value={`${formatNumber(Number(summary.average_hold_seconds ?? 0) / 3600, 2)}h`} />
            </div>
          ) : (
            <div className="text-sm text-muted">No live proxy metrics yet.</div>
          )}
        </Panel>

        <Panel title="Strategy Cohorts">
          <div className="space-y-2 font-mono text-xs">
            {summary?.strategy_breakdown.slice(0, 6).map((row) => (
              <div key={row.source_strategy} className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-primary">{row.source_strategy}</span>
                  <span className="text-secondary">{row.fills_count} fills</span>
                </div>
                <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-secondary">
                  <span>pnl {formatNumber(row.gross_realized_pnl_usd, 2)}</span>
                  <span>cost {formatNumber(row.gross_adverse_slippage_cost_usd, 2)}</span>
                  <span>hold {formatNumber(Number(row.average_hold_seconds ?? 0) / 3600, 2)}h</span>
                </div>
              </div>
            )) ?? <div className="text-muted">No strategy cohorts yet.</div>}
          </div>
        </Panel>

        <Panel title="Run Comparison">
          <div className="space-y-2 font-mono text-xs">
            <Metric label={`${symbol} runs`} value={String(filteredRuns.length)} />
            <Metric label="Avg return" value={`${formatNumber(averageReturnPct, 2)}%`} />
            <Metric label="Best return" value={`${formatNumber(bestReturnPct, 2)}%`} />
            <Metric label="Worst return" value={`${formatNumber(worstReturnPct, 2)}%`} />
            <Metric label="Avg range" value={`${formatNumber(averageRangePct, 2)}%`} />
            <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
              <div className="text-muted">Strategy mix</div>
              <div className="mt-1 flex flex-wrap gap-2 text-secondary">
                {Object.entries(strategyCounts).length === 0 ? (
                  <span>No runs yet.</span>
                ) : (
                  Object.entries(strategyCounts).map(([name, count]) => (
                    <span key={name}>{name} {count}</span>
                  ))
                )}
              </div>
            </div>
          </div>
        </Panel>
      </div>

      <div className="grid gap-3 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel title="Walk-Forward">
          <div className="space-y-3">
            <div className="rounded border border-white/10 bg-black/20 px-3 py-2 text-sm text-secondary">
              Rolling window evaluation over the current candle set. This is the first research slice beyond single-run summaries.
            </div>
            <div className="grid gap-2 sm:grid-cols-4">
              <input value={walkForwardLookback} onChange={(event) => setWalkForwardLookback(event.target.value)} className="h-10 rounded border border-white/10 bg-black/20 px-3 text-primary" placeholder="lookback" />
              <input value={walkForwardTrain} onChange={(event) => setWalkForwardTrain(event.target.value)} className="h-10 rounded border border-white/10 bg-black/20 px-3 text-primary" placeholder="train" />
              <input value={walkForwardTest} onChange={(event) => setWalkForwardTest(event.target.value)} className="h-10 rounded border border-white/10 bg-black/20 px-3 text-primary" placeholder="test" />
              <input value={walkForwardStep} onChange={(event) => setWalkForwardStep(event.target.value)} className="h-10 rounded border border-white/10 bg-black/20 px-3 text-primary" placeholder="step" />
            </div>
            <button
              type="button"
              disabled={loading}
              onClick={() => {
                setLoading(true);
                void runBacktestWalkForward({
                  symbol,
                  timeframe,
                  strategy_name: strategyName,
                  lookback_limit: Number(walkForwardLookback) || 720,
                  train_size: Number(walkForwardTrain) || 240,
                  test_size: Number(walkForwardTest) || 60,
                  step_size: Number(walkForwardStep) || 60,
                })
                  .then(setWalkForward)
                  .finally(() => setLoading(false));
              }}
              className="h-11 w-full rounded border border-cyan/30 bg-cyan/10 font-mono text-xs text-cyan disabled:opacity-60"
            >
              {loading ? "RUNNING..." : `RUN WALK-FORWARD ${symbol} ${timeframe}`}
            </button>
          </div>
        </Panel>

        <Panel title="Walk-Forward Result">
          {walkForward ? (
            <div className="space-y-3">
              <div className="grid gap-2 sm:grid-cols-3 xl:grid-cols-6">
                <Metric label="Windows" value={String(walkForward.windows_count)} />
                <Metric label="Positive" value={String(walkForward.positive_windows_count)} />
                <Metric label="Avg return %" value={formatNumber(walkForward.average_return_pct, 2)} />
                <Metric label="Best %" value={formatNumber(walkForward.best_return_pct, 2)} />
                <Metric label="Worst %" value={formatNumber(walkForward.worst_return_pct, 2)} />
                <Metric label="Avg DD %" value={formatNumber(walkForward.average_drawdown_pct, 2)} />
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-left font-mono text-xs">
                  <thead className="text-muted">
                    <tr>
                      <th className="pb-2 pr-3">Window</th>
                      <th className="pb-2 pr-3">Test Start</th>
                      <th className="pb-2 pr-3">Return %</th>
                      <th className="pb-2 pr-3">DD %</th>
                      <th className="pb-2 pr-3">Vol %</th>
                      <th className="pb-2 pr-3">Trades</th>
                    </tr>
                  </thead>
                  <tbody className="text-secondary">
                    {walkForward.windows.slice(0, 8).map((window) => (
                      <tr key={`wf-${window.window_index}`} className="border-t border-white/10">
                        <td className="py-2 pr-3 text-primary">#{window.window_index}</td>
                        <td className="py-2 pr-3">{new Date(window.test_start).toLocaleString("en-GB", { hour12: false, timeZone: "UTC" })}</td>
                        <td className="py-2 pr-3">{formatNumber(window.return_pct, 2)}</td>
                        <td className="py-2 pr-3">{formatNumber(window.max_drawdown_pct, 2)}</td>
                        <td className="py-2 pr-3">{formatNumber(window.volatility_pct, 2)}</td>
                        <td className="py-2 pr-3">{window.trades_count ?? "--"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="text-sm text-muted">No walk-forward run yet.</div>
          )}
        </Panel>
      </div>

      <Panel title={`Result Filters / ${symbol}`}>
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <select
            value={resultStrategyFilter}
            onChange={(event) => {
              const next = event.target.value;
              setResultStrategyFilter(next);
              void loadOverview(symbol, next, resultTimeframeFilter);
            }}
            className="h-10 rounded border border-white/10 bg-black/20 px-3 text-primary"
          >
            <option value="all">All strategies</option>
            {availableStrategies.map((strategy) => (
              <option key={strategy} value={strategy}>
                {strategy}
              </option>
            ))}
          </select>
          <select
            value={resultTimeframeFilter}
            onChange={(event) => {
              const next = event.target.value;
              setResultTimeframeFilter(next);
              void loadOverview(symbol, resultStrategyFilter, next);
            }}
            className="h-10 rounded border border-white/10 bg-black/20 px-3 text-primary"
          >
            <option value="all">All timeframes</option>
            {availableTimeframes.map((tf) => (
              <option key={tf} value={tf}>
                {tf}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => {
              setResultStrategyFilter("all");
              setResultTimeframeFilter("all");
              void loadOverview(symbol, "all", "all");
            }}
            className="h-10 rounded border border-white/10 bg-black/20 px-3 font-mono text-xs text-secondary"
          >
            RESET FILTERS
          </button>
          <div className="rounded border border-white/10 bg-black/25 px-3 py-2 font-mono text-xs text-secondary">
            {filteredRuns.length} filtered runs
          </div>
        </div>
      </Panel>

      <Panel title={`Latest Run Diagnostics / ${symbol}`}>
        {latestRun ? (
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <Metric label="Benchmark" value={String((latestRun.summary_payload.benchmark as string | undefined) ?? latestRun.strategy_name)} />
            <Metric label="Drawdown" value={`${formatNumber(String((latestRun.summary_payload.max_drawdown_pct as string | undefined) ?? "--"), 2)}%`} />
            <Metric label="Volatility" value={`${formatNumber(String((latestRun.summary_payload.volatility_pct as string | undefined) ?? "--"), 2)}%`} />
            <Metric label="Trend efficiency" value={`${formatNumber(String((latestRun.summary_payload.trend_efficiency_pct as string | undefined) ?? "--"), 2)}%`} />
            <Metric label="Positive candles" value={`${formatNumber(String((latestRun.summary_payload.positive_candles_pct as string | undefined) ?? "--"), 2)}%`} />
            <Metric label="Close bias" value={`${formatNumber(String((latestRun.summary_payload.open_to_close_bias_pct as string | undefined) ?? "--"), 2)}%`} />
            <Metric label="Range trades" value={String((latestRun.summary_payload.trades_count as number | undefined) ?? 0)} />
            <Metric label="Range win rate" value={`${formatNumber(String((latestRun.summary_payload.win_rate_pct as string | undefined) ?? "--"), 2)}%`} />
          </div>
        ) : (
          <div className="text-sm text-muted">No diagnostic run available for {symbol}.</div>
        )}
      </Panel>

      <Panel title="Recent Backtest Runs">
        <div className="space-y-2 font-mono text-xs">
          {runs.length === 0 ? (
            <div className="text-muted">No persisted backtest runs yet.</div>
          ) : (
            runs.map((run) => (
              <div key={run.id} className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-primary">#{run.id} {run.symbol} {run.timeframe} / {run.strategy_name}</span>
                  <span className="text-secondary">{run.status}</span>
                </div>
                <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-secondary">
                  <span>bars {run.sample_size}</span>
                  <span>return {formatNumber(String((run.summary_payload.return_pct as string | undefined) ?? "--"), 2)}%</span>
                  <span>range {formatNumber(String((run.summary_payload.average_range_pct as string | undefined) ?? "--"), 2)}%</span>
                  <span>dd {formatNumber(String((run.summary_payload.max_drawdown_pct as string | undefined) ?? "--"), 2)}%</span>
                  <span>vol {formatNumber(String((run.summary_payload.volatility_pct as string | undefined) ?? "--"), 2)}%</span>
                  <span>start {String((run.summary_payload.start_price as string | undefined) ?? "--")}</span>
                  <span>end {String((run.summary_payload.end_price as string | undefined) ?? "--")}</span>
                  {(run.summary_payload.trades_count as number | undefined) !== undefined ? (
                    <span>trades {String(run.summary_payload.trades_count)}</span>
                  ) : null}
                </div>
              </div>
            ))
          )}
        </div>
      </Panel>

      <Panel title={`Compare Runs / ${symbol}`}>
        {sortedComparisonRuns.length === 0 ? (
          <div className="text-sm text-muted">No runs available for {symbol}.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full font-mono text-xs">
              <thead className="text-muted">
                <tr className="border-b border-white/10">
                  <th className="px-2 py-2 text-left">Run</th>
                  <th className="px-2 py-2 text-left">Strategy</th>
                  <th className="px-2 py-2 text-left">TF</th>
                  <th className="px-2 py-2 text-right">Bars</th>
                  <th className="px-2 py-2 text-right">Return</th>
                  <th className="px-2 py-2 text-right">Drawdown</th>
                  <th className="px-2 py-2 text-right">Range</th>
                  <th className="px-2 py-2 text-right">Start</th>
                  <th className="px-2 py-2 text-right">End</th>
                </tr>
              </thead>
              <tbody>
                {sortedComparisonRuns.slice(0, 12).map((run) => {
                  const returnPct = numericMetric(run.summary_payload.return_pct);
                  return (
                    <tr key={run.id} className="border-b border-white/5">
                      <td className="px-2 py-2 text-primary">#{run.id}</td>
                      <td className="px-2 py-2 text-secondary">{run.strategy_name}</td>
                      <td className="px-2 py-2 text-secondary">{run.timeframe}</td>
                      <td className="px-2 py-2 text-right text-secondary">{run.sample_size}</td>
                      <td className={`px-2 py-2 text-right ${returnPct !== null && returnPct < 0 ? "text-loss" : "text-profit"}`}>
                        {formatNumber(returnPct, 2)}%
                      </td>
                      <td className="px-2 py-2 text-right text-secondary">
                        {formatNumber(numericMetric(run.summary_payload.max_drawdown_pct), 2)}%
                      </td>
                      <td className="px-2 py-2 text-right text-secondary">
                        {formatNumber(numericMetric(run.summary_payload.average_range_pct), 2)}%
                      </td>
                      <td className="px-2 py-2 text-right text-secondary">
                        {formatNumber(numericMetric(run.summary_payload.start_price), 4)}
                      </td>
                      <td className="px-2 py-2 text-right text-secondary">
                        {formatNumber(numericMetric(run.summary_payload.end_price), 4)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <div className="grid gap-3 xl:grid-cols-2">
        <Panel title={`Strategy Summary / ${symbol}`}>
          {strategySummaryRows.length === 0 ? (
            <div className="text-sm text-muted">No grouped strategy stats yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full font-mono text-xs">
                <thead className="text-muted">
                  <tr className="border-b border-white/10">
                    <th className="px-2 py-2 text-left">Strategy</th>
                    <th className="px-2 py-2 text-right">Runs</th>
                    <th className="px-2 py-2 text-right">Avg Return</th>
                    <th className="px-2 py-2 text-right">Best</th>
                    <th className="px-2 py-2 text-right">Worst</th>
                    <th className="px-2 py-2 text-right">Avg Range</th>
                    <th className="px-2 py-2 text-right">Avg Bars</th>
                  </tr>
                </thead>
                <tbody>
                  {strategySummaryRows.map((row) => (
                    <tr key={row.key} className="border-b border-white/5">
                      <td className="px-2 py-2 text-primary">{row.key}</td>
                      <td className="px-2 py-2 text-right text-secondary">{row.runs}</td>
                      <td className="px-2 py-2 text-right text-secondary">{formatNumber(row.avgReturn, 2)}%</td>
                      <td className="px-2 py-2 text-right text-profit">{formatNumber(row.bestReturn, 2)}%</td>
                      <td className="px-2 py-2 text-right text-loss">{formatNumber(row.worstReturn, 2)}%</td>
                      <td className="px-2 py-2 text-right text-secondary">{formatNumber(row.avgRange, 2)}%</td>
                      <td className="px-2 py-2 text-right text-secondary">{formatNumber(row.avgBars, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <Panel title={`Timeframe Summary / ${symbol}`}>
          {timeframeSummaryRows.length === 0 ? (
            <div className="text-sm text-muted">No grouped timeframe stats yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full font-mono text-xs">
                <thead className="text-muted">
                  <tr className="border-b border-white/10">
                    <th className="px-2 py-2 text-left">Timeframe</th>
                    <th className="px-2 py-2 text-right">Runs</th>
                    <th className="px-2 py-2 text-right">Avg Return</th>
                    <th className="px-2 py-2 text-right">Best</th>
                    <th className="px-2 py-2 text-right">Worst</th>
                    <th className="px-2 py-2 text-right">Avg Range</th>
                    <th className="px-2 py-2 text-right">Avg Bars</th>
                  </tr>
                </thead>
                <tbody>
                  {timeframeSummaryRows.map((row) => (
                    <tr key={row.key} className="border-b border-white/5">
                      <td className="px-2 py-2 text-primary">{row.key}</td>
                      <td className="px-2 py-2 text-right text-secondary">{row.runs}</td>
                      <td className="px-2 py-2 text-right text-secondary">{formatNumber(row.avgReturn, 2)}%</td>
                      <td className="px-2 py-2 text-right text-profit">{formatNumber(row.bestReturn, 2)}%</td>
                      <td className="px-2 py-2 text-right text-loss">{formatNumber(row.worstReturn, 2)}%</td>
                      <td className="px-2 py-2 text-right text-secondary">{formatNumber(row.avgRange, 2)}%</td>
                      <td className="px-2 py-2 text-right text-secondary">{formatNumber(row.avgBars, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-white/10 bg-black/25 px-3 py-2 font-mono text-xs">
      <div className="text-muted">{label}</div>
      <div className="mt-1 text-primary">{value}</div>
    </div>
  );
}
