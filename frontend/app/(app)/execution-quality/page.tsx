"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  buildApiUrl,
  type ExecutionIntentLineageOutcomeResponse,
  type SpotExecutionChainLotCloseResponse,
  type SpotExecutionFillSummaryResponse,
  getExecutionChainLotCloses,
  getExecutionFillSummary,
  getExecutionIntentLineageOutcomes
} from "@/lib/api";

type ExecutionQualityState = {
  summary: SpotExecutionFillSummaryResponse | null;
  lineages: ExecutionIntentLineageOutcomeResponse[];
  error: string | null;
  updatedAt: string | null;
};

type ChainDetailState = {
  chainKey: string | null;
  loading: boolean;
  error: string | null;
  detail: SpotExecutionChainLotCloseResponse | null;
};

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="market-panel scanline rounded">
      <div className="flex h-10 items-center border-b border-white/10 px-3">
        <h2 className="font-mono text-[11px] uppercase text-secondary">{title}</h2>
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

function formatPercent(value: number | string | null | undefined) {
  if (value === null || value === undefined) {
    return "--";
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return "--";
  }
  return `${(parsed * 100).toFixed(1)}%`;
}

function formatBps(value: number | string | null | undefined) {
  if (value === null || value === undefined) {
    return "--";
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return "--";
  }
  return `${parsed.toFixed(2)} bps`;
}

function toneClass(value: number) {
  if (value > 0) {
    return "text-profit";
  }
  if (value < 0) {
    return "text-loss";
  }
  return "text-secondary";
}

function formatDurationHours(value: number | string | null | undefined) {
  if (value === null || value === undefined) {
    return "--";
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return "--";
  }
  return `${(parsed / 3600).toFixed(2)}h`;
}

function startOfDayUtc(value: string) {
  return value ? `${value}T00:00:00.000Z` : undefined;
}

function endOfDayUtc(value: string) {
  return value ? `${value}T23:59:59.999Z` : undefined;
}

function exportCsv(path: string, params: URLSearchParams) {
  window.open(buildApiUrl(path, params), "_blank", "noopener,noreferrer");
}

export default function ExecutionQualityPage() {
  const searchParams = useSearchParams();
  const [state, setState] = useState<ExecutionQualityState>({
    summary: null,
    lineages: [],
    error: null,
    updatedAt: null
  });

  const [strategyFilter, setStrategyFilter] = useState(() => searchParams.get("strategy") ?? "all");
  const [lineageFocus, setLineageFocus] = useState(() => searchParams.get("focus") ?? "all");
  const [holdFocus, setHoldFocus] = useState<"all" | "short_better" | "long_better">("all");
  const [lineageSort, setLineageSort] = useState<"recent" | "hold_edge" | "realized" | "slippage">("hold_edge");
  const intentIdFilter = searchParams.get("intent_id");
  const rootIntentIdFilter = searchParams.get("root_intent_id");
  const latestIntentIdFilter = searchParams.get("latest_intent_id");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [lineageOffset, setLineageOffset] = useState(0);
  const [chainsOffset, setChainsOffset] = useState(0);
  const [selectedChainKey, setSelectedChainKey] = useState<string | null>(null);
  const [chainDetail, setChainDetail] = useState<ChainDetailState>({
    chainKey: null,
    loading: false,
    error: null,
    detail: null
  });

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const startAt = startOfDayUtc(fromDate);
        const endAt = endOfDayUtc(toDate);
        const lineageOptions =
          lineageFocus === "replacements"
            ? { minLineageSize: 2, startAt, endAt, offset: lineageOffset }
            : lineageFocus === "slippage-alert"
              ? { flaggedOnly: true, minSlippageBps: 5, startAt, endAt, offset: lineageOffset }
              : lineageFocus === "underfilled"
                ? { underfilledOnly: true, startAt, endAt, offset: lineageOffset }
                : { startAt, endAt, offset: lineageOffset };
        const [summary, lineages] = await Promise.all([
          getExecutionFillSummary(undefined, 500, 10, strategyFilter, undefined, {
            startAt,
            endAt,
            recentChainsOffset: chainsOffset,
            executionIntentId: intentIdFilter ? Number(intentIdFilter) : undefined
          }),
          getExecutionIntentLineageOutcomes(strategyFilter, undefined, 12, {
            ...lineageOptions,
            rootIntentId: rootIntentIdFilter ? Number(rootIntentIdFilter) : undefined,
            latestIntentId: latestIntentIdFilter ? Number(latestIntentIdFilter) : undefined
          })
        ]);
        if (!active) {
          return;
        }
        setState({
          summary,
          lineages,
          error: null,
          updatedAt: new Date().toISOString()
        });
      } catch (error) {
        if (!active) {
          return;
        }
        setState((current) => ({
          ...current,
          error: error instanceof Error ? error.message : "execution quality load failed",
          updatedAt: new Date().toISOString()
        }));
      }
    };

    void load();
    const timer = window.setInterval(() => void load(), 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [chainsOffset, fromDate, intentIdFilter, latestIntentIdFilter, lineageFocus, lineageOffset, rootIntentIdFilter, strategyFilter, toDate]);

  const summary = state.summary;
  const grossRealized = Number(summary?.gross_realized_pnl_usd ?? 0);
  const averageRealized = Number(summary?.average_realized_pnl_per_fill_usd ?? 0);
  const grossAdverseSlippage = Number(summary?.gross_adverse_slippage_cost_usd ?? 0);
  const shortHoldRealized = Number(summary?.short_hold_realized_pnl_usd ?? 0);
  const longHoldRealized = Number(summary?.long_hold_realized_pnl_usd ?? 0);
  const strategyOptions = useMemo(() => {
    return Array.from(
      new Set(
        [
          ...(summary?.strategy_breakdown ?? []).map((row) => row.source_strategy),
          ...(summary?.recent_chains ?? []).map((chain) => chain.source_strategy ?? "unattributed"),
          ...state.lineages.map((lineage) => lineage.source_strategy ?? "unattributed")
        ].filter(Boolean)
      )
    ).sort();
  }, [state.lineages, summary?.recent_chains, summary?.strategy_breakdown]);
  const filteredStrategyRows = useMemo(() => {
    const rows = summary?.strategy_breakdown ?? [];
    if (holdFocus === "all") {
      return rows;
    }
    return rows.filter((row) => {
      const shortPnl = Number(row.short_hold_realized_pnl_usd);
      const longPnl = Number(row.long_hold_realized_pnl_usd);
      return holdFocus === "short_better" ? shortPnl > longPnl : longPnl > shortPnl;
    });
  }, [holdFocus, summary?.strategy_breakdown]);
  const filteredChains = summary?.recent_chains ?? [];
  const filteredLineages = useMemo(() => {
    let rows = [...state.lineages];
    if (holdFocus !== "all") {
      rows = rows.filter((lineage) => {
        const shortPnl = Number(lineage.short_hold_realized_pnl_usd);
        const longPnl = Number(lineage.long_hold_realized_pnl_usd);
        return holdFocus === "short_better" ? shortPnl > longPnl : longPnl > shortPnl;
      });
    }
    rows.sort((left, right) => {
      if (lineageSort === "recent") {
        return new Date(right.latest_created_at).getTime() - new Date(left.latest_created_at).getTime();
      }
      if (lineageSort === "realized") {
        return Number(right.realized_pnl_usd) - Number(left.realized_pnl_usd);
      }
      if (lineageSort === "slippage") {
        return Number(right.slippage_bps ?? 0) - Number(left.slippage_bps ?? 0);
      }
      const leftEdge = Number(left.long_hold_realized_pnl_usd) - Number(left.short_hold_realized_pnl_usd);
      const rightEdge = Number(right.long_hold_realized_pnl_usd) - Number(right.short_hold_realized_pnl_usd);
      return Math.abs(rightEdge) - Math.abs(leftEdge);
    });
    return rows;
  }, [holdFocus, lineageSort, state.lineages]);
  const selectedChain = filteredChains.find((chain) => chain.chain_key === selectedChainKey) ?? null;
  const exportParams = useMemo(() => {
    const params = new URLSearchParams();
    const startAt = startOfDayUtc(fromDate);
    const endAt = endOfDayUtc(toDate);
    if (strategyFilter !== "all") {
      params.set("strategy", strategyFilter);
    }
    if (startAt) {
      params.set("start_at", startAt);
    }
    if (endAt) {
      params.set("end_at", endAt);
    }
    return params;
  }, [fromDate, strategyFilter, toDate]);
  const lineageExportParams = useMemo(() => {
    const params = new URLSearchParams(exportParams);
    if (lineageFocus === "replacements") {
      params.set("min_lineage_size", "2");
    }
    if (lineageFocus === "slippage-alert") {
      params.set("flagged_only", "true");
      params.set("min_slippage_bps", "5");
    }
    if (lineageFocus === "underfilled") {
      params.set("underfilled_only", "true");
    }
    return params;
  }, [exportParams, lineageFocus]);

  useEffect(() => {
    if (selectedChainKey === null) {
      setChainDetail({
        chainKey: null,
        loading: false,
        error: null,
        detail: null
      });
      return;
    }

    let active = true;
    setChainDetail({
      chainKey: selectedChainKey,
      loading: true,
      error: null,
      detail: null
    });

    void getExecutionChainLotCloses(selectedChainKey)
      .then((detail) => {
        if (!active) {
          return;
        }
        setChainDetail({
          chainKey: selectedChainKey,
          loading: false,
          error: null,
          detail
        });
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        setChainDetail({
          chainKey: selectedChainKey,
          loading: false,
          error: error instanceof Error ? error.message : "chain lot close load failed",
          detail: null
        });
      });

    return () => {
      active = false;
    };
  }, [selectedChainKey]);

  return (
    <div className="space-y-3">
      <div className="market-panel rounded px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="font-mono text-[11px] uppercase text-muted">Execution Quality / Ledger Analytics</div>
            <h1 className="mt-1 text-2xl font-semibold tracking-normal">Execution Quality</h1>
            <p className="mt-1 text-sm text-secondary">Fill win-rate, strategy cohorts, and close-chain quality from persisted execution fills.</p>
          </div>
          <div className="font-mono text-[11px] uppercase text-muted">{state.updatedAt ? new Date(state.updatedAt).toLocaleTimeString("en-GB", { hour12: false, timeZone: "UTC" }) : "--"} UTC</div>
        </div>
        {state.error ? (
          <div className="mt-3 rounded border border-loss/30 bg-loss/10 px-3 py-2 font-mono text-[11px] text-loss">
            {state.error}
          </div>
        ) : null}
        {intentIdFilter || rootIntentIdFilter || latestIntentIdFilter ? (
          <div className="mt-3 rounded border border-cyan/30 bg-cyan/10 px-3 py-2 font-mono text-[11px] text-cyan">
            scoped review
            {intentIdFilter ? ` / intent ${intentIdFilter}` : ""}
            {rootIntentIdFilter ? ` / root ${rootIntentIdFilter}` : ""}
            {latestIntentIdFilter ? ` / latest ${latestIntentIdFilter}` : ""}
          </div>
        ) : null}
      </div>

      <Panel title="Filters">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
          <label className="space-y-2">
            <div className="font-mono text-[11px] uppercase text-muted">Strategy</div>
            <select
              value={strategyFilter}
              onChange={(event) => setStrategyFilter(event.target.value)}
              className="w-full rounded border border-white/10 bg-black/25 px-3 py-2 text-sm text-primary outline-none"
            >
              <option value="all">All strategies</option>
              {strategyOptions.map((strategy) => (
                <option key={strategy} value={strategy}>
                  {strategy}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <div className="font-mono text-[11px] uppercase text-muted">Lineage Focus</div>
            <select
              value={lineageFocus}
              onChange={(event) => setLineageFocus(event.target.value)}
              className="w-full rounded border border-white/10 bg-black/25 px-3 py-2 text-sm text-primary outline-none"
            >
              <option value="all">All lineages</option>
              <option value="replacements">Replacement lineages</option>
              <option value="slippage-alert">Slippage alerts</option>
              <option value="underfilled">Underfilled lineages</option>
            </select>
          </label>
          <label className="space-y-2">
            <div className="font-mono text-[11px] uppercase text-muted">From</div>
            <input
              type="date"
              value={fromDate}
              onChange={(event) => {
                setFromDate(event.target.value);
                setLineageOffset(0);
                setChainsOffset(0);
              }}
              className="w-full rounded border border-white/10 bg-black/25 px-3 py-2 text-sm text-primary outline-none"
            />
          </label>
          <label className="space-y-2">
            <div className="font-mono text-[11px] uppercase text-muted">To</div>
            <input
              type="date"
              value={toDate}
              onChange={(event) => {
                setToDate(event.target.value);
                setLineageOffset(0);
                setChainsOffset(0);
              }}
              className="w-full rounded border border-white/10 bg-black/25 px-3 py-2 text-sm text-primary outline-none"
            />
          </label>
          <label className="space-y-2">
            <div className="font-mono text-[11px] uppercase text-muted">Hold Cohort</div>
            <select
              value={holdFocus}
              onChange={(event) => setHoldFocus(event.target.value as "all" | "short_better" | "long_better")}
              className="w-full rounded border border-white/10 bg-black/25 px-3 py-2 text-sm text-primary outline-none"
            >
              <option value="all">All hold cohorts</option>
              <option value="short_better">Short hold stronger</option>
              <option value="long_better">Long hold stronger</option>
            </select>
          </label>
          <label className="space-y-2">
            <div className="font-mono text-[11px] uppercase text-muted">Lineage Rank</div>
            <select
              value={lineageSort}
              onChange={(event) => setLineageSort(event.target.value as "recent" | "hold_edge" | "realized" | "slippage")}
              className="w-full rounded border border-white/10 bg-black/25 px-3 py-2 text-sm text-primary outline-none"
            >
              <option value="hold_edge">Hold edge</option>
              <option value="realized">Realized pnl</option>
              <option value="slippage">Slippage</option>
              <option value="recent">Most recent</option>
            </select>
          </label>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 font-mono text-[11px]">
          <button
            type="button"
            onClick={() => exportCsv("/execution/account/fills/export", exportParams)}
            className="rounded border border-white/10 px-3 py-2 text-primary"
          >
            Export Fills CSV
          </button>
          <button
            type="button"
            onClick={() => exportCsv("/execution/account/fills/chains/export", exportParams)}
            className="rounded border border-white/10 px-3 py-2 text-primary"
          >
            Export Chains CSV
          </button>
          <button
            type="button"
            onClick={() => exportCsv("/execution/intents/lineages/outcomes/export", lineageExportParams)}
            className="rounded border border-white/10 px-3 py-2 text-primary"
          >
            Export Lineages CSV
          </button>
        </div>
      </Panel>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <Panel title="Win Rate">
          <div className="text-2xl font-semibold">{formatPercent(summary?.win_rate)}</div>
          <div className="mt-2 font-mono text-[11px] text-muted">{summary?.winning_fills_count ?? 0} wins / {summary?.losing_fills_count ?? 0} losses</div>
        </Panel>
        <Panel title="Gross Realized">
          <div className={`text-2xl font-semibold ${toneClass(grossRealized)}`}>${formatNumber(summary?.gross_realized_pnl_usd)}</div>
          <div className="mt-2 font-mono text-[11px] text-muted">{summary?.fills_count ?? 0} fills processed</div>
        </Panel>
        <Panel title="Average Fill Notional">
          <div className="text-2xl font-semibold">${formatNumber(summary?.average_fill_notional_usd)}</div>
          <div className="mt-2 font-mono text-[11px] text-muted">Gross ${formatNumber(summary?.gross_notional_usd)}</div>
        </Panel>
        <Panel title="Average Realized">
          <div className={`text-2xl font-semibold ${toneClass(averageRealized)}`}>${formatNumber(summary?.average_realized_pnl_per_fill_usd)}</div>
          <div className="mt-2 font-mono text-[11px] text-muted">{summary?.chains_count ?? 0} order chains</div>
        </Panel>
        <Panel title="Execution Cost">
          <div className={`text-2xl font-semibold ${grossAdverseSlippage > 0 ? "text-warning" : "text-secondary"}`}>
            ${formatNumber(summary?.gross_adverse_slippage_cost_usd)}
          </div>
          <div className="mt-2 font-mono text-[11px] text-muted">Avg adverse {formatBps(summary?.average_adverse_slippage_bps)}</div>
        </Panel>
        <Panel title="Avg Hold">
          <div className="text-2xl font-semibold">{formatDurationHours(summary?.average_hold_seconds)}</div>
          <div className="mt-2 font-mono text-[11px] text-muted">
            {summary?.lot_closes_count ?? 0} lot closes / max {formatDurationHours(summary?.max_hold_seconds)}
          </div>
        </Panel>
      </div>

      <div className="grid gap-3 xl:grid-cols-[0.85fr_1.15fr]">
        <Panel title="Distribution">
          <div className="space-y-3">
            <MetricBar
              label="Winning fills"
              value={summary?.winning_fills_count ?? 0}
              total={summary?.fills_count ?? 0}
              tone="bg-profit"
            />
            <MetricBar
              label="Losing fills"
              value={summary?.losing_fills_count ?? 0}
              total={summary?.fills_count ?? 0}
              tone="bg-loss"
            />
            <MetricBar
              label="Flat fills"
              value={summary?.flat_fills_count ?? 0}
              total={summary?.fills_count ?? 0}
              tone="bg-secondary"
            />
          </div>
        </Panel>

        <Panel title="Strategy Breakdown">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="font-mono text-[11px] uppercase text-muted">
                <tr>
                  <th className="pb-2">Strategy</th>
                  <th className="pb-2">Fills</th>
                  <th className="pb-2">Win Rate</th>
                  <th className="pb-2">Realized</th>
                  <th className="pb-2">Slip Cost</th>
                  <th className="pb-2">Underfill</th>
                  <th className="pb-2">Avg Hold</th>
                  <th className="pb-2">Hold Cohort</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredStrategyRows.map((row) => (
                  <tr key={row.source_strategy}>
                    <td className="py-2 font-medium text-primary">{row.source_strategy}</td>
                    <td className="py-2">{row.fills_count}</td>
                    <td className="py-2">{formatPercent(row.win_rate)}</td>
                    <td className={`py-2 ${toneClass(Number(row.gross_realized_pnl_usd))}`}>
                      ${formatNumber(row.gross_realized_pnl_usd)}
                    </td>
                    <td className={`py-2 ${Number(row.gross_adverse_slippage_cost_usd) > 0 ? "text-warning" : "text-secondary"}`}>
                      ${formatNumber(row.gross_adverse_slippage_cost_usd)}
                      <div className="font-mono text-[11px] text-muted">{formatBps(row.average_adverse_slippage_bps)}</div>
                    </td>
                    <td className="py-2 text-warning">${formatNumber(row.gross_underfill_notional_usd)}</td>
                    <td className="py-2 font-mono text-[11px] text-muted">{formatDurationHours(row.average_hold_seconds)}</td>
                    <td className="py-2">
                      <div className={toneClass(Number(row.short_hold_realized_pnl_usd))}>
                        short ${formatNumber(row.short_hold_realized_pnl_usd)}
                      </div>
                      <div className={`font-mono text-[11px] ${toneClass(Number(row.long_hold_realized_pnl_usd))}`}>
                        long ${formatNumber(row.long_hold_realized_pnl_usd)}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Hold Cohorts">
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
              <div className="font-mono text-[11px] uppercase text-muted">Short Hold PnL</div>
              <div className={`mt-1 text-lg font-semibold ${toneClass(shortHoldRealized)}`}>
                ${formatNumber(summary?.short_hold_realized_pnl_usd)}
              </div>
              <div className="mt-1 font-mono text-[11px] text-muted">{'\u2264'} 1h cohort</div>
            </div>
            <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
              <div className="font-mono text-[11px] uppercase text-muted">Long Hold PnL</div>
              <div className={`mt-1 text-lg font-semibold ${toneClass(longHoldRealized)}`}>
                ${formatNumber(summary?.long_hold_realized_pnl_usd)}
              </div>
              <div className="mt-1 font-mono text-[11px] text-muted">&gt; 1h cohort</div>
            </div>
            <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
              <div className="font-mono text-[11px] uppercase text-muted">Hold Signal</div>
              <div className={`mt-1 text-lg font-semibold ${toneClass(longHoldRealized - shortHoldRealized)}`}>
                {longHoldRealized >= shortHoldRealized ? "long-held closes stronger" : "short-held closes stronger"}
              </div>
              <div className="mt-1 font-mono text-[11px] text-muted">
                avg lot pnl ${formatNumber(summary?.average_realized_pnl_per_lot_close_usd)}
              </div>
            </div>
          </div>
        </Panel>

        <Panel title="Recent Chain Outcomes">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="font-mono text-[11px] uppercase text-muted">
                <tr>
                  <th className="pb-2">Chain</th>
                  <th className="pb-2">Strategy</th>
                  <th className="pb-2">Fills</th>
                  <th className="pb-2">Notional</th>
                  <th className="pb-2">Realized</th>
                  <th className="pb-2">End Qty</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredChains.map((chain) => (
                  <tr
                    key={chain.chain_key}
                    className={`cursor-pointer ${selectedChainKey === chain.chain_key ? "bg-cyan/10" : ""}`}
                    onClick={() => setSelectedChainKey(chain.chain_key)}
                  >
                    <td className="py-2">
                      <div className="font-medium text-primary">{chain.symbol}</div>
                      <div className="font-mono text-[11px] text-muted">{chain.client_order_id ?? chain.venue_order_id ?? chain.chain_key}</div>
                    </td>
                    <td className="py-2 font-mono text-[11px] text-secondary">{chain.source_strategy ?? "unattributed"}</td>
                    <td className="py-2">{chain.fills_count}</td>
                    <td className="py-2">${formatNumber(chain.total_quote_quantity)}</td>
                    <td className={`py-2 ${toneClass(Number(chain.realized_pnl_usd))}`}>${formatNumber(chain.realized_pnl_usd)}</td>
                    <td className="py-2">{formatNumber(chain.ending_net_quantity, 4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex items-center justify-between font-mono text-[11px] text-muted">
            <button
              type="button"
              onClick={() => setChainsOffset((current) => Math.max(current - 10, 0))}
              className="rounded border border-white/10 px-2 py-1 disabled:opacity-40"
              disabled={chainsOffset === 0}
            >
              Prev
            </button>
            <span>chains offset {chainsOffset}</span>
            <button
              type="button"
              onClick={() => setChainsOffset((current) => current + 10)}
              className="rounded border border-white/10 px-2 py-1"
            >
              Next
            </button>
          </div>
        </Panel>
      </div>

      <Panel title="Lot Hold Cohort">
        {selectedChain === null ? (
          <div className="text-sm text-muted">Select a recent chain to inspect FIFO lot hold-time and close slices.</div>
        ) : chainDetail.loading ? (
          <div className="text-sm text-muted">Loading lot cohort detail...</div>
        ) : chainDetail.error ? (
          <div className="text-sm text-loss">{chainDetail.error}</div>
        ) : chainDetail.detail === null ? (
          <div className="text-sm text-muted">No lot cohort detail available.</div>
        ) : (
          <div className="space-y-3">
            <div className="grid gap-3 md:grid-cols-5">
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="font-mono text-[11px] uppercase text-muted">Chain</div>
                <div className="mt-1 text-lg font-semibold">{selectedChain.symbol}</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="font-mono text-[11px] uppercase text-muted">Lot Slices</div>
                <div className="mt-1 text-lg font-semibold">{chainDetail.detail.summary.lot_slices_count}</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="font-mono text-[11px] uppercase text-muted">Avg Hold</div>
                <div className="mt-1 text-lg font-semibold">{formatDurationHours(chainDetail.detail.summary.average_hold_seconds)}</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="font-mono text-[11px] uppercase text-muted">Max Hold</div>
                <div className="mt-1 text-lg font-semibold">{formatDurationHours(chainDetail.detail.summary.max_hold_seconds)}</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="font-mono text-[11px] uppercase text-muted">Realized</div>
                <div className={`mt-1 text-lg font-semibold ${toneClass(Number(chainDetail.detail.summary.total_realized_pnl_usd))}`}>
                  ${formatNumber(chainDetail.detail.summary.total_realized_pnl_usd)}
                </div>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="font-mono text-[11px] uppercase text-muted">
                  <tr>
                    <th className="pb-2">Lot</th>
                    <th className="pb-2">Hold</th>
                    <th className="pb-2">Qty</th>
                    <th className="pb-2">Entry</th>
                    <th className="pb-2">Exit</th>
                    <th className="pb-2">PnL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {chainDetail.detail.rows.map((row) => (
                    <tr key={row.id}>
                      <td className="py-2 font-mono text-[11px] text-muted">lot #{row.position_lot_id}</td>
                      <td className="py-2 font-mono text-[11px] text-muted">{formatDurationHours(row.hold_seconds)}</td>
                      <td className="py-2">{formatNumber(row.closed_quantity, 4)}</td>
                      <td className="py-2">${formatNumber(row.lot_entry_price)}</td>
                      <td className="py-2">${formatNumber(row.fill_exit_price)}</td>
                      <td className={`py-2 ${toneClass(Number(row.realized_pnl_usd))}`}>
                        ${formatNumber(row.realized_pnl_usd)}
                      </td>
                    </tr>
                  ))}
                  {chainDetail.detail.rows.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-4 text-center text-muted">
                        This chain has no closing lot slices yet.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Panel>

      <Panel title="Lineage Outcomes">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="font-mono text-[11px] uppercase text-muted">
                <tr>
                  <th className="pb-2">Lineage</th>
                  <th className="pb-2">Strategy</th>
                  <th className="pb-2">Replacements</th>
                  <th className="pb-2">Filled</th>
                  <th className="pb-2">Slip</th>
                  <th className="pb-2">Hold</th>
                  <th className="pb-2">Cost</th>
                  <th className="pb-2">Realized</th>
                </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredLineages.map((lineage) => (
                <tr key={`${lineage.root_intent_id}-${lineage.latest_intent_id}`}>
                  <td className="py-2">
                    <div className="font-medium text-primary">{lineage.symbol}</div>
                    <div className="font-mono text-[11px] text-muted">
                      {lineage.root_intent_id} {"->"} {lineage.latest_intent_id}
                    </div>
                  </td>
                  <td className="py-2 font-mono text-[11px] text-secondary">{lineage.source_strategy}</td>
                  <td className="py-2">{Math.max(lineage.lineage_size - 1, 0)}</td>
                  <td className="py-2">{formatPercent(lineage.fill_ratio)}</td>
                  <td className={`py-2 ${Number(lineage.slippage_bps ?? 0) <= 0 ? "text-profit" : "text-warning"}`}>
                    <div>{formatBps(lineage.slippage_bps)}</div>
                    <div className="font-mono text-[11px] text-muted">adv {formatBps(lineage.adverse_slippage_bps)}</div>
                  </td>
                  <td className="py-2">
                    <div className="font-mono text-[11px] text-muted">{formatDurationHours(lineage.average_hold_seconds)}</div>
                    <div className={`font-mono text-[11px] ${toneClass(Number(lineage.long_hold_realized_pnl_usd) - Number(lineage.short_hold_realized_pnl_usd))}`}>
                      short ${formatNumber(lineage.short_hold_realized_pnl_usd)} / long ${formatNumber(lineage.long_hold_realized_pnl_usd)}
                    </div>
                  </td>
                  <td className="py-2">
                    <div className={Number(lineage.slippage_cost_usd) > 0 ? "text-warning" : "text-secondary"}>
                      ${formatNumber(lineage.slippage_cost_usd)}
                    </div>
                    <div className="font-mono text-[11px] text-muted">under ${formatNumber(lineage.underfill_notional_usd)}</div>
                  </td>
                  <td className={`py-2 ${toneClass(Number(lineage.realized_pnl_usd))}`}>
                    ${formatNumber(lineage.realized_pnl_usd)}
                  </td>
                </tr>
              ))}
              {filteredLineages.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-4 text-center text-muted">
                    No replacement lineage outcomes yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex items-center justify-between font-mono text-[11px] text-muted">
          <button
            type="button"
            onClick={() => setLineageOffset((current) => Math.max(current - 12, 0))}
            className="rounded border border-white/10 px-2 py-1 disabled:opacity-40"
            disabled={lineageOffset === 0}
          >
            Prev
          </button>
          <span>lineages offset {lineageOffset}</span>
          <button
            type="button"
            onClick={() => setLineageOffset((current) => current + 12)}
            className="rounded border border-white/10 px-2 py-1"
          >
            Next
          </button>
        </div>
      </Panel>
    </div>
  );
}

function MetricBar({
  label,
  value,
  total,
  tone
}: {
  label: string;
  value: number;
  total: number;
  tone: string;
}) {
  const width = total > 0 ? `${Math.max((value / total) * 100, value > 0 ? 6 : 0)}%` : "0%";
  return (
    <div>
      <div className="mb-1 flex items-center justify-between font-mono text-[11px] uppercase text-secondary">
        <span>{label}</span>
        <span>{value}</span>
      </div>
      <div className="h-2 rounded bg-white/8">
        <div className={`h-2 rounded ${tone}`} style={{ width }} />
      </div>
    </div>
  );
}
