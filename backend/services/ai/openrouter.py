from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.runtime_settings import get_runtime_setting
from app.models import (
    AiAnalystRun,
    ExecutionIntent,
    ExecutionVenueEvent,
    SpotExecutionFill,
    SpotExecutionFillLotClose,
)
from services.execution.fill_analytics import (
    summarize_intent_lineage_outcomes,
    summarize_lot_hold_quality,
    summarize_strategy_quality,
)

MODEL_PRICING: dict[str, tuple[Decimal, Decimal]] = {
    "openai/gpt-4.1-mini": (Decimal("0.40"), Decimal("1.60")),
    "google/gemini-2.5-flash-lite": (Decimal("0.10"), Decimal("0.40")),
    "google/gemini-2.5-flash": (Decimal("0.30"), Decimal("2.50")),
}


@dataclass(slots=True)
class OpenRouterRuntime:
    api_key: str
    primary_model: str
    fast_model: str
    heavy_model: str
    max_cost_usd_per_day: Decimal

    def model_for_mode(self, mode: str) -> str:
        if mode == "fast":
            return self.fast_model
        if mode == "heavy":
            return self.heavy_model
        return self.primary_model


async def resolve_openrouter_runtime(session: AsyncSession) -> OpenRouterRuntime:
    api_key = await get_runtime_setting(session, "OPENROUTER_API_KEY")
    if api_key is None:
        raise ValueError("OpenRouter API key is not configured")
    primary_model = await get_runtime_setting(session, "AI_PRIMARY_MODEL", "openai/gpt-4.1-mini")
    fast_model = await get_runtime_setting(session, "AI_FAST_MODEL", "google/gemini-2.5-flash-lite")
    heavy_model = await get_runtime_setting(session, "AI_HEAVY_MODEL", "google/gemini-2.5-flash")
    max_cost_raw = await get_runtime_setting(session, "AI_MAX_COST_USD_PER_DAY", "3.00")
    return OpenRouterRuntime(
        api_key=api_key,
        primary_model=primary_model or "openai/gpt-4.1-mini",
        fast_model=fast_model or "google/gemini-2.5-flash-lite",
        heavy_model=heavy_model or "google/gemini-2.5-flash",
        max_cost_usd_per_day=Decimal(max_cost_raw or "3.00"),
    )


async def current_budget_spend_usd(session: AsyncSession) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(AiAnalystRun.estimated_cost_usd), Decimal("0"))).where(
            func.date(AiAnalystRun.created_at) == func.current_date()
        )
    )
    return Decimal(total or Decimal("0"))


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    input_rate, output_rate = MODEL_PRICING.get(model, (Decimal("0"), Decimal("0")))
    input_cost = (Decimal(input_tokens) / Decimal("1000000")) * input_rate
    output_cost = (Decimal(output_tokens) / Decimal("1000000")) * output_rate
    return (input_cost + output_cost).quantize(Decimal("0.00000001"))


async def build_ai_context(session: AsyncSession) -> dict[str, Any]:
    intents = list(
        (
            await session.scalars(
                select(ExecutionIntent).order_by(ExecutionIntent.created_at.desc()).limit(20)
            )
        ).all()
    )
    fills = list(
        (
            await session.scalars(
                select(SpotExecutionFill).order_by(SpotExecutionFill.filled_at.desc()).limit(200)
            )
        ).all()
    )
    lot_closes = list(
        (
            await session.scalars(
                select(SpotExecutionFillLotClose).order_by(SpotExecutionFillLotClose.closed_at.desc()).limit(200)
            )
        ).all()
    )
    venue_events = list(
        (
            await session.scalars(
                select(ExecutionVenueEvent).order_by(ExecutionVenueEvent.created_at.desc()).limit(50)
            )
        ).all()
    )
    rejected_events = [event for event in venue_events if (event.venue_status or "").upper() in {"REJECTED", "CANCELLED", "CANCELED"}][:10]
    strategy_quality = summarize_strategy_quality(fills)[:6]
    lineages = summarize_intent_lineage_outcomes(intents, fills)[:8]
    hold_quality = summarize_lot_hold_quality(lot_closes)
    return {
        "recent_intents": [
            {
                "symbol": item.symbol,
                "status": item.status,
                "strategy": item.source_strategy,
                "approved_notional": str(item.approved_notional),
                "created_at": item.created_at.isoformat(),
            }
            for item in intents[:10]
        ],
        "strategy_quality": [
            {
                "strategy": item.source_strategy,
                "fills_count": item.fills_count,
                "gross_realized_pnl_usd": str(item.gross_realized_pnl_usd),
                "win_rate": str(item.win_rate),
                "gross_adverse_slippage_cost_usd": str(item.gross_adverse_slippage_cost_usd),
                "gross_underfill_notional_usd": str(item.gross_underfill_notional_usd),
            }
            for item in strategy_quality
        ],
        "lineage_alerts": [
            {
                "symbol": item.symbol,
                "strategy": item.source_strategy,
                "fill_ratio": str(item.fill_ratio),
                "slippage_bps": str(item.slippage_bps) if item.slippage_bps is not None else None,
                "realized_pnl_usd": str(item.realized_pnl_usd),
                "average_hold_seconds": str(item.average_hold_seconds) if item.average_hold_seconds is not None else None,
            }
            for item in lineages
        ],
        "venue_events": [
            {
                "symbol": item.symbol,
                "event_type": item.event_type,
                "venue_status": item.venue_status,
                "ret_code": item.payload.get("retCode") if isinstance(item.payload, dict) else None,
                "ret_msg": item.payload.get("retMsg") if isinstance(item.payload, dict) else None,
                "created_at": item.created_at.isoformat(),
            }
            for item in rejected_events
        ],
        "hold_quality": {
            "lot_closes_count": hold_quality.lot_closes_count,
            "average_hold_seconds": str(hold_quality.average_hold_seconds) if hold_quality.average_hold_seconds is not None else None,
            "max_hold_seconds": str(hold_quality.max_hold_seconds) if hold_quality.max_hold_seconds is not None else None,
            "short_hold_realized_pnl_usd": str(hold_quality.short_hold_realized_pnl_usd),
            "long_hold_realized_pnl_usd": str(hold_quality.long_hold_realized_pnl_usd),
        },
    }


def build_messages(context: dict[str, Any], question: str | None) -> list[dict[str, str]]:
    system_prompt = (
        "You are AIQ-BOT Analyst. You are read-only. "
        "Do not recommend bypassing hard risk limits or enabling live transport. "
        "Summarize the current execution, venue, and hold-quality state. "
        "Be concise, operational, and specific."
    )
    user_prompt = (
        "Analyze the following current trading-system context and produce:\n"
        "1. One-paragraph situation summary\n"
        "2. Top 3 risks or anomalies\n"
        "3. Top 3 concrete next actions\n"
        "4. A short confidence note\n\n"
        f"Context JSON:\n{json.dumps(context, default=str)}\n"
    )
    if question:
        user_prompt += f"\nOperator question:\n{question}\n"
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]


async def run_openrouter_brief(
    session: AsyncSession,
    mode: str,
    question: str | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[AiAnalystRun, dict[str, Any], Decimal]:
    runtime = await resolve_openrouter_runtime(session)
    spent_before = await current_budget_spend_usd(session)
    if spent_before >= runtime.max_cost_usd_per_day:
        run = AiAnalystRun(
            mode=mode,
            model=runtime.model_for_mode(mode),
            status="budget_blocked",
            question=question,
            budget_limit_usd=runtime.max_cost_usd_per_day,
            budget_spent_before_usd=spent_before,
            error_message="daily AI budget exhausted",
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        return run, {}, spent_before

    context = await build_ai_context(session)
    model = runtime.model_for_mode(mode)
    payload = {
        "model": model,
        "messages": build_messages(context, question),
        "temperature": 0.2,
    }
    try:
        async with httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            timeout=45.0,
            transport=transport,
        ) as client:
            response = await client.post(
                "/chat/completions",
                headers={
                    "Authorization": f"Bearer {runtime.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
    except Exception as exc:
        run = AiAnalystRun(
            mode=mode,
            model=model,
            status="failed",
            question=question,
            budget_limit_usd=runtime.max_cost_usd_per_day,
            budget_spent_before_usd=spent_before,
            error_message=str(exc)[:512],
            context_payload=context,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        return run, context, spent_before

    choice = body.get("choices", [{}])[0]
    message = choice.get("message", {})
    response_text = message.get("content")
    if isinstance(response_text, list):
        response_text = "\n".join(
            part.get("text", "") for part in response_text if isinstance(part, dict)
        ).strip()
    usage = body.get("usage", {})
    input_tokens = int(usage.get("prompt_tokens", 0) or 0)
    output_tokens = int(usage.get("completion_tokens", 0) or 0)
    estimated_cost = estimate_cost_usd(model, input_tokens, output_tokens)
    run = AiAnalystRun(
        mode=mode,
        model=model,
        status="completed",
        question=question,
        response_text=response_text if isinstance(response_text, str) else None,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimated_cost,
        budget_limit_usd=runtime.max_cost_usd_per_day,
        budget_spent_before_usd=spent_before,
        context_payload=context,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run, context, spent_before + estimated_cost
