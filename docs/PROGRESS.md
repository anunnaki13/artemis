# Progress Log

## 2026-05-01

### Completed

- Wired frontend owner authentication to backend endpoints:
  - owner registration posts to `/api/auth/register`
  - login posts to `/api/auth/login`
  - registration displays TOTP secret and provisioning URI for authenticator enrollment
  - successful login stores the short-lived access token in browser session storage
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

### Validation

- `make test` passed.
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
