# Implementation Status

This tracks AIQ-BOT v2.1 blueprint coverage as of Phase 1 foundation.

## Implemented

- Repository scaffold matching the v2 architecture.
- Docker Compose development stack: frontend, backend, PostgreSQL/TimescaleDB, Redis, Prometheus.
- FastAPI backend with health, auth registration/login foundation, dashboard summary, risk policy, and encrypted settings endpoints.
- SQLAlchemy async setup and Alembic migrations for `users`, `audit_log`, `app_settings`, `symbols`, `candles`, and `market_snapshots`.
- Argon2 password hashing and TOTP verification helpers.
- Next.js app shell with all nine blueprint application routes.
- Frontend owner register/login flow wired to backend auth endpoints, including TOTP enrollment output.
- Redis-backed auth rate limits, JWT session registry, `/auth/me`, and `/auth/logout` foundation.
- Frontend app route guard validates the HttpOnly cookie session through `/auth/me`.
- Binance public REST market-data ingestion for Spot symbols and candles.
- Capital Profile Manager with v2.1 MICRO/SMALL/STANDARD/SCALED rules and growth-plan config.
- Basic docs, prompt templates, CI, Makefile, lint, test, and typecheck workflows.
- Frontend exposed on VPS port `3066`.
- Settings Vault UI can submit blueprint credentials to the backend without browser secret storage.
- Settings Vault UI preloads configured state, non-secret values, and masked placeholders for secrets.

## Partially Implemented

- Authentication: register/login/TOTP enrollment, Redis-backed session checks, HttpOnly access cookie, logout, rate limits, and frontend route guards are wired; refresh token rotation is pending.
- Database schema: auth, settings, audit, and market-data foundation tables exist; full trading/execution schema from Section 12 is pending.
- Settings Vault: encrypted persistence, masked reads, and frontend preload exist; connection testing is pending.
- Risk policy: config file and read endpoint exist, but the five-layer risk engine is pending.
- Capital profiles: read/evaluate path exists; automatic hourly equity refresh, audit logging, and Telegram profile-change notifications are pending.
- Observability: Prometheus endpoint and service exist, but domain metrics and Grafana dashboards are pending.
- Frontend: route shell exists; production terminal UI is being improved before live data integration.

## Not Implemented Yet

- Binance WebSocket market data service.
- Candle aggregation, orderbook delta sync, funding/open-interest polling.
- Strategy registry, baseline strategies, and microstructure strategies.
- Backtest engine, walk-forward validation, Monte Carlo, sensitivity, Deflated Sharpe.
- Execution engine, idempotent order placement, fill reconciliation, SL/TP manager.
- Paper trading simulator and live-vs-backtest divergence tracker.
- Full execution quality and cost accounting pipeline.
- AI Analyst OpenRouter integration and suggestion approval workflow.
- Notification service, Telegram alerts, recovery service, and dead-man switch.
- Full production deployment hardening, backups, Nginx TLS, and disaster recovery drills.

## Next Blueprint Gate

Phase 1 has started with Binance public REST ingestion. Next implementation step is Binance WebSocket streaming and candle aggregation.
