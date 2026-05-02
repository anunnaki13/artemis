from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models import RecoveryEvent
from services.recovery.monitor import assess_recovery_status, should_send_critical_alert


def test_assess_recovery_status_critical_flags() -> None:
    snapshot = assess_recovery_status(
        market_stream_running=False,
        candle_age_minutes=Decimal("12"),
        live_transport_enabled=False,
        user_stream_running=False,
        stale_dispatching_count=1,
        high_severity_incidents=0,
        digest_anomaly_score=0,
        ai_budget_utilization=Decimal("0.25"),
    )
    assert snapshot.status == "critical"
    assert snapshot.severity == "high"
    assert "market_stream_stopped" in snapshot.flags
    assert "candle_feed_stale" in snapshot.flags
    assert "stale_dispatching_intents" in snapshot.flags


def test_should_send_critical_alert_on_changed_flags() -> None:
    previous = RecoveryEvent(
        id=1,
        status="critical",
        severity="high",
        flags=["market_stream_stopped"],
        summary_payload={},
        created_at=datetime.now(UTC),
    )
    snapshot = assess_recovery_status(
        market_stream_running=False,
        candle_age_minutes=Decimal("12"),
        live_transport_enabled=False,
        user_stream_running=False,
        stale_dispatching_count=0,
        high_severity_incidents=0,
        digest_anomaly_score=0,
        ai_budget_utilization=Decimal("0.25"),
    )
    assert should_send_critical_alert(previous, snapshot, cooldown_minutes=30) is True


def test_should_not_send_critical_alert_inside_cooldown_without_change() -> None:
    previous = RecoveryEvent(
        id=1,
        status="critical",
        severity="high",
        flags=["market_stream_stopped", "candle_feed_stale"],
        summary_payload={},
        created_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    snapshot = assess_recovery_status(
        market_stream_running=False,
        candle_age_minutes=Decimal("12"),
        live_transport_enabled=False,
        user_stream_running=False,
        stale_dispatching_count=0,
        high_severity_incidents=0,
        digest_anomaly_score=0,
        ai_budget_utilization=Decimal("0.25"),
    )
    assert should_send_critical_alert(previous, snapshot, cooldown_minutes=30) is False
