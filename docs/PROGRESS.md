# Progress Log

## 2026-05-01

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

### Validation

- `make test` passed.
- `make lint` passed.
- `make typecheck` passed.
- `npm run lint` passed.
- `npm run typecheck` passed.
- `npm run build` passed.

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

- Binance public market-data WebSocket service.
- Candle aggregation and orderbook sync.
- Strategy registry and baseline strategies.
- Backtest pipeline.
- Full five-layer risk engine.
- Execution engine and order reconciliation.
- AI Analyst backend integration.
- Notification/recovery/dead-man services.
