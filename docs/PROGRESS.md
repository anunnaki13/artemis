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

### Validation

- `make test` passed.
- `make lint` passed.
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
