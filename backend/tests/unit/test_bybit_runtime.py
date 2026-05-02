from services.execution.bybit_runtime import (
    BybitExecutionRuntime,
    ensure_bybit_runtime_ready,
    validate_bybit_runtime,
)


class DummySession:
    pass


async def test_validate_bybit_runtime_accepts_safe_unified_setup(monkeypatch) -> None:
    values = {
        "BYBIT_WHITELISTED_IP": "103.150.197.225",
        "BYBIT_WITHDRAWAL_ENABLED": "false",
    }

    async def fake_get_runtime_setting(_session: object, key: str) -> str | None:
        return values.get(key)

    monkeypatch.setattr("services.execution.bybit_runtime.get_runtime_setting", fake_get_runtime_setting)

    validation = await validate_bybit_runtime(
        DummySession(),  # type: ignore[arg-type]
        BybitExecutionRuntime(
            api_key="key",
            api_secret="secret",
            base_url="https://api.bybit.com",
            testnet=False,
            live_transport_enabled=True,
            account_type="UNIFIED",
        ),
    )

    assert validation.live_ready is True
    assert validation.issues == []


async def test_ensure_bybit_runtime_ready_rejects_missing_whitelist_and_withdraw_enabled(monkeypatch) -> None:
    values = {
        "BYBIT_WHITELISTED_IP": "",
        "BYBIT_WITHDRAWAL_ENABLED": "true",
    }

    async def fake_get_runtime_setting(_session: object, key: str) -> str | None:
        return values.get(key)

    monkeypatch.setattr("services.execution.bybit_runtime.get_runtime_setting", fake_get_runtime_setting)

    try:
        await ensure_bybit_runtime_ready(
            DummySession(),  # type: ignore[arg-type]
            BybitExecutionRuntime(
                api_key="key",
                api_secret="secret",
                base_url="https://api.bybit.com",
                testnet=False,
                live_transport_enabled=True,
                account_type="CONTRACT",
            ),
        )
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected ValueError")

    assert "BYBIT_ACCOUNT_TYPE must be UNIFIED" in message
    assert "BYBIT_WHITELISTED_IP must be configured" in message
    assert "BYBIT_WITHDRAWAL_ENABLED must remain false" in message
