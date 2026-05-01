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
  }>;
  lineage_summary: {
    replacement_lineages_count: number;
    replacement_alerts_count: number;
    worst_slippage_bps: string | null;
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
    last_fill_at: string | null;
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
  winning_fills_count: number;
  losing_fills_count: number;
  flat_fills_count: number;
  win_rate: string;
  average_fill_notional_usd: string;
  average_realized_pnl_per_fill_usd: string;
  strategy_breakdown: Array<{
    source_strategy: string;
    fills_count: number;
    chains_count: number;
    gross_notional_usd: string;
    gross_realized_pnl_usd: string;
    win_rate: string;
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
  return apiFetch<DailyDigestSeriesPointResponse[]>(`/reports/daily-digest/series?${params.toString()}`);
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

export async function getMarketStreamStatus(): Promise<MarketStreamStatusResponse> {
  return apiFetch<MarketStreamStatusResponse>("/market-data/stream/status");
}

export async function getBinanceUserStreamStatus(): Promise<UserStreamStatusResponse> {
  return apiFetch<UserStreamStatusResponse>("/execution/venues/binance/user-stream/status");
}

export async function getExecutionIntents(limit = 8): Promise<ExecutionIntentResponse[]> {
  return apiFetch<ExecutionIntentResponse[]>(`/execution/intents?limit=${limit}`);
}

export async function getOrderbook(symbol: string, limit = 8): Promise<OrderBookResponse> {
  return apiFetch<OrderBookResponse>(`/market-data/orderbook/${symbol}?limit=${limit}`);
}

export async function getLiquidityHistory(symbol: string, limit = 24): Promise<LiquidityPointResponse[]> {
  return apiFetch<LiquidityPointResponse[]>(`/market-data/liquidity/${symbol}/history?limit=${limit}`);
}

export async function getExecutionFills(
  symbol?: string,
  limit = 50,
  strategy?: string,
  pnlFilter?: "winning" | "losing" | "flat",
  options?: { startAt?: string; endAt?: string; offset?: number }
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
  return apiFetch<SpotExecutionFillResponse[]>(`/execution/account/fills?${params.toString()}`);
}

export async function getExecutionFillSummary(
  symbol?: string,
  limit = 250,
  recentChainsLimit = 20,
  strategy?: string,
  pnlFilter?: "winning" | "losing" | "flat",
  options?: { startAt?: string; endAt?: string; recentChainsOffset?: number }
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
  return apiFetch<SpotExecutionFillSummaryResponse>(`/execution/account/fills/summary?${params.toString()}`);
}

export async function getExecutionIntentLineageOutcomes(
  strategy?: string,
  status?: string,
  limit = 50,
  options?: {
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
