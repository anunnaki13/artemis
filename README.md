# AIQ-BOT

AI-Quant-Binance-Bot v2 foundation, built from `AI-Quant-Binance-Bot-Blueprint-v2.md`.

This repository is intentionally survival-first:

- Risk engine has veto authority over all future order flow.
- Every PnL surface must distinguish net and gross values.
- Binance trading credentials must never include withdrawal permission.
- Strategy promotion follows backtest, paper, live micro, then live scaled.
- AI features are advisory only and cannot deploy live parameters.

## Current Phase

Phase 0 foundation is scaffolded:

- FastAPI backend with health, auth registration/login, dashboard summary, and risk policy endpoints.
- PostgreSQL/TimescaleDB, Redis, Prometheus, backend, and frontend Docker Compose.
- Alembic foundation migration for users and audit log.
- Next.js frontend shell with all blueprint v2 routes.
- CI workflow for backend lint/tests and frontend typecheck/build.

Trading logic, market data, live execution, and AI workflows are intentionally not implemented yet.

## Local Setup

```bash
cp .env.example .env
docker compose up --build
```

Services:

- Frontend: `http://localhost:3066`
- Backend: `http://localhost:8000`
- Backend health: `http://localhost:8000/health`
- Prometheus: `http://localhost:9090`

Run migrations:

```bash
docker compose run --rm backend alembic upgrade head
```

Run tests locally:

```bash
cd backend
pip install -e ".[dev]"
pytest
```

## Version Note

This is v2 implementation groundwork. Keep future v2.1 blueprint changes as additive migrations or isolated module updates unless the v2.1 spec explicitly supersedes an architectural rule.
