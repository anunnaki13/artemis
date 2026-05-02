"use client";

import { useEffect, useMemo, useState } from "react";

import {
  buildApiUrl,
  type ExecutionIntentLineageOutcomeResponse,
  type ExecutionIntentOutcomeResponse,
  type ExecutionIntentResponse,
  type ExecutionVenueEventResponse,
  getExecutionIntentByOrderId,
  getExecutionIntentLineageOutcomes,
  getExecutionIntentOutcomes,
  getExecutionVenueEvents
} from "@/lib/api";

type LogsState = {
  events: ExecutionVenueEventResponse[];
  error: string | null;
  updatedAt: string | null;
};

type EventDetailState = {
  loading: boolean;
  error: string | null;
  eventId: number | null;
  intent: ExecutionIntentResponse | null;
  outcome: ExecutionIntentOutcomeResponse | null;
  lineage: ExecutionIntentLineageOutcomeResponse | null;
};

type StatusBucket = "all" | "accepted" | "partial" | "filled" | "cancelled" | "rejected" | "pending" | "unknown";
type ReconcileState = "all" | "pending" | "applied" | "ignored" | "unmatched";

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

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "--";
  }
  return new Date(value).toLocaleString("en-GB", {
    hour12: false,
    timeZone: "UTC"
  });
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

function toneClass(bucket: StatusBucket | ExecutionVenueEventResponse["status_bucket"]) {
  if (bucket === "rejected") {
    return "text-loss";
  }
  if (bucket === "cancelled") {
    return "text-warning";
  }
  if (bucket === "partial") {
    return "text-cyan";
  }
  if (bucket === "filled" || bucket === "accepted") {
    return "text-profit";
  }
  return "text-secondary";
}

function exportCsv(params: URLSearchParams) {
  window.open(buildApiUrl("/execution/venues/events/export", params), "_blank", "noopener,noreferrer");
}

function buildScopedReviewHref(path: string, options: {
  strategy?: string | null;
  focus?: string;
  intentId?: number | null;
  rootIntentId?: number | null;
  latestIntentId?: number | null;
}) {
  const params = new URLSearchParams();
  if (options.strategy) {
    params.set("strategy", options.strategy);
  }
  if (options.focus) {
    params.set("focus", options.focus);
  }
  if (options.intentId) {
    params.set("intent_id", String(options.intentId));
  }
  if (options.rootIntentId) {
    params.set("root_intent_id", String(options.rootIntentId));
  }
  if (options.latestIntentId) {
    params.set("latest_intent_id", String(options.latestIntentId));
  }
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export default function LogsPage() {
  const [state, setState] = useState<LogsState>({
    events: [],
    error: null,
    updatedAt: null
  });
  const [statusBucket, setStatusBucket] = useState<StatusBucket>("all");
  const [reconcileState, setReconcileState] = useState<ReconcileState>("all");
  const [symbol, setSymbol] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [detail, setDetail] = useState<EventDetailState>({
    loading: false,
    error: null,
    eventId: null,
    intent: null,
    outcome: null,
    lineage: null
  });

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const events = await getExecutionVenueEvents({
          limit: 40,
          offset,
          venue: "bybit",
          symbol: symbol || undefined,
          query: search || undefined,
          statusBucket: statusBucket === "all" ? undefined : statusBucket,
          reconcileState: reconcileState === "all" ? undefined : reconcileState
        });
        if (!active) {
          return;
        }
        setState({
          events,
          error: null,
          updatedAt: new Date().toISOString()
        });
      } catch (error) {
        if (!active) {
          return;
        }
        setState((current) => ({
          ...current,
          error: error instanceof Error ? error.message : "venue event load failed",
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
  }, [offset, reconcileState, search, statusBucket, symbol]);

  const filteredEvents = state.events;

  useEffect(() => {
    if (selectedEventId === null) {
      setDetail({
        loading: false,
        error: null,
        eventId: null,
        intent: null,
        outcome: null,
        lineage: null
      });
      return;
    }

    const event = filteredEvents.find((row) => row.id === selectedEventId);
    if (!event) {
      return;
    }
    if (!event.client_order_id && !event.venue_order_id) {
      setDetail({
        loading: false,
        error: "event has no order identifiers",
        eventId: event.id,
        intent: null,
        outcome: null,
        lineage: null
      });
      return;
    }

    let active = true;
    setDetail((current) => ({
      ...current,
      loading: true,
      error: null,
      eventId: event.id
    }));

    void (async () => {
      try {
        const intent = await getExecutionIntentByOrderId({
          clientOrderId: event.client_order_id,
          venueOrderId: event.venue_order_id
        });
        const [outcomes, lineages] = await Promise.all([
          getExecutionIntentOutcomes({ limit: 200 }),
          getExecutionIntentLineageOutcomes(undefined, undefined, 200)
        ]);
        if (!active) {
          return;
        }
        setDetail({
          loading: false,
          error: null,
          eventId: event.id,
          intent,
          outcome: outcomes.find((item) => item.execution_intent_id === intent.id) ?? null,
          lineage:
            lineages.find((item) => item.latest_intent_id === intent.id || item.root_intent_id === intent.id) ?? null
        });
      } catch (error) {
        if (!active) {
          return;
        }
        setDetail({
          loading: false,
          error: error instanceof Error ? error.message : "event detail load failed",
          eventId: event.id,
          intent: null,
          outcome: null,
          lineage: null
        });
      }
    })();

    return () => {
      active = false;
    };
  }, [filteredEvents, selectedEventId]);

  const statusSummary = useMemo(() => {
    return filteredEvents.reduce<Record<string, number>>((acc, event) => {
      acc[event.status_bucket] = (acc[event.status_bucket] ?? 0) + 1;
      return acc;
    }, {});
  }, [filteredEvents]);

  const exportParams = useMemo(() => {
    const params = new URLSearchParams({ limit: "200" });
    params.set("venue", "bybit");
    if (symbol) {
      params.set("symbol", symbol);
    }
    if (search) {
      params.set("query", search);
    }
    if (statusBucket !== "all") {
      params.set("status_bucket", statusBucket);
    }
    if (reconcileState !== "all") {
      params.set("reconcile_state", reconcileState);
    }
    params.set("offset", String(offset));
    return params;
  }, [offset, reconcileState, search, statusBucket, symbol]);

  const selectedEvent = filteredEvents.find((event) => event.id === selectedEventId) ?? null;

  return (
    <div className="space-y-3">
      <div className="market-panel rounded px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="font-mono text-[11px] uppercase text-muted">Logs / Bybit Venue Events</div>
            <h1 className="mt-1 text-2xl font-semibold tracking-normal">Venue Event Review</h1>
            <p className="mt-1 text-sm text-secondary">Review reject, cancel, partial-fill, and reconcile-state diagnostics from persisted Bybit execution events.</p>
          </div>
          <div className="font-mono text-[11px] uppercase text-muted">
            {state.updatedAt ? formatTimestamp(state.updatedAt) : "--"}
          </div>
        </div>
        {state.error ? (
          <div className="mt-3 rounded border border-loss/30 bg-loss/10 px-3 py-2 font-mono text-[11px] text-loss">
            {state.error}
          </div>
        ) : null}
      </div>

      <Panel title="Filters">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <label className="space-y-2">
            <div className="font-mono text-[11px] uppercase text-muted">Status Bucket</div>
            <select
              value={statusBucket}
              onChange={(event) => {
                setStatusBucket(event.target.value as StatusBucket);
                setOffset(0);
              }}
              className="w-full rounded border border-white/10 bg-black/25 px-3 py-2 text-sm text-primary outline-none"
            >
              <option value="all">All buckets</option>
              <option value="rejected">Rejected</option>
              <option value="cancelled">Cancelled</option>
              <option value="partial">Partial</option>
              <option value="accepted">Accepted</option>
              <option value="filled">Filled</option>
              <option value="pending">Pending</option>
              <option value="unknown">Unknown</option>
            </select>
          </label>
          <label className="space-y-2">
            <div className="font-mono text-[11px] uppercase text-muted">Reconcile State</div>
            <select
              value={reconcileState}
              onChange={(event) => {
                setReconcileState(event.target.value as ReconcileState);
                setOffset(0);
              }}
              className="w-full rounded border border-white/10 bg-black/25 px-3 py-2 text-sm text-primary outline-none"
            >
              <option value="all">All states</option>
              <option value="pending">Pending</option>
              <option value="applied">Applied</option>
              <option value="ignored">Ignored</option>
              <option value="unmatched">Unmatched</option>
            </select>
          </label>
          <label className="space-y-2">
            <div className="font-mono text-[11px] uppercase text-muted">Symbol</div>
            <input
              type="text"
              value={symbol}
              onChange={(event) => {
                setSymbol(event.target.value.toUpperCase());
                setOffset(0);
              }}
              placeholder="BTCUSDT"
              className="w-full rounded border border-white/10 bg-black/25 px-3 py-2 text-sm text-primary outline-none"
            />
          </label>
          <label className="space-y-2">
            <div className="font-mono text-[11px] uppercase text-muted">Search</div>
            <input
              type="text"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setOffset(0);
              }}
              placeholder="symbol, order id, retCode, retMsg"
              className="w-full rounded border border-white/10 bg-black/25 px-3 py-2 text-sm text-primary outline-none"
            />
          </label>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 font-mono text-[11px]">
          <button
            type="button"
            onClick={() => exportCsv(exportParams)}
            className="rounded border border-white/10 px-3 py-2 text-primary"
          >
            Export Venue Events CSV
          </button>
        </div>
      </Panel>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <Panel title="Rejected">
          <div className="text-2xl font-semibold text-loss">{statusSummary.rejected ?? 0}</div>
          <div className="mt-2 font-mono text-[11px] text-muted">venue rejects in current window</div>
        </Panel>
        <Panel title="Cancelled">
          <div className="text-2xl font-semibold text-warning">{statusSummary.cancelled ?? 0}</div>
          <div className="mt-2 font-mono text-[11px] text-muted">cancel acknowledgements and expiries</div>
        </Panel>
        <Panel title="Partial">
          <div className="text-2xl font-semibold text-cyan">{statusSummary.partial ?? 0}</div>
          <div className="mt-2 font-mono text-[11px] text-muted">non-terminal fills still in progress</div>
        </Panel>
        <Panel title="Applied">
          <div className="text-2xl font-semibold text-profit">
            {filteredEvents.filter((event) => event.reconcile_state === "applied").length}
          </div>
          <div className="mt-2 font-mono text-[11px] text-muted">events reconciled into intent state</div>
        </Panel>
        <Panel title="Unmatched">
          <div className="text-2xl font-semibold text-warning">
            {filteredEvents.filter((event) => event.reconcile_state === "unmatched").length}
          </div>
          <div className="mt-2 font-mono text-[11px] text-muted">events without intent linkage</div>
        </Panel>
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.15fr_0.85fr]">
      <Panel title="Venue Events">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="font-mono text-[11px] uppercase text-muted">
              <tr>
                <th className="pb-2">Event</th>
                <th className="pb-2">Bucket</th>
                <th className="pb-2">State</th>
                <th className="pb-2">Order IDs</th>
                <th className="pb-2">Diagnostics</th>
                <th className="pb-2">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredEvents.map((event) => (
                <tr
                  key={event.id}
                  className={`cursor-pointer ${selectedEventId === event.id ? "bg-white/[0.04]" : ""}`}
                  onClick={() => setSelectedEventId(event.id)}
                >
                  <td className="py-2">
                    <div className="font-medium text-primary">{event.symbol ?? "--"}</div>
                    <div className="font-mono text-[11px] text-muted">
                      {event.event_type} / {event.venue_status}
                    </div>
                  </td>
                  <td className={`py-2 font-mono text-[11px] uppercase ${toneClass(event.status_bucket)}`}>
                    {event.status_bucket}
                  </td>
                  <td className="py-2 font-mono text-[11px] text-secondary">{event.reconcile_state}</td>
                  <td className="py-2 font-mono text-[11px] text-muted">
                    <div>{event.client_order_id ?? "--"}</div>
                    <div>{event.venue_order_id ?? "--"}</div>
                  </td>
                  <td className="py-2">
                    <div className={event.ret_code !== null ? "text-warning" : "text-secondary"}>
                      {event.ret_code !== null ? `ret ${event.ret_code}` : "--"}
                    </div>
                    <div className="max-w-[320px] truncate font-mono text-[11px] text-muted">
                      {event.ret_msg ?? "no venue error message"}
                    </div>
                  </td>
                  <td className="py-2 font-mono text-[11px] text-muted">
                    <div>{formatTimestamp(event.created_at)}</div>
                    <div>recon {formatTimestamp(event.reconciled_at)}</div>
                  </td>
                </tr>
              ))}
              {filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-muted">
                    No venue events matched the current filters.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex items-center justify-between font-mono text-[11px] text-muted">
          <button
            type="button"
            onClick={() => setOffset((current) => Math.max(current - 40, 0))}
            className="rounded border border-white/10 px-2 py-1 disabled:opacity-40"
            disabled={offset === 0}
          >
            Prev
          </button>
          <span>offset {offset} / showing {filteredEvents.length}</span>
          <button
            type="button"
            onClick={() => setOffset((current) => current + 40)}
            className="rounded border border-white/10 px-2 py-1"
          >
            Next
          </button>
        </div>
      </Panel>

      <Panel title="Intent Drill-Down">
        {selectedEvent === null ? (
          <div className="text-sm text-muted">Select a venue event to inspect linked intent, outcome, and lineage context.</div>
        ) : (
          <div className="space-y-3">
            <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
              <div className="font-medium text-primary">{selectedEvent.symbol ?? "--"} / {selectedEvent.event_type}</div>
              <div className="mt-1 font-mono text-[11px] text-muted">
                {selectedEvent.client_order_id ?? "--"} / {selectedEvent.venue_order_id ?? "--"}
              </div>
              <div className={`mt-1 font-mono text-[11px] uppercase ${toneClass(selectedEvent.status_bucket)}`}>
                {selectedEvent.status_bucket} / {selectedEvent.reconcile_state}
              </div>
            </div>

            {detail.loading ? <div className="text-sm text-muted">Loading linked intent context...</div> : null}
            {detail.error ? <div className="text-sm text-loss">{detail.error}</div> : null}

            {detail.intent ? (
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-primary">Intent #{detail.intent.id}</span>
                  <span className="font-mono text-[11px] text-secondary">{detail.intent.status}</span>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 font-mono text-[11px] text-muted">
                  <span>{detail.intent.source_strategy}</span>
                  <span>{detail.intent.side}</span>
                  <span>approved ${formatNumber(detail.intent.approved_notional)}</span>
                  <span>entry ${formatNumber(detail.intent.entry_price)}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 font-mono text-[11px]">
                  <a
                    href={buildScopedReviewHref("/journal", {
                      strategy: detail.intent.source_strategy,
                      focus: selectedEvent?.status_bucket === "rejected" ? "losers" : undefined,
                      intentId: detail.intent.id
                    })}
                    className="rounded border border-white/10 px-3 py-2 text-primary"
                  >
                    Open Journal
                  </a>
                  <a
                    href={buildScopedReviewHref("/execution-quality", {
                      strategy: detail.intent.source_strategy,
                      focus:
                        selectedEvent?.status_bucket === "partial" || selectedEvent?.status_bucket === "cancelled"
                          ? "underfilled"
                          : selectedEvent?.status_bucket === "rejected"
                            ? "slippage-alert"
                            : undefined,
                      rootIntentId: detail.lineage?.root_intent_id ?? detail.intent.parent_intent_id ?? detail.intent.id,
                      latestIntentId: detail.lineage?.latest_intent_id ?? detail.intent.id
                    })}
                    className="rounded border border-white/10 px-3 py-2 text-primary"
                  >
                    Open Execution Quality
                  </a>
                </div>
              </div>
            ) : null}

            {detail.outcome ? (
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="font-medium text-primary">Outcome</div>
                <div className="mt-2 grid grid-cols-2 gap-2 font-mono text-[11px] text-muted">
                  <span>fills {detail.outcome.fills_count}</span>
                  <span>fill {formatNumber(Number(detail.outcome.fill_ratio) * 100, 1)}%</span>
                  <span>slip {detail.outcome.slippage_bps ? `${formatNumber(detail.outcome.slippage_bps, 2)} bps` : "--"}</span>
                  <span>adv {detail.outcome.adverse_slippage_bps ? `${formatNumber(detail.outcome.adverse_slippage_bps, 2)} bps` : "--"}</span>
                  <span>cost ${formatNumber(detail.outcome.slippage_cost_usd)}</span>
                  <span>under ${formatNumber(detail.outcome.underfill_notional_usd)}</span>
                  <span className={Number(detail.outcome.realized_pnl_usd) >= 0 ? "text-profit" : "text-loss"}>
                    pnl ${formatNumber(detail.outcome.realized_pnl_usd)}
                  </span>
                </div>
              </div>
            ) : null}

            {detail.lineage ? (
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="font-medium text-primary">Lineage</div>
                <div className="mt-1 font-mono text-[11px] text-muted">
                  {detail.lineage.root_intent_id} {"->"} {detail.lineage.latest_intent_id}
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 font-mono text-[11px] text-muted">
                  <span>size {detail.lineage.lineage_size}</span>
                  <span>fill {formatNumber(Number(detail.lineage.fill_ratio) * 100, 1)}%</span>
                  <span>slip {detail.lineage.slippage_bps ? `${formatNumber(detail.lineage.slippage_bps, 2)} bps` : "--"}</span>
                  <span>cost ${formatNumber(detail.lineage.slippage_cost_usd)}</span>
                  <span>under ${formatNumber(detail.lineage.underfill_notional_usd)}</span>
                  <span className={Number(detail.lineage.realized_pnl_usd) >= 0 ? "text-profit" : "text-loss"}>
                    pnl ${formatNumber(detail.lineage.realized_pnl_usd)}
                  </span>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </Panel>
      </div>
    </div>
  );
}
