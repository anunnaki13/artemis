from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import AiAnalystRun, User
from app.schemas.ai_analyst import AiAnalystReviewRequest
from app.schemas.ai_analyst import (
    AiAnalystBriefRequest,
    AiAnalystBriefResponse,
    AiAnalystBudgetRead,
    AiAnalystRunRead,
)
from services.audit import write_audit_log
from services.ai.openrouter import current_budget_spend_usd, resolve_openrouter_runtime, run_openrouter_brief

router = APIRouter(prefix="/ai-analyst", tags=["ai-analyst"])


def build_run_read(run: AiAnalystRun) -> AiAnalystRunRead:
    return AiAnalystRunRead(
        id=int(run.id),
        created_at=run.created_at,
        mode=run.mode,
        model=run.model,
        status=run.status,
        question=run.question,
        response_text=run.response_text,
        input_tokens=run.input_tokens,
        output_tokens=run.output_tokens,
        estimated_cost_usd=run.estimated_cost_usd,
        budget_limit_usd=run.budget_limit_usd,
        budget_spent_before_usd=run.budget_spent_before_usd,
        review_status=run.review_status,
        reviewed_at=run.reviewed_at,
        reviewed_by_user_id=run.reviewed_by_user_id,
        review_notes=run.review_notes,
        error_message=run.error_message,
    )


@router.post("/brief", response_model=AiAnalystBriefResponse)
async def generate_ai_brief(
    payload: AiAnalystBriefRequest,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AiAnalystBriefResponse:
    runtime = await resolve_openrouter_runtime(session)
    run, context, spent_after = await run_openrouter_brief(session, payload.mode, payload.question)
    remaining = runtime.max_cost_usd_per_day - spent_after
    return AiAnalystBriefResponse(
        run=build_run_read(run),
        budget=AiAnalystBudgetRead(
            limit_usd=runtime.max_cost_usd_per_day,
            spent_today_usd=spent_after,
            remaining_usd=remaining if remaining > Decimal("0") else Decimal("0"),
        ),
        context_summary=context,
    )


@router.get("/runs", response_model=list[AiAnalystRunRead])
async def list_ai_runs(
    limit: int = Query(default=20, ge=1, le=100),
    review_status: str | None = Query(default=None, pattern="^(pending|approved|rejected|follow_up)$"),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AiAnalystRunRead]:
    query = select(AiAnalystRun).order_by(AiAnalystRun.created_at.desc())
    if review_status is not None:
        query = query.where(AiAnalystRun.review_status == review_status)
    runs = list((await session.scalars(query.limit(limit))).all())
    return [build_run_read(run) for run in runs]


@router.get("/queue", response_model=list[AiAnalystRunRead])
async def list_ai_review_queue(
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AiAnalystRunRead]:
    runs = list(
        (
            await session.scalars(
                select(AiAnalystRun)
                .where(AiAnalystRun.review_status == "pending")
                .order_by(AiAnalystRun.created_at.desc())
                .limit(limit)
            )
        ).all()
    )
    return [build_run_read(run) for run in runs]


@router.post("/runs/{run_id}/review", response_model=AiAnalystRunRead)
async def review_ai_run(
    run_id: int,
    payload: AiAnalystReviewRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AiAnalystRunRead:
    run = await session.get(AiAnalystRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI run not found")
    before_state = build_run_read(run)
    run.review_status = payload.review_status
    run.review_notes = payload.review_notes
    run.reviewed_at = datetime.now(UTC)
    run.reviewed_by_user_id = str(current_user.id)
    await write_audit_log(
        session,
        action="review",
        entity="ai_analyst_run",
        entity_id=str(run.id),
        before_state=before_state,
        after_state=build_run_read(run),
    )
    await session.commit()
    await session.refresh(run)
    return build_run_read(run)


@router.get("/budget", response_model=AiAnalystBudgetRead)
async def ai_budget(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AiAnalystBudgetRead:
    runtime = await resolve_openrouter_runtime(session)
    spent = await current_budget_spend_usd(session)
    remaining = runtime.max_cost_usd_per_day - spent
    return AiAnalystBudgetRead(
        limit_usd=runtime.max_cost_usd_per_day,
        spent_today_usd=spent,
        remaining_usd=remaining if remaining > Decimal("0") else Decimal("0"),
    )
