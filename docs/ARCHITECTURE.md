# Architecture

The system follows the v2 blueprint structure:

- `frontend`: Next.js dashboard and control plane.
- `backend/app`: FastAPI API gateway, auth, schemas, models, and middleware.
- `backend/services`: domain services for market data, strategy, risk, execution, AI, notifications, and recovery.
- `backend/strategies`: versioned strategy implementations.
- `backend/backtest`: validation and research pipeline.
- `backend/execution_quality`: slippage, fill, and cost accounting.
- `ops`: Docker, deployment, monitoring, and scripts.

Order execution must eventually flow through strategy signal, risk veto, position sizing, execution pre-flight, exchange submission, and fill reconciliation. No frontend code may call venue APIs directly.
