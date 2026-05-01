import csv
import io
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse

from app.db import AsyncSessionLocal, get_session
from app.deps import get_current_user
from app.models import DailyDigestRun, User
from app.schemas.report import DailyDigestArtifactRead, DailyDigestSeriesPointRead
from sqlalchemy.ext.asyncio import AsyncSession
from services.reports.daily_digest import DailyDigestService

router = APIRouter(prefix="/reports", tags=["reports"])
digest_service = DailyDigestService(session_factory=AsyncSessionLocal)


def csv_response(filename: str, headers: list[str], rows: list[list[object]]) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    payload = io.BytesIO(buffer.getvalue().encode("utf-8"))
    return StreamingResponse(
        payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def filter_digest_rows_by_range(
    rows: list[DailyDigestRun],
    *,
    days: int | None,
    start_at: date | None,
    end_at: date | None,
) -> list[DailyDigestRun]:
    if start_at is None and end_at is None and days is not None:
        start_at = datetime.now(tz=UTC).date() - timedelta(days=max(days - 1, 0))
    filtered = rows
    if start_at is not None:
        filtered = [row for row in filtered if row.report_date >= start_at]
    if end_at is not None:
        filtered = [row for row in filtered if row.report_date <= end_at]
    return filtered


@router.post("/daily-digest/run", response_model=DailyDigestArtifactRead)
async def run_daily_digest(
    report_date: date | None = Query(default=None),
    _: User = Depends(get_current_user),
) -> DailyDigestArtifactRead:
    artifact = await digest_service.run_for_date(report_date or datetime.now(tz=UTC).date())
    return DailyDigestArtifactRead(
        report_date=artifact.report_date,
        generated_at=artifact.generated_at,
        json_path=artifact.json_path,
        strategy_csv_path=artifact.strategy_csv_path,
        lineage_csv_path=artifact.lineage_csv_path,
    )


@router.get("/daily-digest/artifacts", response_model=list[DailyDigestArtifactRead])
async def list_daily_digest_artifacts(
    limit: int = Query(default=30, ge=1, le=200),
    _: User = Depends(get_current_user),
) -> list[DailyDigestArtifactRead]:
    return [
        DailyDigestArtifactRead(
            report_date=item.report_date,
            generated_at=item.generated_at,
            json_path=item.json_path,
            strategy_csv_path=item.strategy_csv_path,
            lineage_csv_path=item.lineage_csv_path,
            fills_count=item.fills_count,
            intents_count=item.intents_count,
            lineage_alerts_count=item.lineage_alerts_count,
            top_strategy=item.top_strategy,
            top_strategy_realized_pnl_usd=(
                None if item.top_strategy_realized_pnl_usd is None else str(item.top_strategy_realized_pnl_usd)
            ),
            anomaly_score=item.anomaly_score,
            anomaly_flags=item.anomaly_flags,
        )
        for item in digest_service.list_artifact_summaries(limit)
    ]


@router.get("/daily-digest/runs", response_model=list[DailyDigestArtifactRead])
async def list_daily_digest_runs(
    limit: int = Query(default=30, ge=1, le=200),
    days: int | None = Query(default=None, ge=1, le=3650),
    start_at: date | None = Query(default=None),
    end_at: date | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[DailyDigestArtifactRead]:
    rows = await digest_service.list_run_logs(session, 3650)
    rows = filter_digest_rows_by_range(rows, days=days, start_at=start_at, end_at=end_at)[:limit]
    return [
        DailyDigestArtifactRead(
            report_date=item.report_date,
            generated_at=item.generated_at,
            json_path=item.json_path,
            strategy_csv_path=item.strategy_csv_path,
            lineage_csv_path=item.lineage_csv_path,
            fills_count=item.fills_count,
            intents_count=item.intents_count,
            lineage_alerts_count=item.lineage_alerts_count,
            top_strategy=item.top_strategy,
            top_strategy_realized_pnl_usd=(
                None if item.top_strategy_realized_pnl_usd is None else str(item.top_strategy_realized_pnl_usd)
            ),
            anomaly_score=item.anomaly_score,
            anomaly_flags=item.anomaly_flags,
        )
        for item in rows
    ]


@router.get("/daily-digest/series", response_model=list[DailyDigestSeriesPointRead])
async def list_daily_digest_series(
    limit: int = Query(default=30, ge=1, le=365),
    days: int | None = Query(default=None, ge=1, le=3650),
    start_at: date | None = Query(default=None),
    end_at: date | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[DailyDigestSeriesPointRead]:
    rows = await digest_service.list_run_logs(session, 3650)
    rows = filter_digest_rows_by_range(rows, days=days, start_at=start_at, end_at=end_at)
    rows = rows[:limit]
    return [
        DailyDigestSeriesPointRead(
            report_date=item.report_date,
            generated_at=item.generated_at,
            fills_count=item.fills_count,
            lineage_alerts_count=item.lineage_alerts_count,
            anomaly_score=item.anomaly_score,
            top_strategy_realized_pnl_usd=(
                None if item.top_strategy_realized_pnl_usd is None else str(item.top_strategy_realized_pnl_usd)
            ),
        )
        for item in reversed(rows)
    ]


@router.get("/daily-digest/series/export")
async def export_daily_digest_series(
    limit: int = Query(default=365, ge=1, le=3650),
    days: int | None = Query(default=None, ge=1, le=3650),
    start_at: date | None = Query(default=None),
    end_at: date | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> StreamingResponse:
    rows = await digest_service.list_run_logs(session, 3650)
    rows = filter_digest_rows_by_range(rows, days=days, start_at=start_at, end_at=end_at)
    rows = rows[:limit]
    return csv_response(
        "daily_digest_series.csv",
        [
            "report_date",
            "generated_at",
            "fills_count",
            "lineage_alerts_count",
            "anomaly_score",
            "top_strategy",
            "top_strategy_realized_pnl_usd",
        ],
        [
            [
                row.report_date.isoformat(),
                row.generated_at.isoformat(),
                row.fills_count,
                row.lineage_alerts_count,
                row.anomaly_score,
                row.top_strategy,
                row.top_strategy_realized_pnl_usd,
            ]
            for row in reversed(rows)
        ],
    )


@router.get("/daily-digest/download")
async def download_daily_digest_artifact(
    report_date: date,
    artifact: str = Query(pattern="^(json|strategy_csv|lineage_csv)$"),
    _: User = Depends(get_current_user),
) -> FileResponse:
    report_dir = digest_service.output_dir / report_date.isoformat()
    artifact_map = {
        "json": report_dir / "summary.json",
        "strategy_csv": report_dir / "strategy_breakdown.csv",
        "lineage_csv": report_dir / "lineage_alerts.csv",
    }
    path = artifact_map[artifact]
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report artifact not found")
    media_type = "application/json" if artifact == "json" else "text/csv"
    return FileResponse(path=Path(path), media_type=media_type, filename=path.name)
