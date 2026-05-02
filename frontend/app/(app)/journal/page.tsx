"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  buildApiUrl,
  type ExecutionIntentLineageOutcomeResponse,
  type SpotExecutionChainLotCloseResponse,
  type SpotExecutionFillResponse,
  type SpotExecutionFillLotCloseResponse,
  type SpotExecutionFillSummaryResponse,
  getExecutionChainLotCloses,
  getExecutionFillLotCloses,
  getExecutionFills,
  getExecutionFillSummary,
  getExecutionIntentLineageOutcomes
} from "@/lib/api";

type JournalState = {
  summary: SpotExecutionFillSummaryResponse | null;
  fills: SpotExecutionFillResponse[];
  lineages: ExecutionIntentLineageOutcomeResponse[];
  error: string | null;
  updatedAt: string | null;
};

type FillDetailState = {
  fillId: number | null;
  loading: boolean;
  error: string | null;
  lotCloses: SpotExecutionFillLotCloseResponse[];
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

function formatTime(value: string) {
  return new Date(value).toLocaleString("en-GB", {
    hour12: false,
    timeZone: "UTC"
  });
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

function buildFillChainKey(fill: SpotExecutionFillResponse) {
  if (fill.client_order_id) {
    return `client:${fill.client_order_id}`;
  }
  if (fill.venue_order_id) {
    return `venue:${fill.venue_order_id}`;
  }
  return `fill:${fill.id}`;
}

export default function JournalPage() {
  const searchParams = useSearchParams();
  const [state, setState] = useState<JournalState>({
    summary: null,
    fills: [],
    lineages: [],
    error: null,
    updatedAt: null
  });

  const [strategyFilter, setStrategyFilter] = useState(() => searchParams.get("strategy") ?? "all");
  const [focusFilter, setFocusFilter] = useState(() => searchParams.get("focus") ?? "all");
  const intentIdFilter = searchParams.get("intent_id");
  const rootIntentIdFilter = searchParams.get("root_intent_id");
  const latestIntentIdFilter = searchParams.get("latest_intent_id");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [fillOffset, setFillOffset] = useState(0);
  const [lineageOffset, setLineageOffset] = useState(0);
  const [selectedFillId, setSelectedFillId] = useState<number | null>(null);
  const [selectedChainKey, setSelectedChainKey] = useState<string | null>(null);
  const [fillDetail, setFillDetail] = useState<FillDetailState>({
    fillId: null,
    loading: false,
    error: null,
    lotCloses: []
  });
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
        const pnlFilter =
          focusFilter === "winners" ? "winning" : focusFilter === "losers" ? "losing" : undefined;
        const startAt = startOfDayUtc(fromDate);
        const endAt = endOfDayUtc(toDate);
        const [summary, fills, lineages] = await Promise.all([
          getExecutionFillSummary(undefined, 500, 12, strategyFilter, pnlFilter, {
            startAt,
            endAt,
            recentChainsOffset: fillOffset,
            executionIntentId: intentIdFilter ? Number(intentIdFilter) : undefined
          }),
          getExecutionFills(undefined, 40, strategyFilter, pnlFilter, {
            startAt,
            endAt,
            offset: fillOffset,
            executionIntentId: intentIdFilter ? Number(intentIdFilter) : undefined
          }),
          getExecutionIntentLineageOutcomes(
            strategyFilter,
            undefined,
            12,
            {
              rootIntentId: rootIntentIdFilter ? Number(rootIntentIdFilter) : undefined,
              latestIntentId: latestIntentIdFilter ? Number(latestIntentIdFilter) : undefined,
              minLineageSize: focusFilter === "replacement-heavy" ? 2 : 1,
              flaggedOnly: focusFilter === "slippage-alert",
              minSlippageBps: focusFilter === "slippage-alert" ? 5 : undefined,
              underfilledOnly: focusFilter === "slippage-alert",
              startAt,
              endAt,
              offset: lineageOffset
            }
          )
        ]);
        if (!active) {
          return;
        }
        setState({
          summary,
          fills,
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
          error: error instanceof Error ? error.message : "journal load failed",
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
  }, [fillOffset, focusFilter, fromDate, intentIdFilter, latestIntentIdFilter, lineageOffset, rootIntentIdFilter, strategyFilter, toDate]);

  const summary = state.summary;
  const strategyOptions = useMemo(() => {
    return Array.from(
      new Set(
        [
          ...(summary?.recent_chains ?? []).map((chain) => chain.source_strategy ?? "unattributed"),
          ...state.fills.map((fill) => fill.source_strategy ?? "unattributed"),
          ...state.lineages.map((lineage) => lineage.source_strategy ?? "unattributed")
        ].filter(Boolean)
      )
    ).sort();
  }, [state.fills, state.lineages, summary?.recent_chains]);
  const filteredChains = summary?.recent_chains ?? [];
  const filteredFills = state.fills;
  const filteredLineages = state.lineages;
  const selectedFill = filteredFills.find((fill) => fill.id === selectedFillId) ?? null;
  const selectedChain = filteredChains.find((chain) => chain.chain_key === selectedChainKey) ?? null;
  const exportParams = useMemo(() => {
    const params = new URLSearchParams();
    const pnlFilter =
      focusFilter === "winners" ? "winning" : focusFilter === "losers" ? "losing" : undefined;
    const startAt = startOfDayUtc(fromDate);
    const endAt = endOfDayUtc(toDate);
    if (strategyFilter !== "all") {
      params.set("strategy", strategyFilter);
    }
    if (pnlFilter) {
      params.set("pnl_filter", pnlFilter);
    }
    if (startAt) {
      params.set("start_at", startAt);
    }
    if (endAt) {
      params.set("end_at", endAt);
    }
    return params;
  }, [focusFilter, fromDate, strategyFilter, toDate]);
  const lineageExportParams = useMemo(() => {
    const params = new URLSearchParams(exportParams);
    params.delete("pnl_filter");
    params.set("min_lineage_size", focusFilter === "replacement-heavy" ? "2" : "1");
    if (focusFilter === "slippage-alert") {
      params.set("flagged_only", "true");
      params.set("min_slippage_bps", "5");
      params.set("underfilled_only", "true");
    }
    return params;
  }, [exportParams, focusFilter]);

  useEffect(() => {
    if (selectedFillId === null) {
      setFillDetail({
        fillId: null,
        loading: false,
        error: null,
        lotCloses: []
      });
      return;
    }

    let active = true;
    setFillDetail((current) => ({
      ...current,
      fillId: selectedFillId,
      loading: true,
      error: null
    }));

    void getExecutionFillLotCloses(selectedFillId)
      .then((lotCloses) => {
        if (!active) {
          return;
        }
        setFillDetail({
          fillId: selectedFillId,
          loading: false,
          error: null,
          lotCloses
        });
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        setFillDetail({
          fillId: selectedFillId,
          loading: false,
          error: error instanceof Error ? error.message : "fill lot close load failed",
          lotCloses: []
        });
      });

    return () => {
      active = false;
    };
  }, [selectedFillId]);

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
            <div className="font-mono text-[11px] uppercase text-muted">Journal / Fill Ledger</div>
            <h1 className="mt-1 text-2xl font-semibold tracking-normal">Trade Journal</h1>
            <p className="mt-1 text-sm text-secondary">Order-chain summaries, strategy lineage, and fill-level realized PnL from synced venue state.</p>
          </div>
          <div className="font-mono text-[11px] uppercase text-muted">
            Updated {state.updatedAt ? formatTime(state.updatedAt) : "--"}
          </div>
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
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
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
            <div className="font-mono text-[11px] uppercase text-muted">Focus</div>
            <select
              value={focusFilter}
              onChange={(event) => setFocusFilter(event.target.value)}
              className="w-full rounded border border-white/10 bg-black/25 px-3 py-2 text-sm text-primary outline-none"
            >
              <option value="all">All outcomes</option>
              <option value="winners">Winning outcomes</option>
              <option value="losers">Losing outcomes</option>
              <option value="replacement-heavy">Replacement-heavy lineages</option>
              <option value="slippage-alert">Slippage / fill alerts</option>
            </select>
          </label>
          <label className="space-y-2">
            <div className="font-mono text-[11px] uppercase text-muted">From</div>
            <input
              type="date"
              value={fromDate}
              onChange={(event) => {
                setFromDate(event.target.value);
                setFillOffset(0);
                setLineageOffset(0);
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
                setFillOffset(0);
                setLineageOffset(0);
              }}
              className="w-full rounded border border-white/10 bg-black/25 px-3 py-2 text-sm text-primary outline-none"
            />
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

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <Panel title="Realized PnL">
          <div className={`text-2xl font-semibold ${Number(summary?.gross_realized_pnl_usd ?? 0) >= 0 ? "text-profit" : "text-loss"}`}>
            ${formatNumber(summary?.gross_realized_pnl_usd)}
          </div>
          <div className="mt-2 font-mono text-[11px] text-muted">{summary?.winning_fills_count ?? 0} wins / {summary?.losing_fills_count ?? 0} losses</div>
        </Panel>
        <Panel title="Fill Volume">
          <div className="text-2xl font-semibold">${formatNumber(summary?.gross_notional_usd)}</div>
          <div className="mt-2 font-mono text-[11px] text-muted">{summary?.fills_count ?? 0} fills across {summary?.traded_symbols_count ?? 0} symbols</div>
        </Panel>
        <Panel title="Chain Count">
          <div className="text-2xl font-semibold">{summary?.chains_count ?? 0}</div>
          <div className="mt-2 font-mono text-[11px] text-muted">Recent close sequences grouped by order identifiers</div>
        </Panel>
        <Panel title="Average Fill">
          <div className="text-2xl font-semibold">${formatNumber(summary?.average_fill_notional_usd)}</div>
          <div className="mt-2 font-mono text-[11px] text-muted">Avg realized ${formatNumber(summary?.average_realized_pnl_per_fill_usd)}</div>
        </Panel>
        <Panel title="Execution Cost">
          <div className={`text-2xl font-semibold ${Number(summary?.gross_adverse_slippage_cost_usd ?? 0) > 0 ? "text-warning" : "text-secondary"}`}>
            ${formatNumber(summary?.gross_adverse_slippage_cost_usd)}
          </div>
          <div className="mt-2 font-mono text-[11px] text-muted">Avg adverse {formatBps(summary?.average_adverse_slippage_bps)}</div>
        </Panel>
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel title="Recent Chains">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="font-mono text-[11px] uppercase text-muted">
                <tr>
                  <th className="pb-2">Chain</th>
                  <th className="pb-2">Strategy</th>
                  <th className="pb-2">Qty</th>
                  <th className="pb-2">Avg</th>
                  <th className="pb-2">Realized</th>
                  <th className="pb-2">Closed</th>
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
                    <td className="py-2">{formatNumber(chain.total_quantity, 4)}</td>
                    <td className="py-2">${formatNumber(chain.average_price)}</td>
                    <td className={`py-2 ${Number(chain.realized_pnl_usd) >= 0 ? "text-profit" : "text-loss"}`}>
                      ${formatNumber(chain.realized_pnl_usd)}
                    </td>
                    <td className="py-2 font-mono text-[11px] text-muted">{formatTime(chain.closed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Recent Fills">
          <div className="space-y-2">
            {filteredFills.map((fill) => (
              <div
                key={fill.id}
                className={`cursor-pointer rounded border px-3 py-2 ${selectedFillId === fill.id ? "border-cyan/40 bg-cyan/10" : "border-white/8 bg-white/[0.03]"}`}
                onClick={() => {
                  setSelectedFillId(fill.id);
                  setSelectedChainKey(buildFillChainKey(fill));
                }}
              >
                <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium text-primary">
                        {fill.symbol} <span className={fill.side === "BUY" ? "text-cyan" : "text-warning"}>{fill.side}</span>
                      </div>
                      <div className="font-mono text-[11px] text-muted">{fill.source_strategy ?? "unattributed"} / {fill.client_order_id ?? fill.venue_order_id ?? `fill-${fill.id}`}</div>
                    </div>
                  <div className={`text-sm font-semibold ${Number(fill.realized_pnl_usd) >= 0 ? "text-profit" : "text-loss"}`}>
                    ${formatNumber(fill.realized_pnl_usd)}
                  </div>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2 font-mono text-[11px] text-secondary">
                  <span>qty {formatNumber(fill.quantity, 4)}</span>
                  <span>px {formatNumber(fill.price)}</span>
                  <span>{formatTime(fill.filled_at)}</span>
                </div>
              </div>
            ))}
            <div className="flex items-center justify-between pt-2 font-mono text-[11px] text-muted">
              <button
                type="button"
                onClick={() => setFillOffset((current) => Math.max(current - 40, 0))}
                className="rounded border border-white/10 px-2 py-1 disabled:opacity-40"
                disabled={fillOffset === 0}
              >
                Prev
              </button>
              <span>fills offset {fillOffset}</span>
              <button
                type="button"
                onClick={() => setFillOffset((current) => current + 40)}
                className="rounded border border-white/10 px-2 py-1"
              >
                Next
              </button>
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="Chain Lot Closes">
        {selectedChain === null ? (
          <div className="text-sm text-muted">Select a chain to inspect aggregated FIFO lot consumption.</div>
        ) : chainDetail.loading ? (
          <div className="text-sm text-muted">Loading chain lot-close breakdown...</div>
        ) : chainDetail.error ? (
          <div className="text-sm text-loss">{chainDetail.error}</div>
        ) : chainDetail.detail === null ? (
          <div className="text-sm text-muted">No chain detail available.</div>
        ) : (
          <div className="space-y-3">
            <div className="grid gap-3 md:grid-cols-5">
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="font-mono text-[11px] uppercase text-muted">Closed Qty</div>
                <div className="mt-1 text-lg font-semibold">{formatNumber(chainDetail.detail.summary.total_closed_quantity, 4)}</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="font-mono text-[11px] uppercase text-muted">Realized</div>
                <div className={`mt-1 text-lg font-semibold ${Number(chainDetail.detail.summary.total_realized_pnl_usd) >= 0 ? "text-profit" : "text-loss"}`}>
                  ${formatNumber(chainDetail.detail.summary.total_realized_pnl_usd)}
                </div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="font-mono text-[11px] uppercase text-muted">Lot Slices</div>
                <div className="mt-1 text-lg font-semibold">{chainDetail.detail.summary.lot_slices_count}</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="font-mono text-[11px] uppercase text-muted">Avg Entry</div>
                <div className="mt-1 text-lg font-semibold">${formatNumber(chainDetail.detail.summary.weighted_average_entry_price)}</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="font-mono text-[11px] uppercase text-muted">Avg Exit</div>
                <div className="mt-1 text-lg font-semibold">${formatNumber(chainDetail.detail.summary.weighted_average_exit_price)}</div>
              </div>
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="font-mono text-[11px] uppercase text-muted">Avg Hold</div>
                <div className="mt-1 text-lg font-semibold">{formatDurationHours(chainDetail.detail.summary.average_hold_seconds)}</div>
              </div>
            </div>
            {chainDetail.detail.rows.length === 0 ? (
              <div className="text-sm text-muted">No lot-close rows for this chain. Open-only buy chains usually land here.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="font-mono text-[11px] uppercase text-muted">
                    <tr>
                      <th className="pb-2">Lot</th>
                      <th className="pb-2">Fill</th>
                      <th className="pb-2">Qty</th>
                      <th className="pb-2">Entry</th>
                      <th className="pb-2">Exit</th>
                      <th className="pb-2">Hold</th>
                      <th className="pb-2">PnL</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {chainDetail.detail.rows.map((row) => (
                      <tr key={row.id}>
                        <td className="py-2 font-mono text-[11px] text-muted">lot #{row.position_lot_id}</td>
                        <td className="py-2 font-mono text-[11px] text-muted">
                          {row.fill_client_order_id ?? row.fill_venue_order_id ?? `fill-${row.execution_fill_id}`}
                        </td>
                        <td className="py-2">{formatNumber(row.closed_quantity, 4)}</td>
                        <td className="py-2">${formatNumber(row.lot_entry_price)}</td>
                        <td className="py-2">${formatNumber(row.fill_exit_price)}</td>
                        <td className="py-2 font-mono text-[11px] text-muted">{formatDurationHours(row.hold_seconds)}</td>
                        <td className={`py-2 ${Number(row.realized_pnl_usd) >= 0 ? "text-profit" : "text-loss"}`}>
                          ${formatNumber(row.realized_pnl_usd)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </Panel>

      <Panel title="Fill Lot Closes">
        {selectedFill === null ? (
          <div className="text-sm text-muted">Select a fill to inspect FIFO lot-close slices.</div>
        ) : fillDetail.loading ? (
          <div className="text-sm text-muted">Loading lot-close breakdown...</div>
        ) : fillDetail.error ? (
          <div className="text-sm text-loss">{fillDetail.error}</div>
        ) : fillDetail.lotCloses.length === 0 ? (
          <div className="text-sm text-muted">No lot-close rows for this fill. Buy fills usually open lots rather than close them.</div>
        ) : (
          <div className="space-y-2">
            <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
              <div className="font-medium text-primary">
                {selectedFill.symbol} / fill #{selectedFill.id}
              </div>
              <div className="mt-1 font-mono text-[11px] text-muted">
                {selectedFill.client_order_id ?? selectedFill.venue_order_id ?? "no-order-id"}
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="font-mono text-[11px] uppercase text-muted">
                  <tr>
                    <th className="pb-2">Lot</th>
                    <th className="pb-2">Qty</th>
                    <th className="pb-2">Entry</th>
                    <th className="pb-2">Exit</th>
                    <th className="pb-2">Hold</th>
                    <th className="pb-2">PnL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {fillDetail.lotCloses.map((lotClose) => (
                    <tr key={lotClose.id}>
                      <td className="py-2 font-mono text-[11px] text-muted">lot #{lotClose.position_lot_id}</td>
                      <td className="py-2">{formatNumber(lotClose.closed_quantity, 4)}</td>
                      <td className="py-2">${formatNumber(lotClose.lot_entry_price)}</td>
                      <td className="py-2">${formatNumber(lotClose.fill_exit_price)}</td>
                      <td className="py-2 font-mono text-[11px] text-muted">{formatDurationHours(lotClose.hold_seconds)}</td>
                      <td className={`py-2 ${Number(lotClose.realized_pnl_usd) >= 0 ? "text-profit" : "text-loss"}`}>
                        ${formatNumber(lotClose.realized_pnl_usd)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Panel>

      <Panel title="Replacement Lineages">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="font-mono text-[11px] uppercase text-muted">
              <tr>
                <th className="pb-2">Lineage</th>
                <th className="pb-2">Strategy</th>
                <th className="pb-2">Statuses</th>
                <th className="pb-2">Fill Ratio</th>
                <th className="pb-2">Slippage</th>
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
                      root {lineage.root_intent_id} {"->"} latest {lineage.latest_intent_id}
                    </div>
                  </td>
                  <td className="py-2 font-mono text-[11px] text-secondary">{lineage.source_strategy}</td>
                  <td className="py-2 font-mono text-[11px] text-muted">{lineage.lineage_statuses.join(" -> ")}</td>
                  <td className="py-2">{formatNumber(Number(lineage.fill_ratio) * 100, 1)}%</td>
                  <td className={`py-2 ${Number(lineage.slippage_bps ?? 0) <= 0 ? "text-profit" : "text-warning"}`}>
                    <div>{formatBps(lineage.slippage_bps)}</div>
                    <div className="font-mono text-[11px] text-muted">adv {formatBps(lineage.adverse_slippage_bps)}</div>
                  </td>
                  <td className="py-2">
                    <div className={Number(lineage.slippage_cost_usd) > 0 ? "text-warning" : "text-secondary"}>
                      ${formatNumber(lineage.slippage_cost_usd)}
                    </div>
                    <div className="font-mono text-[11px] text-muted">under ${formatNumber(lineage.underfill_notional_usd)}</div>
                  </td>
                  <td className={`py-2 ${Number(lineage.realized_pnl_usd) >= 0 ? "text-profit" : "text-loss"}`}>
                    ${formatNumber(lineage.realized_pnl_usd)}
                  </td>
                </tr>
              ))}
              {filteredLineages.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-4 text-center text-muted">
                    No replacement lineages recorded yet.
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
