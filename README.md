# AIQ-BOT

AIQ-BOT is an operator-centric quantitative trading system for Bybit-oriented spot execution, microstructure monitoring, risk-gated order flow, recovery monitoring, AI-assisted review, and post-trade analytics.

It is not a single "strategy script". It is a layered trading stack with:

- market-data ingestion
- orderbook reconstruction
- signal evaluation
- risk veto and capital-profile controls
- execution intent lifecycle management
- venue-state synchronization
- journal and execution-quality accounting
- digest reporting and anomaly tracking

The current repository state is beyond a scaffold. It already contains a functioning backend/frontend foundation for a trading platform with live market-state ingestion, execution lifecycle controls, operator reporting, synchronized account-state read models, recovery monitoring, and first-pass research tooling.

## Current Runtime State

Date baseline: `2026-05-02`

- Active venue runtime: `Bybit`
- Public frontend: `http://103.150.197.225:3066`
- Backend health: `http://127.0.0.1:8000/health`
- Current overall completion estimate: `~94%`
- Current mode: operator-ready and paper-workflow-ready, but not yet fully hardened for confident real-money operation

Current handoff references:

- [docs/HANDOFF_2026-05-02.md](/home/damnation/trade/docs/HANDOFF_2026-05-02.md:1)
- [docs/IMPLEMENTATION_STATUS.md](/home/damnation/trade/docs/IMPLEMENTATION_STATUS.md:1)
- [docs/PROGRESS.md](/home/damnation/trade/docs/PROGRESS.md:1)
- [docs/DEVELOPMENT_ROADMAP.md](/home/damnation/trade/docs/DEVELOPMENT_ROADMAP.md:1)

## What This Bot Is

AIQ-BOT is a **decision-and-control system for systematic trading**, not merely an automated order sender.

At a high level, the system models trading as a sequence of constrained state transitions:

1. observe the market
2. reconstruct relevant state
3. generate a candidate signal
4. evaluate the signal against hard risk constraints
5. convert approved signals into execution intents
6. track execution against venue events
7. reconcile fills into balances, positions, and PnL
8. measure outcome quality through journal and operator analytics

This is close to how modern algorithmic trading systems are designed in practice: **separate alpha generation from risk control, execution, accounting, and monitoring**. That separation matters because failure modes in trading systems usually do not come from one bad prediction alone; they come from weak lifecycle control, poor reconciliation, hidden state drift, or missing operator visibility.

## What Problem It Solves

Most retail trading bots collapse five different concerns into one code path:

- market data
- signal logic
- order placement
- position tracking
- PnL reporting

That architecture is fragile. It becomes difficult to answer basic operational questions:

- What state did the model observe when it made the decision?
- Was the signal blocked by risk, or was it allowed and then poorly executed?
- Did the venue partially fill the order, reject it, or cancel it asynchronously?
- Is the current position derived from local assumptions or synchronized venue truth?
- Is daily PnL moving because of mark-to-market, realized closes, slippage, or replacement churn?

AIQ-BOT addresses that by turning the bot into a **stateful research-and-operations platform** rather than a thin order loop.

## How It Works

### 1. Market-state ingestion

The system ingests Bybit data through both REST and WebSocket paths.

- REST:
  - symbol metadata
  - historical candles
  - orderbook bootstrap snapshots
- WebSocket:
  - kline
  - ticker
  - orderbook delta
- futures context polling:
  - funding rate
  - open interest

This data is persisted and normalized into internal tables such as:

- `symbols`
- `candles`
- `market_snapshots`
- `orderbook_snapshots`

### 2. Orderbook reconstruction and microstructure features

Instead of relying only on last-trade prices, the bot reconstructs in-memory orderbook state and derives microstructure metrics such as:

- spread
- spread in basis points
- best bid / best ask
- bid depth notional within 0.5%
- ask depth notional within 0.5%
- imbalance ratio

This matters because execution quality and short-horizon signal quality are strongly conditioned on liquidity geometry, not just candle direction. In microstructure terms, the bot is not treating the market as a scalar price process only; it treats it as a **state-dependent liquidity field**.

### 3. Signal evaluation

The first implemented strategy path uses orderbook imbalance and persistence features to evaluate directional pressure. The strategy layer is intentionally separated from the rest of the lifecycle so that future strategies can be added without rewriting execution and accounting logic.

The current strategy output is a structured signal, not an order. That distinction is deliberate.

### 4. Risk gate

Every signal passes through a risk veto layer before it can become executable.

Current risk evaluation includes checks on:

- max concurrent positions
- max position size
- leverage constraints
- daily loss budget
- strategy restrictions by capital profile
- futures eligibility
- liquidity floor
- minimum target R
- total active exposure

This follows a core systems principle: **risk is not a post-hoc metric; it is a transition constraint on state evolution**.

### 5. Execution intents

Approved signals become `execution_intents`. This is the key abstraction between decision and venue interaction.

An execution intent carries:

- symbol
- side
- requested notional
- approved notional
- source strategy
- signal payload
- risk payload
- lifecycle status
- venue identifiers when available

This abstraction provides auditability and lets the system reason about:

- queued vs approved vs dispatching vs executed
- replaced intents
- cancelled intents
- failed intents
- venue reconciliation by order identifiers

### 6. Execution lifecycle and reconciliation

The worker layer moves intents through an execution lifecycle. The system already supports:

- dispatch
- explicit reconcile
- timeout failure handling
- cancel requests
- replace lineage for pre-dispatch orders

There is also a venue-facing contract for Bybit execution transport, with runtime gating so that authenticated live placement is only used when explicitly enabled. Live and private-stream access are blocked unless the runtime passes three safety checks:

- `BYBIT_ACCOUNT_TYPE=UNIFIED`
- `BYBIT_WHITELISTED_IP` is configured
- `BYBIT_WITHDRAWAL_ENABLED=false`

### 7. Venue-state synchronization

The Bybit private user stream is consumed to synchronize account truth into backend state.

Persisted read models include:

- `spot_account_balances`
- `spot_symbol_positions`
- `spot_order_fill_states`
- `spot_execution_fills`
- `execution_venue_events`

This is important because venue truth is asynchronous. Real systems do not safely operate by assuming "submit order" implies "final state known". Instead, they consume order and account events, then reconcile local state from those events.

### 8. Accounting, journal, and execution quality

The system persists fill-level ledger rows and builds higher-order analytics on top:

- raw fills
- fill chains
- intent outcomes
- replacement lineage outcomes
- strategy-attributed performance summaries
- dashboard-level operator cohorts

This allows the system to separate:

- realized PnL
- unrealized PnL
- mark-to-market exposure
- slippage and underfill pressure
- strategy-level outcome quality

### 9. Reporting and anomaly tracking

The bot also produces daily digest artifacts and persists digest run summaries.

Digest reporting includes:

- `summary.json`
- `strategy_breakdown.csv`
- `lineage_alerts.csv`

The system additionally scores daily anomalies using criteria such as:

- zero fills
- negative top-strategy PnL
- high lineage-alert pressure

These digests are not just file exports; they feed the dashboard and operator review surfaces through persisted run logs and trend series.

### 10. Recovery and AI review

The system now includes an explicit recovery/ops layer and a reviewed AI analyst path.

Recovery layer:

- persisted `recovery_events`
- periodic background checks
- heartbeat / dead-man / Telegram hooks
- operator status surfaces in dashboard and terminal

AI layer:

- OpenRouter-backed analyst brief generation
- persisted `ai_analyst_runs`
- daily cost budget guard
- review queue with `pending / approved / rejected / follow_up`

This matters because the platform is no longer just emitting signals and reports. It is beginning to model operational failure, alerting, and human review as first-class system states.

## Why Bybit, Not Binance

The venue choice is operational. Binance has become harder to use reliably from Indonesia, so this repository is being migrated to a Bybit-primary architecture.

That is not a cosmetic rename. It changes:

- authenticated transport assumptions
- private stream semantics
- order identifier conventions
- account model assumptions such as `UNIFIED`
- operator safety checks around whitelist and withdrawal posture

The migration plan driving that work is documented in [BINANCE-TO-BYBIT-MIGRATION.md](/home/damnation/trade/BINANCE-TO-BYBIT-MIGRATION.md:1).

## What Is Already Functional

The following surfaces are already backend-driven and operator-usable:

- `Dashboard`
- `Terminal`
- `Strategies`
- `Risk`
- `Backtest`
- `AI Analyst`
- `Journal`
- `Execution Quality`
- `Logs`
- `Settings`

Important implemented backend capabilities:

- Bybit market-data sync and stream maintenance
- candle auto-refresh and orderbook fallback reads
- strategy evaluation and risk preview
- execution intent queue and lifecycle worker
- Bybit venue diagnostics and incident normalization
- synced balances, positions, fills, and FIFO lot-close audit
- digest generation, anomaly scoring, and trend series
- AI analyst run logging and review queue
- recovery monitor and critical-state persistence

Important remaining gaps:

- final live-execution confidence hardening
- deeper research stack beyond current walk-forward/read-model level
- full design-system rollout page-by-page
- final ops/recovery polish and replay tooling

## What Makes It Different

### 1. It is state-first, not signal-first

Many bots start from strategy code and bolt everything else around it. AIQ-BOT starts from state management:

- observed market state
- approved risk state
- execution lifecycle state
- venue truth state
- accounting state
- operator reporting state

That makes it more suitable for controlled scaling, post-mortem analysis, and future strategy expansion.

### 2. It treats execution as a measured process

The bot does not treat order placement as the end of the problem. It models:

- intent creation
- dispatch
- venue acknowledgement
- partial fills
- cancellation
- replacement lineage
- realized and unrealized PnL evolution

In scientific terms, it is closer to an **inference-control-observation loop** than a one-shot decision script.

### 3. It uses microstructure information, not just candles

The current architecture explicitly supports orderbook-based features and liquidity metrics. That is a meaningful differentiator from indicator-only bots, because the execution environment itself becomes part of the modeled state.

### 4. It has a proper operator layer

The dashboard, journal, execution-quality pages, digest reports, and CSV/export surfaces are first-class parts of the system. This matters operationally because the difference between a research toy and a trading system is usually not the signal formula; it is the **observability and control surface**.

## Scientific Framing

The design can be understood through three formal lenses:

### State estimation

The bot builds an internal approximation of latent market and account state from asynchronous observations:

- price events
- orderbook deltas
- venue execution reports
- account balance updates

This is a practical state-estimation problem under partial observability.

### Constrained control

Signals do not directly become actions. They are filtered through a hard constraint system. That makes the execution path a constrained-control problem:

- candidate action
- feasibility check
- bounded action
- venue interaction
- observed outcome

### Outcome attribution

The system persists enough lineage to evaluate whether performance degradation came from:

- weak signal quality
- risk throttling
- poor fill quality
- replacement churn
- missing liquidity

That is essential for any scientifically credible iterative improvement loop.

## Current Implemented Scope

The implemented system currently includes:

- auth and settings vault
- Bybit-only market-data ingestion
- orderbook reconstruction and liquidity metrics
- historical market snapshot persistence
- first strategy path
- risk gate
- execution intent lifecycle
- Bybit runtime safety gating for live/private access
- venue user-stream synchronization
- synced balances and positions
- fill ledger and execution-quality summaries
- venue diagnostics for reject/cancel/partial event review
- execution-cost accounting for adverse slippage and underfill pressure
- dashboard/operator analytics
- daily digest generation, persistence, and anomaly tracking

The most current implementation and roadmap details are tracked in:

- [docs/PROGRESS.md](docs/PROGRESS.md)
- [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md)
- [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## What Is Still Missing

The system is not yet a complete production trading stack.

Major remaining areas include:

- complete live execution hardening
- lot-level accounting refinement
- broader multi-strategy registry
- backtest and walk-forward research engine
- Monte Carlo and sensitivity analysis
- recovery service and dead-man switch
- AI Analyst backend integration

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

Run backend tests locally:

```bash
cd backend
pip install -e ".[dev]"
pytest
```

Run frontend validation locally:

```bash
cd frontend
npm install
npm run lint
npm run typecheck
npm run build
```

## Safety Model

The repository follows several non-negotiable rules:

- risk gate has veto authority over order flow
- AI is advisory, not autonomous for live parameter deployment
- live credentials must not include withdrawal permission
- strategy promotion should move through:
  - backtest
  - paper
  - live micro
  - live scaled

## Short Summary

AIQ-BOT is best understood as a **quant trading operating system in progress**: it combines market-state estimation, risk-gated execution control, venue reconciliation, and post-trade analytics into one coherent platform. Its differentiator is not a single alpha formula. Its differentiator is the discipline of the full trading lifecycle.
