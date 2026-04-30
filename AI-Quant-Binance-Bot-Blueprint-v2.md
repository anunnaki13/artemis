# AI-Quant-Binance-Bot — Production Blueprint v2.0

> **Institutional-grade crypto automation for independent traders.**
>
> A production-ready, AI-augmented Binance trading platform engineered around survival-first principles: real cost accounting, anti-overfitting discipline, layered risk controls, and operational resilience.

**Codename:** `AIQ-BOT`
**Version:** 2.0 (Production Blueprint)
**Status:** Specification — Reference for Codex / Claude Code implementation
**License:** Private / Proprietary

---

## Table of Contents

1. [Core Philosophy & Non-Negotiables](#1-core-philosophy--non-negotiables)
2. [System Architecture](#2-system-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Repository Structure](#4-repository-structure)
5. [Backend Services (Detailed)](#5-backend-services-detailed)
6. [Risk Engine — Layered Defense](#6-risk-engine--layered-defense)
7. [Strategy Framework & Alpha Sources](#7-strategy-framework--alpha-sources)
8. [Backtest & Validation Pipeline](#8-backtest--validation-pipeline)
9. [Execution Quality & Cost Accounting](#9-execution-quality--cost-accounting)
10. [AI Analyst — Guardrailed Intelligence](#10-ai-analyst--guardrailed-intelligence)
11. [Frontend — Premium Dashboard](#11-frontend--premium-dashboard)
12. [Database Schema](#12-database-schema)
13. [Security & Secrets Management](#13-security--secrets-management)
14. [Observability & Disaster Recovery](#14-observability--disaster-recovery)
15. [Deployment & Infrastructure](#15-deployment--infrastructure)
16. [Development Roadmap & Promotion Gates](#16-development-roadmap--promotion-gates)
17. [Codex / Claude Code Build Instructions](#17-codex--claude-code-build-instructions)
18. [Appendix](#18-appendix)

---

## 1. Core Philosophy & Non-Negotiables

### 1.1 Survival-First Principles

The platform is built around the assumption that **most retail crypto bots fail in live trading despite passing backtests**. The architecture explicitly addresses every known failure mode.

**The Five Laws (in order of precedence):**

1. **Don't lose the account.** Risk engine has veto power over every order.
2. **Cost honesty.** Every PnL number displayed is *net* of fees, funding, and slippage.
3. **Validate before deploying.** No strategy reaches live without walk-forward + paper trade validation.
4. **Fail safe, not silent.** Every component has a defined failure behavior; default is "flatten and pause."
5. **Backtest first → Paper trade → Live small → Scale safely.** No exceptions, no shortcuts.

### 1.2 Hard Constraints (NEVER violate)

| Constraint | Value | Rationale |
|---|---|---|
| API key permission | Trading only, NO withdrawal | Even if compromised, attacker can't drain funds |
| IP whitelist on Binance | MANDATORY | Prevents stolen-key remote exploitation |
| Initial live capital | ≤ amount user can fully lose without distress | Tuition fee, not retirement money |
| Strategy promotion gate | Walk-forward profitable + 30 days paper trade | Filter overfit strategies |
| Max daily loss | Hard stop, no override | No revenge trading possible |
| Withdrawal automation | NEVER implemented | Eliminates an entire attack surface |

### 1.3 Mode Hierarchy

The bot operates in one of four modes, with strict transition rules:

```
BACKTEST  →  PAPER  →  LIVE_MICRO  →  LIVE_SCALED
            (30d+)    (3 months+)
```

- **BACKTEST** — Historical simulation only. No API calls.
- **PAPER** — Real-time market data, simulated fills. Mandatory minimum 30 days.
- **LIVE_MICRO** — Real money, capped at user-defined micro size (default: 5% of intended capital).
- **LIVE_SCALED** — Full capital. Requires 3 months of LIVE_MICRO with metrics matching backtest within tolerance.

**Promotion is gated** (see [Section 16](#16-development-roadmap--promotion-gates)) and enforced by the system, not by user discretion.

---

## 2. System Architecture

### 2.1 High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                       FRONTEND (Next.js)                        │
│   Dashboard │ Terminal │ Strategy Lab │ Backtest │ Risk │ AI    │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST + WebSocket
┌────────────────────────────▼────────────────────────────────────┐
│                    API GATEWAY (FastAPI)                        │
│              Auth │ Rate Limit │ Audit Logger                   │
└────┬──────────┬──────────┬──────────┬──────────┬────────────────┘
     │          │          │          │          │
┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼───┐ ┌───▼────┐
│Market  │ │Strategy│ │Risk    │ │Exec   │ │AI      │
│Data    │ │Engine  │ │Engine  │ │Engine │ │Analyst │
│Service │ │        │ │(VETO)  │ │       │ │        │
└────┬───┘ └───┬────┘ └───┬────┘ └───┬───┘ └───┬────┘
     │         │          │           │         │
     └─────────┴──────────┴───────────┴─────────┘
                          │
              ┌───────────┴────────────┐
              │                        │
        ┌─────▼─────┐          ┌──────▼──────┐
        │PostgreSQL │          │    Redis    │
        │(persist)  │          │ (state/pub) │
        └───────────┘          └─────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
      ┌───────▼────────┐    ┌────────▼────────┐
      │ Binance REST   │    │ Binance WS      │
      │ + WebSocket    │    │ (User Data)     │
      └────────────────┘    └─────────────────┘
```

### 2.2 Critical Path: Order Flow

Every order traverses the following pipeline. **Each gate has veto power.**

```
Strategy Signal
      │
      ▼
[Gate 1] Risk Engine — Pre-trade checks
      │  ✓ Within risk per trade?
      │  ✓ Daily loss budget remaining?
      │  ✓ Max concurrent positions?
      │  ✓ Correlation exposure?
      │  ✓ Circuit breakers green?
      │
      ▼
[Gate 2] Position Sizer — Volatility-adjusted
      │  ATR / realized vol → calculate qty
      │  Apply Kelly fractional cap
      │  Apply regime throttle multiplier
      │
      ▼
[Gate 3] Execution Engine — Pre-flight
      │  ✓ Symbol filters (MIN_NOTIONAL, LOT_SIZE)
      │  ✓ Account balance sufficient?
      │  ✓ Latency to Binance acceptable?
      │
      ▼
[Gate 4] Binance API — Place order
      │
      ▼
[Gate 5] Fill Tracker — Reconcile
      │  Record actual fill vs expected
      │  Log slippage cost
      │  Update execution quality metrics
      │
      ▼
Position Open + SL/TP attached
```

### 2.3 Critical Path: Heartbeat & Shutdown

```
Every 30s:  Heartbeat → DB → Telegram (if missed > 2 minutes)
Every 5s:   Position reconciliation with Binance
Every 1s:   Risk engine evaluation
On crash:   Dead-man switch → close all positions → alert
On boot:    State recovery from Binance (truth source) → resume
```

---

## 3. Tech Stack

### Backend
- **Python 3.11+** (asyncio-first)
- **FastAPI** — REST API + WebSocket
- **CCXT** + **python-binance** — Exchange connectivity (CCXT for portability, python-binance for low-latency WS)
- **SQLAlchemy 2.0** (async) — ORM
- **Alembic** — Migrations
- **Pandas** + **NumPy** — Data manipulation
- **vectorbt** — Backtesting engine (primary)
- **backtesting.py** — Cross-validation backtesting
- **Pydantic v2** — Data validation
- **APScheduler** — Cron-like jobs
- **structlog** — Structured logging
- **Prometheus client** — Metrics export

### Frontend
- **Next.js 14+** (App Router)
- **TypeScript 5+**
- **TailwindCSS 3+**
- **shadcn/ui** — Component primitives
- **Recharts** + **Lightweight Charts (TradingView)** — Charting
- **Framer Motion** — Animations
- **TanStack Query** — Data fetching
- **Zustand** — State management
- **Socket.io-client** — Real-time updates

### Database & Cache
- **PostgreSQL 15+** — Primary store (TimescaleDB extension for time-series)
- **Redis 7+** — Cache, pub/sub, rate limiting

### Infrastructure
- **Ubuntu 22.04 LTS** VPS (minimum 2 vCPU, 4GB RAM, 40GB SSD)
- **Docker** + **Docker Compose**
- **Nginx** (reverse proxy + TLS termination)
- **Cloudflare** (DDoS protection + DNS, optional)
- **Let's Encrypt** (TLS via certbot)

### AI Layer
- **OpenRouter API** — Multi-model gateway
- Recommended models:
  - **Claude Sonnet 4** — Primary analyst (reasoning, explanation)
  - **DeepSeek R1** — Heavy analysis, cost-efficient
  - **GPT-4o-mini** — Fast classification tasks

### Observability
- **Prometheus** + **Grafana** — Metrics & dashboards
- **Loki** — Log aggregation
- **UptimeRobot** or **Healthchecks.io** — External uptime monitor
- **Telegram Bot API** — Alerts

### Security
- **HashiCorp Vault** OR **age-encrypted secrets** (sealed in repo, decrypted at boot)
- **fail2ban** — SSH brute-force protection
- **ufw** — Firewall

---

## 4. Repository Structure

```
ai-quant-binance-bot/
├── frontend/
│   ├── app/
│   │   ├── (auth)/login/
│   │   ├── (app)/
│   │   │   ├── dashboard/
│   │   │   ├── terminal/
│   │   │   ├── strategies/
│   │   │   ├── backtest/
│   │   │   ├── risk/
│   │   │   ├── ai-analyst/
│   │   │   ├── journal/
│   │   │   ├── execution-quality/
│   │   │   └── logs/
│   │   └── api/
│   ├── components/
│   │   ├── ui/              # shadcn primitives
│   │   ├── charts/
│   │   ├── kpi/
│   │   ├── tables/
│   │   └── layout/
│   ├── lib/
│   │   ├── api.ts
│   │   ├── ws.ts
│   │   └── utils.ts
│   ├── stores/              # Zustand
│   └── styles/
│
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entrypoint
│   │   ├── config.py        # Pydantic settings
│   │   ├── deps.py          # Dependency injection
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── dashboard.py
│   │   │   ├── trading.py
│   │   │   ├── strategies.py
│   │   │   ├── backtest.py
│   │   │   ├── risk.py
│   │   │   ├── ai.py
│   │   │   └── ws.py        # WebSocket endpoints
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic DTOs
│   │   └── middleware/
│   │
│   ├── services/
│   │   ├── market_data/     # WS streams, candle aggregation
│   │   ├── execution/       # Order placement, reconciliation
│   │   ├── risk/            # Pre-trade checks, circuit breakers
│   │   ├── strategy/        # Signal generation
│   │   ├── ai/              # OpenRouter integration
│   │   ├── notification/    # Telegram, email
│   │   └── recovery/        # State recovery, dead-man switch
│   │
│   ├── strategies/
│   │   ├── base.py          # Abstract Strategy class
│   │   ├── indicators.py    # Reusable indicator library
│   │   ├── ema_momentum/
│   │   ├── vwap_reversion/
│   │   ├── rsi_bounce/
│   │   ├── breakout_volume/
│   │   ├── orderbook_imbalance/   # Microstructure
│   │   ├── funding_divergence/    # Cross-market
│   │   └── liquidation_cascade/   # Microstructure
│   │
│   ├── backtest/
│   │   ├── engine.py
│   │   ├── walk_forward.py
│   │   ├── monte_carlo.py
│   │   ├── sensitivity.py
│   │   └── metrics.py       # Sharpe, Deflated Sharpe, Sortino, etc.
│   │
│   ├── execution_quality/
│   │   ├── slippage_tracker.py
│   │   ├── fill_analyzer.py
│   │   └── cost_accounting.py
│   │
│   ├── alembic/             # DB migrations
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   └── pyproject.toml
│
├── ops/
│   ├── docker/
│   │   ├── Dockerfile.backend
│   │   ├── Dockerfile.frontend
│   │   └── nginx.conf
│   ├── grafana/
│   │   └── dashboards/
│   ├── prometheus/
│   │   └── prometheus.yml
│   └── scripts/
│       ├── backup_db.sh
│       ├── restore_db.sh
│       ├── deploy.sh
│       └── healthcheck.sh
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── RUNBOOK.md           # Incident response
│   ├── STRATEGY_GUIDE.md
│   ├── RISK_POLICY.md
│   └── DEPLOYMENT.md
│
├── prompts/                 # AI prompts (versioned)
│   ├── analyst_system.md
│   ├── strategy_explain.md
│   └── regime_classify.md
│
├── .env.example
├── docker-compose.yml
├── docker-compose.prod.yml
├── Makefile
└── README.md
```

---

## 5. Backend Services (Detailed)

### 5.1 `market_data_service`

**Responsibility:** Real-time and historical market data; single source of truth for prices.

**Components:**
- WebSocket manager (auto-reconnect, gap detection)
- Candle aggregator (1m → 5m → 1h rollups)
- Orderbook snapshot + delta sync
- Historical data fetcher (for backtest)
- Funding rate poller (every 1m)
- Open Interest poller (every 1m)

**Failure Modes Handled:**
- WS disconnect → exponential backoff reconnect, mark stale, alert
- Gap in candles → REST fill, validate continuity
- Binance maintenance → switch to "frozen" state, no signals fire

### 5.2 `strategy_service`

**Responsibility:** Generate signals from market data using configured strategies.

**Components:**
- Strategy registry (load enabled strategies)
- Signal generator (per-strategy, per-symbol)
- Signal aggregator (merge multi-strategy signals with weights)
- Parameter manager (versioned, with rollback)
- Regime classifier (trending / mean-reverting / choppy / extreme)

**Output:** `Signal(symbol, side, conviction, source_strategy, regime, timestamp)`

### 5.3 `risk_service`

**See [Section 6](#6-risk-engine--layered-defense) for full detail.**

**Responsibility:** Veto unsafe orders, calculate position size, enforce limits.

**Always-On Checks:**
- Daily loss budget
- Max concurrent positions
- Correlation exposure
- Circuit breaker status

### 5.4 `execution_service`

**Responsibility:** Place, modify, cancel orders on Binance with reconciliation.

**Components:**
- Order placer (with retry + idempotency keys)
- Fill tracker (matches expected vs actual)
- SL/TP manager (server-side via OCO when possible, client-side fallback)
- Position reconciliation loop (every 5s, Binance is truth)
- Symbol filter validator (MIN_NOTIONAL, LOT_SIZE, PRICE_FILTER)

**Critical Rules:**
- Every order has an idempotency key (UUID) → prevents duplicates on retry
- Every order is logged BEFORE submission and AFTER confirmation
- Reconciliation always trusts Binance state over local state

### 5.5 `ai_service`

**See [Section 10](#10-ai-analyst--guardrailed-intelligence).**

### 5.6 `notification_service`

**Responsibility:** Multi-channel alerting with severity routing.

**Channels:**
- **Telegram** (primary, low-latency)
- **Email** (digest, daily summary)
- **Webhook** (optional, for custom integrations)

**Severity Levels:**
- `INFO` — Daily summary, trade open/close (Telegram silent)
- `WARNING` — Strategy underperforming, latency anomaly (Telegram with sound)
- `CRITICAL` — Circuit breaker tripped, API down, dead-man switch fired (Telegram + Email + repeated until ack)

### 5.7 `recovery_service`

**Responsibility:** Crash recovery and state synchronization.

**Boot Sequence:**
1. Read last known state from PostgreSQL
2. Fetch ground truth from Binance (open orders, positions, balance)
3. Diff local vs Binance → resolve discrepancies (Binance wins)
4. Re-attach SL/TP if missing
5. Resume normal operation OR enter `SAFE_MODE` if discrepancies severe

**Dead-Man Switch:**
- Heartbeat to external monitor every 30s
- If monitor doesn't see heartbeat for 2 minutes → triggers webhook
- Webhook calls a separate "kill" endpoint (deployed independently) that flattens all positions

---

## 6. Risk Engine — Layered Defense

The Risk Engine is the **most important component** of the platform. It has veto power over all orders and runs continuously.

### 6.1 Pre-Trade Checks (Layer 1)

Every signal passes through these checks before sizing:

| Check | Rule | Default |
|---|---|---|
| Daily loss budget | Cumulative PnL today > -X% of equity → BLOCK | -2% |
| Weekly drawdown | Equity drop from week high > X% → BLOCK | -5% |
| Max concurrent positions | Open positions ≥ N → BLOCK new | 3 |
| Correlation exposure | Sum of |β| to BTC across positions > X → BLOCK | 2.5 |
| Cooldown after losses | N consecutive losses → pause Y minutes | 3 losses, 60min |
| API health | Latency p95 > 500ms OR error rate > 5% → BLOCK | strict |
| Time-of-day filter | Within blackout windows (e.g., low-liquidity hours) | configurable |

### 6.2 Position Sizing (Layer 2)

**Volatility-adjusted, NOT fixed percent:**

```
position_size = (equity × risk_per_trade) / (ATR × atr_multiplier)
              × regime_multiplier
              × kelly_cap_multiplier
              × (1 / correlation_factor)
```

**Where:**
- `risk_per_trade` — User config (default 0.5% of equity)
- `ATR` — Average True Range, sets stop distance
- `atr_multiplier` — Stop placement (default 1.5× ATR)
- `regime_multiplier` — Trending: 1.0, Choppy: 0.5, Extreme vol: 0.3
- `kelly_cap_multiplier` — Min(Kelly fraction × 0.25, 1.0) — fractional Kelly
- `correlation_factor` — 1 + Σ|ρ_i| for existing positions

### 6.3 Drawdown De-Risking Ladder (Layer 3)

Equity-curve-aware automatic risk reduction:

| Drawdown from Peak | Action |
|---|---|
| 0% to -3% | Normal operation |
| -3% to -5% | Reduce position size by 30% |
| -5% to -8% | Reduce position size by 50% |
| -8% to -10% | Pause new entries, manage existing only |
| -10% to -15% | Flatten all, enter `LOCKED` mode |
| > -15% | `LOCKED` — requires manual review + acknowledgment |

### 6.4 Circuit Breakers (Layer 4)

Automated halts triggered by anomalies:

| Trigger | Action | Reset |
|---|---|---|
| API error rate > 10% over 5 min | Pause new orders | After 10 min healthy |
| Latency p99 > 1500ms over 1 min | Pause + alert | After 5 min healthy |
| Equity deviation > 3σ from expected curve | Flatten all + alert | Manual |
| Volume spike > 5× 1h average + price move > 3σ | Flatten longs OR shorts depending on direction | After volatility normalizes |
| Funding rate extreme (>1% per 8h) | Block new perp positions in that direction | Hourly re-check |
| Liquidation cascade detected (>$50M liquidations in 1 min) | Pause 15 min | Auto |

### 6.5 Hard Limits (Layer 5 — UNCHANGEABLE during runtime)

Set at boot, **cannot be modified by AI or runtime config:**

- Max position size per trade: 10% of equity
- Max total exposure: 100% of equity (no leverage stacking)
- Max leverage (futures): 3x
- Max daily loss: -5% (different from -2% budget; this is the absolute cap)
- Withdrawal: NEVER (API key shouldn't have it; verified at boot)

### 6.6 Risk Configuration File

```yaml
# config/risk_policy.yaml
risk_per_trade: 0.005         # 0.5% of equity
max_daily_loss: 0.02          # 2% soft, 5% hard (immutable)
max_weekly_drawdown: 0.05
max_concurrent_positions: 3
max_correlation_sum: 2.5
loss_streak_pause:
  count: 3
  duration_minutes: 60
position_sizing:
  method: atr_volatility
  atr_period: 14
  atr_multiplier: 1.5
  kelly_fraction: 0.25
regime_multipliers:
  trending: 1.0
  ranging: 0.7
  choppy: 0.5
  extreme: 0.3
drawdown_ladder:
  - { threshold: -0.03, size_multiplier: 0.7 }
  - { threshold: -0.05, size_multiplier: 0.5 }
  - { threshold: -0.08, size_multiplier: 0.0 }   # pause
  - { threshold: -0.10, action: flatten_lock }
hard_limits:                  # IMMUTABLE
  max_position_pct: 0.10
  max_total_exposure_pct: 1.00
  max_leverage: 3.0
  absolute_max_daily_loss: 0.05
```

---

## 7. Strategy Framework & Alpha Sources

### 7.1 Strategy Categories

**Category A: Technical (Baseline / Educational)**

These are intentionally simple. They work as templates, NOT as expected alpha sources.

- EMA Momentum (12/26 cross with ATR-based filter)
- VWAP Reversion (mean-reversion to session VWAP)
- RSI Bounce (oversold/overbought with trend filter)
- Breakout Volume (range break + volume confirmation)

**Category B: Microstructure (Real Alpha Sources)**

- **Orderbook Imbalance** — Bid/ask depth ratio + queue dynamics
- **Liquidation Cascade Surfing** — Detect liq events, trade the snap-back
- **Spot-Perp Basis** — Trade convergence when basis dislocates
- **Funding Rate Divergence** — Extreme funding → contrarian setup

**Category C: Cross-Market**

- **Cross-exchange spread** — Binance vs OKX/Bybit (info-only without arb infra)
- **BTC-Alt rotation signals** — Dominance shifts predict alt rallies
- **Stablecoin flow** — USDT/USDC mint/burn as macro signal

**Category D: AI-Augmented (Carefully Guardrailed)**

- AI suggests parameter adjustments → ENTERS BACKTEST QUEUE → walk-forward validates → human approves → paper trade 7 days → live (NEVER auto-deploy)

### 7.2 Strategy Base Class

```python
# backend/strategies/base.py (specification)
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel

class Signal(BaseModel):
    symbol: str
    side: Literal["long", "short"]
    conviction: float  # 0.0 to 1.0
    source: str
    regime: str
    suggested_stop: Optional[float]
    suggested_take_profit: Optional[float]
    metadata: dict

class Strategy(ABC):
    name: str
    version: str  # semver, e.g. "1.2.0"
    parameter_schema: dict  # JSON schema for params

    @abstractmethod
    async def generate_signal(
        self,
        market_data: MarketData,
        params: dict
    ) -> Optional[Signal]:
        ...

    @abstractmethod
    def required_data(self) -> DataRequirements:
        """Declare what data the strategy needs (timeframes, lookback, etc.)"""
        ...

    def get_config_hash(self, params: dict) -> str:
        """Deterministic hash for versioning + replay"""
        ...
```

### 7.3 Strategy Versioning (Git-like)

Every strategy run is uniquely identified by `(strategy_name, version, parameter_hash)`. This allows:

- Exact replay of past trades
- Rollback to previous versions if live performance drops
- A/B testing between versions in paper trade
- Audit trail of which version made which decision

---

## 8. Backtest & Validation Pipeline

### 8.1 Backtest Engine Requirements

**Inputs:**
- Symbol(s)
- Timeframe(s)
- Date range
- Initial capital
- Fee schedule (maker/taker, with VIP tier)
- Slippage model (configurable: fixed bps, ATR-based, orderbook-based)
- Funding rate inclusion (for perp)
- Strategy + parameters

**Outputs:**
- Equity curve
- Trade log (every trade, with execution quality data)
- Standard metrics: ROI, Sharpe, Sortino, Calmar, Max DD, Profit Factor, Win Rate, Avg R
- **Deflated Sharpe Ratio** (corrects for multiple-testing bias)
- Monte Carlo trade-shuffle distribution (5000 iterations)
- Walk-forward results
- Parameter sensitivity heatmap

### 8.2 Validation Pipeline (MANDATORY before paper trade)

```
1. In-Sample Backtest
   └─ Strategy + initial parameters on first 70% of data

2. Walk-Forward Analysis
   └─ Rolling window: optimize on N months → test on next M months
   └─ Aggregate out-of-sample performance is the TRUE metric

3. Out-of-Sample Validation
   └─ Held-out final 30% never touched during optimization

4. Monte Carlo Robustness
   └─ Shuffle trade order 5000 times
   └─ Report: 5th/50th/95th percentile DD, ruin probability

5. Parameter Sensitivity
   └─ Grid: ±20% on each parameter
   └─ If ROI drops > 50%, strategy is overfit → REJECT

6. Multi-Period Stability
   └─ Performance per quarter
   └─ Worst quarter > -10% → REJECT (regime-fragile)

7. Cost-Adjusted Reality Check
   └─ Re-run with fees × 1.5 and slippage × 2
   └─ If still profitable → robust to cost shocks
```

**Promotion criteria to PAPER:**
- ✅ Walk-forward Sharpe > 1.0
- ✅ Deflated Sharpe > 0.5
- ✅ MC 5th-percentile DD < risk_policy.max_weekly_drawdown × 2
- ✅ Parameter sensitivity passes
- ✅ Worst quarter > -10%
- ✅ Profitable after cost shock

### 8.3 Live vs Backtest Divergence Tracker

**Continuous monitoring once live:**

For each strategy in live, track rolling 30-trade metrics and compare to backtest expectations:

```
divergence_score = |live_sharpe - bt_sharpe| / bt_sharpe_stddev
```

Alerts:
- `divergence_score > 1.0` → Yellow flag, investigate
- `divergence_score > 2.0` → Auto-pause strategy, require manual review
- `divergence_score > 3.0` → Auto-disable strategy + alert

---

## 9. Execution Quality & Cost Accounting

### 9.1 Execution Quality Monitor

**Tracks per-order:**
- Expected fill price (at signal time)
- Requested order price
- Actual fill price(s) — handles partial fills
- Fill latency (signal → submitted → confirmed)
- Maker/taker classification
- Fee paid
- Slippage in bps and absolute USD

**Aggregations (per symbol, per strategy, per timeframe):**
- Average slippage
- Slippage distribution
- Fill rate (% of orders fully filled at first attempt)
- Reject rate
- Cancellation rate

**Display in UI:** Dedicated "Execution Quality" page showing the gap between theoretical and realized performance.

### 9.2 Cost Accounting (Net vs Gross PnL)

**Every PnL display in the system is NET unless explicitly labeled "Gross."**

Tracked categories:
- **Trading fees** — maker/taker, per trade
- **Funding costs** — for perp positions, paid/received
- **Slippage** — actual fill vs expected, materialized as cost
- **Spread cost** — for market orders, half the spread

**Daily / Weekly / Monthly Cost Report:**

```
Period: 2026-04-01 to 2026-04-30
Gross PnL:           +$2,450.00
- Trading Fees:        -$340.20
- Funding Paid:        -$87.50
+ Funding Received:    +$45.00
- Slippage:           -$215.30
- Spread:             -$92.00
─────────────────────────────────
Net PnL:             +$1,760.00
```

This eliminates the #1 cause of "profitable backtest, losing live" surprise.

---

## 10. AI Analyst — Guardrailed Intelligence

### 10.1 AI's Role (Permitted)

✅ **Diagnosis**
- Explain losing streaks ("Last 5 losses occurred in regime X, where this strategy historically underperforms")
- Detect overfitting risk in proposed parameters
- Summarize current market regime
- Identify anomalies in execution quality

✅ **Suggestion**
- Propose parameter adjustments (enters Backtest Queue)
- Propose new strategy hypotheses (enters Research Queue)
- Recommend risk policy reviews

✅ **Reporting**
- Daily summary email/Telegram
- Weekly performance review
- Monthly strategy health report

### 10.2 AI's Role (FORBIDDEN — Hard-Coded Restrictions)

❌ **Never directly modifies live parameters**
❌ **Never deploys strategies to live mode**
❌ **Never overrides risk engine veto**
❌ **Never adjusts risk policy hard limits**
❌ **Never executes orders directly**
❌ **Never has Binance API credentials**

These are enforced at the architectural level — the AI service has no write access to risk_policy, no order execution permissions, and no live strategy deployment endpoint.

### 10.3 The AI Suggestion Pipeline

```
AI generates suggestion
        │
        ▼
  Backtest Queue (automated)
        │
        ▼
  Walk-forward validation
        │
        ▼
  Human Review Dashboard
        │
        ▼
  [APPROVE] ← user clicks
        │
        ▼
  Paper trade (7 days minimum)
        │
        ▼
  [APPROVE LIVE] ← user clicks
        │
        ▼
  Live deployment with new version tag
```

### 10.4 Prompt Templates (Versioned)

Stored in `prompts/` directory, versioned with the codebase:

- `analyst_system.md` — System prompt defining role, constraints, output format
- `regime_classify.md` — Regime classification with structured output
- `losing_streak_explain.md` — Diagnosis prompt
- `parameter_review.md` — Critique proposed parameter changes
- `strategy_explain.md` — Generate strategy explanation for journal

### 10.5 Trade Journal Auto-Tagging

Every closed trade is sent to AI for tagging:

**Tags AI assigns (multi-label):**
- `good_entry_good_exit`
- `good_entry_bad_exit`
- `bad_entry_good_exit`
- `fomo_entry`
- `stopped_at_noise`
- `let_winner_run`
- `cut_winner_short`
- `revenge_trade_detected`
- `regime_mismatch`
- `news_driven_random`

This data accumulates and feeds back into strategy improvement and self-discipline review.

---

## 11. Frontend — Premium Dashboard

### 11.1 Design System

**Visual Identity:**
- Dark modern terminal-finance aesthetic
- Glassmorphism cards with subtle gradients
- Smooth Framer Motion transitions (prefer 200-300ms ease-out)
- Monospace for numbers (JetBrains Mono / Geist Mono)
- Sans-serif for UI (Inter / Geist Sans)
- Data-rich but elegant — never cluttered

**Color Tokens:**

```css
/* Backgrounds */
--bg-base: oklch(0.12 0.005 270);       /* near-black */
--bg-elevated: oklch(0.16 0.008 270);   /* card */
--bg-glass: oklch(0.20 0.010 270 / 0.6);

/* Foregrounds */
--fg-primary: oklch(0.96 0.005 270);
--fg-secondary: oklch(0.70 0.010 270);
--fg-muted: oklch(0.50 0.010 270);

/* Accents */
--accent-primary: oklch(0.75 0.18 165);  /* emerald */
--accent-secondary: oklch(0.78 0.15 200); /* cyan */

/* Semantic */
--profit: oklch(0.75 0.18 145);
--loss: oklch(0.65 0.22 25);
--neutral: oklch(0.65 0.02 270);
--warning: oklch(0.78 0.16 75);
```

**Inspirations:**
- Stripe Dashboard
- Linear
- Vercel
- TradingView
- Modern hedge fund internal tools (Citadel, Two Sigma aesthetics)

### 11.2 Pages

#### Page 1: Executive Dashboard

**Top Row — KPI Cards:**
- Total Equity (with sparkline of last 30d)
- Daily PnL (animated counter, color-coded)
- Weekly PnL
- Monthly PnL
- Open Positions (count + total exposure)
- Win Rate (last 30 trades)
- Sharpe (rolling 30d)
- Max Drawdown (current)
- Bot Status (chip: RUNNING / PAUSED / LOCKED)
- Market Regime (chip: TRENDING / RANGING / CHOPPY / EXTREME)

**Main Charts:**
- Equity Curve (overlaid: live, paper, backtest expected)
- PnL Heatmap (calendar view)
- Win/Loss Distribution histogram
- Strategy Contribution stacked area

**Right Sidebar:**
- Active Alerts (last 10)
- Live Signal Feed
- Quick Actions (Pause All, Close All — with double-confirm modal)

#### Page 2: Live Trading Terminal

- TradingView chart (Lightweight Charts)
- Orderbook depth (bid/ask ladder, with imbalance indicator)
- Recent Trades tape
- Open Positions table (with inline close buttons)
- Pending Orders table
- Current Signals panel (per strategy)
- Emergency Kill Switch (red button, requires typing "FLATTEN" to confirm)

#### Page 3: Strategy Lab

Grid of strategy cards. Each card:
- Name + version + status toggle (ON/OFF)
- Mini equity curve sparkline (live + backtest)
- Live ROI / Win Rate / DD / Trade Count
- Backtest comparison (divergence indicator)
- Last signal timestamp
- Parameter editor (opens drawer)
- Action buttons: Backtest / Paper / Promote / Disable / Rollback

#### Page 4: Backtest Center

**Setup Form:**
- Symbol multi-select
- Timeframe selector
- Date range picker (presets: 30d / 90d / 1y / 3y)
- Initial capital
- Fee tier selector (regular / VIP1-9)
- Slippage model selector
- Strategy selector + parameter editor

**Run Type:**
- Single backtest
- Walk-forward (with window size config)
- Parameter sweep (grid / random / Bayesian)
- Monte Carlo robustness

**Results Panel:**
- Equity curve with drawdown shading
- Trade log (sortable, filterable)
- Metrics card (with Deflated Sharpe prominent)
- MC distribution chart
- Sensitivity heatmap
- "Promote to Paper Trade" button (only enabled if all promotion criteria met)

#### Page 5: Risk Command Center

- Current risk policy (read-only display, "Edit Policy" button)
- Risk policy editor (with diff view before save)
- Active circuit breakers status grid (all green / specific yellow/red)
- Drawdown ladder visualization (current position on ladder)
- Correlation matrix heatmap of open positions
- Daily loss budget gauge
- Hard limits display (greyed out, "Immutable" badge)

#### Page 6: AI Analyst

- **Daily Briefing card** — AI-generated regime + portfolio summary
- **Ask AI** chat interface (streaming responses)
- **Suggestions Queue** — pending AI suggestions awaiting approval
- **Diagnosis** — paste trade ID or strategy, get AI analysis
- **Research Notes** — AI-generated weekly research

#### Page 7: Trade Journal

- Trade list with AI-assigned tags
- Filter by tag, strategy, regime, outcome
- Click trade → detailed timeline (signal → entry → mgmt → exit)
- AI explanation per trade
- Manual notes field (user can add context)

#### Page 8: Execution Quality

- Slippage distribution per symbol
- Fill rate trends
- Maker/taker ratio
- Latency histogram (signal → confirmed)
- Cost breakdown (fees / funding / slippage / spread)
- Comparison: Backtest expected vs Live realized

#### Page 9: Logs & Audit Trail

Tabs:
- Orders (with full lifecycle: signal → submit → fill → close)
- Errors (with stack traces, severity)
- API Events (Binance API calls, with latency)
- Strategy Decisions (every signal evaluated, including rejected ones)
- Risk Engine Vetoes (every blocked order with reason)
- User Actions (every UI interaction that changed state)
- AI Interactions (every prompt + response, for audit)

All logs are **append-only** and exportable.

### 11.3 Real-time Architecture

- WebSocket connection to backend for live data
- Optimistic updates with rollback on error
- Toast notifications for important events
- Sound alerts (configurable) for CRITICAL events

---

## 12. Database Schema

### 12.1 Core Tables

```sql
-- Users (single-user mode initially, multi-user-ready)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    totp_secret TEXT,           -- 2FA
    role TEXT NOT NULL DEFAULT 'owner',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Encrypted API credentials
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    exchange TEXT NOT NULL,
    label TEXT,
    encrypted_key BYTEA NOT NULL,
    encrypted_secret BYTEA NOT NULL,
    permissions JSONB,           -- {"trade": true, "withdraw": false}
    ip_whitelist TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Strategies (versioned)
CREATE TABLE strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    version TEXT NOT NULL,         -- semver
    code_hash TEXT NOT NULL,       -- git commit or content hash
    parameters JSONB NOT NULL,
    parameter_hash TEXT NOT NULL,
    status TEXT NOT NULL,          -- draft, backtest, paper, live_micro, live_scaled, retired
    promoted_at TIMESTAMPTZ,
    promoted_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (name, version, parameter_hash)
);

-- Signals (every signal generated, even rejected)
CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID REFERENCES strategies(id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    conviction REAL,
    regime TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    metadata JSONB,
    risk_decision TEXT,            -- approved, rejected
    rejection_reason TEXT
);

-- Orders (pre-submission record)
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key UUID UNIQUE NOT NULL,
    signal_id UUID REFERENCES signals(id),
    exchange_order_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    type TEXT NOT NULL,
    qty NUMERIC NOT NULL,
    price NUMERIC,
    status TEXT NOT NULL,
    submitted_at TIMESTAMPTZ,
    confirmed_at TIMESTAMPTZ,
    filled_at TIMESTAMPTZ,
    raw_response JSONB
);

-- Fills (handles partial)
CREATE TABLE fills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id),
    qty NUMERIC NOT NULL,
    price NUMERIC NOT NULL,
    fee NUMERIC NOT NULL,
    fee_currency TEXT NOT NULL,
    is_maker BOOLEAN,
    timestamp TIMESTAMPTZ NOT NULL
);

-- Positions
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID REFERENCES strategies(id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    entry_qty NUMERIC NOT NULL,
    entry_price NUMERIC NOT NULL,
    current_qty NUMERIC NOT NULL,
    avg_price NUMERIC NOT NULL,
    stop_price NUMERIC,
    take_profit_price NUMERIC,
    opened_at TIMESTAMPTZ NOT NULL,
    closed_at TIMESTAMPTZ,
    realized_pnl NUMERIC,
    fees_paid NUMERIC,
    funding_paid NUMERIC,
    slippage_cost NUMERIC,
    ai_tags TEXT[],
    notes TEXT
);

-- Equity snapshots (TimescaleDB hypertable)
CREATE TABLE equity_snapshots (
    timestamp TIMESTAMPTZ NOT NULL,
    equity NUMERIC NOT NULL,
    cash NUMERIC NOT NULL,
    unrealized_pnl NUMERIC NOT NULL,
    realized_pnl_today NUMERIC NOT NULL,
    open_positions INT NOT NULL
);
SELECT create_hypertable('equity_snapshots', 'timestamp');

-- Backtest runs
CREATE TABLE backtests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID REFERENCES strategies(id),
    config JSONB NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    metrics JSONB,
    equity_curve JSONB,
    trade_log_path TEXT
);

-- Risk events (vetoes, breaker trips, ladder steps)
CREATE TABLE risk_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    payload JSONB,
    auto_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ
);

-- AI interactions (audit)
CREATE TABLE ai_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    interaction_type TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_template TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    input_tokens INT,
    output_tokens INT,
    cost_usd NUMERIC,
    response JSONB
);

-- Audit log (append-only, all state changes)
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    user_id UUID,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id TEXT,
    before_state JSONB,
    after_state JSONB,
    ip_address INET
);

-- Logs (Loki is primary; this is for queryable structured logs)
CREATE TABLE logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    level TEXT NOT NULL,
    service TEXT NOT NULL,
    message TEXT NOT NULL,
    context JSONB
);
```

### 12.2 Indexes (Performance Critical)

```sql
CREATE INDEX idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX idx_signals_strategy_symbol ON signals(strategy_id, symbol, timestamp DESC);
CREATE INDEX idx_orders_status ON orders(status) WHERE status IN ('submitted', 'partially_filled');
CREATE INDEX idx_positions_open ON positions(symbol) WHERE closed_at IS NULL;
CREATE INDEX idx_audit_log_entity ON audit_log(entity, entity_id, timestamp DESC);
```

---

## 13. Security & Secrets Management

### 13.1 API Key Hygiene

**Binance API key MUST be:**
- ✅ Trading enabled
- ❌ Withdrawal DISABLED (verified at boot, refuse to start if enabled)
- ✅ IP whitelisted to VPS IP
- 🔄 Rotated every 90 days

**Boot-time verification:**
```python
# Pseudocode
async def verify_api_safety():
    permissions = await binance.get_account_api_permissions()
    if permissions.get("enableWithdrawals"):
        raise SecurityError("API key has withdrawal permission. ABORT.")
    if not permissions.get("ipRestrict"):
        raise SecurityError("API key has no IP restriction. ABORT.")
```

### 13.2 Secrets Storage

**Development:**
- `.env` file (gitignored)
- `.env.example` committed with placeholders

**Production (one of):**
- HashiCorp Vault (preferred for multi-env)
- `age`-encrypted file checked into repo, decrypted at boot via key on disk
- Docker secrets (for swarm/k8s)

**NEVER:**
- Commit secrets to git
- Log secrets (redact in structured logger)
- Display secrets in UI (show only `sk_****abcd`)

### 13.3 Authentication

- **Web UI:** Email + password (Argon2id) + TOTP 2FA mandatory
- **API:** JWT short-lived (15 min) + refresh token (7 days)
- **Session management:** Redis with sliding expiration
- **Rate limiting:** 100 req/min per user, 10 login attempts per IP per hour

### 13.4 Network Security

- VPS firewall (ufw): allow only 22 (SSH), 443 (HTTPS), 80 (HTTPS redirect)
- SSH: key-only auth, no root login, fail2ban enabled
- TLS: Let's Encrypt, auto-renew, A+ on SSL Labs
- Cloudflare (optional): DDoS protection, hide origin IP

### 13.5 Audit Trail Requirements

Every state-changing action is logged with:
- Who (user_id + IP)
- What (action + entity)
- When (UTC timestamp)
- Before/After state (for diffs)

Audit logs are **append-only** at the application layer. For tamper-evidence, consider periodic snapshots to immutable storage (S3 Object Lock or similar).

---

## 14. Observability & Disaster Recovery

### 14.1 Metrics (Prometheus)

**Application metrics:**
- `aiq_signals_generated_total{strategy, symbol, regime}`
- `aiq_signals_rejected_total{reason}`
- `aiq_orders_submitted_total{symbol, side, type}`
- `aiq_orders_filled_total`
- `aiq_orders_rejected_total{reason}`
- `aiq_slippage_bps{symbol, side}` (histogram)
- `aiq_api_latency_seconds{endpoint}` (histogram)
- `aiq_equity_usd` (gauge)
- `aiq_open_positions` (gauge)
- `aiq_risk_engine_vetoes_total{reason}`
- `aiq_circuit_breaker_trips_total{name}`
- `aiq_ai_cost_usd_total{model}`

**System metrics (node_exporter):**
- CPU, memory, disk, network

### 14.2 Dashboards (Grafana)

Pre-built dashboards in `ops/grafana/dashboards/`:
- **Operations Overview** — system health at a glance
- **Trading Performance** — PnL, win rate, by strategy
- **Risk Engine** — vetoes, breakers, drawdown
- **Execution Quality** — slippage, fill rates, latency
- **AI Costs** — token usage, cost per analysis

### 14.3 Logging

- **Structured (JSON) logs** via structlog
- Shipped to **Loki** for aggregation
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Sensitive data redacted automatically (API keys, secrets)
- Retention: 30 days hot, 1 year cold (S3-compatible storage)

### 14.4 External Monitoring

- **Healthchecks.io** ping every 30s — alerts if missed > 2 min
- **UptimeRobot** monitor on `/api/health` every 5 min
- **Telegram heartbeat** every 4 hours during quiet periods, immediate on critical events

### 14.5 Disaster Recovery

#### Scenarios & Runbooks

**Scenario A: VPS goes down with open positions**

1. External monitor detects no heartbeat for 2 minutes
2. Webhook fires to **dead-man switch service** (deployed independently on a second small VPS or serverless)
3. Dead-man switch authenticates with separate read+trade-only key (different from main bot)
4. Flattens all positions on Binance
5. Sends critical alert
6. Requires manual restart

**Scenario B: Binance maintenance during open positions**

1. Bot detects API errors / WS disconnects
2. Risk engine enters `FROZEN` state — no new orders, can still close
3. Aggressively retries to close positions when API returns
4. Logs full event timeline

**Scenario C: Database corruption**

1. Daily automated backups to S3-compatible storage
2. Backup retention: 7 daily + 4 weekly + 12 monthly
3. Recovery procedure documented in `docs/RUNBOOK.md`
4. RTO: 30 minutes
5. RPO: 24 hours (acceptable since Binance is truth source for positions)

**Scenario D: Bot stuck in infinite loop**

1. Watchdog process monitors main loop heartbeat
2. If main loop stalls > 60s, watchdog SIGTERMs the process
3. Container auto-restart kicks in
4. Recovery service runs (state sync from Binance)

#### Backup Procedure

```bash
# ops/scripts/backup_db.sh
# Runs nightly via cron
pg_dump -Fc aiq_db | age -r $BACKUP_PUBLIC_KEY > backup-$(date +%Y%m%d).age
aws s3 cp backup-*.age s3://aiq-backups/ --storage-class STANDARD_IA
# Lifecycle policy on bucket handles retention
```

#### State Recovery on Boot

```python
# Pseudocode
async def recover_state():
    # 1. Load last known state from DB
    local_state = await db.load_open_positions()
    
    # 2. Get truth from Binance
    binance_positions = await binance.get_positions()
    binance_orders = await binance.get_open_orders()
    
    # 3. Diff and resolve
    discrepancies = diff(local_state, binance_positions)
    if discrepancies:
        log.critical("State discrepancy detected", diff=discrepancies)
        await alert_critical("State recovery diff", discrepancies)
        
        # Binance wins
        await db.reconcile_to(binance_positions, binance_orders)
    
    # 4. Verify SL/TP attached
    for pos in binance_positions:
        if not pos.has_stop():
            await execution.attach_emergency_stop(pos)
    
    # 5. Health check before resuming
    if not await health_check_all_services():
        await enter_safe_mode()
        return
    
    log.info("State recovery complete, resuming normal operation")
```

---

## 15. Deployment & Infrastructure

### 15.1 VPS Specifications

**Minimum:**
- 2 vCPU
- 4 GB RAM
- 40 GB SSD
- 1 Gbps network
- Ubuntu 22.04 LTS

**Recommended (for live trading):**
- 4 vCPU
- 8 GB RAM
- 80 GB SSD
- Geographic location: AWS Tokyo or similar (closest to Binance servers for latency)

### 15.2 Docker Compose (Production)

```yaml
# docker-compose.prod.yml
version: "3.9"

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: ../ops/docker/Dockerfile.frontend
    restart: unless-stopped
    environment:
      - NEXT_PUBLIC_API_URL=${PUBLIC_API_URL}
    networks: [aiq-net]
    depends_on: [backend]

  backend:
    build:
      context: ./backend
      dockerfile: ../ops/docker/Dockerfile.backend
    restart: unless-stopped
    env_file: .env.prod
    networks: [aiq-net]
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: timescale/timescaledb:latest-pg15
    restart: unless-stopped
    env_file: .env.prod
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks: [aiq-net]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER"]
      interval: 10s

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    networks: [aiq-net]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  prometheus:
    image: prom/prometheus
    restart: unless-stopped
    volumes:
      - ./ops/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    networks: [aiq-net]

  grafana:
    image: grafana/grafana
    restart: unless-stopped
    env_file: .env.prod
    volumes:
      - grafana-data:/var/lib/grafana
      - ./ops/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    networks: [aiq-net]

  loki:
    image: grafana/loki
    restart: unless-stopped
    volumes:
      - loki-data:/loki
    networks: [aiq-net]

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./ops/docker/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ops/certs:/etc/letsencrypt
    networks: [aiq-net]
    depends_on: [frontend, backend]

networks:
  aiq-net:

volumes:
  pgdata:
  prometheus-data:
  grafana-data:
  loki-data:
```

### 15.3 Environment Variables

```env
# .env.example

# ─── Mode ───
MODE=paper                          # backtest | paper | live_micro | live_scaled

# ─── Binance ───
BINANCE_API_KEY=
BINANCE_API_SECRET=
BINANCE_TESTNET=false               # true for paper trade testnet
BINANCE_VIP_TIER=0

# ─── Risk Policy (loaded from config/risk_policy.yaml at boot) ───
RISK_POLICY_PATH=./config/risk_policy.yaml

# ─── Database ───
POSTGRES_USER=aiq
POSTGRES_PASSWORD=                  # CHANGE
POSTGRES_DB=aiq_db
DATABASE_URL=postgresql+asyncpg://aiq:${POSTGRES_PASSWORD}@db:5432/aiq_db

# ─── Redis ───
REDIS_PASSWORD=                     # CHANGE
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# ─── Auth ───
JWT_SECRET=                         # CHANGE — generate with: openssl rand -hex 64
JWT_EXPIRE_MINUTES=15
REFRESH_EXPIRE_DAYS=7
ARGON2_TIME_COST=3
ARGON2_MEMORY_COST=65536

# ─── AI ───
OPENROUTER_API_KEY=
AI_PRIMARY_MODEL=anthropic/claude-sonnet-4
AI_FAST_MODEL=openai/gpt-4o-mini
AI_HEAVY_MODEL=deepseek/deepseek-r1
AI_MAX_COST_USD_PER_DAY=5.00

# ─── Notifications ───
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=alerts@yourdomain.com
EMAIL_TO=you@yourdomain.com

# ─── Monitoring ───
HEALTHCHECK_PING_URL=               # https://hc-ping.com/<uuid>
DEAD_MAN_SWITCH_WEBHOOK=            # external webhook
PROMETHEUS_ENABLED=true

# ─── Frontend ───
PUBLIC_API_URL=https://yourdomain.com/api
NEXT_PUBLIC_WS_URL=wss://yourdomain.com/ws
```

### 15.4 Deploy Procedure

```bash
# ops/scripts/deploy.sh
set -e

# 1. Pull latest
git pull origin main

# 2. Run pre-deploy validation
./ops/scripts/preflight.sh

# 3. Migrate DB
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 4. Build & restart with zero-downtime (rolling)
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d --no-deps --build backend
sleep 10
./ops/scripts/healthcheck.sh || (echo "Health check failed, rolling back"; exit 1)
docker compose -f docker-compose.prod.yml up -d --no-deps --build frontend

# 5. Post-deploy verification
./ops/scripts/healthcheck.sh
./ops/scripts/smoke_test.sh

# 6. Notify
./ops/scripts/notify_deploy.sh "Deployed $(git rev-parse --short HEAD)"
```

---

## 16. Development Roadmap & Promotion Gates

### Phase 0: Foundation (Week 1-2)

- [ ] Repository scaffolding
- [ ] Docker Compose dev environment
- [ ] Database schema + Alembic migrations
- [ ] Authentication (login + 2FA)
- [ ] Frontend shell (sidebar, top bar, theme system)
- [ ] CI/CD (lint, test, build, deploy)
- [ ] Logging + Prometheus instrumentation skeleton

**Gate to Phase 1:** `make test` green, deploys cleanly to staging VPS.

### Phase 1: Market Data + Premium UI Shell (Week 3-4)

- [ ] Binance WS connection (public streams)
- [ ] Candle aggregation
- [ ] Orderbook sync
- [ ] Dashboard page with real-time data
- [ ] Trading Terminal with TradingView chart
- [ ] Telegram notification integration

**Gate to Phase 2:** Real-time data flowing, charts rendering, no memory leaks over 24h.

### Phase 2: Backtest Engine (Week 5-7)

- [ ] vectorbt integration
- [ ] Walk-forward analysis
- [ ] Monte Carlo simulation
- [ ] Parameter sensitivity
- [ ] Deflated Sharpe + standard metrics
- [ ] Backtest UI with results visualization
- [ ] At least 4 baseline strategies (EMA, VWAP, RSI, Breakout) implemented

**Gate to Phase 3:** A strategy passes ALL promotion criteria in backtest with realistic data.

### Phase 3: Risk Engine + Paper Trade (Week 8-10)

- [ ] Full Risk Engine (all 5 layers)
- [ ] Risk Command Center UI
- [ ] Paper trading mode (simulated fills with realistic slippage)
- [ ] Execution Quality monitoring
- [ ] Cost accounting (gross vs net)
- [ ] Live vs Backtest divergence tracker

**Gate to Phase 4:** Paper trade successful 30+ days with metrics within 20% of backtest expectations.

### Phase 4: AI Analyst (Week 11-12)

- [ ] OpenRouter integration with cost cap
- [ ] AI Analyst page
- [ ] Daily briefing automation
- [ ] Trade journal auto-tagging
- [ ] Suggestion queue with approval workflow
- [ ] Diagnosis workflows

**Gate to Phase 5:** AI providing meaningful daily briefings, suggestion pipeline works end-to-end.

### Phase 5: LIVE_MICRO (Week 13+)

- [ ] Production deployment hardening
- [ ] Security audit (API perms, IP whitelist, etc.)
- [ ] Disaster recovery testing (kill VPS, verify dead-man switch)
- [ ] Backup/restore drill
- [ ] Live deployment with strict micro capital limit
- [ ] **Minimum 3 months of LIVE_MICRO before considering scaling**

**Gate to Phase 6:** 3+ months of LIVE_MICRO with metrics matching backtest expectations within tolerance, no critical incidents.

### Phase 6: LIVE_SCALED + Advanced Strategies (Month 6+)

- [ ] Microstructure strategies (orderbook imbalance, etc.)
- [ ] Cross-market strategies
- [ ] Multi-symbol portfolio optimization
- [ ] Capital scaling per growth plan

### Phase 7: Optional — Multi-Tenant SaaS (Month 12+)

Only if proven profitable for personal use first.

- [ ] User management & isolation
- [ ] Per-user API key encryption
- [ ] Billing integration
- [ ] Compliance review (KYC, regulatory)
- [ ] Marketing site

**This phase has different security requirements and should NOT be combined with personal-use phases.**

---

## 17. Codex / Claude Code Build Instructions

### 17.1 Master Prompt (paste this when starting a build session)

```
You are building AI-Quant-Binance-Bot, a production-grade crypto trading platform.

CRITICAL RULES:
1. Follow this blueprint exactly — do not skip risk/security/observability requirements.
2. Build in the phase order specified. Do not jump ahead.
3. Every PnL display must be NET of fees, funding, and slippage. Label gross/net explicitly.
4. The Risk Engine has veto power over every order. Never bypass it.
5. The AI Analyst must NEVER directly modify live parameters or deploy strategies.
6. Every order needs an idempotency key.
7. Binance is always the source of truth for positions — local state must reconcile to it.
8. Production secrets NEVER go in code. Use environment variables or secret managers.
9. Use async/await throughout the backend. No blocking calls in request handlers.
10. Write tests as you go. No new feature without tests.

CODE STYLE:
- Python: black, ruff, mypy strict, async-first
- TypeScript: strict mode, ESLint, Prettier
- Commits: Conventional Commits (feat:, fix:, docs:, etc.)

ASK BEFORE:
- Adding a new external dependency
- Deviating from the architecture
- Changing the risk policy hard limits

OUTPUT:
- Generate files step by step with explanations
- After each major component, run tests and report results
- Show the structure before generating code in a new directory

Start with Phase 0. Confirm completion of each phase before proceeding.
```

### 17.2 Per-Phase Prompts

Save these in `prompts/build/phase-{0-7}.md` and feed them to the AI sequentially.

**Phase 0 prompt example:**

```
Implement Phase 0 (Foundation) of AI-Quant-Binance-Bot.

Tasks:
1. Create the repository structure as specified in Section 4.
2. Set up Docker Compose for local development (postgres, redis, backend, frontend).
3. Implement the database schema from Section 12 with Alembic migrations.
4. Build authentication: email+password (Argon2id) + TOTP 2FA.
5. Create the frontend shell with sidebar navigation, top command bar, and dark theme using tokens from Section 11.1.
6. Set up CI/CD pipeline (GitHub Actions): lint, test, type-check on every PR.
7. Add structlog and Prometheus instrumentation skeletons.

Do NOT yet implement market data, strategies, or trading logic.

Deliverables:
- Working `docker compose up` that brings up empty but functional system
- User can register, enable 2FA, login
- Frontend shell renders all 9 page routes (placeholder content OK)
- `make test` passes
- README with setup instructions

When done, run all tests and confirm Phase 0 gate criteria are met.
```

### 17.3 Code Quality Standards

- **Test coverage:** ≥ 80% for risk engine, ≥ 60% overall
- **Type checking:** `mypy --strict` for backend, `tsc --noEmit` for frontend
- **No silent failures:** All exceptions either handled with recovery action or logged with severity
- **No magic numbers:** Constants in named config
- **Documentation:** Every public function has docstring with Args/Returns/Raises

### 17.4 Anti-Patterns to Avoid

❌ Catching broad exceptions without re-raising or alerting
❌ Hardcoding symbols, parameters, or risk limits in code
❌ Calling Binance API from frontend
❌ Storing API keys in JWT payload or local storage
❌ Optimistic state updates without server confirmation for trade actions
❌ Backtest with look-ahead bias (using future data)
❌ Sharpe ratio comparison without considering Deflated Sharpe
❌ AI suggestions auto-applied to live config
❌ Missing reconciliation after order submission
❌ Floating-point arithmetic on money — use `Decimal` in Python

---

## 18. Appendix

### 18.1 Glossary

- **Deflated Sharpe Ratio (DSR):** Sharpe corrected for multiple-testing bias; closer to true expected performance.
- **Walk-Forward Analysis:** Rolling optimize-and-test methodology that mimics live deployment conditions.
- **Kelly Criterion:** Optimal bet size formula; full Kelly is too aggressive, fractional (e.g., 0.25×) is standard.
- **ATR (Average True Range):** Volatility measure used for stop placement and position sizing.
- **Dead-Man Switch:** External monitor that triggers position flatten if main system goes silent.
- **Idempotency Key:** Unique ID per order that prevents duplicate submissions on retry.
- **Regime:** Classification of current market state (trending, ranging, choppy, extreme).
- **Slippage:** Difference between expected and actual fill price.
- **Funding Rate:** Periodic payment between perpetual longs and shorts.

### 18.2 Reading List (for the developer)

- *Advances in Financial Machine Learning* — Marcos López de Prado (essential for Deflated Sharpe, walk-forward, MC)
- *Building Winning Algorithmic Trading Systems* — Kevin Davey
- *Algorithmic and High-Frequency Trading* — Cartea, Jaimungal, Penalva (microstructure)
- Binance API documentation — `https://binance-docs.github.io/apidocs/`
- Binance API rate limits and order rules — Symbol-specific filters

### 18.3 License & Disclaimers

This blueprint is private/proprietary. Code generated from this blueprint is for personal use unless explicitly licensed otherwise.

**TRADING DISCLAIMER:** Algorithmic trading carries substantial risk. Past performance, including backtest results, is not indicative of future results. Cryptocurrency markets are highly volatile and can result in total loss of capital. This software is provided "as is" without warranty. The user assumes all risk.

**No part of this system constitutes financial advice.**

### 18.4 Change Log

- **v2.0 (this version)** — Production-grade rewrite: layered risk engine, walk-forward validation pipeline, execution quality monitoring, cost accounting, AI guardrails, disaster recovery, security hardening, promotion gates.
- **v1.0** — Initial blueprint (UI-focused, structural).

---

**End of Blueprint v2.0**

*Build slowly. Validate ruthlessly. Ship safely.*
