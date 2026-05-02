# Runbook

## Safe Defaults

- Default mode is `paper`.
- Withdrawal automation is never implemented.
- `BYBIT_WITHDRAWAL_ENABLED` must remain `false`.
- Live Bybit runtime requires `BYBIT_ACCOUNT_TYPE=UNIFIED` and a configured `BYBIT_WHITELISTED_IP`.
- If state reconciliation conflicts with Bybit, Bybit is the source of truth.
- Critical failures should pause new entries or flatten positions once live execution exists.

## Phase 0 Incidents

Phase 0 has no live trading. Operational incidents are limited to API, database, Redis, frontend, and CI failures.
