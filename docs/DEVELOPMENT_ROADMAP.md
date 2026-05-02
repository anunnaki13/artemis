# Development Roadmap

This document separates three views of the system:

1. what has already been delivered
2. what is currently operational
3. what should be developed next, in order

Date baseline: `2026-05-02`

Current overall completion estimate: `~94%`

## 1. Delivered So Far

### Foundation and platform

- FastAPI backend, Next.js frontend, PostgreSQL/Timescale, Redis, Prometheus, Docker Compose.
- Owner authentication with TOTP, Redis-backed session validation, login/register rate limits, logout, and HttpOnly cookie flow.
- Encrypted Settings Vault with masked reads and protected writes.
- Dense operator UI shell for:
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

### Market data and microstructure

- Bybit Spot symbol sync and candle ingestion.
- Bybit public WebSocket streaming for:
  - kline
  - ticker
  - depth deltas
- Bybit linear polling for:
  - funding rate
  - open interest
- In-memory orderbook reconstruction with gap recovery and REST rebootstrap.
- Derived liquidity metrics:
  - spread
  - spread bps
  - best bid / ask
  - 0.5% bid depth notional
  - 0.5% ask depth notional
  - imbalance ratio
- Persistence for:
  - candles
  - market snapshots
  - historical orderbook snapshots

### Strategy and risk foundation

- Capital profile and growth-plan configs.
- Symbol universe filtering and blacklist support.
- Initial `orderbook_imbalance` strategy evaluation.
- Risk gate for signals with checks on:
  - position sizing
  - leverage
  - daily loss
  - forbidden strategy list
  - liquidity floor
  - target R
  - total exposure
- Risk now derives open positions and exposure from synced venue state instead of only manual inputs.

### Execution core

- Execution intent queue with status transitions and audit persistence.
- Worker lifecycle with:
  - queue
  - approve
  - dispatch
  - execute
  - fail stale
  - reconcile
- Stable execution adapter contract.
- Paper adapter and Bybit adapter scaffolding.
- Runtime-gated authenticated Bybit execution transport.
- Cancel flow for `dispatching` intents.
- Replace flow for `queued` / `approved` intents.
- Order-id-based reconciliation.
- Raw venue event persistence.

### Venue account state

- Bybit private-stream consumer for authenticated execution/account events.
- Synced spot balances.
- Synced spot symbol positions.
- Partial-fill dedupe using cumulative order-fill state.
- Mark-to-market state with:
  - realized pnl
  - unrealized pnl
  - last mark price
  - market value

### Journal and execution quality

- Fill ledger with intent attribution and strategy attribution.
- Fill summary and chain summary reads.
- Lineage outcome reads for replacement chains.
- Per-strategy outcome summaries.
- Execution-cost analytics:
  - adverse slippage bps
  - adverse slippage cost
  - underfill notional
- Frontend Journal and Execution Quality pages now consume live backend data instead of placeholders.

### Reporting and operator tooling

- CSV exports for:
  - fills
  - fill chains
  - lineage outcomes
  - dashboard strategy breakdown
  - dashboard lineage alerts
- Daily digest generation:
  - `summary.json`
  - `strategy_breakdown.csv`
  - `lineage_alerts.csv`
- Scheduled daily digest runner.
- Artifact retention cleanup.
- Telegram completion notification for digest generation.
- Digest anomaly scoring.
- Persisted `daily_digest_runs` table.
- Digest trend series API and dashboard visualization.
- Range presets and CSV export for digest series.
- Comparison mode in dashboard trend panel:
  - anomaly vs fills
  - anomaly vs lineage alerts
  - anomaly vs top-strategy pnl
- Venue diagnostics for Bybit execution events with dashboard summary and CSV export.

### Recovery, AI review, and research batch

- AI Analyst OpenRouter integration with persisted run log.
- AI Analyst review queue and operator review actions.
- Recovery event persistence and background recovery monitor.
- Persisted backtest runs and grouped overview analytics.
- Walk-forward backtest windows and aggregate diagnostics.
- First-pass Quantum design rollout across the global shell and selected operator pages.

## 2. Current Operational Surface

The system is not just scaffolded anymore. It currently behaves like an early operator-grade trading platform foundation.

### Backend currently operational

- live market-data streaming and persistence
- orderbook reconstruction and liquidity metrics
- basic strategy evaluation
- risk-gated execution intent submission
- queue / dispatch / reconcile execution lifecycle
- venue account sync for balances and spot positions
- journal-grade fill recording
- digest generation, digest history, anomaly tracking

### Frontend currently operational

- Dashboard is live and backend-driven
- Journal is backend-driven
- Execution Quality is backend-driven
- Digest trend and digest anomaly panels are live
- Settings/Auth flows are wired end to end

### VPS/runtime

- public frontend: `http://103.150.197.225:3066`
- backend health: `http://127.0.0.1:8000/health`
- latest runtime state has been repeatedly validated during implementation

## 3. Development Steps Completed

This is the implementation sequence that has already been delivered.

1. Phase 0 repo/platform foundation
2. auth hardening and settings vault
3. market-data REST ingestion
4. market-data WebSocket ingestion
5. orderbook reconstruction and liquidity metrics
6. historical orderbook persistence
7. first strategy evaluation path
8. risk gate
9. execution intent queue
10. worker lifecycle and reconciliation
11. adapter contract and order identifiers
12. runtime Bybit transport gating
13. venue user-stream consumer
14. synced balances and positions
15. partial-fill dedupe and mark-to-market pnl
16. cancel/replace lineage
17. fill ledger and chain summaries
18. strategy attribution in journal/execution quality
19. dashboard/operator exports
20. daily digest generation and retention
21. digest anomaly scoring
22. persisted digest run logs
23. digest trend series and comparison mode
24. Bybit runtime cutover and safety gating
25. venue diagnostics and execution-cost analytics

## 4. Next Development Queue

The next steps below are ordered by leverage, not by novelty.

### Near-term priority

1. Finish the Quantum design rollout
   - `dashboard`
   - `backtest`
   - `risk`
   - `journal`
   - `execution-quality`

2. Final live-execution hardening
   - retry/idempotency discipline
   - safer repair/replay workflows
   - deeper venue reconciliation

3. Research-stack maturity
   - saved presets
   - richer exports
   - broader walk-forward compare surfaces
   - later Monte Carlo and sensitivity

### Execution and trading-core hardening

4. Strategy registry expansion
   - multiple baseline strategies
   - parameterized strategy config registry
   - strategy enable/disable controls

### Research and validation

5. Broader research engine depth
6. walk-forward, Monte Carlo, and sensitivity validation
7. Deflated Sharpe and experiment ranking
8. live-vs-research divergence reporting

### Ops and resilience

9. dead-man switch
10. heartbeat and repeated critical alerts
11. recovery workflows and replay tooling
12. backup and restore verification

### Product and AI layer

13. AI Analyst recommendation workflow depth
14. operator action queue for reviewed AI outputs
15. recommendation audit and outcome attribution

## 5. Recommended Build Order From Here

If development continues without changing direction, the most efficient sequence is:

1. finish page-by-page Quantum restyle
2. finish final live-execution hardening
3. deepen research stack
4. expand strategy set
5. keep tightening recovery/ops workflows
6. deepen AI recommendation workflow

That keeps the platform usable while reducing the highest-risk gaps first.
