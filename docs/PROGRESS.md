# Progress Log

Current overall completion estimate: `~94%`

## 2026-05-02

### Completed

- Fixed the `daily-digest/runs` request-validation mismatch that caused frontend callers using `limit=365` to receive `422`.
- Hardened market-stream lifecycle:
  - added throttled `ensure_market_stream_running(...)`
  - added startup maintainer task in the app process
  - recovery monitor now ensures the stream before evaluating runtime health
- Improved recovery signal quality after restart:
  - latest direct recovery check no longer flags `market_stream_stopped`
  - current expected warning is digest/anomaly-related when there are zero fills
- Added AI Analyst review workflow:
  - persisted review metadata on `ai_analyst_runs`
  - queue endpoint
  - review action endpoint
  - frontend review controls for `pending / approved / rejected / follow_up`
- Added recovery monitoring:
  - `recovery_events` table
  - background monitor loop
  - `/api/recovery/status`
  - `/api/recovery/events`
  - `/api/recovery/checks/run`
  - heartbeat/dead-man/Telegram hooks
- Added backtest persistence and research-read models:
  - `backtest_runs` table
  - `/api/backtest/runs`
  - `/api/backtest/overview`
  - `/api/backtest/walk-forward`
  - grouped strategy/timeframe summaries
  - window-by-window walk-forward results
- Continued page-level Quantum design rollout from `AIQ-DESIGN-SYSTEM-BLUEPRINT.md`:
  - global shell/base tokens
  - `terminal`
  - `logs`
  - `strategies`
- Promoted Bybit to the active venue runtime across market data, execution preview, and private-stream account sync.
- Added safer Bybit operator/runtime visibility:
  - dashboard now shows Bybit runtime readiness, mainnet/testnet mode, and transport safety state
  - settings guidance now explains demo/testnet flow and keeps live transport as an explicit last switch
- Fixed the dashboard price stream so it now renders actual candle closes rather than reusing liquidity-history lines:
  - `/api/market-data/candles` now refreshes stale Bybit candle data on demand
  - dashboard price stream supports `BTCUSDT`, `ETHUSDT`, and `SOLUSDT`
  - dashboard price stream supports `1m`, `5m`, and `15m`
- Added Bybit REST/WebSocket market-data clients and stream service for:
  - Spot symbol sync
  - candle ingestion
  - ticker snapshots
  - orderbook depth updates
  - funding-rate and open-interest polling
- Added Bybit execution runtime, adapter, authenticated transport, and private-stream consumer.
- Switched owner settings surface from Binance credentials to Bybit credentials and account metadata.
- Added live/private-access Bybit runtime guardrails:
  - `BYBIT_ACCOUNT_TYPE` must be `UNIFIED`
  - `BYBIT_WHITELISTED_IP` must be configured
  - `BYBIT_WITHDRAWAL_ENABLED` must remain `false`
- Trimmed the active execution package surface to Bybit-first exports only.
- Removed legacy Binance runtime modules and legacy Binance unit suites from the active repository path.
- Imported [BINANCE-TO-BYBIT-MIGRATION.md](/home/damnation/trade/BINANCE-TO-BYBIT-MIGRATION.md:1) into the local repository so the migration blueprint now lives with the working tree.
- Hardened live Bybit transport so `retCode != 0` is treated as venue failure even on HTTP `200`.
- Added venue diagnostics and operator alerting for Bybit reject/cancel/partial events:
  - `/api/execution/venues/events`
  - `/api/execution/venues/events/export`
  - dashboard venue-event summary and alert cards
- Added execution-cost analytics:
  - adverse slippage bps
  - adverse slippage cost
  - underfill notional
- Added FIFO lot-level spot position accounting:
  - new `spot_position_lots` table
  - realized PnL on sells now consumes persisted open lots instead of relying only on blended average-entry math
- Added close-lot audit trail:
  - new `spot_execution_fill_lot_closes` table
  - each closing fill now records which lots it consumed and realized PnL per consumed lot slice
- Added chain-level FIFO lot-close review:
  - `/api/execution/account/fills/chains/{chain_key}/lot-closes`
  - weighted entry/exit rollup per chain
  - hold-to-close timing derived from persisted lot `opened_at` and close timestamps
- Surfaced execution-cost metrics in:
  - dashboard strategy cohorts
  - Journal
  - Execution Quality
- Surfaced FIFO lot-close review in operator UI:
  - `Journal` now shows per-fill and per-chain lot-close breakdown
  - `Execution Quality` now shows lot hold cohorts for selected recent chains
- Replaced placeholder `Strategies`, `Risk`, `Terminal`, `Backtest`, and `AI Analyst` pages with backend-driven read models.
- Added read-only OpenRouter analyst flow:
  - `/api/ai-analyst/brief`
  - `/api/ai-analyst/runs`
  - `/api/ai-analyst/budget`
  - persisted `ai_analyst_runs`
  - daily cost guard using `AI_MAX_COST_USD_PER_DAY`

### Current Delivered Sequence

1. foundation, auth, settings vault
2. market-data ingestion and orderbook reconstruction
3. strategy evaluation and risk gate
4. execution queue, lifecycle, reconciliation, cancel, and replace
5. venue account sync, balances, positions, and PnL
6. journal, execution-quality, and execution-cost analytics
7. venue diagnostics and operator alerting
8. dashboard exports, digests, anomaly tracking, and digest trend tooling
9. Bybit-primary venue migration and runtime safety gating
10. AI Analyst live integration and review queue
11. recovery monitor and persisted ops events
12. backtest persisted runs, overview, and walk-forward
13. first-pass Quantum design-system rollout

### Next Development Sequence

1. finish Quantum restyle for `dashboard`, `backtest`, `risk`, `journal`, and `execution-quality`
2. harden live execution further:
   - retry/idempotency discipline
   - safer repair/replay workflows
   - deeper venue reconciliation
3. mature research stack:
   - saved presets
   - richer exports
   - better walk-forward comparisons
   - later Monte Carlo / sensitivity
4. continue ops/recovery polish and operator drill tooling

## 2026-05-01

Historical note: the entries below describe the original first-pass venue implementation before the repository was cut over to a Bybit-primary runtime on `2026-05-02`.

### Completed

- Wired frontend owner authentication to backend endpoints:
  - owner registration posts to `/api/auth/register`
  - login posts to `/api/auth/login`
  - registration displays TOTP secret and provisioning URI for authenticator enrollment
  - successful login stores the short-lived access token in an HttpOnly backend cookie
- Wired Settings page to preload backend configuration status:
  - configured/empty status is shown per field
  - non-secret values preload into inputs
  - secret inputs stay blank and show masked backend values only as placeholders
- Added Phase 1 market-data persistence foundation:
  - `symbols` table for Binance symbol filters and status
  - `candles` table for OHLCV ingestion
  - `market_snapshots` table for ticker/orderbook/funding/open-interest snapshots
- Added auth hardening foundation:
  - Redis-backed login/register rate limits
  - access-token session registry keyed by JWT `jti`
  - `/api/auth/me` session validation endpoint
  - `/api/auth/logout` session revocation endpoint
- Wired app route guard to `/api/auth/me` so protected pages redirect to login when the browser token is missing or invalid.
- Updated auth storage for blueprint v2.1 compliance:
  - removed browser `sessionStorage` token persistence
  - frontend auth requests use credentialed HttpOnly cookies
- Added Binance public REST ingestion foundation:
  - `/api/market-data/symbols/sync` syncs Binance Spot symbol metadata and filters
  - `/api/market-data/symbols` reads persisted symbols
  - `/api/market-data/candles/ingest` ingests Binance kline/candlestick batches
  - `/api/market-data/candles` reads persisted candles
- Incorporated blueprint v2.1 small-capital requirements:
  - `config/capital_profiles.yaml`
  - `config/growth_plan.yaml`
  - `CapitalProfileManager`
  - `/api/risk/capital-profile` returns `MICRO` for simulated `$100` equity
- Added Telegram notification service skeleton:
  - reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from encrypted Settings Vault or environment fallback
  - protected `/api/notifications/telegram/test` endpoint sends a test message
  - notifier unit test uses an HTTP mock transport
- Added v2.1 Symbol Universe Manager foundation:
  - `config/edge/universe.yaml`
  - `config/edge/blacklist.yaml`
  - `/api/edge/universe/refresh` filters Binance 24h tickers into the mid-cap universe
  - unit tests cover blacklist, volume filter, stablecoin base exclusion, and ranking
- Added Binance WebSocket streaming foundation:
  - configurable Binance combined-stream base URL
  - owner-protected `/api/market-data/stream/start`, `/stop`, and `/status` endpoints
  - streaming service persists live kline updates into `candles`
  - mini-ticker and book-ticker events persist into `market_snapshots`
  - shutdown hook stops the stream task cleanly
- Extended market-data streaming with microstructure and futures snapshots:
  - combined stream now includes `@depth@100ms` orderbook delta events
  - funding-rate snapshots poll from Binance Futures premium index
  - open-interest snapshots poll from Binance Futures open-interest endpoint
  - stream status now reports polling cycles in addition to websocket message counts
- Added in-memory orderbook reconstruction and liquidity metrics:
  - bootstraps Binance REST depth snapshots before applying live deltas
  - maintains per-symbol bid/ask ladders from websocket depth updates
  - computes spread, spread bps, 0.5% depth notionals, and imbalance ratio
  - owner-protected `/api/market-data/orderbook/{symbol}` exposes current ladder and metrics
- Hardened market-data backend around orderbook continuity:
  - depth sequence gaps now trigger a per-symbol REST rebootstrap instead of leaving stale state
  - added `/api/market-data/liquidity/{symbol}/latest` for the newest persisted liquidity metrics
  - added `/api/market-data/liquidity/{symbol}/history` for recent persisted liquidity metric points
- Added dedicated historical orderbook snapshot persistence:
  - new `orderbook_snapshots` table with ladder slices plus derived metrics
  - stream service persists top-of-book ladder snapshots on a configurable interval
  - added `/api/market-data/orderbook/{symbol}/snapshots` for historical ladder reads
- Started consuming orderbook metrics in the strategy layer:
  - implemented `orderbook_imbalance` strategy evaluation against persisted orderbook snapshots
  - added owner-protected `/api/strategies/orderbook-imbalance/evaluate`
  - diagnostics include persistence ratio, average imbalance, spread, and depth checks
- Added backend risk gating for strategy signals:
  - implemented signal evaluation against capital profile and hard risk limits
  - added `/api/risk/evaluate-signal`
  - gate checks position size, leverage, daily loss, forbidden strategies, futures eligibility, liquidity floor, and target R
- Added execution-intent queue and audit persistence:
  - new `execution_intents` table for queued/approved/rejected/cancelled/executed intents
  - added `/api/execution/intents/submit`, list, and status-update endpoints
  - signal submission reuses risk gating before queue insertion
  - audit log now records intent creation and status transitions
- Added execution lifecycle worker stub:
  - intents now carry `dispatched_at`, `executed_at`, and `execution_payload`
  - added `/api/execution/worker/dispatch-next` to process the oldest approved intent
  - paper execution adapter simulates fills and advances intent state through `dispatching` to `executed`
- Added reconciliation and timeout handling for execution lifecycle:
  - added `/api/execution/intents/{intent_id}/reconcile` for explicit execution reports
  - added `/api/execution/worker/fail-stale` to fail timed-out `dispatching` intents
  - configurable dispatch timeout now protects the queue from stuck lifecycle state
- Added stable execution adapter contract and order identifiers:
  - intents now persist `client_order_id`, `venue_order_id`, and `execution_venue`
  - worker dispatch path records accepted venue metadata before final execution result
  - paper adapter now follows the same dispatch/execute contract intended for future venue adapters
- Added order-id-based lookup and reconciliation:
  - added `/api/execution/intents/by-order-id`
  - added `/api/execution/reconcile/by-order-id`
  - backend can now close execution intents from venue-facing identifiers instead of only internal intent ids
- Added stubbed Binance venue adapter contract:
  - explicit Binance order request builder with HMAC signing path
  - transport abstraction separates request construction from venue I/O
  - worker now awaits adapter dispatch/execute, making future live adapters a drop-in replacement
- Added authenticated Binance runtime resolution and request preview:
  - runtime loader now reads Binance execution credentials and testnet/base-url flags from settings vault
  - added `/api/execution/venues/binance/intents/{intent_id}/preview-order`
  - preview path validates request construction and signing inputs without placing live orders
- Added runtime-selected execution transport gating:
  - worker now chooses paper, stubbed Binance, or authenticated Binance transport per request
  - authenticated Binance transport is only selected when live mode and vault/runtime flag explicitly enable it
  - venue HTTP failures are persisted as failed execution lifecycle events with raw response payload
- Added feed-driven execution reconciliation and raw venue event persistence:
  - new `execution_venue_events` table stores raw asynchronous venue order/fill updates
  - added `/api/execution/venues/events/ingest` for owner-controlled venue event ingestion
  - async venue statuses now map into lifecycle transitions for `FILLED`, `CANCELED`, `REJECTED`, and related terminal states
  - non-terminal updates such as `PARTIALLY_FILLED` persist on the intent as live execution progress without prematurely closing the lifecycle
- Added Binance venue-native async execution consumer:
  - new Binance user-stream service subscribes to authenticated spot `executionReport` events over WebSocket API
  - added `/api/execution/venues/binance/user-stream/start`, `/stop`, and `/status`
  - listener now persists raw venue events and updates matching intents directly without manual reconciliation calls
  - app shutdown now stops both market-data and execution venue streams cleanly
- Added spot account-state reconciliation from venue events:
  - new `spot_account_balances` table stores current free, locked, total, and estimated USD value per asset
  - Binance user stream now consumes `outboundAccountPosition` and `balanceUpdate`
  - added `/api/execution/account/balances`
  - dashboard summary now includes top synchronized balances for operator visibility
- Added spot symbol-exposure reconciliation from trade fills:
  - new `spot_symbol_positions` table stores net quantity, average entry price, quote exposure, and realized notional per symbol
  - Binance user stream now consumes `executionReport` trade deltas into a symbol-level exposure read model
  - added `/api/execution/account/positions`
  - dashboard summary now includes top synchronized symbol exposures alongside balances
- Wired risk evaluation to persisted venue exposure state:
  - `/api/risk/evaluate-signal` now derives open-position count and total exposure from `spot_symbol_positions` when manual inputs are omitted
  - execution intent submission reuses the same derived exposure path
  - hard total exposure cap is now enforced in the risk gate in addition to per-trade position sizing
- Hardened spot position reconciliation for repeated partial fills:
  - new `spot_order_fill_states` table stores cumulative per-order fill progress keyed by client/venue order identifiers
  - Binance user stream now applies symbol exposure updates from cumulative `executionReport` quantities (`z`/`Z`) instead of trusting each event as a fresh fill delta
  - duplicate or replayed partial-fill events no longer double-count net quantity or quote exposure
- Added persisted mark-to-market PnL state for spot positions:
  - `spot_symbol_positions` now stores `last_mark_price`, `market_value_usd`, `realized_pnl_usd`, and `unrealized_pnl_usd`
  - position marks refresh from the latest `market_snapshots` price on fill updates and account-position reads
  - dashboard summary now exposes realized and unrealized position PnL from synced backend state
- Added execution-intent cancel/replace lineage for non-dispatched orders:
  - `execution_intents` now tracks `cancelled_at`, `parent_intent_id`, and `replaced_by_intent_id`
  - added `POST /api/execution/intents/{intent_id}/replace` for `queued` and `approved` intents
  - replacement flow cancels the original intent, re-runs risk evaluation for the replacement request, and links both intents for auditability
- Added venue-aware cancel flow for dispatched intents:
  - lifecycle now includes `cancel_requested` before terminal cancel resolution
  - added `POST /api/execution/intents/{intent_id}/cancel`
  - paper and Binance adapter paths now support explicit cancel requests, with venue response persisted into intent execution payload
- Added execution fill ledger for journal-grade close accounting:
  - new `spot_execution_fills` table stores each fill delta with quantity, quote quantity, price, realized pnl, and post-fill position state
  - account-state reconciliation now persists fill rows alongside aggregate position updates
  - added `GET /api/execution/account/fills`
- Added execution-quality and journal summary reads on top of the fill ledger:
  - new `GET /api/execution/account/fills/summary`
  - backend now computes fill win-rate, gross realized pnl, gross notional, and recent order-chain summaries grouped by order identifiers
- Added intent and strategy attribution to the fill ledger:
  - `spot_execution_fills` now stores `execution_intent_id` and `source_strategy`
  - Binance user-stream reconciliation passes matched intent attribution into persisted fill rows
  - execution summary reads can now be segmented by strategy lineage instead of raw order ids only
- Added frontend operator surfaces for journal and execution-quality:
  - Journal now reads live fill ledger rows and summary chains
  - Execution Quality now reads live fill and lineage summaries
  - strategy-level breakdown and lineage outcome views are visible in UI
- Added dashboard operator/export surfaces:
  - dashboard now shows strategy cohorts, lineage alerts, and execution/operator panels from backend state
  - CSV exports are available for strategy breakdown, lineage alerts, fills, chains, and lineage outcomes
- Added scheduled digest reporting and operator analytics:
  - new `/api/reports/daily-digest/run`, `/artifacts`, `/runs`, `/series`, and digest artifact download/export paths
  - daily digest generates JSON plus CSV artifacts, performs retention cleanup, and can notify Telegram
  - digest metadata now persists in `daily_digest_runs`
  - digest anomaly scoring tracks zero-fill days, negative top-strategy pnl, and high lineage-alert pressure
  - dashboard now shows digest anomaly banner, digest run log, trend sparklines, range presets, series CSV export, and comparison overlays

### Validation

- `make test` passed.
- `make lint` passed.
- `make typecheck` passed.
- `npm run lint` passed.
- `npm run typecheck` passed.
- `npm run build` passed.

### Current Delivered Sequence

1. foundation, auth, settings vault
2. market-data REST + websocket ingestion
3. orderbook reconstruction + liquidity metrics
4. strategy evaluation + risk gate
5. execution queue + worker lifecycle + reconciliation
6. venue user-stream sync for balances, positions, and fills
7. journal/execution-quality read models and frontend pages
8. digest reporting, anomaly scoring, run-log persistence, and dashboard analytics

### Next Development Sequence

1. digest comparison statistics and richer operator filtering
2. production-grade venue execution hardening
3. stronger lot-level pnl accounting and execution cost audit
4. multi-strategy registry expansion
5. backtest, walk-forward, Monte Carlo, and sensitivity research layers
6. recovery, dead-man switch, and alerting hardening
7. AI Analyst backend integration and approval workflow

## 2026-04-30

### Completed

- Cloned `anunnaki13/artemis` into `/home/damnation/trade`.
- Implemented Phase 0 foundation scaffold from the v2 blueprint.
- Added FastAPI backend foundation:
  - health endpoint
  - auth register/login endpoints
  - Argon2 password hashing
  - TOTP helper verification
  - SQLAlchemy async setup
  - Alembic foundation migration
- Added Next.js frontend shell:
  - Dashboard
  - Terminal
  - Strategies
  - Backtest
  - Risk
  - AI Analyst
  - Journal
  - Execution Quality
  - Logs
  - Settings
  - Login
- Exposed frontend on VPS port `3066`.
- Added Docker Compose stack:
  - frontend
  - backend
  - TimescaleDB/PostgreSQL
  - Redis
  - Prometheus
- Added project docs:
  - `README.md`
  - `docs/ARCHITECTURE.md`
  - `docs/RISK_POLICY.md`
  - `docs/RUNBOOK.md`
  - `docs/DEPLOYMENT.md`
  - `docs/IMPLEMENTATION_STATUS.md`
  - `docs/CREDENTIALS_MATRIX.md`
- Upgraded frontend look into a dense trading-terminal UI.
- Added Settings UI for required blueprint credentials.
- Added encrypted Settings Vault backend:
  - `app_settings` table migration
  - server-side Fernet encryption derived from `JWT_SECRET`
  - masked settings read API
  - settings update API with allowed-key whitelist
  - frontend save form wired to `/api/settings`
- Improved Login UI for owner email/password/TOTP.

### Validation

- `make test` passed.
- `make lint` passed.
- `make typecheck` passed.
- `npm run build` passed.
- Docker Compose build and runtime were verified.
- Backend health verified at `http://127.0.0.1:8000/health`.
- Frontend verified at `http://103.150.197.225:3066`.

### Current Blueprint Coverage

Phase 0 is partially complete and operational as a development foundation.

Remaining before Phase 1:

- Add refresh-token rotation for long-lived owner sessions.

### Not Started Yet

- Historical note: this 2026-04-30 snapshot predates the Bybit cutover and should not be read as current runtime status.
- Candle aggregation and orderbook sync.
- Strategy registry and baseline strategies.
- Backtest pipeline.
- Full five-layer risk engine.
- Execution engine and order reconciliation.
- AI Analyst backend integration.
- Notification/recovery/dead-man services.
