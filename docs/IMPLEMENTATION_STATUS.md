# Implementation Status

This tracks AIQ-BOT v2.1 blueprint coverage during the Binance-to-Bybit migration. Bybit is now the primary and only active runtime venue in the repository; older progress entries may still describe the original first-pass Binance implementation as historical context.

Current completion estimate: `~94%`

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
- Bybit public REST market-data ingestion for Spot symbols and candles.
- Bybit public WebSocket market-data streaming foundation with owner-controlled start/stop/status endpoints.
- Dashboard price stream now uses persisted Bybit candle-close series, with stale-candle refresh on the `/api/market-data/candles` read path and operator-side symbol/timeframe switching.
- Orderbook top-of-book snapshots from Bybit depth-delta streams.
- Funding-rate and open-interest polling snapshots from Bybit linear public endpoints.
- In-memory orderbook ladder reconstruction with derived spread, imbalance, and 0.5% liquidity-depth metrics.
- Depth-gap recovery by per-symbol orderbook rebootstrap, plus persisted liquidity-metric read endpoints.
- Dedicated `orderbook_snapshots` persistence for historical ladder slices and derived metrics.
- Initial strategy-layer consumption of orderbook metrics through `orderbook_imbalance` evaluation.
- Initial risk-layer consumption of strategy signals through capital-profile and hard-limit gating.
- Execution-intent queue with audit persistence for signals that pass the risk gate.
- Execution lifecycle worker stub with paper adapter and dispatch/execution state transitions.
- Reconciliation endpoint and stale-dispatch timeout sweep for execution lifecycle control.
- Stable execution adapter contract with persisted client/venue order identifiers.
- Order-id-based lookup and reconciliation for venue-facing lifecycle events.
- Stubbed Bybit execution adapter contract with transport abstraction and signed order-request builder.
- Runtime Bybit credential resolution and safe signed-order preview endpoint.
- Runtime-selected execution transport gating with authenticated Bybit path guarded behind explicit enablement.
- Feed-driven execution reconciliation with persisted raw venue events and async venue-status mapping.
- Bybit venue-native private-stream consumer for async execution updates with owner-controlled lifecycle endpoints.
- Runtime safety gating for Bybit live/private access requiring `UNIFIED`, whitelist IP, and withdrawal-disabled acknowledgement.
- Spot account-balance reconciliation from venue account events with persisted read model.
- Spot symbol-exposure reconciliation from execution fills with persisted average-entry and exposure state.
- Risk-gate consumption of persisted spot exposure state for open-position and total-exposure enforcement.
- Per-order cumulative fill-state persistence to prevent duplicate partial-fill events from double-counting symbol exposure.
- Persisted mark-to-market spot position state with realized and unrealized PnL fields refreshed from market snapshots.
- FIFO lot-level spot position accounting through persisted `spot_position_lots`, used to compute realized PnL from actual open lots instead of only blended average-entry state.
- Per-fill lot-close audit trail through persisted `spot_execution_fill_lot_closes`, so each closing fill can be traced to the lots it consumed and the realized PnL per consumed lot slice.
- Chain-level FIFO lot-close review API and operator UI, including weighted entry/exit prices and hold-to-close timing from persisted lot lifecycle timestamps.
- Execution-intent cancel/replace lineage for pre-dispatch intents with parent/replacement linkage and fresh risk re-evaluation.
- Venue-aware cancel path for `dispatching` execution intents with `cancel_requested` lifecycle support and adapter-backed cancellation.
- Persisted per-fill execution ledger for symbol-level journal and close-sequence accounting.
- Execution-quality and journal summary reads derived from the per-fill ledger.
- Fill-ledger attribution to execution intents and source strategies.
- Dashboard/operator read models for strategy cohorts, lineage alerts, digest artifacts, digest anomaly banner, and digest trend series.
- Dashboard/operator read models for Bybit venue diagnostics, strategy cohorts, lineage alerts, digest artifacts, digest anomaly banner, and digest trend series.
- Journal and Execution Quality pages backed by live fill-ledger, chain-summary, lineage-outcome, and strategy-attribution APIs.
- Execution-cost analytics for adverse slippage cost, adverse slippage bps, and underfill notional across fill summaries, intent outcomes, lineage outcomes, and strategy cohorts.
- AI Analyst OpenRouter integration with read-only live-context briefing, persisted `ai_analyst_runs`, and daily budget guardrails.
- AI Analyst review queue with persisted operator review state and review notes.
- Daily digest runner with retention, Telegram completion notice, anomaly scoring, persisted `daily_digest_runs`, range-filtered digest series, and series CSV export.
- Recovery monitor with persisted `recovery_events`, operator status API, background checks, and alert side effects.
- Backtest persisted runs, grouped overview read model, and walk-forward window analysis.
- Market-stream maintainer task that keeps Bybit stream bootstrap inside the app lifecycle instead of relying only on request-triggered recovery.
- First-pass Quantum design-system rollout in the global shell and key operator pages.
- Capital Profile Manager with v2.1 MICRO/SMALL/STANDARD/SCALED rules and growth-plan config.
- Telegram notification skeleton with protected test endpoint and encrypted settings lookup.
- Symbol Universe Manager foundation with Bybit 24h ticker filtering and blacklist enforcement.
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
- Notifications: Telegram test path exists; recurring heartbeat, severity routing, repeated critical alerts, and email fallback are pending.
- Edge modules: Symbol Universe Manager exists as an on-demand endpoint; daily scheduler, persistence, UI, and regime state machine are pending.
- Frontend: core operator pages are now backend-driven; Quantum design rollout is partially complete and still uneven page-to-page.
- Recovery: active and useful, but broader replay/repair tooling is still pending.
- Backtest: persisted, queryable, and walk-forward capable, but still not a full research engine.

## Not Implemented Yet

- Candle aggregation and snapshot persistence exist for Bybit kline, ticker, depth-delta, funding-rate, and open-interest feeds; orderbook ladders are reconstructed in memory, liquidity metrics are exposed both live and from recent persisted snapshots, and dedicated orderbook snapshot history is now persisted, while full unthrottled ladder persistence is still pending.
- Strategy registry, baseline strategies, and microstructure strategies.
- Full research engine depth: saved presets, Monte Carlo, sensitivity, Deflated Sharpe, and broader experiment orchestration.
- Execution engine, idempotent order placement, fill reconciliation, SL/TP manager.
- Paper trading simulator and live-vs-backtest divergence tracker.
- Full lot-level execution-quality and cost accounting pipeline.
- AI Analyst is reviewed but still lacks deeper recommendation-to-operator workflow and action queue semantics.
- Recovery/ops layer still lacks replay, drill, and deeper repair workflows.
- Full production deployment hardening, backups, Nginx TLS, and disaster recovery drills.
- Comprehensive research pipeline: backtest engine, walk-forward, Monte Carlo, sensitivity, and Deflated Sharpe.
- Multi-strategy registry with robust configuration, enablement, and comparative analytics.

## Next Blueprint Gate

Phase 1 now includes Bybit REST/WebSocket ingestion, futures-context polling, in-memory orderbook reconstruction, historical orderbook snapshot storage, strategy/risk/execution foundations, venue-native private-stream reconciliation, synced balances and positions, partial-fill dedupe, mark-to-market PnL, cancel/replace lifecycle, journal-grade fill ledger, strategy-attributed journal and execution-quality reads, venue diagnostics, first-pass execution-cost analytics, chain-level FIFO lot-close and hold-time review, dashboard/operator exports, scheduled digest reporting, digest anomaly scoring, persisted digest run logs, recovery monitoring, AI review queue, backtest persisted runs, and walk-forward analytics. The next blueprint gate is final live-execution hardening plus research-stack maturity, followed by full design-system completion.
