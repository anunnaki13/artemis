import asyncio
import csv
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.core.runtime_settings import get_runtime_setting
from app.models import DailyDigestRun, ExecutionIntent, SpotExecutionFill
from services.execution.fill_analytics import summarize_intent_lineage_outcomes, summarize_strategy_quality
from services.notification.telegram import TelegramConfig, TelegramNotifier


@dataclass(frozen=True)
class DailyDigestArtifact:
    report_date: date
    generated_at: datetime
    json_path: str
    strategy_csv_path: str
    lineage_csv_path: str


@dataclass(frozen=True)
class DailyDigestArtifactSummary:
    report_date: date
    generated_at: datetime
    json_path: str
    strategy_csv_path: str
    lineage_csv_path: str
    fills_count: int
    intents_count: int
    lineage_alerts_count: int
    top_strategy: str | None
    top_strategy_realized_pnl_usd: Decimal | None
    anomaly_score: int
    anomaly_flags: list[str]


class DailyDigestService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._session_factory = session_factory
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    @property
    def output_dir(self) -> Path:
        return Path(self._settings.reports_output_dir)

    def _date_bounds(self, report_date: date) -> tuple[datetime, datetime]:
        start = datetime.combine(report_date, time.min, tzinfo=UTC)
        end = start + timedelta(days=1)
        return start, end

    async def build_snapshot(self, session: AsyncSession, report_date: date) -> dict[str, object]:
        start_at, end_at = self._date_bounds(report_date)
        fills = list(
            (
                await session.scalars(
                    select(SpotExecutionFill)
                    .where(SpotExecutionFill.filled_at >= start_at, SpotExecutionFill.filled_at < end_at)
                    .order_by(SpotExecutionFill.filled_at.desc())
                )
            ).all()
        )
        intents = list(
            (
                await session.scalars(
                    select(ExecutionIntent)
                    .where(ExecutionIntent.created_at >= start_at, ExecutionIntent.created_at < end_at)
                    .order_by(ExecutionIntent.created_at.desc())
                )
            ).all()
        )
        strategy_breakdown = summarize_strategy_quality(fills)
        lineage_outcomes = summarize_intent_lineage_outcomes(intents, fills)
        lineage_alerts = [
            item
            for item in lineage_outcomes
            if item.lineage_size > 1
            and (
                (item.slippage_bps is not None and item.slippage_bps > Decimal("5"))
                or item.fill_ratio < Decimal("0.9")
            )
        ]
        return {
            "report_date": report_date.isoformat(),
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "fills_count": len(fills),
            "intents_count": len(intents),
            "strategy_breakdown": [
                {
                    "source_strategy": item.source_strategy,
                    "fills_count": item.fills_count,
                    "chains_count": item.chains_count,
                    "gross_notional_usd": str(item.gross_notional_usd),
                    "gross_realized_pnl_usd": str(item.gross_realized_pnl_usd),
                    "win_rate": str(item.win_rate),
                }
                for item in strategy_breakdown
            ],
            "lineage_alerts": [
                {
                    "root_intent_id": item.root_intent_id,
                    "latest_intent_id": item.latest_intent_id,
                    "symbol": item.symbol,
                    "source_strategy": item.source_strategy,
                    "lineage_size": item.lineage_size,
                    "lineage_statuses": item.lineage_statuses,
                    "fill_ratio": str(item.fill_ratio),
                    "slippage_bps": None if item.slippage_bps is None else str(item.slippage_bps),
                    "realized_pnl_usd": str(item.realized_pnl_usd),
                    "last_fill_at": None if item.last_fill_at is None else item.last_fill_at.isoformat(),
                }
                for item in lineage_alerts
            ],
        }

    def _write_csv(self, path: Path, headers: list[str], rows: list[list[object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)

    def _build_digest_message(self, artifact: DailyDigestArtifact, snapshot: dict[str, object]) -> str:
        summary = self._summarize_snapshot(snapshot)
        top_strategy_line = "top_strategy: n/a"
        if summary.top_strategy is not None and summary.top_strategy_realized_pnl_usd is not None:
            top_strategy_line = (
                f"top_strategy: {summary.top_strategy} ({summary.top_strategy_realized_pnl_usd} USD)"
            )
        elif summary.top_strategy is not None:
            top_strategy_line = f"top_strategy: {summary.top_strategy}"
        return (
            f"Daily digest ready\n"
            f"date: {artifact.report_date.isoformat()}\n"
            f"generated_at: {artifact.generated_at.isoformat()}\n"
            f"fills: {summary.fills_count}\n"
            f"intents: {summary.intents_count}\n"
            f"{top_strategy_line}\n"
            f"lineage_alerts: {summary.lineage_alerts_count}\n"
            f"json: {artifact.json_path}\n"
            f"strategy_csv: {artifact.strategy_csv_path}\n"
            f"lineage_csv: {artifact.lineage_csv_path}"
        )

    def _summarize_snapshot(self, snapshot: dict[str, object]) -> DailyDigestArtifactSummary:
        strategy_rows = cast(list[dict[str, object]], snapshot.get("strategy_breakdown", []))
        lineage_rows = cast(list[dict[str, object]], snapshot.get("lineage_alerts", []))
        top_strategy = max(
            strategy_rows,
            key=lambda item: Decimal(str(item.get("gross_realized_pnl_usd", "0"))),
            default=None,
        )
        top_strategy_name = None
        top_strategy_realized_pnl_usd = None
        if top_strategy is not None:
            top_strategy_name = str(top_strategy.get("source_strategy") or "unknown")
            top_strategy_realized_pnl_usd = Decimal(str(top_strategy.get("gross_realized_pnl_usd", "0")))
        fills_count = int(str(snapshot.get("fills_count", 0)))
        intents_count = int(str(snapshot.get("intents_count", 0)))
        anomaly_flags: list[str] = []
        if fills_count == 0:
            anomaly_flags.append("zero_fills")
        if top_strategy_realized_pnl_usd is not None and top_strategy_realized_pnl_usd < 0:
            anomaly_flags.append("negative_top_strategy_pnl")
        if len(lineage_rows) >= 3:
            anomaly_flags.append("high_lineage_alerts")
        return DailyDigestArtifactSummary(
            report_date=date.fromisoformat(str(snapshot.get("report_date", "1970-01-01"))),
            generated_at=datetime.fromisoformat(str(snapshot.get("generated_at", "1970-01-01T00:00:00+00:00"))),
            json_path="",
            strategy_csv_path="",
            lineage_csv_path="",
            fills_count=fills_count,
            intents_count=intents_count,
            lineage_alerts_count=len(lineage_rows),
            top_strategy=top_strategy_name,
            top_strategy_realized_pnl_usd=top_strategy_realized_pnl_usd,
            anomaly_score=len(anomaly_flags),
            anomaly_flags=anomaly_flags,
        )

    async def generate(self, session: AsyncSession, report_date: date) -> DailyDigestArtifact:
        snapshot = await self.build_snapshot(session, report_date)
        report_dir = self.output_dir / report_date.isoformat()
        report_dir.mkdir(parents=True, exist_ok=True)
        json_path = report_dir / "summary.json"
        strategy_csv_path = report_dir / "strategy_breakdown.csv"
        lineage_csv_path = report_dir / "lineage_alerts.csv"
        json_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        strategy_rows = cast(list[dict[str, object]], snapshot["strategy_breakdown"])
        lineage_rows = cast(list[dict[str, object]], snapshot["lineage_alerts"])
        self._write_csv(
            strategy_csv_path,
            [
                "source_strategy",
                "fills_count",
                "chains_count",
                "gross_notional_usd",
                "gross_realized_pnl_usd",
                "win_rate",
            ],
            [
                [
                    item["source_strategy"],
                    item["fills_count"],
                    item["chains_count"],
                    item["gross_notional_usd"],
                    item["gross_realized_pnl_usd"],
                    item["win_rate"],
                ]
                for item in strategy_rows
            ],
        )
        self._write_csv(
            lineage_csv_path,
            [
                "root_intent_id",
                "latest_intent_id",
                "symbol",
                "source_strategy",
                "lineage_size",
                "lineage_statuses",
                "fill_ratio",
                "slippage_bps",
                "realized_pnl_usd",
                "last_fill_at",
            ],
            [
                [
                    item["root_intent_id"],
                    item["latest_intent_id"],
                    item["symbol"],
                    item["source_strategy"],
                    item["lineage_size"],
                    " | ".join(cast(list[str], item["lineage_statuses"])),
                    item["fill_ratio"],
                    item["slippage_bps"],
                    item["realized_pnl_usd"],
                    item["last_fill_at"],
                ]
                for item in lineage_rows
            ],
        )
        return DailyDigestArtifact(
            report_date=report_date,
            generated_at=datetime.fromisoformat(str(snapshot["generated_at"])),
            json_path=str(json_path),
            strategy_csv_path=str(strategy_csv_path),
            lineage_csv_path=str(lineage_csv_path),
        )

    def list_artifacts(self, limit: int = 30) -> list[DailyDigestArtifact]:
        if not self.output_dir.exists():
            return []
        artifacts: list[DailyDigestArtifact] = []
        for report_dir in sorted((path for path in self.output_dir.iterdir() if path.is_dir()), reverse=True):
            try:
                report_date = date.fromisoformat(report_dir.name)
            except ValueError:
                continue
            json_path = report_dir / "summary.json"
            strategy_csv_path = report_dir / "strategy_breakdown.csv"
            lineage_csv_path = report_dir / "lineage_alerts.csv"
            if not json_path.exists():
                continue
            generated_at = datetime.fromtimestamp(json_path.stat().st_mtime, tz=UTC)
            artifacts.append(
                DailyDigestArtifact(
                    report_date=report_date,
                    generated_at=generated_at,
                    json_path=str(json_path),
                    strategy_csv_path=str(strategy_csv_path),
                    lineage_csv_path=str(lineage_csv_path),
                )
            )
            if len(artifacts) >= limit:
                break
        return artifacts

    def list_artifact_summaries(self, limit: int = 30) -> list[DailyDigestArtifactSummary]:
        summaries: list[DailyDigestArtifactSummary] = []
        for artifact in self.list_artifacts(limit):
            snapshot = cast(dict[str, object], json.loads(Path(artifact.json_path).read_text(encoding="utf-8")))
            base_summary = self._summarize_snapshot(snapshot)
            summaries.append(
                DailyDigestArtifactSummary(
                    report_date=artifact.report_date,
                    generated_at=artifact.generated_at,
                    json_path=artifact.json_path,
                    strategy_csv_path=artifact.strategy_csv_path,
                    lineage_csv_path=artifact.lineage_csv_path,
                    fills_count=base_summary.fills_count,
                    intents_count=base_summary.intents_count,
                    lineage_alerts_count=base_summary.lineage_alerts_count,
                    top_strategy=base_summary.top_strategy,
                    top_strategy_realized_pnl_usd=base_summary.top_strategy_realized_pnl_usd,
                    anomaly_score=base_summary.anomaly_score,
                    anomaly_flags=base_summary.anomaly_flags,
                )
            )
        return summaries

    async def upsert_run_log(self, session: AsyncSession, artifact: DailyDigestArtifact) -> DailyDigestRun:
        snapshot = cast(dict[str, object], json.loads(Path(artifact.json_path).read_text(encoding="utf-8")))
        summary = self._summarize_snapshot(snapshot)
        run = await session.get(DailyDigestRun, artifact.report_date)
        if run is None:
            run = DailyDigestRun(
                report_date=artifact.report_date,
                generated_at=artifact.generated_at,
                fills_count=summary.fills_count,
                intents_count=summary.intents_count,
                lineage_alerts_count=summary.lineage_alerts_count,
                top_strategy=summary.top_strategy,
                top_strategy_realized_pnl_usd=summary.top_strategy_realized_pnl_usd,
                anomaly_score=summary.anomaly_score,
                anomaly_flags=summary.anomaly_flags,
                json_path=artifact.json_path,
                strategy_csv_path=artifact.strategy_csv_path,
                lineage_csv_path=artifact.lineage_csv_path,
            )
            session.add(run)
            await session.flush()
            return run
        run.generated_at = artifact.generated_at
        run.fills_count = summary.fills_count
        run.intents_count = summary.intents_count
        run.lineage_alerts_count = summary.lineage_alerts_count
        run.top_strategy = summary.top_strategy
        run.top_strategy_realized_pnl_usd = summary.top_strategy_realized_pnl_usd
        run.anomaly_score = summary.anomaly_score
        run.anomaly_flags = summary.anomaly_flags
        run.json_path = artifact.json_path
        run.strategy_csv_path = artifact.strategy_csv_path
        run.lineage_csv_path = artifact.lineage_csv_path
        await session.flush()
        return run

    async def list_run_logs(self, session: AsyncSession, limit: int = 30) -> list[DailyDigestRun]:
        rows = list(
            (
                await session.scalars(
                    select(DailyDigestRun)
                    .order_by(DailyDigestRun.generated_at.desc())
                    .limit(limit)
                )
            ).all()
        )
        if rows:
            return rows
        for artifact in self.list_artifacts(limit):
            await self.upsert_run_log(session, artifact)
        await session.flush()
        return list(
            (
                await session.scalars(
                    select(DailyDigestRun)
                    .order_by(DailyDigestRun.generated_at.desc())
                    .limit(limit)
                )
            ).all()
        )

    def cleanup_expired_artifacts(self, today: date | None = None) -> list[str]:
        today = today or datetime.now(tz=UTC).date()
        retention_days = max(self._settings.reports_daily_digest_retention_days, 1)
        cutoff = today - timedelta(days=retention_days)
        deleted: list[str] = []
        if not self.output_dir.exists():
            return deleted
        for report_dir in self.output_dir.iterdir():
            if not report_dir.is_dir():
                continue
            try:
                report_date = date.fromisoformat(report_dir.name)
            except ValueError:
                continue
            if report_date >= cutoff:
                continue
            for child in report_dir.iterdir():
                if child.is_file():
                    child.unlink(missing_ok=True)
            report_dir.rmdir()
            deleted.append(report_dir.name)
        return deleted

    async def _notify_digest_generated(self, session: AsyncSession, artifact: DailyDigestArtifact) -> None:
        if not self._settings.reports_daily_digest_telegram_enabled:
            return
        fallback_token = (
            self._settings.telegram_bot_token.get_secret_value()
            if self._settings.telegram_bot_token is not None
            else None
        )
        bot_token = await get_runtime_setting(session, "TELEGRAM_BOT_TOKEN", fallback_token)
        chat_id = await get_runtime_setting(session, "TELEGRAM_CHAT_ID", self._settings.telegram_chat_id)
        if bot_token is None or chat_id is None:
            return
        notifier = TelegramNotifier(TelegramConfig(bot_token=bot_token, chat_id=chat_id))
        snapshot = cast(dict[str, object], json.loads(Path(artifact.json_path).read_text(encoding="utf-8")))
        message = self._build_digest_message(artifact, snapshot)
        try:
            await notifier.send_message(message)
        except Exception:
            return

    async def run_for_date(self, report_date: date) -> DailyDigestArtifact:
        if self._session_factory is None:
            raise RuntimeError("daily digest session factory is not configured")
        async with self._session_factory() as session:
            artifact = await self.generate(session, report_date)
            await self.upsert_run_log(session, artifact)
            self.cleanup_expired_artifacts(report_date)
            await self._notify_digest_generated(session, artifact)
            await session.commit()
            return artifact

    async def _scheduler_loop(self) -> None:
        while not self._stop_event.is_set():
            now = datetime.now(tz=UTC)
            target = datetime.combine(now.date(), time(hour=self._settings.reports_daily_digest_hour_utc), tzinfo=UTC)
            if target <= now:
                target += timedelta(days=1)
            wait_seconds = (target - now).total_seconds()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=wait_seconds)
                break
            except TimeoutError:
                await self.run_for_date((target - timedelta(days=1)).date())

    async def start(self) -> None:
        if not self._settings.reports_daily_digest_enabled or self._session_factory is None:
            return
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
