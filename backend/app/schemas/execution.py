from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.risk import SignalRiskEvaluateRequest, SignalRiskEvaluateResponse
from strategies.base import Signal

IntentStatus = Literal["queued", "approved", "rejected", "cancel_requested", "cancelled", "executed"]
LifecycleStatus = Literal[
    "queued",
    "approved",
    "rejected",
    "cancel_requested",
    "cancelled",
    "dispatching",
    "executed",
    "failed",
]
VenueEventState = Literal["pending", "applied", "ignored", "unmatched"]


class ExecutionIntentSubmitRequest(BaseModel):
    signal_risk: SignalRiskEvaluateRequest
    notes: str | None = Field(default=None, max_length=512)


class ExecutionIntentRead(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    symbol: str
    side: str
    status: LifecycleStatus
    source_strategy: str
    requested_notional: Decimal
    approved_notional: Decimal
    entry_price: Decimal
    client_order_id: str | None
    venue_order_id: str | None
    execution_venue: str | None
    dispatched_at: datetime | None
    executed_at: datetime | None
    cancelled_at: datetime | None
    parent_intent_id: int | None
    replaced_by_intent_id: int | None
    owner_user_id: str
    signal: Signal
    risk: SignalRiskEvaluateResponse
    execution_payload: dict[str, object] | None
    notes: str | None


class ExecutionIntentSubmitResponse(BaseModel):
    queued: bool
    risk: SignalRiskEvaluateResponse
    intent: ExecutionIntentRead | None


class ExecutionIntentReplaceRequest(BaseModel):
    signal_risk: SignalRiskEvaluateRequest
    notes: str | None = Field(default=None, max_length=512)
    cancel_reason: str | None = Field(default=None, max_length=256)


class ExecutionIntentReplaceResponse(BaseModel):
    risk: SignalRiskEvaluateResponse
    cancelled_intent: ExecutionIntentRead
    replacement_intent: ExecutionIntentRead


class ExecutionIntentStatusUpdateRequest(BaseModel):
    status: Literal["approved", "rejected", "cancelled", "executed", "failed"]
    notes: str | None = Field(default=None, max_length=512)


class ExecutionIntentCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=256)


class ExecutionDispatchResponse(BaseModel):
    dispatched: bool
    intent: ExecutionIntentRead | None
    detail: str


class ExecutionReconcileRequest(BaseModel):
    status: Literal["executed", "failed", "cancelled"]
    filled_notional: Decimal
    average_price: Decimal
    venue: str = Field(min_length=1, max_length=64)
    venue_order_id: str | None = Field(default=None, max_length=128)
    client_order_id: str | None = Field(default=None, max_length=128)
    details: dict[str, object] = Field(default_factory=dict)


class ExecutionTimeoutSweepResponse(BaseModel):
    timed_out_count: int
    intents: list[ExecutionIntentRead]


class ExecutionOrderLookupRequest(BaseModel):
    client_order_id: str | None = Field(default=None, max_length=128)
    venue_order_id: str | None = Field(default=None, max_length=128)


class ExecutionOrderReconcileRequest(ExecutionReconcileRequest):
    client_order_id: str | None = Field(default=None, max_length=128)
    venue_order_id: str | None = Field(default=None, max_length=128)


class ExecutionVenueEventIngestRequest(BaseModel):
    venue: str = Field(min_length=1, max_length=64)
    event_type: str = Field(min_length=1, max_length=64)
    venue_status: str = Field(min_length=1, max_length=64)
    symbol: str | None = Field(default=None, max_length=32)
    client_order_id: str | None = Field(default=None, max_length=128)
    venue_order_id: str | None = Field(default=None, max_length=128)
    filled_notional: Decimal | None = None
    average_price: Decimal | None = None
    details: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_order_identifier(self) -> "ExecutionVenueEventIngestRequest":
        if self.client_order_id is None and self.venue_order_id is None:
            raise ValueError("client_order_id or venue_order_id is required")
        return self


class ExecutionVenueEventRead(BaseModel):
    id: int
    created_at: datetime
    reconciled_at: datetime | None
    execution_intent_id: int | None
    venue: str
    event_type: str
    venue_status: str
    symbol: str | None
    client_order_id: str | None
    venue_order_id: str | None
    reconcile_state: VenueEventState
    payload: dict[str, object]


class ExecutionVenueEventIngestResponse(BaseModel):
    matched: bool
    event: ExecutionVenueEventRead
    intent: ExecutionIntentRead | None


class BinanceUserStreamStatusResponse(BaseModel):
    running: bool
    subscribed: bool
    reconnect_attempts: int
    messages_processed: int
    subscription_id: int | None
    last_event_type: str | None
    last_message_at: datetime | None
    last_error: str | None


class SpotAccountBalanceRead(BaseModel):
    asset: str
    free: Decimal
    locked: Decimal
    total: Decimal
    total_value_usd: Decimal | None
    last_delta: Decimal | None
    updated_at: datetime
    source_event: str | None


class SpotSymbolPositionRead(BaseModel):
    symbol: str
    base_asset: str
    quote_asset: str
    net_quantity: Decimal
    average_entry_price: Decimal | None
    last_mark_price: Decimal | None
    quote_exposure_usd: Decimal | None
    market_value_usd: Decimal | None
    realized_notional: Decimal
    realized_pnl_usd: Decimal
    unrealized_pnl_usd: Decimal | None
    updated_at: datetime
    source_event: str | None


class SpotExecutionFillRead(BaseModel):
    id: int
    filled_at: datetime
    symbol: str
    side: str
    execution_intent_id: int | None
    source_strategy: str | None
    client_order_id: str | None
    venue_order_id: str | None
    trade_id: int | None
    quantity: Decimal
    quote_quantity: Decimal
    price: Decimal
    realized_pnl_usd: Decimal
    post_fill_net_quantity: Decimal
    post_fill_average_entry_price: Decimal | None
    source_event: str | None


class SpotExecutionFillChainRead(BaseModel):
    chain_key: str
    symbol: str
    side: str
    execution_intent_id: int | None
    source_strategy: str | None
    client_order_id: str | None
    venue_order_id: str | None
    fills_count: int
    opened_at: datetime
    closed_at: datetime
    total_quantity: Decimal
    total_quote_quantity: Decimal
    average_price: Decimal
    realized_pnl_usd: Decimal
    ending_net_quantity: Decimal
    ending_average_entry_price: Decimal | None


class SpotExecutionFillSummaryRead(BaseModel):
    fills_count: int
    chains_count: int
    traded_symbols_count: int
    gross_notional_usd: Decimal
    gross_realized_pnl_usd: Decimal
    winning_fills_count: int
    losing_fills_count: int
    flat_fills_count: int
    win_rate: Decimal
    average_fill_notional_usd: Decimal
    average_realized_pnl_per_fill_usd: Decimal
    strategy_breakdown: list[dict[str, object]]
    recent_chains: list[SpotExecutionFillChainRead]


class ExecutionIntentOutcomeRead(BaseModel):
    execution_intent_id: int
    symbol: str
    side: str
    source_strategy: str
    intent_status: LifecycleStatus
    requested_notional: Decimal
    approved_notional: Decimal
    entry_price: Decimal
    created_at: datetime
    dispatched_at: datetime | None
    executed_at: datetime | None
    fills_count: int
    filled_quantity: Decimal
    filled_quote_quantity: Decimal
    average_fill_price: Decimal | None
    realized_pnl_usd: Decimal
    fill_ratio: Decimal
    slippage_bps: Decimal | None
    last_fill_at: datetime | None


class ExecutionIntentLineageOutcomeRead(BaseModel):
    root_intent_id: int
    latest_intent_id: int
    symbol: str
    side: str
    source_strategy: str
    lineage_size: int
    lineage_statuses: list[str]
    requested_notional: Decimal
    approved_notional: Decimal
    created_at: datetime
    latest_created_at: datetime
    fills_count: int
    filled_quantity: Decimal
    filled_quote_quantity: Decimal
    average_fill_price: Decimal | None
    realized_pnl_usd: Decimal
    fill_ratio: Decimal
    slippage_bps: Decimal | None
    last_fill_at: datetime | None


class BinanceExecutionPreviewResponse(BaseModel):
    symbol: str
    side: str
    base_url: str
    testnet: bool
    live_transport_enabled: bool
    transport_mode: str
    client_order_id: str
    unsigned_payload: dict[str, str | int]
    signed_payload_keys: list[str]
