from datetime import date, datetime

from pydantic import BaseModel


class DailyDigestArtifactRead(BaseModel):
    report_date: date
    generated_at: datetime
    json_path: str
    strategy_csv_path: str
    lineage_csv_path: str
    fills_count: int | None = None
    intents_count: int | None = None
    lineage_alerts_count: int | None = None
    top_strategy: str | None = None
    top_strategy_realized_pnl_usd: str | None = None
    anomaly_score: int | None = None
    anomaly_flags: list[str] | None = None


class DailyDigestSeriesPointRead(BaseModel):
    report_date: date
    generated_at: datetime
    fills_count: int
    lineage_alerts_count: int
    anomaly_score: int
    top_strategy_realized_pnl_usd: str | None = None
    anomaly_flags: list[str] = []


class DailyDigestStrategyBreakdownRowRead(BaseModel):
    source_strategy: str
    fills_count: int
    chains_count: int
    gross_notional_usd: str
    gross_realized_pnl_usd: str
    win_rate: str


class DailyDigestLineageAlertRowRead(BaseModel):
    root_intent_id: int
    latest_intent_id: int
    symbol: str
    source_strategy: str
    lineage_size: int
    lineage_statuses: list[str]
    fill_ratio: str
    slippage_bps: str | None = None
    realized_pnl_usd: str
    last_fill_at: str | None = None


class DailyDigestPreviewRead(BaseModel):
    report_date: date
    generated_at: datetime
    fills_count: int
    intents_count: int
    strategy_breakdown: list[DailyDigestStrategyBreakdownRowRead]
    lineage_alerts: list[DailyDigestLineageAlertRowRead]
