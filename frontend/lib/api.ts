const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

type RegisterPayload = {
  email: string;
  password: string;
};

type LoginPayload = RegisterPayload & {
  totp_code: string;
};

export type RegisterResponse = {
  user_id: string;
  totp_secret: string;
  provisioning_uri: string;
};

export type UserSessionResponse = {
  user_id: string;
  email: string;
  role: string;
};

export type DashboardSummaryResponse = {
  equity: { net: number; currency: string };
  daily_pnl: { net: number; gross: number };
  weekly_pnl: { net: number; gross: number };
  bot_status: string;
  market_regime: string;
  execution_status: string;
  bybit_runtime: {
    configured: boolean;
    live_ready: boolean;
    testnet: boolean;
    live_transport_enabled: boolean;
    account_type: string | null;
    issues: string[];
  };
  exposure_notional: string;
  execution_counts: Record<string, number>;
  recent_intents: Array<{
    id: number;
    symbol: string;
    status: string;
    source_strategy: string;
    approved_notional: string;
    created_at: string;
    notes: string | null;
  }>;
  strategy_breakdown: Array<{
    source_strategy: string;
    fills_count: number;
    chains_count: number;
    gross_notional_usd: string;
    gross_realized_pnl_usd: string;
    win_rate: string;
    gross_adverse_slippage_cost_usd: string;
    average_adverse_slippage_bps: string;
    gross_underfill_notional_usd: string;
    average_hold_seconds: string | null;
    max_hold_seconds: string | null;
    lot_closes_count: number;
    short_hold_realized_pnl_usd: string;
    long_hold_realized_pnl_usd: string;
  }>;
  lineage_summary: {
    replacement_lineages_count: number;
    replacement_alerts_count: number;
    worst_slippage_bps: string | null;
  };
  venue_event_summary: {
    accepted: number;
    partial: number;
    filled: number;
    cancelled: number;
    rejected: number;
    pending: number;
    unknown: number;
  };
  lineage_alerts: Array<{
    root_intent_id: number;
    latest_intent_id: number;
    symbol: string;
    source_strategy: string;
    lineage_size: number;
    lineage_statuses: string[];
    fill_ratio: string;
    slippage_bps: string | null;
    realized_pnl_usd: string;
    average_hold_seconds: string | null;
    max_hold_seconds: string | null;
    short_hold_realized_pnl_usd: string;
    long_hold_realized_pnl_usd: string;
    last_fill_at: string | null;
  }>;
  hold_summary: {
    lot_closes_count: number;
    average_hold_seconds: string | null;
    max_hold_seconds: string | null;
    short_hold_realized_pnl_usd: string;
    long_hold_realized_pnl_usd: string;
  };
  venue_event_alerts: Array<{
    id: number;
    created_at: string;
    venue: string;
    event_type: string;
    venue_status: string;
    status_bucket: "accepted" | "partial" | "filled" | "cancelled" | "rejected" | "pending" | "unknown";
    symbol: string | null;
    client_order_id: string | null;
    venue_order_id: string | null;
    reconcile_state: string;
    ret_code: number | null;
    ret_msg: string | null;
  }>;
  digest_runs: Array<{
    report_date: string;
    generated_at: string;
    fills_count: number;
    intents_count: number;
    lineage_alerts_count: number;
    top_strategy: string | null;
    top_strategy_realized_pnl_usd: string | null;
    anomaly_score: number;
    anomaly_flags: string[];
  }>;
  digest_alert: {
    report_date: string;
    anomaly_score: number;
    anomaly_flags: string[];
    fills_count: number;
    lineage_alerts_count: number;
    top_strategy: string | null;
    top_strategy_realized_pnl_usd: string | null;
  } | null;
  market_stream: {
    running: boolean;
    symbols: string[];
    interval: string | null;
    messages_processed: number;
    poll_cycles: number;
    last_error: string | null;
    last_message_at: string | null;
  };
  user_stream: {
    running: boolean;
    subscribed: boolean;
    messages_processed: number;
    last_event_type: string | null;
    last_error: string | null;
    last_message_at: string | null;
  };
  focus_liquidity: {
    symbol: string;
    timestamp: string;
    spread_bps: string | null;
    imbalance_ratio: string | null;
    best_bid: string | null;
    best_ask: string | null;
    bid_depth_notional: string;
    ask_depth_notional: string;
  } | null;
  balances: Array<{
    asset: string;
    free: string;
    locked: string;
    total: string;
    total_value_usd: string | null;
    updated_at: string;
  }>;
};

export type MarketStreamStatusResponse = {
  running: boolean;
  symbols: string[];
  interval: string | null;
  reconnect_attempts: number;
  messages_processed: number;
  poll_cycles: number;
  last_message_at: string | null;
  last_error: string | null;
};

export type UserStreamStatusResponse = {
  running: boolean;
  subscribed: boolean;
  reconnect_attempts: number;
  messages_processed: number;
  subscription_id: number | null;
  last_event_type: string | null;
  last_message_at: string | null;
  last_error: string | null;
};

export type ExecutionVenueEventResponse = {
  id: number;
  created_at: string;
  reconciled_at: string | null;
  execution_intent_id: number | null;
  venue: string;
  event_type: string;
  venue_status: string;
  symbol: string | null;
  client_order_id: string | null;
  venue_order_id: string | null;
  reconcile_state: "pending" | "applied" | "ignored" | "unmatched";
  status_bucket: "accepted" | "partial" | "filled" | "cancelled" | "rejected" | "pending" | "unknown";
  ret_code: number | null;
  ret_msg: string | null;
  payload: Record<string, unknown>;
};

export type ExecutionIntentResponse = {
  id: number;
  created_at: string;
  updated_at: string;
  symbol: string;
  side: string;
  status: string;
  source_strategy: string;
  requested_notional: string;
  approved_notional: string;
  entry_price: string;
  client_order_id: string | null;
  venue_order_id: string | null;
  execution_venue: string | null;
  dispatched_at: string | null;
  executed_at: string | null;
  cancelled_at: string | null;
  parent_intent_id: number | null;
  replaced_by_intent_id: number | null;
  owner_user_id: string;
  notes: string | null;
  signal: {
    symbol: string;
    side: string;
    conviction: number;
    source: string;
    regime: string;
  };
  risk: {
    allowed: boolean;
    reasons: string[];
    profile_name: string;
    recommended_max_notional: string;
  };
  execution_payload: Record<string, unknown> | null;
};

export type OrderBookResponse = {
  symbol: string;
  bids: Array<{ price: string; quantity: string }>;
  asks: Array<{ price: string; quantity: string }>;
  metrics: {
    spread: string | null;
    spread_bps: string | null;
    mid_price: string | null;
    bid_depth_notional_0p5pct: string;
    ask_depth_notional_0p5pct: string;
    imbalance_ratio_0p5pct: string | null;
    best_bid: string | null;
    best_ask: string | null;
    last_update_id: number | null;
    updated_at: string | null;
  };
};

export type LiquidityPointResponse = {
  symbol: string;
  timestamp: string;
  metrics: OrderBookResponse["metrics"];
};

export type CandleResponse = {
  symbol: string;
  timeframe: string;
  open_time: string;
  close_time: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
};

export type SpotExecutionFillResponse = {
  id: number;
  filled_at: string;
  symbol: string;
  side: string;
  execution_intent_id: number | null;
  source_strategy: string | null;
  client_order_id: string | null;
  venue_order_id: string | null;
  trade_id: number | null;
  quantity: string;
  quote_quantity: string;
  price: string;
  realized_pnl_usd: string;
  post_fill_net_quantity: string;
  post_fill_average_entry_price: string | null;
  source_event: string | null;
};

export type SpotExecutionFillLotCloseResponse = {
  id: number;
  execution_fill_id: number;
  position_lot_id: number;
  symbol: string;
  closed_quantity: string;
  lot_entry_price: string;
  fill_exit_price: string;
  realized_pnl_usd: string;
  lot_opened_at: string | null;
  hold_seconds: string | null;
  closed_at: string;
};

export type SpotExecutionChainLotCloseSummaryResponse = {
  chain_key: string;
  symbol: string;
  fills_count: number;
  lot_slices_count: number;
  lots_count: number;
  total_closed_quantity: string;
  total_realized_pnl_usd: string;
  weighted_average_entry_price: string | null;
  weighted_average_exit_price: string | null;
  average_hold_seconds: string | null;
  max_hold_seconds: string | null;
  opened_at: string;
  closed_at: string;
};

export type SpotExecutionChainLotCloseRowResponse = {
  id: number;
  execution_fill_id: number;
  position_lot_id: number;
  symbol: string;
  closed_quantity: string;
  lot_entry_price: string;
  fill_exit_price: string;
  realized_pnl_usd: string;
  lot_opened_at: string | null;
  hold_seconds: string | null;
  closed_at: string;
  fill_client_order_id: string | null;
  fill_venue_order_id: string | null;
  fill_source_strategy: string | null;
};

export type SpotExecutionChainLotCloseResponse = {
  summary: SpotExecutionChainLotCloseSummaryResponse;
  rows: SpotExecutionChainLotCloseRowResponse[];
};

export type SpotExecutionFillChainResponse = {
  chain_key: string;
  symbol: string;
  side: string;
  execution_intent_id: number | null;
  source_strategy: string | null;
  client_order_id: string | null;
  venue_order_id: string | null;
  fills_count: number;
  opened_at: string;
  closed_at: string;
  total_quantity: string;
  total_quote_quantity: string;
  average_price: string;
  realized_pnl_usd: string;
  ending_net_quantity: string;
  ending_average_entry_price: string | null;
};

export type SpotExecutionFillSummaryResponse = {
  fills_count: number;
  chains_count: number;
  traded_symbols_count: number;
  gross_notional_usd: string;
  gross_realized_pnl_usd: string;
  gross_adverse_slippage_cost_usd: string;
  winning_fills_count: number;
  losing_fills_count: number;
  flat_fills_count: number;
  win_rate: string;
  average_fill_notional_usd: string;
  average_realized_pnl_per_fill_usd: string;
  average_adverse_slippage_bps: string;
  lot_closes_count: number;
  average_hold_seconds: string | null;
  max_hold_seconds: string | null;
  average_realized_pnl_per_lot_close_usd: string;
  short_hold_realized_pnl_usd: string;
  long_hold_realized_pnl_usd: string;
  strategy_breakdown: Array<{
    source_strategy: string;
    fills_count: number;
    chains_count: number;
    gross_notional_usd: string;
    gross_realized_pnl_usd: string;
    win_rate: string;
    gross_adverse_slippage_cost_usd: string;
    average_adverse_slippage_bps: string;
    gross_underfill_notional_usd: string;
    lot_closes_count: number;
    average_hold_seconds: string | null;
    max_hold_seconds: string | null;
    average_realized_pnl_per_lot_close_usd: string;
    short_hold_realized_pnl_usd: string;
    long_hold_realized_pnl_usd: string;
  }>;
  recent_chains: SpotExecutionFillChainResponse[];
};

export type ExecutionIntentLineageOutcomeResponse = {
  root_intent_id: number;
  latest_intent_id: number;
  symbol: string;
  side: string;
  source_strategy: string;
  lineage_size: number;
  lineage_statuses: string[];
  requested_notional: string;
  approved_notional: string;
  created_at: string;
  latest_created_at: string;
  fills_count: number;
  filled_quantity: string;
  filled_quote_quantity: string;
  average_fill_price: string | null;
  realized_pnl_usd: string;
  fill_ratio: string;
  slippage_bps: string | null;
  adverse_slippage_bps: string | null;
  slippage_cost_usd: string;
  underfill_notional_usd: string;
  average_hold_seconds: string | null;
  max_hold_seconds: string | null;
  short_hold_realized_pnl_usd: string;
  long_hold_realized_pnl_usd: string;
  last_fill_at: string | null;
};

export type ExecutionIntentOutcomeResponse = {
  execution_intent_id: number;
  symbol: string;
  side: string;
  source_strategy: string;
  intent_status: string;
  requested_notional: string;
  approved_notional: string;
  entry_price: string;
  created_at: string;
  dispatched_at: string | null;
  executed_at: string | null;
  fills_count: number;
  filled_quantity: string;
  filled_quote_quantity: string;
  average_fill_price: string | null;
  realized_pnl_usd: string;
  fill_ratio: string;
  slippage_bps: string | null;
  adverse_slippage_bps: string | null;
  slippage_cost_usd: string;
  underfill_notional_usd: string;
  last_fill_at: string | null;
};

export type DailyDigestArtifactResponse = {
  report_date: string;
  generated_at: string;
  json_path: string;
  strategy_csv_path: string;
  lineage_csv_path: string;
  fills_count: number | null;
  intents_count: number | null;
  lineage_alerts_count: number | null;
  top_strategy: string | null;
  top_strategy_realized_pnl_usd: string | null;
  anomaly_score: number | null;
  anomaly_flags: string[] | null;
};

export type DailyDigestSeriesPointResponse = {
  report_date: string;
  generated_at: string;
  fills_count: number;
  lineage_alerts_count: number;
  anomaly_score: number;
  top_strategy_realized_pnl_usd: string | null;
  anomaly_flags: string[];
};

export type DailyDigestPreviewResponse = {
  report_date: string;
  generated_at: string;
  fills_count: number;
  intents_count: number;
  strategy_breakdown: Array<{
    source_strategy: string;
    fills_count: number;
    chains_count: number;
    gross_notional_usd: string;
    gross_realized_pnl_usd: string;
    win_rate: string;
  }>;
  lineage_alerts: Array<{
    root_intent_id: number;
    latest_intent_id: number;
    symbol: string;
    source_strategy: string;
    lineage_size: number;
    lineage_statuses: string[];
    fill_ratio: string;
    slippage_bps: string | null;
    realized_pnl_usd: string;
    last_fill_at: string | null;
  }>;
};

async function parseApiError(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item) => item?.msg ?? "validation error").join("; ");
    }
  } catch {
    // Fall through to a generic status message.
  }
  return `request failed: ${response.status}`;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    cache: "no-store",
    credentials: "include",
    ...init
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return response.json() as Promise<T>;
}

export function buildApiUrl(path: string, params?: URLSearchParams) {
  const query = params && Array.from(params.keys()).length > 0 ? `?${params.toString()}` : "";
  return `${API_URL}${path}${query}`;
}

export async function getDashboardSummary(): Promise<DashboardSummaryResponse> {
  return apiFetch<DashboardSummaryResponse>("/dashboard/summary");
}

export async function listDailyDigestArtifacts(limit = 10): Promise<DailyDigestArtifactResponse[]> {
  return apiFetch<DailyDigestArtifactResponse[]>(`/reports/daily-digest/artifacts?limit=${limit}`);
}

export async function listDailyDigestSeries(limit = 30): Promise<DailyDigestSeriesPointResponse[]> {
  return apiFetch<DailyDigestSeriesPointResponse[]>(`/reports/daily-digest/series?limit=${limit}`);
}

export async function listDailyDigestSeriesFiltered(options?: {
  limit?: number;
  days?: number;
  startAt?: string;
  endAt?: string;
  flaggedOnly?: boolean;
}): Promise<DailyDigestSeriesPointResponse[]> {
  const params = new URLSearchParams();
  params.set("limit", String(options?.limit ?? 365));
  if (options?.days) {
    params.set("days", String(options.days));
  }
  if (options?.startAt) {
    params.set("start_at", options.startAt);
  }
  if (options?.endAt) {
    params.set("end_at", options.endAt);
  }
  if (options?.flaggedOnly) {
    params.set("flagged_only", "true");
  }
  return apiFetch<DailyDigestSeriesPointResponse[]>(`/reports/daily-digest/series?${params.toString()}`);
}

export async function listDailyDigestRunsFiltered(options?: {
  limit?: number;
  days?: number;
  startAt?: string;
  endAt?: string;
  flaggedOnly?: boolean;
}): Promise<DailyDigestArtifactResponse[]> {
  const params = new URLSearchParams();
  params.set("limit", String(options?.limit ?? 365));
  if (options?.days) {
    params.set("days", String(options.days));
  }
  if (options?.startAt) {
    params.set("start_at", options.startAt);
  }
  if (options?.endAt) {
    params.set("end_at", options.endAt);
  }
  if (options?.flaggedOnly) {
    params.set("flagged_only", "true");
  }
  return apiFetch<DailyDigestArtifactResponse[]>(`/reports/daily-digest/runs?${params.toString()}`);
}

export async function runDailyDigest(reportDate?: string): Promise<DailyDigestArtifactResponse> {
  const params = new URLSearchParams();
  if (reportDate) {
    params.set("report_date", reportDate);
  }
  return apiFetch<DailyDigestArtifactResponse>("/reports/daily-digest/run" + (params.size > 0 ? `?${params.toString()}` : ""), {
    method: "POST"
  });
}

export async function getDailyDigestPreview(reportDate: string): Promise<DailyDigestPreviewResponse> {
  return apiFetch<DailyDigestPreviewResponse>(`/reports/daily-digest/preview?report_date=${reportDate}`);
}

export async function getMarketStreamStatus(): Promise<MarketStreamStatusResponse> {
  return apiFetch<MarketStreamStatusResponse>("/market-data/stream/status");
}

export async function getBybitUserStreamStatus(): Promise<UserStreamStatusResponse> {
  return apiFetch<UserStreamStatusResponse>("/execution/venues/bybit/user-stream/status");
}

export async function getExecutionIntents(limit = 8): Promise<ExecutionIntentResponse[]> {
  return apiFetch<ExecutionIntentResponse[]>(`/execution/intents?limit=${limit}`);
}

export async function getExecutionIntentByOrderId(options: {
  clientOrderId?: string | null;
  venueOrderId?: string | null;
}): Promise<ExecutionIntentResponse> {
  const params = new URLSearchParams();
  if (options.clientOrderId) {
    params.set("client_order_id", options.clientOrderId);
  }
  if (options.venueOrderId) {
    params.set("venue_order_id", options.venueOrderId);
  }
  return apiFetch<ExecutionIntentResponse>(`/execution/intents/by-order-id?${params.toString()}`);
}

export async function getOrderbook(symbol: string, limit = 8): Promise<OrderBookResponse> {
  return apiFetch<OrderBookResponse>(`/market-data/orderbook/${symbol}?limit=${limit}`);
}

export async function getLiquidityHistory(symbol: string, limit = 24): Promise<LiquidityPointResponse[]> {
  return apiFetch<LiquidityPointResponse[]>(`/market-data/liquidity/${symbol}/history?limit=${limit}`);
}

export async function getCandles(symbol: string, interval = "1m", limit = 60): Promise<CandleResponse[]> {
  const params = new URLSearchParams({
    symbol,
    interval,
    limit: String(limit),
  });
  return apiFetch<CandleResponse[]>(`/market-data/candles?${params.toString()}`);
}

export async function getExecutionFills(
  symbol?: string,
  limit = 50,
  strategy?: string,
  pnlFilter?: "winning" | "losing" | "flat",
  options?: { startAt?: string; endAt?: string; offset?: number; executionIntentId?: number }
): Promise<SpotExecutionFillResponse[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (symbol) {
    params.set("symbol", symbol);
  }
  if (strategy && strategy !== "all") {
    params.set("strategy", strategy);
  }
  if (pnlFilter) {
    params.set("pnl_filter", pnlFilter);
  }
  if (options?.startAt) {
    params.set("start_at", options.startAt);
  }
  if (options?.endAt) {
    params.set("end_at", options.endAt);
  }
  if (options?.offset) {
    params.set("offset", String(options.offset));
  }
  if (options?.executionIntentId) {
    params.set("execution_intent_id", String(options.executionIntentId));
  }
  return apiFetch<SpotExecutionFillResponse[]>(`/execution/account/fills?${params.toString()}`);
}

export async function getExecutionFillLotCloses(fillId: number): Promise<SpotExecutionFillLotCloseResponse[]> {
  return apiFetch<SpotExecutionFillLotCloseResponse[]>(`/execution/account/fills/${fillId}/lot-closes`);
}

export async function getExecutionChainLotCloses(chainKey: string): Promise<SpotExecutionChainLotCloseResponse> {
  return apiFetch<SpotExecutionChainLotCloseResponse>(
    `/execution/account/fills/chains/${encodeURIComponent(chainKey)}/lot-closes`
  );
}

export async function getExecutionFillSummary(
  symbol?: string,
  limit = 250,
  recentChainsLimit = 20,
  strategy?: string,
  pnlFilter?: "winning" | "losing" | "flat",
  options?: { startAt?: string; endAt?: string; recentChainsOffset?: number; executionIntentId?: number }
): Promise<SpotExecutionFillSummaryResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    recent_chains_limit: String(recentChainsLimit)
  });
  if (symbol) {
    params.set("symbol", symbol);
  }
  if (strategy && strategy !== "all") {
    params.set("strategy", strategy);
  }
  if (pnlFilter) {
    params.set("pnl_filter", pnlFilter);
  }
  if (options?.startAt) {
    params.set("start_at", options.startAt);
  }
  if (options?.endAt) {
    params.set("end_at", options.endAt);
  }
  if (options?.recentChainsOffset) {
    params.set("recent_chains_offset", String(options.recentChainsOffset));
  }
  if (options?.executionIntentId) {
    params.set("execution_intent_id", String(options.executionIntentId));
  }
  return apiFetch<SpotExecutionFillSummaryResponse>(`/execution/account/fills/summary?${params.toString()}`);
}

export async function getExecutionIntentLineageOutcomes(
  strategy?: string,
  status?: string,
  limit = 50,
  options?: {
    rootIntentId?: number;
    latestIntentId?: number;
    minLineageSize?: number;
    flaggedOnly?: boolean;
    minSlippageBps?: number;
    underfilledOnly?: boolean;
    startAt?: string;
    endAt?: string;
    offset?: number;
  }
): Promise<ExecutionIntentLineageOutcomeResponse[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (strategy && strategy !== "all") {
    params.set("strategy", strategy);
  }
  if (status) {
    params.set("status", status);
  }
  if (options?.minLineageSize) {
    params.set("min_lineage_size", String(options.minLineageSize));
  }
  if (options?.rootIntentId) {
    params.set("root_intent_id", String(options.rootIntentId));
  }
  if (options?.latestIntentId) {
    params.set("latest_intent_id", String(options.latestIntentId));
  }
  if (options?.flaggedOnly) {
    params.set("flagged_only", "true");
  }
  if (options?.minSlippageBps !== undefined) {
    params.set("min_slippage_bps", String(options.minSlippageBps));
  }
  if (options?.underfilledOnly) {
    params.set("underfilled_only", "true");
  }
  if (options?.startAt) {
    params.set("start_at", options.startAt);
  }
  if (options?.endAt) {
    params.set("end_at", options.endAt);
  }
  if (options?.offset) {
    params.set("offset", String(options.offset));
  }
  return apiFetch<ExecutionIntentLineageOutcomeResponse[]>(`/execution/intents/lineages/outcomes?${params.toString()}`);
}

export async function getExecutionIntentOutcomes(options?: {
  strategy?: string;
  status?: string;
  limit?: number;
  executionIntentId?: number;
}): Promise<ExecutionIntentOutcomeResponse[]> {
  const params = new URLSearchParams({ limit: String(options?.limit ?? 100) });
  if (options?.strategy && options.strategy !== "all") {
    params.set("strategy", options.strategy);
  }
  if (options?.status) {
    params.set("status", options.status);
  }
  if (options?.executionIntentId) {
    params.set("execution_intent_id", String(options.executionIntentId));
  }
  return apiFetch<ExecutionIntentOutcomeResponse[]>(`/execution/intents/outcomes?${params.toString()}`);
}

export async function getExecutionVenueEvents(options?: {
  limit?: number;
  offset?: number;
  venue?: string;
  symbol?: string;
  query?: string;
  reconcileState?: "pending" | "applied" | "ignored" | "unmatched";
  statusBucket?: "accepted" | "partial" | "filled" | "cancelled" | "rejected" | "pending" | "unknown";
}): Promise<ExecutionVenueEventResponse[]> {
  const params = new URLSearchParams({ limit: String(options?.limit ?? 50) });
  if (options?.offset) {
    params.set("offset", String(options.offset));
  }
  if (options?.venue) {
    params.set("venue", options.venue);
  }
  if (options?.symbol) {
    params.set("symbol", options.symbol);
  }
  if (options?.query) {
    params.set("query", options.query);
  }
  if (options?.reconcileState) {
    params.set("reconcile_state", options.reconcileState);
  }
  if (options?.statusBucket) {
    params.set("status_bucket", options.statusBucket);
  }
  return apiFetch<ExecutionVenueEventResponse[]>(`/execution/venues/events?${params.toString()}`);
}

export async function registerOwner(payload: RegisterPayload): Promise<RegisterResponse> {
  return apiFetch<RegisterResponse>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export async function loginOwner(payload: LoginPayload): Promise<UserSessionResponse> {
  return apiFetch<UserSessionResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export async function getCurrentUser(): Promise<UserSessionResponse> {
  return apiFetch<UserSessionResponse>("/auth/me");
}

export async function logoutOwner() {
  await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    credentials: "include"
  });
}
