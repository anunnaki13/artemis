"use client";

import { useEffect, useState } from "react";

import {
  type BybitExecutionPreviewResponse,
  type CandleResponse,
  type DashboardSummaryResponse,
  type ExecutionDispatchResponse,
  type ExecutionIntentResponse,
  type ExecutionTimeoutSweepResponse,
  type ExecutionVenueEventResponse,
  type MarketStreamStatusResponse,
  type OrderBookResponse,
  type RecoveryEventResponse,
  type SpotAccountBalanceResponse,
  type SpotSymbolPositionResponse,
  cancelExecutionIntent,
  dispatchNextExecutionIntent,
  failStaleExecutionIntents,
  getCandles,
  getDashboardSummary,
  getExecutionIntents,
  getBybitExecutionPreview,
  getExecutionVenueEvents,
  getMarketStreamStatus,
  getOrderbook,
  getRecoveryStatus,
  getSpotAccountBalances,
  getSpotSymbolPositions,
  updateExecutionIntentStatus,
  runRecoveryCheck,
} from "@/lib/api";

function formatNumber(value: string | number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "--";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "--";
  return parsed.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function buildPath(candles: CandleResponse[]) {
  const values = [...candles].reverse().map((item) => Number(item.close)).filter((value) => Number.isFinite(value));
  if (values.length === 0) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || 1;
  return values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * 1000;
      const y = 500 - ((value - min) / spread) * 420;
      return `${index === 0 ? "M" : "L"}${x} ${y}`;
    })
    .join(" ");
}

function Box({ title, children, mode = "read only" }: { title: string; children: React.ReactNode; mode?: string }) {
  return (
    <section className="market-panel scanline rounded-xl">
      <div className="flex h-10 items-center justify-between border-b border-white/10 px-3">
        <h2 className="font-mono text-[11px] uppercase text-secondary">{title}</h2>
        <span className="font-mono text-[10px] uppercase text-muted">{mode}</span>
      </div>
      <div className="p-3">{children}</div>
    </section>
  );
}

export default function TerminalPage() {
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [orderbook, setOrderbook] = useState<OrderBookResponse | null>(null);
  const [candles, setCandles] = useState<CandleResponse[]>([]);
  const [stream, setStream] = useState<MarketStreamStatusResponse | null>(null);
  const [intents, setIntents] = useState<ExecutionIntentResponse[]>([]);
  const [selectedIntent, setSelectedIntent] = useState<ExecutionIntentResponse | null>(null);
  const [preview, setPreview] = useState<BybitExecutionPreviewResponse | null>(null);
  const [balances, setBalances] = useState<SpotAccountBalanceResponse[]>([]);
  const [positions, setPositions] = useState<SpotSymbolPositionResponse[]>([]);
  const [venueEvents, setVenueEvents] = useState<ExecutionVenueEventResponse[]>([]);
  const [recovery, setRecovery] = useState<RecoveryEventResponse | null>(null);
  const [actionResult, setActionResult] = useState<string | null>(null);

  const load = async (preserveIntentId?: number | null) => {
    const [summaryResult, orderbookResult, candlesResult, streamResult, intentsResult, balancesResult, positionsResult, venueEventsResult, recoveryResult] = await Promise.allSettled([
      getDashboardSummary(),
      getOrderbook("BTCUSDT", 8),
      getCandles("BTCUSDT", "1m", 80),
      getMarketStreamStatus(),
      getExecutionIntents(20),
      getSpotAccountBalances(10),
      getSpotSymbolPositions(10, true),
      getExecutionVenueEvents({ limit: 8, venue: "bybit" }),
      getRecoveryStatus(),
    ]);
    if (summaryResult.status === "fulfilled") setSummary(summaryResult.value);
    if (orderbookResult.status === "fulfilled") setOrderbook(orderbookResult.value);
    if (candlesResult.status === "fulfilled") setCandles(candlesResult.value);
    if (streamResult.status === "fulfilled") setStream(streamResult.value);
    if (balancesResult.status === "fulfilled") setBalances(balancesResult.value);
    if (positionsResult.status === "fulfilled") setPositions(positionsResult.value);
    if (venueEventsResult.status === "fulfilled") setVenueEvents(venueEventsResult.value);
    if (recoveryResult.status === "fulfilled") setRecovery(recoveryResult.value);
    if (intentsResult.status === "fulfilled") {
      setIntents(intentsResult.value);
      const nextSelected =
        intentsResult.value.find((item) => item.id === preserveIntentId) ??
        intentsResult.value[0] ??
        null;
      setSelectedIntent(nextSelected);
    }
  };

  useEffect(() => {
    let active = true;
    void load();
    const timer = window.setInterval(() => void load(), 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!selectedIntent) {
      setPreview(null);
      return;
    }
    let active = true;
    void getBybitExecutionPreview(selectedIntent.id)
      .then((result) => {
        if (active) setPreview(result);
      })
      .catch(() => {
        if (active) setPreview(null);
      });
    return () => {
      active = false;
    };
  }, [selectedIntent]);

  const latest = candles[0] ?? null;
  const prev = candles[1] ?? null;
  const delta =
    latest && prev && Number(prev.close) !== 0
      ? ((Number(latest.close) - Number(prev.close)) / Number(prev.close)) * 100
      : null;
  const chart = buildPath(candles);
  const canApprove = selectedIntent?.status === "queued";
  const canReject = selectedIntent?.status === "queued";
  const canDispatch = selectedIntent?.status === "approved";
  const canCancel = selectedIntent ? ["queued", "approved", "dispatching"].includes(selectedIntent.status) : false;
  const canFailStale = intents.some((intent) => intent.status === "dispatching");
  const selectedRetCode = selectedIntent?.execution_payload?.ret_code;
  const selectedRetMsg = selectedIntent?.execution_payload?.ret_msg;
  const incidentIntents = intents.filter((intent) => ["failed", "cancelled", "rejected", "dispatching"].includes(intent.status));
  const incidentCounts = {
    failed: incidentIntents.filter((intent) => intent.status === "failed").length,
    rejected: incidentIntents.filter((intent) => intent.status === "rejected").length,
    cancelled: incidentIntents.filter((intent) => intent.status === "cancelled").length,
    dispatching: incidentIntents.filter((intent) => intent.status === "dispatching").length,
  };
  const auditTrail = [
    ...intents.map((intent) => ({
      kind: "intent" as const,
      sortAt: intent.updated_at ?? intent.created_at,
      id: `intent-${intent.id}`,
      title: `intent #${intent.id} ${intent.symbol}`,
      subtitle: `${intent.status} / ${intent.source_strategy}`,
      detail:
        intent.execution_payload?.ret_msg
          ? String(intent.execution_payload.ret_msg)
          : `${intent.side} / $${formatNumber(intent.approved_notional, 2)}`,
      tone:
        intent.status === "executed"
          ? "text-profit"
          : intent.status === "failed" || intent.status === "rejected" || intent.status === "cancelled"
            ? "text-loss"
            : "text-warning",
      onSelect: () => setSelectedIntent(intent),
    })),
    ...venueEvents.map((event) => ({
      kind: "event" as const,
      sortAt: event.created_at,
      id: `event-${event.id}`,
      title: `${event.symbol ?? "--"} ${event.event_type}`,
      subtitle: `${event.status_bucket} / ${event.venue_status}`,
      detail: event.ret_msg ? event.ret_msg : event.client_order_id ?? "venue event",
      tone: event.status_bucket === "rejected" ? "text-loss" : event.status_bucket === "partial" || event.status_bucket === "cancelled" ? "text-warning" : "text-secondary",
      onSelect: () => {
        if (event.execution_intent_id) {
          const matched = intents.find((intent) => intent.id === event.execution_intent_id);
          if (matched) {
            setSelectedIntent(matched);
          }
        }
      },
    })),
  ]
    .sort((left, right) => new Date(right.sortAt).getTime() - new Date(left.sortAt).getTime())
    .slice(0, 10);

  const handleApprove = async () => {
    if (!selectedIntent) return;
    const updated = await updateExecutionIntentStatus(selectedIntent.id, { status: "approved", notes: "approved from terminal" });
    setActionResult(`intent #${updated.id} approved`);
    await load(updated.id);
  };

  const handleReject = async () => {
    if (!selectedIntent) return;
    const updated = await updateExecutionIntentStatus(selectedIntent.id, { status: "rejected", notes: "rejected from terminal" });
    setActionResult(`intent #${updated.id} rejected`);
    await load(updated.id);
  };

  const handleCancel = async () => {
    if (!selectedIntent) return;
    const updated = await cancelExecutionIntent(selectedIntent.id, "cancelled from terminal");
    setActionResult(`intent #${updated.id} ${updated.status}`);
    await load(updated.id);
  };

  const handleDispatch = async () => {
    const result: ExecutionDispatchResponse = await dispatchNextExecutionIntent();
    setActionResult(result.detail);
    await load(result.intent?.id ?? selectedIntent?.id ?? null);
  };

  const handleFailStale = async () => {
    const result: ExecutionTimeoutSweepResponse = await failStaleExecutionIntents();
    setActionResult(
      result.timed_out_count > 0
        ? `${result.timed_out_count} dispatching intents marked failed`
        : "no stale dispatching intents found",
    );
    await load(selectedIntent?.id ?? null);
  };

  const handleRecoveryCheck = async () => {
    setActionResult(null);
    const event = await runRecoveryCheck();
    setRecovery(event);
    setActionResult(`recovery ${event.status} / ${event.flags.join(", ") || "no flags"}`);
    await load(selectedIntent?.id ?? null);
  };

  return (
    <div className="grid gap-3 xl:grid-cols-[1fr_340px]">
      <div className="space-y-3">
        <div className="quantum-hero rounded-2xl px-4 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="quantum-badge">Execution Terminal</div>
              <div className="mt-3 font-mono text-[11px] text-muted">BTCUSDT / BYBIT TERMINAL</div>
              <div className="mt-1 font-mono text-3xl font-semibold text-primary">
                {formatNumber(latest?.close, 2)}{" "}
                <span className={`text-base ${delta !== null && delta < 0 ? "text-loss" : "text-profit"}`}>
                  {delta === null ? "--" : `${formatNumber(delta, 2)}%`}
                </span>
              </div>
              <p className="quantum-subtitle mt-2">
                Queue controls, venue incidents, balances, positions, and recovery state are kept in one guarded operator surface.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2 font-mono text-[11px] text-secondary">
              <span className="rounded border border-white/10 bg-black/25 px-3 py-2">
                MID {formatNumber(orderbook?.metrics.mid_price, 2)}
              </span>
              <span className="rounded border border-white/10 bg-black/25 px-3 py-2">
                SPREAD {formatNumber(orderbook?.metrics.spread_bps, 2)}bps
              </span>
              <span className={`rounded border px-3 py-2 ${stream?.running ? "border-profit/30 bg-profit/10 text-profit" : "border-warning/30 bg-warning/10 text-warning"}`}>
                {stream?.running ? "STREAM ONLINE" : "STREAM STOPPED"}
              </span>
            </div>
          </div>
        </div>

        <Box title="Price Action">
          <div className="relative h-[520px] overflow-hidden rounded border border-white/10 bg-black/40">
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1000 520" preserveAspectRatio="none">
              {Array.from({ length: 11 }).map((_, index) => (
                <line key={`h-${index}`} x1="0" x2="1000" y1={index * 52} y2={index * 52} stroke="rgba(255,255,255,.055)" />
              ))}
              {Array.from({ length: 16 }).map((_, index) => (
                <line key={`v-${index}`} y1="0" y2="520" x1={index * 66} x2={index * 66} stroke="rgba(255,255,255,.04)" />
              ))}
              {chart ? <path d={chart} fill="none" stroke="#22f5a5" strokeWidth="3" /> : null}
            </svg>
            <div className="absolute right-3 top-3 rounded border border-white/10 bg-black/70 px-3 py-2 font-mono text-xs text-secondary">
              {summary?.bybit_runtime?.testnet ? "TESTNET" : "MAINNET"} / {summary?.execution_status ?? "IDLE"}
            </div>
          </div>
        </Box>
      </div>

      <div className="space-y-3">
        <Box title="Depth Ladder">
          <div className="space-y-1 font-mono text-xs">
            {orderbook?.asks.slice(0, 4).map((level) => (
              <div key={`ask-${level.price}`} className="grid grid-cols-3 rounded bg-loss/10 px-2 py-2 text-loss">
                <span>ASK</span>
                <span className="text-right">{formatNumber(level.price, 2)}</span>
                <span className="text-right">{formatNumber(level.quantity, 6)}</span>
              </div>
            ))}
            {orderbook?.bids.slice(0, 4).map((level) => (
              <div key={`bid-${level.price}`} className="grid grid-cols-3 rounded bg-profit/10 px-2 py-2 text-profit">
                <span>BID</span>
                <span className="text-right">{formatNumber(level.price, 2)}</span>
                <span className="text-right">{formatNumber(level.quantity, 6)}</span>
              </div>
            ))}
          </div>
        </Box>

        <Box title="Terminal State">
          <div className="space-y-2 font-mono text-xs">
            <StateRow label="Market stream" value={stream?.running ? "running" : "stopped"} />
            <StateRow label="User stream" value={summary?.user_stream.running ? (summary.user_stream.subscribed ? "synced" : "connecting") : "idle"} />
            <StateRow label="Venue" value={summary?.bybit_runtime?.testnet ? "Bybit testnet" : "Bybit mainnet"} />
            <StateRow label="Execution transport" value={summary?.bybit_runtime?.live_transport_enabled ? "live-enabled" : "safe-disabled"} />
            <StateRow label="Dispatching intents" value={String(incidentCounts.dispatching)} />
            <StateRow label="Failed intents" value={String(incidentCounts.failed)} />
          </div>
        </Box>

        <Box title="Recovery Monitor" mode="ops / recovery">
          <div className="space-y-2 font-mono text-xs">
            <StateRow label="Status" value={recovery?.status ?? "--"} />
            <StateRow label="Severity" value={recovery?.severity ?? "--"} />
            <StateRow label="Heartbeat" value={recovery?.heartbeat_ping_ok === null ? "--" : recovery?.heartbeat_ping_ok ? "ok" : "fail"} />
            <StateRow label="Flags" value={recovery?.flags.join(", ") || "none"} />
            <button
              type="button"
              onClick={() => void handleRecoveryCheck()}
              className="h-10 w-full rounded border border-white/10 bg-black/20 px-3 text-secondary"
            >
              RUN RECOVERY CHECK
            </button>
          </div>
        </Box>

        <Box title="Intent Preview" mode="guarded control">
          <div className="space-y-2 font-mono text-xs">
            <select
              value={selectedIntent?.id ?? ""}
              onChange={(event) => setSelectedIntent(intents.find((item) => item.id === Number(event.target.value)) ?? null)}
              className="h-10 w-full rounded border border-white/10 bg-black/20 px-3 text-primary"
            >
              {intents.map((intent) => (
                <option key={intent.id} value={intent.id}>
                  #{intent.id} {intent.symbol} {intent.status}
                </option>
              ))}
            </select>
            {preview ? (
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
                <div>{preview.symbol} / {preview.side} / {preview.transport_mode}</div>
                <div className="mt-1">clientOrderId {preview.client_order_id}</div>
                <div className="mt-1">base {preview.base_url}</div>
                  <div className="mt-1">status {selectedIntent?.status ?? "--"}</div>
                {selectedRetCode !== undefined && selectedRetCode !== null ? (
                  <div className="mt-1">retCode {String(selectedRetCode)} / {selectedRetMsg ? String(selectedRetMsg) : "--"}</div>
                ) : null}
                {selectedIntent?.execution_payload?.incident_type ? (
                  <div className="mt-1">
                    {String(selectedIntent.execution_payload.incident_type)} / {String(selectedIntent.execution_payload.suggested_action ?? "--")} / {String(selectedIntent.execution_payload.severity ?? "--")}
                    {selectedIntent.execution_payload.retryable ? " / retryable" : ""}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="text-muted">No preview available.</div>
            )}
            <div className="grid gap-2 sm:grid-cols-3">
              <button
                type="button"
                disabled={!canApprove}
                onClick={() => void handleApprove()}
                className="h-10 rounded border border-cyan/30 bg-cyan/10 px-3 text-cyan disabled:opacity-40"
              >
                APPROVE
              </button>
              <button
                type="button"
                disabled={!canReject}
                onClick={() => void handleReject()}
                className="h-10 rounded border border-loss/30 bg-loss/10 px-3 text-loss disabled:opacity-40"
              >
                REJECT
              </button>
              <button
                type="button"
                disabled={!canDispatch}
                onClick={() => void handleDispatch()}
                className="h-10 rounded border border-profit/30 bg-profit/10 px-3 text-profit disabled:opacity-40"
              >
                DISPATCH NEXT
              </button>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <button
                type="button"
                disabled={!canCancel}
                onClick={() => void handleCancel()}
                className="h-10 rounded border border-warning/30 bg-warning/10 px-3 text-warning disabled:opacity-40"
              >
                CANCEL
              </button>
              <button
                type="button"
                disabled={!canFailStale}
                onClick={() => void handleFailStale()}
                className="h-10 rounded border border-white/10 bg-black/20 px-3 text-secondary disabled:opacity-40"
              >
                FAIL STALE
              </button>
            </div>
            {actionResult ? <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">{actionResult}</div> : null}
          </div>
        </Box>

        <Box title="Intent History">
          <div className="space-y-1 font-mono text-xs">
            {intents.length === 0 ? (
              <div className="text-muted">No execution intents yet.</div>
            ) : (
              intents.map((intent) => {
                const tone =
                  intent.status === "executed"
                    ? "text-profit"
                    : intent.status === "rejected" || intent.status === "failed" || intent.status === "cancelled"
                      ? "text-loss"
                      : intent.status === "dispatching"
                        ? "text-warning"
                        : "text-secondary";
                const retCode = intent.execution_payload?.ret_code;
                const retMsg = intent.execution_payload?.ret_msg;
                return (
                  <button
                    key={intent.id}
                    type="button"
                    onClick={() => setSelectedIntent(intent)}
                    className={`w-full rounded border px-2 py-2 text-left ${
                      selectedIntent?.id === intent.id ? "border-cyan/40 bg-cyan/10" : "border-white/10 bg-black/25"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-primary">#{intent.id} {intent.symbol}</span>
                      <span className={tone}>{intent.status}</span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-secondary">
                      <span>{intent.source_strategy}</span>
                      <span>{intent.side}</span>
                      <span>${formatNumber(intent.approved_notional, 2)}</span>
                      {retCode !== undefined && retCode !== null ? <span>ret {String(retCode)}</span> : null}
                    </div>
                    {retMsg ? <div className="mt-1 text-muted">{String(retMsg)}</div> : null}
                  </button>
                );
              })
            )}
          </div>
        </Box>

        <Box title="Worker Incidents">
          <div className="space-y-2 font-mono text-xs">
            <div className="grid grid-cols-2 gap-2">
              <StateRow label="Rejected" value={String(incidentCounts.rejected)} />
              <StateRow label="Cancelled" value={String(incidentCounts.cancelled)} />
            </div>
            {incidentIntents.slice(0, 6).map((intent) => (
              <button
                key={`incident-${intent.id}`}
                type="button"
                onClick={() => setSelectedIntent(intent)}
                className="w-full rounded border border-white/10 bg-black/25 px-2 py-2 text-left"
              >
                <div className="flex items-center justify-between">
                  <span className="text-primary">#{intent.id} {intent.symbol}</span>
                  <span className={intent.status === "failed" || intent.status === "rejected" ? "text-loss" : "text-warning"}>
                    {intent.status}
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-secondary">
                  <span>{intent.source_strategy}</span>
                  <span>${formatNumber(intent.approved_notional, 2)}</span>
                  {intent.execution_payload?.ret_code !== undefined && intent.execution_payload?.ret_code !== null ? (
                    <span>ret {String(intent.execution_payload.ret_code)}</span>
                  ) : null}
                </div>
              </button>
            ))}
          </div>
        </Box>

        <Box title="Venue Incidents">
          <div className="space-y-1 font-mono text-xs">
            {venueEvents
              .filter((event) => ["partial", "cancelled", "rejected"].includes(event.status_bucket))
              .slice(0, 6)
              .map((event) => (
                <div key={event.id} className="rounded border border-white/10 bg-black/25 px-2 py-2">
                  <div className="flex items-center justify-between">
                    <span className="text-primary">{event.symbol ?? "--"} / {event.event_type}</span>
                    <span className={event.status_bucket === "rejected" ? "text-loss" : "text-warning"}>
                      {event.status_bucket}
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-secondary">
                    <span>{event.venue_status}</span>
                    {event.ret_code !== null ? <span>ret {event.ret_code}</span> : null}
                    {event.client_order_id ? <span>{event.client_order_id}</span> : null}
                  </div>
                  {event.ret_msg ? <div className="mt-1 text-muted">{event.ret_msg}</div> : null}
                </div>
              ))}
            {venueEvents.filter((event) => ["partial", "cancelled", "rejected"].includes(event.status_bucket)).length === 0 ? (
              <div className="text-muted">No recent venue incidents.</div>
            ) : null}
          </div>
        </Box>

        <Box title="Audit Trail">
          <div className="space-y-1 font-mono text-xs">
            {auditTrail.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={item.onSelect}
                className="w-full rounded border border-white/10 bg-black/25 px-2 py-2 text-left"
              >
                <div className="flex items-center justify-between">
                  <span className="text-primary">{item.title}</span>
                  <span className={item.tone}>{item.subtitle}</span>
                </div>
                <div className="mt-1 text-muted">{item.detail}</div>
              </button>
            ))}
            {auditTrail.length === 0 ? <div className="text-muted">No audit trail entries.</div> : null}
          </div>
        </Box>

        <Box title="Balances">
          <div className="space-y-1 font-mono text-xs">
            {balances.length === 0 ? (
              <div className="text-muted">No synced balances yet.</div>
            ) : (
              balances.slice(0, 6).map((balance) => (
                <div key={balance.asset} className="grid grid-cols-[1fr_auto_auto] gap-2 rounded border border-white/10 bg-black/25 px-2 py-2">
                  <span className="text-primary">{balance.asset}</span>
                  <span className="text-secondary">{formatNumber(balance.total, 6)}</span>
                  <span className="text-secondary">${formatNumber(balance.total_value_usd, 2)}</span>
                </div>
              ))
            )}
          </div>
        </Box>

        <Box title="Positions">
          <div className="space-y-1 font-mono text-xs">
            {positions.length === 0 ? (
              <div className="text-muted">No open symbol positions.</div>
            ) : (
              positions.slice(0, 6).map((position) => (
                <div key={position.symbol} className="rounded border border-white/10 bg-black/25 px-2 py-2">
                  <div className="flex items-center justify-between">
                    <span className="text-primary">{position.symbol}</span>
                    <span className={Number(position.unrealized_pnl_usd ?? 0) < 0 ? "text-loss" : "text-profit"}>
                      uPnL {formatNumber(position.unrealized_pnl_usd, 2)}
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-secondary">
                    <span>qty {formatNumber(position.net_quantity, 6)}</span>
                    <span>entry {formatNumber(position.average_entry_price, 4)}</span>
                    <span>mark {formatNumber(position.last_mark_price, 4)}</span>
                    <span>exp ${formatNumber(position.quote_exposure_usd, 2)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </Box>
      </div>
    </div>
  );
}

function StateRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded border border-white/10 bg-black/25 px-3 py-2">
      <span className="text-secondary">{label}</span>
      <span className="text-primary">{value}</span>
    </div>
  );
}
