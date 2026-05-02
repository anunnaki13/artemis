from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


AiMode = Literal["fast", "primary", "heavy"]
AiReviewStatus = Literal["pending", "approved", "rejected", "follow_up"]


class AiAnalystBriefRequest(BaseModel):
    mode: AiMode = "primary"
    question: str | None = Field(default=None, max_length=2000)


class AiAnalystBudgetRead(BaseModel):
    limit_usd: Decimal
    spent_today_usd: Decimal
    remaining_usd: Decimal


class AiAnalystRunRead(BaseModel):
    id: int
    created_at: datetime
    mode: str
    model: str
    status: str
    question: str | None
    response_text: str | None
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: Decimal | None
    budget_limit_usd: Decimal | None
    budget_spent_before_usd: Decimal | None
    review_status: AiReviewStatus
    reviewed_at: datetime | None
    reviewed_by_user_id: str | None
    review_notes: str | None
    error_message: str | None


class AiAnalystBriefResponse(BaseModel):
    run: AiAnalystRunRead
    budget: AiAnalystBudgetRead
    context_summary: dict[str, object]


class AiAnalystReviewRequest(BaseModel):
    review_status: Literal["approved", "rejected", "follow_up"]
    review_notes: str | None = Field(default=None, max_length=512)
