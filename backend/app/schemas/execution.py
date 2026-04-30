from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.risk import SignalRiskEvaluateRequest, SignalRiskEvaluateResponse
from strategies.base import Signal

IntentStatus = Literal["queued", "approved", "rejected", "cancelled", "executed"]
LifecycleStatus = Literal["queued", "approved", "rejected", "cancelled", "dispatching", "executed", "failed"]
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
    owner_user_id: str
    signal: Signal
    risk: SignalRiskEvaluateResponse
    execution_payload: dict[str, object] | None
    notes: str | None


class ExecutionIntentSubmitResponse(BaseModel):
    queued: bool
    risk: SignalRiskEvaluateResponse
    intent: ExecutionIntentRead | None


class ExecutionIntentStatusUpdateRequest(BaseModel):
    status: Literal["approved", "rejected", "cancelled", "executed", "failed"]
    notes: str | None = Field(default=None, max_length=512)


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
