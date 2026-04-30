# Runbook

## Safe Defaults

- Default mode is `paper`.
- Withdrawal automation is never implemented.
- If state reconciliation conflicts with Binance, Binance is the source of truth.
- Critical failures should pause new entries or flatten positions once live execution exists.

## Phase 0 Incidents

Phase 0 has no live trading. Operational incidents are limited to API, database, Redis, frontend, and CI failures.

