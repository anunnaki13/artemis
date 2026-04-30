# Implementation Status

This tracks AIQ-BOT v2 blueprint coverage as of Phase 0 foundation.

## Implemented

- Repository scaffold matching the v2 architecture.
- Docker Compose development stack: frontend, backend, PostgreSQL/TimescaleDB, Redis, Prometheus.
- FastAPI backend with health, auth registration/login foundation, dashboard summary, risk policy, and encrypted settings endpoints.
- SQLAlchemy async setup and Alembic migrations for `users`, `audit_log`, and `app_settings`.
- Argon2 password hashing and TOTP verification helpers.
- Next.js app shell with all nine blueprint application routes.
- Frontend owner register/login flow wired to backend auth endpoints, including TOTP enrollment output.
- Basic docs, prompt templates, CI, Makefile, lint, test, and typecheck workflows.
- Frontend exposed on VPS port `3066`.
- Settings Vault UI can submit blueprint credentials to the backend without browser secret storage.

## Partially Implemented

- Authentication: register/login/TOTP enrollment is wired; refresh tokens, Redis-backed sessions, route guards, and rate limiting are pending.
- Database schema: foundation tables exist; full trading schema from Section 12 is pending.
- Settings Vault: encrypted persistence and masked reads exist; frontend preload/edit state still needs refinement.
- Risk policy: config file and read endpoint exist, but the five-layer risk engine is pending.
- Observability: Prometheus endpoint and service exist, but domain metrics and Grafana dashboards are pending.
- Frontend: route shell exists; production terminal UI is being improved before live data integration.

## Not Implemented Yet

- Binance REST/WebSocket market data service.
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

Phase 0 gate is close: `make test`, `make lint`, `make typecheck`, Docker Compose, and migrations are working locally. Before Phase 1, add session/rate-limit hardening and expand the foundation schema enough to support market-data ingestion.
