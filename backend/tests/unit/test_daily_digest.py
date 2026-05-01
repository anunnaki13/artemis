from datetime import UTC, date, datetime
from pathlib import Path

from services.reports.daily_digest import DailyDigestArtifact, DailyDigestService


class StubDigestService(DailyDigestService):
    async def build_snapshot(self, session: object, report_date: date) -> dict[str, object]:
        return {
            "report_date": report_date.isoformat(),
            "generated_at": datetime(2026, 5, 1, 0, 0, tzinfo=UTC).isoformat(),
            "fills_count": 2,
            "intents_count": 1,
            "strategy_breakdown": [
                {
                    "source_strategy": "orderbook_imbalance",
                    "fills_count": 2,
                    "chains_count": 1,
                    "gross_notional_usd": "1000",
                    "gross_realized_pnl_usd": "25",
                    "win_rate": "1",
                }
            ],
            "lineage_alerts": [
                {
                    "root_intent_id": 10,
                    "latest_intent_id": 11,
                    "symbol": "BTCUSDT",
                    "source_strategy": "orderbook_imbalance",
                    "lineage_size": 2,
                    "lineage_statuses": ["cancelled", "executed"],
                    "fill_ratio": "0.85",
                    "slippage_bps": "8.5",
                    "realized_pnl_usd": "12",
                    "last_fill_at": datetime(2026, 5, 1, 1, 0, tzinfo=UTC).isoformat(),
                }
            ],
        }


class FakeSession:
    async def commit(self) -> None:
        return None


def test_daily_digest_list_artifacts_reads_generated_files(tmp_path: Path) -> None:
    service = DailyDigestService()
    service._settings.reports_output_dir = str(tmp_path)  # type: ignore[misc]

    report_dir = tmp_path / "2026-05-01"
    report_dir.mkdir(parents=True)
    (report_dir / "summary.json").write_text("{}", encoding="utf-8")
    (report_dir / "strategy_breakdown.csv").write_text("a,b\n", encoding="utf-8")
    (report_dir / "lineage_alerts.csv").write_text("a,b\n", encoding="utf-8")

    artifacts = service.list_artifacts(limit=10)

    assert len(artifacts) == 1
    assert artifacts[0].report_date == date(2026, 5, 1)


def test_daily_digest_list_artifact_summaries_reads_operational_fields(tmp_path: Path) -> None:
    service = DailyDigestService()
    service._settings.reports_output_dir = str(tmp_path)  # type: ignore[misc]

    report_dir = tmp_path / "2026-05-01"
    report_dir.mkdir(parents=True)
    (report_dir / "summary.json").write_text(
        """
        {
          "report_date": "2026-05-01",
          "generated_at": "2026-05-01T00:00:00+00:00",
          "fills_count": 2,
          "intents_count": 1,
          "strategy_breakdown": [
            {"source_strategy": "orderbook_imbalance", "gross_realized_pnl_usd": "25"},
            {"source_strategy": "mean_reversion", "gross_realized_pnl_usd": "10"}
          ],
          "lineage_alerts": [{"root_intent_id": 10}]
        }
        """.strip(),
        encoding="utf-8",
    )
    (report_dir / "strategy_breakdown.csv").write_text("a,b\n", encoding="utf-8")
    (report_dir / "lineage_alerts.csv").write_text("a,b\n", encoding="utf-8")

    summaries = service.list_artifact_summaries(limit=10)

    assert len(summaries) == 1
    assert summaries[0].fills_count == 2
    assert summaries[0].intents_count == 1
    assert summaries[0].lineage_alerts_count == 1
    assert summaries[0].top_strategy == "orderbook_imbalance"
    assert str(summaries[0].top_strategy_realized_pnl_usd) == "25"
    assert summaries[0].anomaly_score == 0
    assert summaries[0].anomaly_flags == []


def test_daily_digest_summary_scores_anomalies(tmp_path: Path) -> None:
    service = DailyDigestService()
    service._settings.reports_output_dir = str(tmp_path)  # type: ignore[misc]

    report_dir = tmp_path / "2026-05-02"
    report_dir.mkdir(parents=True)
    (report_dir / "summary.json").write_text(
        """
        {
          "report_date": "2026-05-02",
          "generated_at": "2026-05-02T00:00:00+00:00",
          "fills_count": 0,
          "intents_count": 2,
          "strategy_breakdown": [
            {"source_strategy": "orderbook_imbalance", "gross_realized_pnl_usd": "-12"}
          ],
          "lineage_alerts": [{"root_intent_id": 1}, {"root_intent_id": 2}, {"root_intent_id": 3}]
        }
        """.strip(),
        encoding="utf-8",
    )
    (report_dir / "strategy_breakdown.csv").write_text("a,b\n", encoding="utf-8")
    (report_dir / "lineage_alerts.csv").write_text("a,b\n", encoding="utf-8")

    summary = service.list_artifact_summaries(limit=10)[0]

    assert summary.anomaly_score == 3
    assert summary.anomaly_flags == [
        "zero_fills",
        "negative_top_strategy_pnl",
        "high_lineage_alerts",
    ]


def test_daily_digest_cleanup_expired_artifacts_removes_old_directories(tmp_path: Path) -> None:
    service = DailyDigestService()
    service._settings.reports_output_dir = str(tmp_path)  # type: ignore[misc]
    service._settings.reports_daily_digest_retention_days = 7  # type: ignore[misc]

    old_dir = tmp_path / "2026-04-01"
    old_dir.mkdir(parents=True)
    (old_dir / "summary.json").write_text("{}", encoding="utf-8")

    fresh_dir = tmp_path / "2026-05-01"
    fresh_dir.mkdir(parents=True)
    (fresh_dir / "summary.json").write_text("{}", encoding="utf-8")

    deleted = service.cleanup_expired_artifacts(today=date(2026, 5, 2))

    assert deleted == ["2026-04-01"]
    assert not old_dir.exists()
    assert fresh_dir.exists()


async def test_daily_digest_generate_writes_json_and_csv_files(tmp_path: Path) -> None:
    service = StubDigestService()
    service._settings.reports_output_dir = str(tmp_path)  # type: ignore[misc]

    artifact = await service.generate(FakeSession(), date(2026, 5, 1))  # type: ignore[arg-type]

    assert Path(artifact.json_path).exists()
    assert Path(artifact.strategy_csv_path).exists()
    assert Path(artifact.lineage_csv_path).exists()
    assert "orderbook_imbalance" in Path(artifact.strategy_csv_path).read_text(encoding="utf-8")
    assert "BTCUSDT" in Path(artifact.lineage_csv_path).read_text(encoding="utf-8")


def test_daily_digest_message_contains_operational_summary(tmp_path: Path) -> None:
    service = DailyDigestService()
    digest_artifact = DailyDigestArtifact(
        report_date=date(2026, 5, 1),
        generated_at=datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
        json_path=str(tmp_path / "summary.json"),
        strategy_csv_path=str(tmp_path / "strategy_breakdown.csv"),
        lineage_csv_path=str(tmp_path / "lineage_alerts.csv"),
    )
    snapshot = {
        "fills_count": 2,
        "intents_count": 1,
        "strategy_breakdown": [
            {
                "source_strategy": "orderbook_imbalance",
                "gross_realized_pnl_usd": "25",
            },
            {
                "source_strategy": "mean_reversion",
                "gross_realized_pnl_usd": "10",
            },
        ],
        "lineage_alerts": [{"root_intent_id": 10}],
    }

    message = service._build_digest_message(digest_artifact, snapshot)

    assert "fills: 2" in message
    assert "intents: 1" in message
    assert "top_strategy: orderbook_imbalance (25 USD)" in message
    assert "lineage_alerts: 1" in message
