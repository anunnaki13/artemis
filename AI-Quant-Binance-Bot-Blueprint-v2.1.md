# AI-Quant-Binance-Bot — Production Blueprint v2.1

> **Institutional-grade crypto automation for independent traders.**
> **Designed for small-capital reality ($100–$10,000) with defensible edge built in.**
>
> A production-ready, AI-augmented crypto trading platform engineered around three pillars:
> 1. **Survival** — real cost accounting, anti-overfitting, layered risk controls, operational resilience
> 2. **Defensible edge** — strategies and data sources that don't decay when copied by other retail bots
> 3. **Small-capital fitness** — every design decision is checked against a $100 starting balance

**Codename:** `AIQ-BOT`
**Version:** 2.1 (Production Blueprint with Edge Layer + Small Capital Profile)
**Status:** Specification — Reference for Codex / Claude Code implementation
**License:** Private / Proprietary

---

## Table of Contents

1. [Core Philosophy & Non-Negotiables](#1-core-philosophy--non-negotiables)
2. [Small Capital Reality ($100 Profile)](#2-small-capital-reality-100-profile)
3. [System Architecture](#3-system-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Repository Structure](#5-repository-structure)
6. [Backend Services (Detailed)](#6-backend-services-detailed)
7. [Risk Engine — Layered Defense](#7-risk-engine--layered-defense)
8. [Strategy Framework & Alpha Sources](#8-strategy-framework--alpha-sources)
9. [Defensible Edge Layer](#9-defensible-edge-layer)
10. [Backtest & Validation Pipeline](#10-backtest--validation-pipeline)
11. [Execution Quality & Cost Accounting](#11-execution-quality--cost-accounting)
12. [AI Analyst — Guardrailed Intelligence](#12-ai-analyst--guardrailed-intelligence)
13. [Frontend — Premium Dashboard](#13-frontend--premium-dashboard)
14. [Database Schema](#14-database-schema)
15. [Security & Secrets Management](#15-security--secrets-management)
16. [Observability & Disaster Recovery](#16-observability--disaster-recovery)
17. [Deployment & Infrastructure](#17-deployment--infrastructure)
18. [Development Roadmap & Promotion Gates](#18-development-roadmap--promotion-gates)
19. [Codex / Claude Code Build Instructions](#19-codex--claude-code-build-instructions)
20. [Appendix](#20-appendix)

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

## 2. Small Capital Reality ($100 Profile)

> **This section is critical. Every implementation decision must be checked against the $100 starting balance constraint. Codex/Claude Code MUST read this before writing any trading logic.**

### 2.1 Why Small Capital Changes Everything

A $100 account is **not a smaller version of a $10,000 account**. It's a fundamentally different problem with different optimal solutions.

**What works at $100k breaks at $100:**

| Constraint | $10,000 Account | $100 Account |
|---|---|---|
| Min position size (Binance Spot) | Easy: 0.5% = $50 | Hard: $5 = 5% of equity |
| Min notional ($5–$10 on Binance) | Negligible | Forces minimum 5–10% per trade |
| Fee impact (0.1% taker) | 0.001% per trade | 0.001% per trade (same %), but compounds heavier on small wins |
| Slippage on $5 order | Near zero | Often 0.05–0.20% on illiquid alts |
| Stop loss precision | Loose stops fine | Need tight, precise stops |
| Risk per trade | 0.5% = $50 | 0.5% = $0.50 — too small to clear fees |
| Number of concurrent positions | 3–5 fine | Maximum 1–2 due to min notional |

### 2.2 Hard Rules for Small Capital Profile

**The system MUST detect equity tier and enforce these rules automatically.**

```yaml
# config/capital_profiles.yaml
profiles:
  micro:                        # $50 - $500
    min_notional_buffer: 1.5    # Require 1.5x exchange min notional
    max_concurrent_positions: 1 # Only 1 trade at a time
    risk_per_trade_pct: 2.0     # Higher % needed to overcome fees (2% of $100 = $2 risk)
    min_trade_target_r: 2.5     # Min reward:risk to justify fee drag
    preferred_fee_tier: maker_only  # Avoid taker fees aggressively
    stablecoin_only_in_idle: true   # No HODLing volatile assets when no signal
    avoid_pairs_below_volume: 50000000  # $50M daily volume min
    use_futures: false          # Spot only initially (lower complexity, no funding cost surprise)

  small:                        # $500 - $5,000
    min_notional_buffer: 1.2
    max_concurrent_positions: 2
    risk_per_trade_pct: 1.5
    min_trade_target_r: 2.0
    preferred_fee_tier: maker_preferred
    use_futures: optional       # Allow if funding-arb strategy enabled

  standard:                     # $5,000 - $50,000
    min_notional_buffer: 1.0
    max_concurrent_positions: 3
    risk_per_trade_pct: 1.0
    min_trade_target_r: 1.5
    preferred_fee_tier: any
    use_futures: yes

  scaled:                       # $50,000+
    min_notional_buffer: 1.0
    max_concurrent_positions: 5
    risk_per_trade_pct: 0.5     # Lower % because more diversification
    min_trade_target_r: 1.5
    preferred_fee_tier: any
    use_futures: yes
```

**Implementation requirement:** A `CapitalProfileManager` service evaluates `current_equity` every hour and switches profile automatically. Profile changes are logged to audit_log and require Telegram notification.

### 2.3 The $100 Starting Strategy

**Phase: LIVE_MICRO with $100**

Recommended initial allocation:
- **70% ($70)** — Single funding rate arbitrage position OR single high-conviction directional trade
- **30% ($30)** — Reserved as "dry powder" for circuit-breaker recovery, not deployable

**Why funding arb is ideal for $100:**
- Market neutral (no directional risk)
- Returns 5–30% APR realistic on USDT pairs during normal funding periods
- Can compound without requiring increased complexity
- Teaches operational discipline without strategy risk

**Why NOT day trading at $100:**
- Even 20 trades/month at 0.1% taker each = 2% monthly drag from fees alone
- Need to win 60%+ at 1.5R just to break even after costs
- Mental cost / dollar at risk is highest at this size

### 2.4 Fee Optimization Strategy (Mandatory at $100)

```yaml
# Fee minimization protocol
fee_strategy:
  default_order_type: limit     # Limit orders = maker fees
  taker_fallback_after_seconds: 60  # If limit not filled in 60s, evaluate
  taker_fallback_only_if: signal_still_valid AND price_within_0.1pct
  use_bnb_for_fees: true        # 25% fee discount when paying in BNB
  maintain_bnb_balance: 5       # USD equivalent
  vip_tier_target: VIP1         # Aim for VIP1 within 6 months
```

**Implementation requirement:** Order placement must default to `LIMIT` orders. Market orders require explicit override flag and are logged as `FEE_PREMIUM_ORDER` for monitoring.

### 2.5 Capital Growth Plan (Compounding Discipline)

Auto-managed equity tiers — system automatically rebalances strategy mix as capital grows:

```yaml
# config/growth_plan.yaml
tiers:
  - equity_min: 50
    equity_max: 200
    name: "seed"
    strategy_mix:
      funding_arb: 70           # % of capital
      cash: 30
    monthly_target_pct: 3       # Conservative 3% target

  - equity_min: 200
    equity_max: 500
    name: "germination"
    strategy_mix:
      funding_arb: 50
      mid_cap_swing: 30
      cash: 20
    monthly_target_pct: 4

  - equity_min: 500
    equity_max: 2000
    name: "growth"
    strategy_mix:
      funding_arb: 30
      mid_cap_swing: 30
      regime_trend: 25
      cash: 15
    monthly_target_pct: 5

  - equity_min: 2000
    equity_max: 10000
    name: "diversification"
    strategy_mix:
      funding_arb: 25
      mid_cap_swing: 25
      regime_trend: 20
      microstructure: 15
      cash: 15
    monthly_target_pct: 6

  - equity_min: 10000
    name: "scaled"
    strategy_mix: dynamic_allocation  # AI-suggested rebalancing
    monthly_target_pct: 5
```

**The system enforces this. AI cannot deviate. User can only enable/disable strategies, not change allocation without explicit override + audit log entry.**

### 2.6 Withdrawal Discipline

A $100 account that grows must be **partially withdrawn** to lock in gains and maintain risk-of-ruin discipline:

```yaml
withdrawal_policy:
  enabled: true
  trigger: equity_doubles_from_starting
  withdraw_pct_of_profit: 30    # Take 30% of profit out, keep 70% for compounding
  withdraw_to_address: configured_at_setup  # Whitelisted address only
  cooldown_days: 30
```

**Note:** Bot does NOT have withdrawal API permission (that's a hard rule from Section 1). This is a notification system — bot alerts user "withdrawal milestone reached" and user manually withdraws via Binance UI with 2FA.

### 2.7 Small-Capital UI Considerations

Frontend must show:
- **Current Capital Profile** badge prominently (MICRO / SMALL / STANDARD / SCALED)
- **Min Trade Size** for current profile
- **Estimated Fee Drag %** based on current trade frequency
- **Effective Capital After Reserves** (equity minus circuit breaker reserve)
- **Next Profile Threshold** progress bar (gamification of discipline)

### 2.8 Strategies That Are FORBIDDEN at MICRO Profile

System must refuse to enable these strategies when `equity < $500`:

- ❌ Multi-leg basis trades (capital lockup too high)
- ❌ Grid trading (requires multiple concurrent orders)
- ❌ DCA strategies with > 3 levels (capital fragmentation)
- ❌ Futures with leverage > 2x (margin call risk too high)
- ❌ Strategies with average hold time < 1 hour (fee drag kills it)
- ❌ Pair trading (need 2x capital for matched positions)

System must show clear UI message: *"This strategy requires minimum $500 equity. Currently $X."*

---

## 3. System Architecture

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

## 4. Tech Stack

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

## 5. Repository Structure

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

## 6. Backend Services (Detailed)

### 6.1 `market_data_service`

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

### 6.2 `strategy_service`

**Responsibility:** Generate signals from market data using configured strategies.

**Components:**
- Strategy registry (load enabled strategies)
- Signal generator (per-strategy, per-symbol)
- Signal aggregator (merge multi-strategy signals with weights)
- Parameter manager (versioned, with rollback)
- Regime classifier (trending / mean-reverting / choppy / extreme)

**Output:** `Signal(symbol, side, conviction, source_strategy, regime, timestamp)`

### 6.3 `risk_service`

**See [Section 7](#7-risk-engine--layered-defense) for full detail.**

**Responsibility:** Veto unsafe orders, calculate position size, enforce limits.

**Always-On Checks:**
- Daily loss budget
- Max concurrent positions
- Correlation exposure
- Circuit breaker status

### 6.4 `execution_service`

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

### 6.5 `ai_service`

**See [Section 12](#12-ai-analyst--guardrailed-intelligence) for full detail.**

### 6.6 `notification_service`

**Responsibility:** Multi-channel alerting with severity routing.

**Channels:**
- **Telegram** (primary, low-latency)
- **Email** (digest, daily summary)
- **Webhook** (optional, for custom integrations)

**Severity Levels:**
- `INFO` — Daily summary, trade open/close (Telegram silent)
- `WARNING` — Strategy underperforming, latency anomaly (Telegram with sound)
- `CRITICAL` — Circuit breaker tripped, API down, dead-man switch fired (Telegram + Email + repeated until ack)

### 6.7 `recovery_service`

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

## 7. Risk Engine — Layered Defense

The Risk Engine is the **most important component** of the platform. It has veto power over all orders and runs continuously.

### 7.1 Pre-Trade Checks (Layer 1)

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

### 7.2 Position Sizing (Layer 2)

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

### 7.3 Drawdown De-Risking Ladder (Layer 3)

Equity-curve-aware automatic risk reduction:

| Drawdown from Peak | Action |
|---|---|
| 0% to -3% | Normal operation |
| -3% to -5% | Reduce position size by 30% |
| -5% to -8% | Reduce position size by 50% |
| -8% to -10% | Pause new entries, manage existing only |
| -10% to -15% | Flatten all, enter `LOCKED` mode |
| > -15% | `LOCKED` — requires manual review + acknowledgment |

### 7.4 Circuit Breakers (Layer 4)

Automated halts triggered by anomalies:

| Trigger | Action | Reset |
|---|---|---|
| API error rate > 10% over 5 min | Pause new orders | After 10 min healthy |
| Latency p99 > 1500ms over 1 min | Pause + alert | After 5 min healthy |
| Equity deviation > 3σ from expected curve | Flatten all + alert | Manual |
| Volume spike > 5× 1h average + price move > 3σ | Flatten longs OR shorts depending on direction | After volatility normalizes |
| Funding rate extreme (>1% per 8h) | Block new perp positions in that direction | Hourly re-check |
| Liquidation cascade detected (>$50M liquidations in 1 min) | Pause 15 min | Auto |

### 7.5 Hard Limits (Layer 5 — UNCHANGEABLE during runtime)

Set at boot, **cannot be modified by AI or runtime config:**

- Max position size per trade: 10% of equity
- Max total exposure: 100% of equity (no leverage stacking)
- Max leverage (futures): 3x
- Max daily loss: -5% (different from -2% budget; this is the absolute cap)
- Withdrawal: NEVER (API key shouldn't have it; verified at boot)

### 7.6 Risk Configuration File

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

## 8. Strategy Framework & Alpha Sources

### 8.1 Strategy Categories

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

### 8.2 Strategy Base Class

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

### 8.3 Strategy Versioning (Git-like)

Every strategy run is uniquely identified by `(strategy_name, version, parameter_hash)`. This allows:

- Exact replay of past trades
- Rollback to previous versions if live performance drops
- A/B testing between versions in paper trade
- Audit trail of which version made which decision

---

## 9. Defensible Edge Layer

> **This section addresses the most important question: "If others can build the same bot, why will mine still profit?"**
>
> Every retail bot running standard EMA/RSI/Breakout strategies will eventually break even after fees in efficient markets. This layer adds **structural advantages** that don't decay when copied.

### 9.1 Edge Sources Hierarchy

The platform must implement edge sources in this priority order:

| Priority | Edge Source | Decay Risk | Capital Required |
|---|---|---|---|
| 1 | **Funding Rate Arbitrage** | Low (structural) | $100+ |
| 2 | **Crowding Detector (anti-herd)** | Low (behavioral) | $200+ |
| 3 | **Mid-Cap Symbol Universe** | Medium | $500+ |
| 4 | **Regime State Machine** | Low (always relevant) | $200+ |
| 5 | **Alternative Data Layer** | Low (data moat) | $500+ |
| 6 | **Asian Session Edge** | Medium | $200+ |
| 7 | **Multi-Venue Arbitrage** | High (competitive) | $2,000+ |
| 8 | **DeFi Cross-Pollination** | Medium | $1,000+ |

### 9.2 Module: Funding Rate Arbitrage Engine

**Objective:** Capture predictable funding payments while maintaining market neutrality.

**How it works:**
- When perp funding rate is significantly positive (longs pay shorts), open `short perp + long spot` of equal notional
- Earn the funding payment every 8 hours
- Close when funding normalizes or convergence opportunity disappears
- Market neutral = no directional risk

**Implementation:**

```python
# backend/strategies/funding_arb/strategy.py (specification)

class FundingArbStrategy(Strategy):
    """
    Cash-and-carry on Binance perp + spot.
    
    Entry: funding_rate > entry_threshold AND
           spot_perp_basis < acceptable_basis
    Exit:  funding_rate < exit_threshold OR
           basis_diverges OR
           hold_period > max_hold
    
    Capital efficiency: Uses 50% of allocated capital on perp short,
                       50% on spot long, perfectly hedged.
    """
    
    parameter_schema = {
        "entry_funding_threshold_8h": 0.0005,    # 0.05% per 8h = ~5.5% APR floor
        "exit_funding_threshold_8h": 0.00005,    # Exit when funding cools
        "max_basis_at_entry": 0.002,             # Max 0.2% basis
        "min_volume_24h_usd": 50_000_000,        # Liquidity filter
        "max_hold_hours": 168,                    # 1 week max
        "preferred_pairs": ["BTC", "ETH", "SOL"], # Major pairs only initially
    }
    
    async def generate_signal(self, market_data, params):
        # Returns FundingArbSignal with both legs specified
        ...
```

**Database additions for funding arb:**

```sql
CREATE TABLE funding_arb_positions (
    id UUID PRIMARY KEY,
    symbol TEXT NOT NULL,
    perp_position_id UUID REFERENCES positions(id),
    spot_position_id UUID REFERENCES positions(id),
    entry_funding_rate NUMERIC,
    entry_basis NUMERIC,
    funding_collected_total NUMERIC DEFAULT 0,
    funding_collection_count INT DEFAULT 0,
    opened_at TIMESTAMPTZ NOT NULL,
    closed_at TIMESTAMPTZ
);
```

**UI: Dedicated Funding Arb dashboard tab showing:**
- Current funding rates across all monitored pairs (color-coded heatmap)
- Active arb positions with cumulative funding earned
- Historical funding rate chart per pair (30/90/365 days)
- Realized APR vs theoretical APR

**Codex Build Note:** Implement this BEFORE any directional strategy. It's the lowest-risk, highest-success-probability edge for $100 capital.

### 9.3 Module: Crowding Detector (Anti-Herd Engine)

**Objective:** Detect when retail bots are over-positioned in one direction and trade against them.

**Inputs (data sources required):**
- Funding rate (from Binance)
- Open Interest (from Binance + Coinglass API)
- Long/Short ratio (Binance position data)
- Liquidation events (Coinglass API or Hyblock)
- Social sentiment (LunarCrush API or Santiment — optional)

**Crowding Score Formula:**

```python
# backend/services/edge/crowding_detector.py

def calculate_crowding_score(symbol: str, lookback_hours: int = 24) -> CrowdingScore:
    """
    Returns score from -100 (extreme short crowding) to +100 (extreme long crowding).
    
    Components (each normalized to z-score over lookback):
    - Funding rate (40% weight)
    - OI growth rate (20% weight)
    - Long/short ratio extreme (20% weight)
    - Liquidation imbalance (10% weight)
    - Social sentiment z-score (10% weight, if available)
    
    Combined into single score with sign indicating direction.
    """
```

**Trade Rules:**

| Crowding Score | Action |
|---|---|
| `> +75` | High conviction SHORT setup (longs over-crowded) |
| `+50 to +75` | Watch for short entry signals from other strategies |
| `-50 to +50` | Neutral, no signal |
| `-75 to -50` | Watch for long entry signals |
| `< -75` | High conviction LONG setup (shorts over-crowded) |

**Important:** Crowding score is a **filter and conviction multiplier**, not a standalone signal generator. It increases or decreases conviction of other strategy signals. This prevents over-trading the indicator.

**Implementation requirement:**

```yaml
# config/edge/crowding.yaml
crowding_detector:
  enabled: true
  refresh_interval_seconds: 300       # Every 5 min
  data_sources:
    funding_rate: binance               # Built-in
    open_interest: binance              # Built-in
    long_short_ratio: binance           # Built-in (futures only)
    liquidations: coinglass             # Requires API key
    sentiment: lunarcrush               # Optional, requires API key
  weights:
    funding: 0.40
    oi_growth: 0.20
    ls_ratio: 0.20
    liquidations: 0.10
    sentiment: 0.10
  contrarian_thresholds:
    high_conviction: 75
    moderate: 50
```

### 9.4 Module: Symbol Universe Manager

**Objective:** Auto-discover trading pairs that are profitable for retail-size capital and avoid over-competitive mainstream pairs.

**The "Goldilocks Zone":**
- Volume too low → slippage destroys profits
- Volume too high → too competitive, edge eroded
- Sweet spot: Daily volume between $20M and $200M (mid-cap altcoins)

**Discovery Process:**

```python
# backend/services/edge/universe_manager.py

class SymbolUniverseManager:
    """
    Maintains rotating list of tradeable symbols.
    Refreshed daily.
    """
    
    async def refresh_universe(self):
        all_pairs = await binance.get_all_usdt_pairs()
        
        scored_pairs = []
        for pair in all_pairs:
            score = self.score_pair(pair)
            if score.passes_filters:
                scored_pairs.append(score)
        
        # Top N by composite score
        self.universe = sorted(scored_pairs, key=lambda x: x.score, reverse=True)[:50]
        
    def score_pair(self, pair) -> PairScore:
        """
        Filters (must pass ALL):
        - Daily volume: $20M - $200M
        - Listed on Binance > 90 days
        - Not in "blacklist" (memecoins, scams, restructured tokens)
        - Spread average < 0.05%
        - At least 30 days price history
        - Not currently in maintenance
        
        Score components:
        - Volatility regime stability (consistent ATR)
        - Liquidity depth at 0.5% from mid
        - Funding rate availability (perp exists)
        - Correlation to BTC (lower = more diversification value)
        """
```

**Maintenance Universe (smaller, always-monitored):**
- BTC, ETH, SOL — for funding arb baseline
- Top 5 from rotating universe — for directional strategies

**Blacklist enforcement:**

```yaml
# config/edge/blacklist.yaml
blacklisted_symbols:
  - reason: "memecoin_pump_dump_pattern"
    pairs: [PEPE, SHIB, DOGE, FLOKI, BONK]    # User can override
  - reason: "manipulated_thin_book"
    pairs: []   # Updated by automated detection
  - reason: "regulatory_concern"
    pairs: []
  - reason: "user_excluded"
    pairs: []
```

**UI:** Universe Management page showing current 50 tradeable symbols with their scores, history of additions/removals, and manual override controls.

### 9.5 Module: Regime State Machine

**Objective:** Explicit market regime classification with automatic strategy enable/disable.

**Six Regimes:**

| Regime | Detection | Active Strategies |
|---|---|---|
| `BULL_TRENDING` | BTC > 200MA + ADX>25 + low_vol | trend_following, breakout |
| `BEAR_TRENDING` | BTC < 200MA + ADX>25 + low_vol | short_trend, mean_reversion_short |
| `RANGE_LOW_VOL` | ADX<20 + ATR<percentile_30 | mean_reversion, vwap_revert |
| `RANGE_HIGH_VOL` | ADX<20 + ATR>percentile_70 | scalp_only, reduced_size |
| `CAPITULATION` | Drawdown >30% + extreme_fear | accumulate_dca, no_shorts |
| `EUPHORIA` | RSI>80 weekly + extreme_greed | distribute, no_longs |

**Implementation:**

```python
# backend/services/edge/regime_classifier.py

class RegimeClassifier:
    async def classify(self) -> Regime:
        """
        Multi-timeframe analysis:
        - Daily: trend direction (200MA position, ADX)
        - 4H: volatility (ATR percentile)
        - 1H: momentum (RSI)
        - On-chain: F&G index, exchange flows (when available)
        
        Stickiness: Regime change requires 2 consecutive classifications
        to prevent whipsaw.
        """
        
    async def on_regime_change(self, old: Regime, new: Regime):
        """
        - Disable strategies not allowed in new regime
        - Reduce position sizes during transition (1 hour grace period)
        - Alert via Telegram with explanation
        - Log to regime_history table
        """
```

**Database:**

```sql
CREATE TABLE regime_history (
    id UUID PRIMARY KEY,
    regime TEXT NOT NULL,
    confidence NUMERIC NOT NULL,
    classified_at TIMESTAMPTZ NOT NULL,
    indicators JSONB NOT NULL,    -- snapshot of all classification inputs
    duration_hours NUMERIC        -- filled in when next regime starts
);

CREATE TABLE strategy_regime_mapping (
    strategy_id UUID REFERENCES strategies(id),
    regime TEXT NOT NULL,
    enabled BOOLEAN NOT NULL,
    size_multiplier NUMERIC DEFAULT 1.0,
    PRIMARY KEY (strategy_id, regime)
);
```

**UI:** Regime indicator badge on every page (top bar). Dedicated Regime page showing:
- Current regime with confidence score
- Historical regime timeline (last 90 days)
- Performance per regime per strategy
- Pending regime change alerts

### 9.6 Module: Alternative Data Layer

**Objective:** Provide data signals that 99% of retail bots don't have access to.

**Data Sources (with monthly cost estimates):**

| Source | Provides | Monthly Cost | Priority |
|---|---|---|---|
| Coinglass API | Liquidations, OI per exchange | Free tier OK | Required |
| LunarCrush | Social sentiment, galaxy score | $24-99 | Tier 2 |
| Santiment | On-chain sentiment, network | $49-199 | Tier 2 |
| Glassnode | On-chain metrics, whale flows | $39-799 | Tier 3 |
| CryptoQuant | Exchange flows, miner data | $99-999 | Tier 3 |
| Nansen | Wallet labels, smart money | $150-1800 | Tier 4 (advanced) |

**Implementation Pattern (modular, capital-aware):**

```python
# backend/services/data/alt_data_manager.py

class AltDataManager:
    """
    Modular data layer. Each provider is optional and gracefully
    degrades if not configured.
    
    Cost-aware: Only enables paid sources when capital justifies it.
    """
    
    def __init__(self, capital: Decimal, config: AltDataConfig):
        self.providers = []
        
        # Always enabled (free or near-free)
        self.providers.append(BinanceDataProvider())
        self.providers.append(CoinglassProvider(config.coinglass_key))
        
        # Tier 2: Enable when capital > $500
        if capital >= 500 and config.lunarcrush_key:
            self.providers.append(LunarCrushProvider(config.lunarcrush_key))
        
        # Tier 3: Enable when capital > $2000
        if capital >= 2000:
            if config.santiment_key:
                self.providers.append(SantimentProvider(config.santiment_key))
            if config.glassnode_key:
                self.providers.append(GlassnodeProvider(config.glassnode_key))
        
        # Higher tiers...
```

**Configuration:**

```yaml
# config/edge/alt_data.yaml
alt_data:
  cache_ttl_seconds: 300
  rate_limits:
    coinglass: 30                # per minute
    lunarcrush: 10
    santiment: 60
  fallback_behavior: graceful   # Continue if API down
  
  signals_using_alt_data:
    - whale_accumulation         # Glassnode whales
    - social_extreme            # LunarCrush sentiment
    - exchange_outflow_spike    # CryptoQuant
    - smart_money_follow        # Nansen labels
```

### 9.7 Module: Asian Session Edge

**Objective:** Exploit time-zone information advantages.

**Key insights:**
- Asian session (00:00-08:00 UTC) often has different liquidity profile than US/EU
- Indonesian/Korean/Japanese exchanges sometimes price-discover before global exchanges react
- Listing announcements on Asian exchanges (Indodax, Upbit, Bithumb) can predate price moves on Binance

**Implementation:**

```python
# backend/services/edge/asian_session_monitor.py

class AsianSessionMonitor:
    """
    Tracks Asian-exchange-specific signals.
    
    Watches:
    - Upbit (Korea) listing announcements
    - Binance Korea/Asia volume spikes
    - Asian-hours BTC/ETH dominance shifts
    - JPY/KRW pair flows on aggregators
    """
    
    asian_active_hours_utc = (0, 8)   # 00:00 - 08:00 UTC
    
    async def check_asian_listing_announcements(self):
        """Poll Upbit, Bithumb announcements every 60s during active hours"""
        
    async def detect_asian_session_anomaly(self):
        """
        Volume in Asian session > 2x recent average AND
        price move > 1.5 ATR within 1 hour →
        publish AsianSessionAlert event
        """
```

**Configuration:**

```yaml
# config/edge/asian_session.yaml
asian_session_edge:
  enabled: true
  active_utc_hours: [0, 8]
  monitor_exchanges:
    - upbit                        # Korea
    - bithumb                      # Korea
    - bitflyer                     # Japan
    - indodax                      # Indonesia (your local edge)
  signals_emitted:
    - asian_listing_announcement
    - asian_volume_anomaly
    - asian_basis_divergence
```

**Special note:** Since user is based in Indonesia, the system should give extra weight to Indodax/Tokocrypto signals — these can sometimes lead Binance price action by minutes during Asian hours.

### 9.8 Module: Strategy Retirement Protocol

**Objective:** Kill underperforming strategies based on objective criteria, not emotion.

**Retirement Triggers (any one triggers review):**

```yaml
# config/edge/retirement_policy.yaml
strategy_retirement:
  auto_review_triggers:
    - condition: "live_sharpe_30d < 0 for 14 consecutive days"
      action: pause_and_review
    - condition: "live_drawdown > backtest_max_drawdown * 1.5"
      action: pause_and_review
    - condition: "divergence_score > 2.5 for 7 days"
      action: pause_and_review
    - condition: "win_rate_30d < backtest_win_rate * 0.6"
      action: pause_and_review
    - condition: "consecutive_losses > 8"
      action: immediate_pause
    - condition: "regime_unchanged_30d AND zero_signals_30d"
      action: pause_dormant
  
  retirement_decision_window_days: 7   # User has 7 days to review paused strategy
  auto_retire_after_days: 30           # If no decision, auto-retire
  
  required_for_resume:
    - new_backtest_passing_promotion_criteria
    - paper_trade_minimum_days: 14
    - user_acknowledgment_of_changes
```

**Implementation requirement:** This runs as a daily cron job. Results displayed in UI with one-click "Acknowledge & Retire" or "Modify & Re-validate" buttons.

### 9.9 Module: Pre-Commitment Device

**Objective:** Prevent emotional intervention during normal-but-painful drawdown periods.

**The problem:** A statistically expected drawdown of -10% can feel like the world is ending. Many traders kill profitable strategies during these expected drawdowns.

**The solution:** UI features that make destructive manual override deliberately difficult during predetermined risk states.

**Pre-Commitment Rules (set at strategy promotion to LIVE):**

```yaml
# config/edge/precommitment.yaml
precommitment:
  enabled: true
  
  during_drawdown:
    threshold_pct: -5
    require_cooldown_minutes: 60       # 60 min cool-off before any change
    require_typed_phrase: true         # Type "I ACCEPT EXPECTED DRAWDOWN"
    show_backtest_dd_comparison: true  # Display: "Current DD is within backtest 70th percentile"
    
  during_loss_streak:
    threshold_consecutive_losses: 5
    require_journal_entry: true        # Must write journal entry before disabling
    require_cooldown_minutes: 30
    
  high_friction_actions:               # These actions get extra friction
    - close_all_positions
    - disable_strategy_in_drawdown
    - increase_risk_after_losses
    - withdraw_during_active_position
```

**UI Implementation:**

When user attempts a high-friction action during a flagged condition, modal shows:
1. Backtest expected drawdown distribution (visual)
2. "Your current drawdown is at the X percentile of expected outcomes"
3. Cooldown timer
4. Required typed phrase
5. Optional: AI Analyst opinion ("Based on 200 historical drawdowns of this magnitude, X% recovered within 30 days")

**Critical:** Pre-commitment can be globally disabled in `Settings > Advanced > Disable Pre-Commitment` with a 24-hour cooldown to prevent disabling-then-acting-emotionally.

### 9.10 Module: Multi-Venue Connector (Phase 6+)

**Objective:** When capital justifies it ($2,000+), expand beyond Binance for arbitrage opportunities.

**Architecture:**

```python
# backend/services/venues/base.py

class VenueAdapter(ABC):
    """
    Abstract adapter for any exchange.
    Implementations: BinanceAdapter, OKXAdapter, BybitAdapter, etc.
    """
    
    @abstractmethod
    async def get_orderbook(self, symbol: str): ...
    
    @abstractmethod
    async def place_order(self, order: Order): ...
    
    # ... etc

class MultiVenueRouter:
    """
    Routes orders to best execution venue.
    Manages cross-venue strategies (basis arb, latency arb).
    """
```

**Capital Tier Activation:**

```yaml
# config/edge/multi_venue.yaml
multi_venue:
  enabled_at_capital: 2000
  
  venues:
    binance:
      always_enabled: true
    okx:
      enable_at_capital: 2000
    bybit:
      enable_at_capital: 5000
    deribit:
      enable_at_capital: 10000   # Options markets
  
  strategies_unlocked:
    cross_venue_basis_arb: 2000
    funding_rate_optimization_arb: 5000   # Choose best funding venue
    triangular_arb: 10000
```

**Note:** Multi-venue is HIGH operational complexity. Only justified after MICRO-tier strategies prove profitable for 6+ months.

### 9.11 Module: DeFi Cross-Pollination (Optional, Capital > $1000)

**Objective:** Bridge CEX bot insights with DeFi opportunities (Solana DLMM, Ethereum DEX).

**This module integrates with:**
- Solana DLMM positions (user's existing capability)
- Meteora pools
- Hyperliquid (decentralized perps)

**Use cases:**
1. **Funding rate arbitrage on Hyperliquid** when Binance funding extreme
2. **DLMM position sizing informed by CEX volatility data**
3. **Cross-venue hedging:** long Solana spot on CEX + short on DEX perps when basis dislocates

**Implementation:** This is a dedicated `defi_bridge_service` that exposes DLMM and DEX state to the main bot. NOT in initial implementation — defer to Phase 7+.

```yaml
# config/edge/defi_bridge.yaml (placeholder for future)
defi_bridge:
  enabled: false                  # Default off, enable manually
  enable_at_capital: 1000
  integrations:
    solana_dlmm: false
    hyperliquid: false
    ethereum_uniswap: false
```

### 9.12 Edge Layer — Integration Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                       EDGE LAYER                                │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Funding Arb  │  │ Crowding     │  │ Symbol Universe      │   │
│  │ Engine       │  │ Detector     │  │ Manager              │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────────┘   │
│         │                 │                   │                 │
│  ┌──────▼─────────────────▼───────────────────▼─────────────┐   │
│  │           REGIME STATE MACHINE                           │   │
│  │  (orchestrates which strategies are active per regime)   │   │
│  └─────────────────────────┬────────────────────────────────┘   │
│                            │                                    │
│  ┌─────────────────────────▼────────────────────────────────┐   │
│  │          ALTERNATIVE DATA LAYER                          │   │
│  │  Coinglass │ LunarCrush │ Santiment │ Glassnode (cap-tier)│  │
│  └─────────────────────────┬────────────────────────────────┘   │
│                            │                                    │
│  ┌──────────────┐  ┌──────▼───────┐  ┌──────────────────────┐   │
│  │ Asian Session│  │ Pre-Commit   │  │ Strategy Retirement  │   │
│  │ Monitor      │  │ Device       │  │ Protocol             │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
              [Strategy Service consumes signals]
                            │
                            ▼
                   [Risk Engine veto]
                            │
                            ▼
                  [Execution]
```

### 9.13 Edge Layer Implementation Order (Critical for Codex/Claude Code)

Build in this exact order. Each module must be completed and tested before next:

1. **Symbol Universe Manager** (Phase 2 of roadmap) — Even backtest needs proper universe
2. **Regime State Machine** (Phase 2) — Required for strategy activation logic
3. **Funding Rate Arb Engine** (Phase 3) — First profitable strategy at $100
4. **Crowding Detector** (Phase 3) — Conviction multiplier
5. **Strategy Retirement Protocol** (Phase 4) — Required before live
6. **Pre-Commitment Device** (Phase 4) — Required before live
7. **Asian Session Monitor** (Phase 5) — Bonus edge once stable
8. **Alternative Data Layer** (Phase 5+) — Enable per capital tier
9. **Multi-Venue Connector** (Phase 6+) — Only when capital > $2000
10. **DeFi Cross-Pollination** (Phase 7+) — Advanced, optional

---

## 10. Backtest & Validation Pipeline

### 10.1 Backtest Engine Requirements

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

### 10.2 Validation Pipeline (MANDATORY before paper trade)

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

### 10.3 Live vs Backtest Divergence Tracker

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

## 11. Execution Quality & Cost Accounting

### 11.1 Execution Quality Monitor

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

### 11.2 Cost Accounting (Net vs Gross PnL)

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

## 12. AI Analyst — Guardrailed Intelligence

### 12.1 AI's Role (Permitted)

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

### 12.2 AI's Role (FORBIDDEN — Hard-Coded Restrictions)

❌ **Never directly modifies live parameters**
❌ **Never deploys strategies to live mode**
❌ **Never overrides risk engine veto**
❌ **Never adjusts risk policy hard limits**
❌ **Never executes orders directly**
❌ **Never has Binance API credentials**

These are enforced at the architectural level — the AI service has no write access to risk_policy, no order execution permissions, and no live strategy deployment endpoint.

### 12.3 The AI Suggestion Pipeline

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

### 12.4 Prompt Templates (Versioned)

Stored in `prompts/` directory, versioned with the codebase:

- `analyst_system.md` — System prompt defining role, constraints, output format
- `regime_classify.md` — Regime classification with structured output
- `losing_streak_explain.md` — Diagnosis prompt
- `parameter_review.md` — Critique proposed parameter changes
- `strategy_explain.md` — Generate strategy explanation for journal

### 12.5 Trade Journal Auto-Tagging

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

## 13. Frontend — Premium Dashboard

### 13.1 Design System

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

### 13.2 Pages

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

### 13.3 Real-time Architecture

- WebSocket connection to backend for live data
- Optimistic updates with rollback on error
- Toast notifications for important events
- Sound alerts (configurable) for CRITICAL events

---

## 14. Database Schema

### 14.1 Core Tables

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

### 14.2 Indexes (Performance Critical)

```sql
CREATE INDEX idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX idx_signals_strategy_symbol ON signals(strategy_id, symbol, timestamp DESC);
CREATE INDEX idx_orders_status ON orders(status) WHERE status IN ('submitted', 'partially_filled');
CREATE INDEX idx_positions_open ON positions(symbol) WHERE closed_at IS NULL;
CREATE INDEX idx_audit_log_entity ON audit_log(entity, entity_id, timestamp DESC);
```

---

## 15. Security & Secrets Management

### 15.1 API Key Hygiene

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

### 15.2 Secrets Storage

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

### 15.3 Authentication

- **Web UI:** Email + password (Argon2id) + TOTP 2FA mandatory
- **API:** JWT short-lived (15 min) + refresh token (7 days)
- **Session management:** Redis with sliding expiration
- **Rate limiting:** 100 req/min per user, 10 login attempts per IP per hour

### 15.4 Network Security

- VPS firewall (ufw): allow only 22 (SSH), 443 (HTTPS), 80 (HTTPS redirect)
- SSH: key-only auth, no root login, fail2ban enabled
- TLS: Let's Encrypt, auto-renew, A+ on SSL Labs
- Cloudflare (optional): DDoS protection, hide origin IP

### 15.5 Audit Trail Requirements

Every state-changing action is logged with:
- Who (user_id + IP)
- What (action + entity)
- When (UTC timestamp)
- Before/After state (for diffs)

Audit logs are **append-only** at the application layer. For tamper-evidence, consider periodic snapshots to immutable storage (S3 Object Lock or similar).

---

## 16. Observability & Disaster Recovery

### 16.1 Metrics (Prometheus)

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

### 16.2 Dashboards (Grafana)

Pre-built dashboards in `ops/grafana/dashboards/`:
- **Operations Overview** — system health at a glance
- **Trading Performance** — PnL, win rate, by strategy
- **Risk Engine** — vetoes, breakers, drawdown
- **Execution Quality** — slippage, fill rates, latency
- **AI Costs** — token usage, cost per analysis

### 16.3 Logging

- **Structured (JSON) logs** via structlog
- Shipped to **Loki** for aggregation
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Sensitive data redacted automatically (API keys, secrets)
- Retention: 30 days hot, 1 year cold (S3-compatible storage)

### 16.4 External Monitoring

- **Healthchecks.io** ping every 30s — alerts if missed > 2 min
- **UptimeRobot** monitor on `/api/health` every 5 min
- **Telegram heartbeat** every 4 hours during quiet periods, immediate on critical events

### 16.5 Disaster Recovery

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

## 17. Deployment & Infrastructure

### 17.1 VPS Specifications

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

### 17.2 Docker Compose (Production)

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

### 17.3 Environment Variables

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

### 17.4 Deploy Procedure

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

## 18. Development Roadmap & Promotion Gates

> **This roadmap is designed for a $100 starting capital trader. Each phase has explicit deliverables, gate criteria, and edge module integration. Codex/Claude Code MUST complete each phase fully before moving to the next.**

### Phase 0: Foundation (Week 1-2)

**Goal:** Working skeleton — empty but functional system.

- [ ] Repository scaffolding per Section 5
- [ ] Docker Compose dev environment (postgres + redis + backend + frontend)
- [ ] Database schema + Alembic migrations (all tables from Section 14)
- [ ] **Capital Profile Manager** (Section 2.2) — reads `current_equity`, returns active profile
- [ ] Authentication (email + password Argon2id + TOTP 2FA)
- [ ] Frontend shell (sidebar, top bar, dark theme tokens from Section 13.1)
- [ ] CI/CD (GitHub Actions: lint + test + type-check)
- [ ] Logging (structlog) + Prometheus instrumentation skeleton
- [ ] Telegram notification service skeleton

**Gate to Phase 1:**
- `make test` green
- All 9 page routes render placeholder content
- User can register, enable 2FA, login
- Capital Profile Manager returns "MICRO" for $100 simulated balance
- Telegram test message delivers

---

### Phase 1: Market Data + Edge Foundation (Week 3-5)

**Goal:** Real-time data flowing + first two edge modules.

**Market data:**
- [ ] Binance WS connection (public streams) with auto-reconnect
- [ ] Candle aggregation (1m → 5m → 1h → 4h → 1d)
- [ ] Orderbook sync (snapshot + delta)
- [ ] Funding rate poller (every 1m for monitored symbols)
- [ ] Open Interest poller (every 1m)
- [ ] Historical data fetcher (for backtest)

**Edge modules (per Section 9.13 order):**
- [ ] **Symbol Universe Manager** (Section 9.4) — daily refresh, blacklist enforcement
- [ ] **Regime State Machine** (Section 9.5) — six-regime classifier with stickiness logic
- [ ] Regime indicator badge in top bar
- [ ] Universe Management UI page

**Gate to Phase 2:**
- Real-time data flows for 24h with no memory leaks
- Universe Manager correctly identifies 50 mid-cap pairs in $20M-$200M volume zone
- Regime State Machine correctly classifies last 90 days of BTC into the six regimes
- Regime change events appear in Telegram

---

### Phase 2: Backtest Engine + Validation (Week 6-9)

**Goal:** Bulletproof backtest pipeline that prevents overfit strategies from advancing.

**Backtest core:**
- [ ] vectorbt integration (primary)
- [ ] backtesting.py integration (cross-validation)
- [ ] Walk-forward analysis with rolling windows
- [ ] Monte Carlo trade-shuffle (5000 iterations)
- [ ] Parameter sensitivity heatmap generator
- [ ] Standard metrics: ROI, Sharpe, Sortino, Calmar, Max DD, PF, Win Rate
- [ ] **Deflated Sharpe Ratio** computation
- [ ] Cost-shock test (re-run with fees × 1.5 + slippage × 2)

**Strategies (baseline only, NOT for live trading):**
- [ ] Strategy base class (Section 8.2)
- [ ] EMA Momentum (Category A)
- [ ] VWAP Reversion (Category A)
- [ ] RSI Bounce (Category A)
- [ ] Breakout Volume (Category A)

**Backtest UI:**
- [ ] Setup form with all inputs (Section 13.2 Page 4)
- [ ] Run types: single, walk-forward, parameter sweep, MC robustness
- [ ] Results visualization (equity curve, MC distribution, sensitivity heatmap)
- [ ] "Promote to Paper Trade" button (locked unless ALL gate criteria met)

**Gate to Phase 3:**
- At least one baseline strategy passes ALL promotion criteria from Section 10.2 on real BTC/ETH data
- Backtest shows realistic costs (fees + slippage modeled correctly)
- UI clearly displays which criteria a strategy passed/failed

---

### Phase 3: Risk Engine + Funding Arb (Week 10-13)

**Goal:** Production risk engine + first profitable strategy for $100 capital.

**Risk Engine (per Section 7):**
- [ ] Pre-Trade Checks (Layer 1) — all 7 checks
- [ ] Position Sizing (Layer 2) — ATR-based with regime + Kelly + correlation factors
- [ ] Drawdown De-Risking Ladder (Layer 3)
- [ ] Circuit Breakers (Layer 4) — all 6 triggers
- [ ] Hard Limits (Layer 5) — runtime-immutable enforcement
- [ ] Risk Configuration loader from `config/risk_policy.yaml`
- [ ] Risk Command Center UI (Section 13.2 Page 5)

**Edge Modules:**
- [ ] **Funding Rate Arbitrage Engine** (Section 9.2) — first live-tradeable strategy
- [ ] Funding Arb dedicated UI tab
- [ ] **Crowding Detector** (Section 9.3) — Coinglass API integration
- [ ] Crowding score conviction multiplier hook

**Paper Trading + Execution Quality:**
- [ ] Paper trading mode (simulated fills with realistic slippage model)
- [ ] Execution Quality Monitor (Section 11.1)
- [ ] Cost Accounting (Section 11.2) — every PnL display NET vs GROSS labeled
- [ ] Live vs Backtest Divergence Tracker (Section 10.3)

**Gate to Phase 4:**
- Funding Arb strategy runs in paper mode for 30+ days
- Live paper metrics within 20% of backtest expectations
- Risk engine successfully blocks at least 5 unsafe order attempts during testing
- Circuit breakers tested manually (simulate API failure, verify pause)
- Cost accounting shows net PnL accurately reflecting all costs

---

### Phase 4: AI Analyst + Pre-Live Hardening (Week 14-16)

**Goal:** AI guardrails + retirement protocol + pre-commitment device. Everything needed before risking real money.

**AI Analyst (Section 12):**
- [ ] OpenRouter integration with daily cost cap
- [ ] AI Analyst page (Section 13.2 Page 6)
- [ ] Daily briefing automation (regime + portfolio summary)
- [ ] Trade journal auto-tagging
- [ ] Suggestion queue with approval workflow
- [ ] Diagnosis workflows (paste trade ID → AI explanation)
- [ ] Hard-coded forbidden actions enforced architecturally (Section 12.2)

**Edge Modules:**
- [ ] **Strategy Retirement Protocol** (Section 9.8) — daily cron + UI review
- [ ] **Pre-Commitment Device** (Section 9.9) — friction modals during drawdown

**Trade Journal:**
- [ ] Trade Journal page (Section 13.2 Page 7)
- [ ] AI tag display + filtering
- [ ] Manual notes field

**Gate to Phase 5:**
- AI provides meaningful daily briefings for 14 consecutive days
- Suggestion → Backtest → Approval → Paper pipeline tested end-to-end
- Pre-commitment modal triggers correctly when drawdown threshold breached (test with paper trading)
- Strategy Retirement Protocol auto-flags a deliberately broken strategy

---

### Phase 5: LIVE_MICRO with $100 (Week 17+)

**Goal:** First real money. Maximum caution.

**Pre-deployment hardening:**
- [ ] Security audit checklist:
  - [ ] Binance API key has TRADING ONLY permission (verified at boot)
  - [ ] IP whitelist active on Binance
  - [ ] 2FA mandatory on web UI
  - [ ] All secrets in encrypted store, not in `.env`
  - [ ] Audit log fully wired
- [ ] Disaster recovery drills:
  - [ ] Kill VPS during open paper position → verify dead-man switch flattens
  - [ ] Corrupt database → verify restore procedure works
  - [ ] Force API timeout → verify circuit breaker trips
  - [ ] Restart bot mid-position → verify state recovery from Binance
- [ ] Backup procedure tested (DB dump → S3 → restore on fresh VPS)
- [ ] Production deployment per Section 17

**Live deployment with $100:**
- [ ] Capital Profile = MICRO enforced
- [ ] Only Funding Arb strategy enabled (single strategy first)
- [ ] Max 1 concurrent position
- [ ] Risk per trade: 2% of equity ($2)
- [ ] Drawdown ladder strict enforcement
- [ ] Daily Telegram heartbeat + summary

**Gate to Phase 6:**
- **Minimum 3 months of LIVE_MICRO with no critical incidents**
- Funding Arb produces positive net PnL for 90 days
- Live performance matches paper trade expectations within ±25%
- Equity has grown to at least $200 (graduates to "germination" tier)
- Zero security incidents (no API key leaks, no unauthorized access attempts)

---

### Phase 6: Strategy Diversification (Month 6+)

**Goal:** Add directional strategies as capital grows. Layer in mid-cap and Asian session edge.

**Trigger conditions:** Equity ≥ $200 AND Phase 5 gate passed.

**New strategies (added one at a time, validated independently):**
- [ ] Mid-Cap Swing strategy (uses Symbol Universe Manager output)
- [ ] Regime-aware trend follower (uses Regime State Machine)
- [ ] Mean reversion on RANGE_LOW_VOL regime

**Edge Modules:**
- [ ] **Asian Session Monitor** (Section 9.7) — Indodax/Upbit/Bithumb feeds
- [ ] **Alternative Data Layer** (Section 9.6) — Tier 2 sources when capital ≥ $500

**Capital management:**
- [ ] Auto-rebalancing per `growth_plan.yaml` tier
- [ ] Withdrawal milestone notifications
- [ ] Strategy mix dashboard

**Gate to Phase 7:**
- Equity ≥ $1,000 with consistent monthly profit
- 3+ strategies running concurrently without correlation issues
- All edge modules contributing measurable signal lift

---

### Phase 7: Multi-Venue + Advanced Edges (Month 12+)

**Goal:** Expand beyond Binance once $2,000+ justifies operational complexity.

**Trigger conditions:** Equity ≥ $2,000 AND Phase 6 gate passed.

- [ ] **Multi-Venue Connector** (Section 9.10) — OKX, Bybit adapters
- [ ] Cross-venue basis arbitrage strategy
- [ ] **Microstructure strategies**: orderbook imbalance, liquidation cascade
- [ ] Multi-symbol portfolio optimization
- [ ] Tier 3 alternative data sources (Glassnode, CryptoQuant)

**Gate to Phase 8 (Optional):**
- Equity ≥ $10,000 with documented track record
- 6+ months of multi-venue operations stable

---

### Phase 8 (Optional): DeFi Cross-Pollination (Month 18+)

**Trigger conditions:** Equity ≥ $1,000 in CEX bot AND user has separate DeFi capital.

- [ ] **DeFi Bridge Service** (Section 9.11) — read-only initially
- [ ] Solana DLMM integration (user's existing system)
- [ ] Hyperliquid funding arb cross-venue
- [ ] CEX-DEX basis trade strategies

---

### Phase 9 (Optional): Multi-Tenant SaaS (Year 2+)

**Only if proven profitable for personal use across multiple market regimes.**

This phase has fundamentally different security and compliance requirements. **Do NOT combine with personal-use development.**

- [ ] Multi-user data isolation
- [ ] Per-user API key encryption (envelope encryption)
- [ ] Billing integration (Stripe)
- [ ] KYC/regulatory compliance review (jurisdiction-specific)
- [ ] Customer support infrastructure
- [ ] SLA monitoring + multi-region failover

---

### Capital-Tier-Aware Phase Summary

| Phase | Min Capital | Strategies Active | Edge Modules Active |
|---|---|---|---|
| 0–4 | $0 (paper) | None / Backtest only | Universe + Regime |
| 5 | $100 | Funding Arb only | + Crowding + Retirement + Pre-Commit |
| 6 | $200 | + Mid-Cap Swing, Regime Trend | + Asian Session + Alt Data Tier 2 |
| 7 | $2,000 | + Microstructure, Cross-Venue | + Multi-Venue + Alt Data Tier 3 |
| 8 | $1,000 (CEX) + DeFi capital | + DeFi bridge strategies | + DeFi Bridge |
| 9 | N/A (different track) | SaaS deployment | All |

---

## 19. Codex / Claude Code Build Instructions

> **This section is the entry point for AI coding agents (Codex, Claude Code) building this system. Read it carefully and follow exactly.**

### 19.1 Master Prompt (paste this when starting any build session)

```
You are building AI-Quant-Binance-Bot v2.1, a production-grade crypto trading
platform optimized for small-capital traders ($100 starting balance).

═══ ABSOLUTE RULES (violation = stop and ask) ═══

1. SMALL CAPITAL FIRST — every implementation choice must work for $100 equity.
   Check Section 2 (Small Capital Reality) before writing trading logic.

2. PHASE ORDER IS LAW — do not skip ahead. Each phase has gate criteria that
   must be met before proceeding. See Section 18.

3. EDGE BEFORE STRATEGIES — implement Edge Layer modules (Section 9) in the
   order specified in Section 9.13. Funding Arb is the FIRST live strategy,
   not EMA/RSI/Breakout.

4. NET PNL ONLY — every PnL number displayed in UI is net of fees, funding,
   and slippage. Always label "Gross" explicitly when shown separately.

5. RISK ENGINE IS SUPREME — it has veto power over every order. Never bypass.
   See Section 7 for all 5 layers.

6. AI ANALYST FORBIDDEN ACTIONS — see Section 12.2. Hard-code these
   restrictions architecturally, NOT just in prompts. The AI service must
   not have credentials or write access to live config.

7. IDEMPOTENCY KEYS — every order has a UUID idempotency key. No exceptions.

8. BINANCE IS TRUTH — local position state must reconcile to Binance every
   5 seconds. On boot, always sync from Binance first.

9. SECRETS DISCIPLINE — never in code, never in JWT, never in localStorage.
   Encrypted at rest, redacted in logs.

10. ASYNC THROUGHOUT — backend uses async/await. No blocking I/O in handlers.

11. DECIMAL FOR MONEY — never use float for money. Python: `Decimal`.
    JavaScript: `decimal.js` or string-based math.

12. TESTS WITH FEATURES — no new feature merges without tests. Risk engine
    must have ≥80% coverage.

═══ CODE STYLE ═══

Python: black + ruff + mypy strict, async-first, Pydantic v2 for validation
TypeScript: strict mode, ESLint, Prettier, no `any` without justification
Commits: Conventional Commits (feat:, fix:, docs:, refactor:, test:)
Branching: feature branches, PR with CI green required for merge

═══ ASK BEFORE ═══

- Adding any new external dependency
- Deviating from the blueprint architecture
- Changing risk_policy.yaml hard limits
- Modifying capital_profiles.yaml thresholds
- Changing AI Analyst forbidden actions list

═══ OUTPUT BEHAVIOR ═══

- Generate files incrementally with explanations
- After each major component: run tests and report results
- Show planned directory structure before creating files
- At end of each phase: provide a checklist of gate criteria met

═══ STARTING POINT ═══

Begin with Phase 0 (Section 18). Confirm Phase 0 completion before
proceeding to Phase 1. Use the per-phase prompts in Section 19.2.
```

### 19.2 Per-Phase Prompts

Save these in `prompts/build/phase-{N}.md`. Feed them to the AI sequentially after master prompt.

#### Phase 0 Prompt — Foundation

```
Implement Phase 0 (Foundation) of AI-Quant-Binance-Bot v2.1.

Reference: Blueprint Section 18 (Roadmap), Section 5 (Repo Structure),
Section 14 (Database Schema), Section 13.1 (Design System).

Tasks:
1. Create repository structure exactly per Section 5.
2. Docker Compose dev environment: postgres-15 (with TimescaleDB), redis-7,
   backend (FastAPI), frontend (Next.js 14 App Router).
3. Database schema from Section 14 with Alembic migrations. Use TimescaleDB
   hypertable for equity_snapshots.
4. Capital Profile Manager service (Section 2.2). Reads current_equity,
   loads config/capital_profiles.yaml, returns active profile. Expose
   GET /api/capital-profile endpoint.
5. Authentication: email + Argon2id password + TOTP 2FA. JWT 15min + refresh
   7d. Implement per Section 15.3.
6. Frontend shell: sidebar with all 9 routes, top command bar, dark theme
   using EXACT color tokens from Section 13.1 (use OKLCH values, not RGB).
7. CI/CD GitHub Actions: lint + test + mypy + tsc on every PR.
8. structlog with JSON output + redaction filter for secrets.
9. Prometheus client with /metrics endpoint (empty metrics OK at this stage).
10. Telegram notification skeleton: send_message() function + test endpoint.

Do NOT yet implement: market data, strategies, trading, AI, edge modules.

Deliverables:
- `docker compose up` brings up working but empty system
- User registers → enables 2FA → logs in successfully
- All 9 page routes render (placeholder content acceptable)
- GET /api/capital-profile returns "MICRO" for $100 simulated equity
- Telegram test message delivers
- `make test` passes
- README.md with full setup instructions

When done: run gate criteria checklist from Section 18 Phase 0.
```

#### Phase 1 Prompt — Market Data + Edge Foundation

```
Implement Phase 1 of AI-Quant-Binance-Bot v2.1.

Reference: Section 18 Phase 1, Section 6.1 (market_data_service),
Section 9.4 (Symbol Universe), Section 9.5 (Regime State Machine).

Tasks:
A. Market Data Service (Section 6.1):
   - Binance WS connection with auto-reconnect + exponential backoff
   - Candle aggregator: 1m → 5m, 15m, 1h, 4h, 1d rollups
   - Orderbook snapshot + delta sync
   - Funding rate poller (every 60s for monitored symbols)
   - Open Interest poller (every 60s)
   - Historical data fetcher with gap detection
   - Failure modes: WS disconnect → reconnect + alert,
     gap detected → REST fill,
     Binance maintenance → enter FROZEN state

B. Symbol Universe Manager (Section 9.4):
   - Daily refresh job (APScheduler)
   - Filters: $20M-$200M daily volume, listed >90d, not blacklisted
   - Score: volatility stability, liquidity depth at 0.5%, BTC correlation
   - Persist top 50 to DB
   - UI page: Universe Management with score breakdown + manual override

C. Regime State Machine (Section 9.5):
   - Six regimes: BULL_TRENDING, BEAR_TRENDING, RANGE_LOW_VOL,
     RANGE_HIGH_VOL, CAPITULATION, EUPHORIA
   - Multi-timeframe inputs: daily 200MA + ADX, 4H ATR percentile,
     1H RSI, F&G index (free CFGI API)
   - Stickiness: 2 consecutive classifications required for change
   - regime_history table populated
   - Telegram alert on regime change with explanation
   - Top bar regime badge in UI (color-coded)

D. Dashboard skeleton with placeholder KPI cards consuming real data.

Deliverables:
- WS streams stable for 24h
- Universe Manager identifies 50 valid mid-cap pairs
- Regime classifier correctly labels last 90 days BTC into six regimes
  (verify against historical: 2024 Q1 = BULL_TRENDING, etc.)
- Regime transitions logged + Telegram-alerted

Gate: Run for 24h continuous. Verify no memory leaks (check process RSS).
```

#### Phase 2 Prompt — Backtest + Validation Pipeline

```
Implement Phase 2 of AI-Quant-Binance-Bot v2.1.

Reference: Section 10 (Backtest), Section 8 (Strategy Framework).

A. Backtest Engine:
   - vectorbt as primary engine
   - backtesting.py for cross-validation
   - Walk-forward analysis (configurable window)
   - Monte Carlo trade-shuffle (5000 iterations, parallelized)
   - Parameter sensitivity heatmap (±20% grid)
   - Metrics: ROI, Sharpe, Sortino, Calmar, MDD, PF, Win Rate, Avg R
   - CRITICAL: Implement Deflated Sharpe Ratio (López de Prado formula)
   - Cost-shock test: re-run with fees × 1.5 + slippage × 2
   - Realistic slippage model: ATR-based + orderbook-aware

B. Strategy Framework:
   - Strategy base class per Section 8.2
   - Strategy versioning (semver + parameter_hash)
   - Database: strategies table with version + code_hash + parameter_hash

C. Baseline Strategies (NOT for live trading — for backtest validation only):
   - EMA Momentum (12/26 cross + ATR filter)
   - VWAP Reversion (mean-reversion to session VWAP)
   - RSI Bounce (oversold/overbought + trend filter)
   - Breakout Volume (range break + volume confirmation)

D. Backtest UI (Section 13.2 Page 4):
   - Setup form: pairs, timeframe, date range, capital, fees, slippage model
   - Run types: single, walk-forward, parameter sweep, MC robustness
   - Results: equity curve, MC distribution, sensitivity heatmap, trade log
   - Promotion criteria checklist (Section 10.2)
   - "Promote to Paper" button: LOCKED unless ALL criteria green

Critical: Tests must verify NO look-ahead bias. Add test that confirms
strategy can only see past data at decision time.

Deliverables:
- At least one baseline strategy passes ALL Section 10.2 criteria on real
  BTC/ETH 2-year data with realistic costs
- Backtest UI shows clear pass/fail per criterion
- Cost-shock test correctly stresses strategies
- All metrics reproducible across runs (deterministic with seed)
```

#### Phase 3 Prompt — Risk Engine + Funding Arb

```
Implement Phase 3 of AI-Quant-Binance-Bot v2.1.

This is the most critical phase. The Risk Engine is built here. The first
strategy capable of trading $100 capital live is built here.

Reference: Section 7 (Risk Engine - all 5 layers), Section 9.2 (Funding Arb),
Section 9.3 (Crowding Detector), Section 11 (Execution Quality + Cost Acct).

A. Risk Engine (Section 7):
   - Layer 1: Pre-Trade Checks (all 7 checks from Section 7.1)
   - Layer 2: Position Sizing (ATR + regime + Kelly + correlation)
   - Layer 3: Drawdown De-Risking Ladder (Section 7.3 thresholds)
   - Layer 4: Circuit Breakers (all 6 triggers from Section 7.4)
   - Layer 5: Hard Limits — RUNTIME IMMUTABLE
     * Load config/risk_policy.yaml at boot
     * Hard limits CANNOT be modified after boot (architectural enforcement)
     * Verify at boot: API key has NO withdraw permission
     * Verify at boot: API key has IP whitelist
     * Refuse to start if either fails

B. Risk Command Center UI (Section 13.2 Page 5):
   - Current policy display (read-only)
   - Edit Policy with diff view
   - Hard Limits section greyed with "Immutable" badge
   - Circuit breakers status grid
   - Drawdown ladder visualization (current position)
   - Daily loss budget gauge
   - Correlation matrix heatmap

C. Funding Rate Arbitrage Engine (Section 9.2):
   - Implement FundingArbStrategy class
   - Entry: funding_rate > 0.0005 per 8h AND basis < 0.002
   - Cash-and-carry: short perp + long spot of equal notional
   - Hedge ratio rebalancing
   - Exit: funding cools OR basis diverges OR hold > 7 days
   - funding_arb_positions table populated
   - Dedicated Funding Arb UI tab with cumulative funding earned

D. Crowding Detector (Section 9.3):
   - Coinglass API integration (free tier OK)
   - Score formula from Section 9.3 (5 components)
   - Output: -100 to +100 score
   - Hook into strategy signal generation as conviction multiplier

E. Paper Trading Mode:
   - Realistic fill simulation (slippage from Section 11.1 model)
   - Treats orders identically to live but doesn't hit real API
   - Configurable: instant fill vs realistic delay

F. Execution Quality Monitor (Section 11.1):
   - Track per-order: expected vs actual fill, slippage bps, fee paid,
     latency
   - Aggregate per symbol/strategy/timeframe

G. Cost Accounting (Section 11.2):
   - Every PnL display = NET PnL by default
   - "Show Gross" toggle for transparency
   - Daily/weekly/monthly cost breakdown report

H. Live vs Backtest Divergence Tracker (Section 10.3):
   - Rolling 30-trade comparison
   - Auto-pause strategy if divergence_score > 2.0

Deliverables:
- Funding Arb runs in paper mode for 30+ days successfully
- Risk engine demonstrably blocks unsafe orders (test with deliberately
  oversized orders, correlation violations, etc.)
- Cost accounting matches manual calculation
- Boot security check refuses to start with bad API key permissions
```

#### Phase 4 Prompt — AI Analyst + Pre-Live Hardening

```
Implement Phase 4 of AI-Quant-Binance-Bot v2.1.

Reference: Section 12 (AI Analyst), Section 9.8 (Retirement Protocol),
Section 9.9 (Pre-Commitment Device), Section 13.2 Pages 6-7.

A. AI Analyst Service (Section 12):
   - OpenRouter integration with daily cost cap (default $5/day)
   - Models: claude-sonnet-4 (primary), gpt-4o-mini (fast), deepseek-r1 (heavy)
   - Versioned prompt templates in prompts/
   - ai_interactions table populated for audit
   - Hard architectural enforcement of forbidden actions:
     * AI service has NO Binance API access
     * AI service has NO write access to risk_policy
     * AI service has NO write access to live strategy params
     * AI service has NO order execution endpoint access
   - Daily briefing automation (regime + portfolio summary)
   - Trade journal auto-tagging (multi-label per Section 12.5)
   - Suggestion queue with required human approval workflow
   - "Ask AI" chat interface with streaming

B. AI Analyst UI (Section 13.2 Page 6):
   - Daily Briefing card
   - Ask AI chat
   - Suggestions Queue
   - Diagnosis tool (paste trade ID → AI explanation)

C. Trade Journal UI (Section 13.2 Page 7):
   - Trade list with AI tags
   - Filter by tag/strategy/regime/outcome
   - Click trade → detailed timeline + AI explanation
   - Manual notes field

D. Strategy Retirement Protocol (Section 9.8):
   - Daily cron evaluating all retirement triggers
   - Auto-pause flagged strategies
   - Review UI with one-click Acknowledge & Retire
   - 30-day auto-retire if no decision

E. Pre-Commitment Device (Section 9.9):
   - Detect drawdown ≥5% → require typed phrase + 60min cooldown
   - Detect 5+ consecutive losses → require journal entry + 30min cooldown
   - Modal with backtest DD distribution + percentile context
   - Settings > Disable Pre-Commitment with 24h cooldown

Deliverables:
- AI delivers meaningful daily briefing for 14 consecutive days in paper
- Suggestion → Backtest → Approval → Paper pipeline tested end-to-end
- Pre-commitment modal triggers correctly on simulated drawdown
- Retirement protocol auto-flags a deliberately broken strategy in test

Critical test: Try to make AI directly modify risk policy via cleverly
worded prompt. The architectural enforcement must block this regardless
of prompt content.
```

#### Phase 5 Prompt — LIVE_MICRO with $100

```
Implement Phase 5 of AI-Quant-Binance-Bot v2.1.

THIS IS THE FIRST PHASE WITH REAL MONEY. EXTREME CAUTION REQUIRED.

Reference: Section 15 (Security), Section 16 (Observability + DR),
Section 17 (Deployment), Section 2.3 ($100 strategy).

A. Pre-Deployment Security Audit (each must pass):
   - [ ] Binance API key: trading enabled, withdraw DISABLED
   - [ ] IP whitelist active on Binance
   - [ ] Boot check refuses bad permissions
   - [ ] All secrets in encrypted store (age or Vault)
   - [ ] Audit log fully wired (every state-changing action)
   - [ ] 2FA mandatory and tested
   - [ ] TLS A+ on SSL Labs
   - [ ] fail2ban active on SSH
   - [ ] ufw firewall: only 22, 80, 443 open

B. Disaster Recovery Drills (each must pass):
   - [ ] Kill VPS during open paper position → dead-man switch flattens
   - [ ] Corrupt DB → restore from backup works
   - [ ] Force API timeout → circuit breaker trips
   - [ ] Restart bot mid-position → state recovery from Binance succeeds
   - [ ] Backup procedure: DB dump → S3-compatible → restore on fresh VPS

C. Observability Stack (Section 16):
   - Prometheus + Grafana running
   - All metrics from Section 16.1 emitted
   - Pre-built dashboards installed
   - Loki for log aggregation
   - Healthchecks.io ping every 30s
   - UptimeRobot on /api/health

D. Production Deployment (Section 17):
   - docker-compose.prod.yml with all services
   - Nginx reverse proxy + Let's Encrypt
   - Cloudflare in front (optional)
   - Deploy script with healthcheck + rollback

E. Live Configuration for $100:
   - MODE=live_micro
   - Capital Profile = MICRO (auto-detected at $100)
   - Only Funding Arb strategy enabled
   - Max 1 concurrent position
   - Risk per trade = 2% of equity
   - Daily Telegram heartbeat + summary
   - Withdrawal milestone alerts at $200 equity

F. Monitoring Dashboard:
   - Real-time PnL (NET only, gross hidden)
   - Daily summary email at 23:55 UTC
   - All circuit breaker states visible
   - Easy emergency kill switch (typed confirmation)

Deliverables:
- Production deployment hardened and audited
- ALL DR drills passed
- $100 deployed with Funding Arb only
- 24h smoke test successful (no errors in logs)
- Telegram heartbeat working

DO NOT proceed past Phase 5 for at least 90 days of stable LIVE_MICRO.
```

#### Phase 6 Prompt — Diversification (Equity ≥ $200)

```
Implement Phase 6 of AI-Quant-Binance-Bot v2.1.

Trigger conditions (verify ALL before starting):
- Phase 5 ran ≥ 90 days with no critical incidents
- Equity ≥ $200
- Funding Arb produced positive net PnL for 90 days
- Live performance within ±25% of paper expectations

Reference: Section 9.7 (Asian Session), Section 9.6 (Alt Data),
Section 2.5 (Growth Plan).

A. New Strategies (add ONE at a time, validate independently for 30d each):
   - Mid-Cap Swing strategy using Universe Manager output
     * 4H/Daily timeframe (NOT intraday — fee drag at MICRO+)
     * Min target R = 2.5
     * Limit-order-first execution
   - Regime-aware trend follower (BULL_TRENDING + BEAR_TRENDING regimes)
   - Mean reversion specialist (RANGE_LOW_VOL regime only)

B. Asian Session Monitor (Section 9.7):
   - Indodax announcements polling (Indonesian local edge)
   - Upbit + Bithumb announcements
   - Asian-hours volume anomaly detector
   - Special weight to Indodax signals (user is Indonesia-based)

C. Alternative Data Layer Tier 2 (Section 9.6):
   - LunarCrush integration (sentiment + galaxy score)
   - Santiment integration (on-chain sentiment)
   - Cost-aware activation: only enable when capital ≥ $500

D. Capital Auto-Rebalancing:
   - Implement growth_plan.yaml tier evaluation
   - Auto-rebalance strategy mix as equity grows
   - Withdrawal milestone notifications

Deliverables:
- 3+ strategies running concurrently without correlation issues
- Asian session module producing measurable signal lift
- Capital profile auto-graduates from MICRO → SMALL at $500
- All edge modules contributing measurable performance
```

#### Phase 7 Prompt — Multi-Venue (Equity ≥ $2,000)

```
Implement Phase 7 of AI-Quant-Binance-Bot v2.1.

Trigger: Equity ≥ $2,000 + Phase 6 stable for 6+ months.

Reference: Section 9.10 (Multi-Venue Connector).

A. Venue Adapter Pattern:
   - Abstract VenueAdapter base class
   - BinanceAdapter (existing, refactored)
   - OKXAdapter (new)
   - BybitAdapter (new)
   - Unified order routing through MultiVenueRouter

B. Cross-Venue Strategies:
   - Cross-venue basis arbitrage (Binance vs OKX)
   - Funding rate optimization (choose best venue)

C. Microstructure Strategies:
   - Orderbook imbalance signal generator
   - Liquidation cascade surfer
   - Spot-perp basis trader

D. Multi-symbol Portfolio Optimization:
   - Mean-variance optimizer for strategy weights
   - Correlation-aware rebalancing

E. Alternative Data Tier 3:
   - Glassnode (whale flows)
   - CryptoQuant (exchange flows)

Deliverables:
- Multi-venue order routing tested
- At least one cross-venue arb produces consistent profit
- Operational complexity manageable (no on-call hellfire)
```

#### Phase 8 Prompt — DeFi Bridge (Optional)

```
Implement Phase 8 of AI-Quant-Binance-Bot v2.1.

Optional. Only if user has separate DeFi capital and CEX equity ≥ $1,000.

Reference: Section 9.11.

A. DeFi Bridge Service (read-only initially):
   - Solana RPC connection
   - DLMM position monitoring
   - Hyperliquid perps integration

B. Cross-Pollination Strategies:
   - Hyperliquid funding arb when Binance extreme
   - DLMM sizing informed by CEX volatility
   - CEX-DEX basis trades when dislocated

This phase has highest complexity. Defer if Phase 7 not rock-solid.
```

#### Phase 9 Prompt — Multi-Tenant SaaS (Year 2+)

```
SaaS implementation. Different security/compliance bar.

DO NOT combine with personal-use development. This is a separate fork.

Requirements changes:
- Multi-tenant data isolation (row-level security in Postgres)
- Per-user API key encryption (envelope encryption with KMS)
- Stripe billing integration
- KYC/regulatory review per jurisdiction
- 24/7 monitoring + on-call rotation
- SOC 2 / ISO 27001 if enterprise customers

Build only if personal use proves profitable across multiple regimes.
```

### 19.3 Code Quality Standards (Enforced via CI)

| Standard | Tool | Threshold |
|---|---|---|
| Python lint | ruff | Zero errors |
| Python format | black | Auto-applied |
| Python types | mypy --strict | Zero errors |
| Python tests | pytest | ≥80% on risk_engine, ≥60% overall |
| TS lint | ESLint | Zero errors |
| TS format | Prettier | Auto-applied |
| TS types | tsc --noEmit | Zero errors |
| Secret scan | gitleaks | Zero leaked secrets |
| Dep audit | pip-audit + npm audit | Zero high CVEs |

### 19.4 Anti-Patterns to Reject (Codex MUST refuse to write these)

❌ Floating-point arithmetic on money (use `Decimal`)
❌ Catching broad exceptions without re-raising or alerting
❌ Hardcoding symbols, params, or risk limits in code (must come from config)
❌ Calling Binance API from frontend
❌ Storing API keys in JWT payload, localStorage, or sessionStorage
❌ Optimistic state updates without server confirmation for trade actions
❌ Backtest with look-ahead bias (using future data at decision time)
❌ Sharpe comparison without considering Deflated Sharpe
❌ AI suggestions auto-applied to live config
❌ Missing reconciliation after order submission
❌ Synchronous I/O in async handlers
❌ Shared mutable state across requests without locks
❌ Sleeping/blocking inside event loop
❌ Test that requires real Binance API (use fixtures/mocks)
❌ Production code without structured logging
❌ Frontend forms (`<form>`) in React artifacts (use onClick handlers)
❌ Risk engine code path that lacks audit log entry
❌ AI service holding any credential other than OpenRouter API key

### 19.5 File Creation Order Within a Phase

When implementing a phase, create files in this order:

1. **Database migrations** (Alembic) — schema changes first
2. **Pydantic models / SQLAlchemy models** — data shapes
3. **Service layer** (pure logic, testable)
4. **Tests for service layer** — verify logic before integration
5. **API routes / endpoints** — expose via HTTP
6. **Tests for endpoints** — integration tests
7. **Frontend types** (TypeScript interfaces matching Pydantic)
8. **Frontend hooks/services** — data fetching layer
9. **Frontend components** — presentation
10. **E2E tests** — final verification

This order minimizes rework when schemas change.

### 19.6 Communication Protocol with Codex/Claude Code

When Codex/Claude Code is implementing, expected interaction pattern:

```
USER: "Start Phase 0"
AGENT: [shows planned directory structure for confirmation]
USER: "Approved, proceed"
AGENT: [generates files in order from Section 19.5]
       [runs tests after each major module]
       [reports: "Phase 0 progress: 7/10 tasks complete"]
AGENT: [at end of phase] "Phase 0 complete. Gate criteria checklist:
        ✅ make test green
        ✅ All 9 routes render
        ✅ Capital Profile returns MICRO for $100
        ✅ Telegram delivers
        Ready to proceed to Phase 1?"
USER: "Yes"
AGENT: [starts Phase 1 with Phase 1 prompt]
```

### 19.7 Pre-Flight Checklist Before Live Deployment

Before any LIVE_MICRO transition, the agent MUST verify:

```
[ ] All Phase 0-4 gate criteria documented as met
[ ] Backup tested: DB → S3 → restore on fresh VPS
[ ] Dead-man switch tested: VPS killed, positions flattened
[ ] API key permissions verified (trade only, IP locked)
[ ] Hard limits in risk_policy.yaml reviewed by user
[ ] capital_profiles.yaml MICRO settings reviewed by user
[ ] Telegram alerts firing for all severity levels
[ ] Healthchecks.io + UptimeRobot active
[ ] User has acknowledged trading disclaimer (Section 20.3)
[ ] Initial capital is amount user can fully lose without distress
[ ] Funding Arb is the ONLY enabled strategy
[ ] AI Analyst forbidden actions architecturally enforced (test with red-team prompt)
```

Refuse to deploy live until ALL items checked.

---

## 20. Appendix

### 20.1 Glossary

**Trading & Quant**
- **ATR:** Volatility measure used for stop placement and position sizing.
- **Basis:** Price difference between perp/futures and spot. Foundation of cash-and-carry arbitrage.
- **Cash-and-Carry:** Market-neutral: short perp + long spot to capture funding rate.
- **Crowding:** Condition where retail bots are over-positioned in one direction.
- **Deflated Sharpe Ratio (DSR):** Sharpe corrected for multiple-testing bias.
- **Funding Rate:** Periodic payment between perpetual longs and shorts (8h on Binance).
- **Kelly Criterion:** Optimal bet size formula; fractional (0.25x) is standard.
- **Open Interest (OI):** Total outstanding derivative positions.
- **Regime:** Classification of current market state.
- **Slippage:** Difference between expected and actual fill price.
- **Walk-Forward Analysis:** Rolling optimize-and-test methodology.

**System & Operational**
- **Capital Profile:** Tier (MICRO/SMALL/STANDARD/SCALED) gating strategies based on equity.
- **Circuit Breaker:** Automated halt triggered by anomalies.
- **Dead-Man Switch:** External monitor that flattens positions if main system goes silent.
- **Divergence Score:** Measure of how far live performance deviates from backtest.
- **Edge Decay:** Tendency of strategies to lose profitability as discovered by others.
- **Idempotency Key:** Unique ID per order preventing duplicate submissions on retry.
- **Pre-Commitment Device:** UI friction preventing emotional intervention during drawdowns.
- **Promotion Gate:** Hard criteria for advancing strategy: backtest -> paper -> live.
- **State Reconciliation:** Syncing local state with exchange truth (exchange wins).

### 20.2 Reading List

**Essential**
- *Advances in Financial Machine Learning* - Marcos López de Prado
- *Building Winning Algorithmic Trading Systems* - Kevin Davey
- *Trading and Exchanges: Market Microstructure for Practitioners* - Larry Harris

**Microstructure & Crypto**
- *Algorithmic and High-Frequency Trading* - Cartea, Jaimungal, Penalva
- *DeFi and the Future of Finance* - Campbell Harvey
- Binance API: https://binance-docs.github.io/apidocs/

**Risk & Operations**
- *Antifragile* - Nassim Taleb
- *Site Reliability Engineering* - Google
- *The Phoenix Project* - Gene Kim

### 20.3 License & Disclaimers

This blueprint is private/proprietary. Code generated from this blueprint is for personal use unless explicitly licensed otherwise.

**TRADING DISCLAIMER:** Algorithmic trading carries substantial risk. Past performance, including backtest results, is not indicative of future results. Cryptocurrency markets are highly volatile and can result in total loss of capital. This software is provided "as is" without warranty. The user assumes all risk.

**For $100 starting capital users:**
- Treat your initial $100 as **tuition for learning**, not investment capital
- Do not deposit money you cannot afford to lose entirely
- Losing months are mathematically expected
- Do not borrow money or use credit to fund trading
- Realistic 12-month outcome: -100% to +200%

**No part of this system constitutes financial advice.**

### 20.4 Quick Reference: Config Files

| Concern | Section | Config File |
|---|---|---|
| Capital tier behavior | §2 | `config/capital_profiles.yaml` |
| Risk policy | §7 | `config/risk_policy.yaml` |
| Growth plan | §2.5 | `config/growth_plan.yaml` |
| Crowding detector | §9.3 | `config/edge/crowding.yaml` |
| Symbol blacklist | §9.4 | `config/edge/blacklist.yaml` |
| Alt data | §9.6 | `config/edge/alt_data.yaml` |
| Asian session | §9.7 | `config/edge/asian_session.yaml` |
| Strategy retirement | §9.8 | `config/edge/retirement_policy.yaml` |
| Pre-commitment | §9.9 | `config/edge/precommitment.yaml` |
| Multi-venue | §9.10 | `config/edge/multi_venue.yaml` |

### 20.5 FAQ

**Q: Why is Funding Arb the FIRST live strategy, not EMA?**
A: At $100 with 0.1% taker fees, you need ~60% win rate at 1.5R just to break even. Funding arb is market-neutral and works at small capital. EMA strategies are educational fixtures only.

**Q: Why are baseline strategies still implemented if unprofitable?**
A: For backtest framework validation. They serve as test fixtures. They are NEVER promoted to live.

**Q: Can the AI Analyst really not bypass forbidden actions?**
A: Architectural enforcement: AI service has no API credentials, no DB write access to risk_policy, no access to live deployment endpoints. A malicious prompt cannot execute through nonexistent permissions.

**Q: What if my $100 grows to $0?**
A: Stop. Review audit log. Either fix and restart with new $100 (continued tuition), or accept that algo trading isn't right. Do not chase losses.

**Q: Should I use Binance Futures or Spot?**
A: Spot only at MICRO. System enables futures starting SMALL tier, but only for funding arb (where futures is required for short leg).

**Q: How to test dead-man switch without risk?**
A: Test in paper mode first. For live test: small position, kill VPS process via `kill -9`, verify dead-man switch (separate VPS) flattens position.

### 20.6 Change Log

**v2.1 (current)** - Small Capital + Defensible Edge release:
- Added Section 2: Small Capital Reality ($100 Profile)
- Added Section 9: Defensible Edge Layer (11 modules)
- Reorganized Roadmap: 9 phases with explicit $100 path
- Per-phase Codex/Claude Code prompts (Phase 0-9)
- Capital-tier-aware module activation
- Indonesian local edge (Indodax priority in Asian Session)

**v2.0** - Production-grade rewrite: 5-layer risk engine, walk-forward validation, execution quality monitoring, cost accounting, AI guardrails, disaster recovery, security hardening, promotion gates.

**v1.0** - Initial blueprint (UI-focused, structural).

---

**End of Blueprint v2.1**

*Build slowly. Validate ruthlessly. Ship safely.*

*Edge over time, not edge in moments.*
