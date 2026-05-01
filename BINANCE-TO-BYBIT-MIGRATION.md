# AI-Quant Bot — Binance to Bybit Migration Guide

> **For Codex / Claude Code:** This document is a step-by-step migration guide from Binance to Bybit for the AI-Quant-Binance-Bot codebase. Follow phases in order. Do not skip steps. Each phase has verification criteria.

**Target:** Convert existing Binance-targeted codebase to Bybit-primary while keeping CCXT abstraction for future multi-venue support.

**Estimated effort:** 2-4 days of focused work depending on how much code already exists.

**Project rename:** `AI-Quant-Binance-Bot` → `AI-Quant-Bybit-Bot` (or keep neutral: `AI-Quant-Crypto-Bot`)

---

## Table of Contents

1. [Migration Strategy Overview](#1-migration-strategy-overview)
2. [Critical Differences: Binance vs Bybit](#2-critical-differences-binance-vs-bybit)
3. [Phase A: Configuration & Naming](#3-phase-a-configuration--naming)
4. [Phase B: Exchange Adapter Layer](#4-phase-b-exchange-adapter-layer)
5. [Phase C: Symbol & Market Data](#5-phase-c-symbol--market-data)
6. [Phase D: Order Execution](#6-phase-d-order-execution)
7. [Phase E: Funding Rate & Futures Specific](#7-phase-e-funding-rate--futures-specific)
8. [Phase F: WebSocket Streams](#8-phase-f-websocket-streams)
9. [Phase G: Testing & Validation](#9-phase-g-testing--validation)
10. [Phase H: Documentation Updates](#10-phase-h-documentation-updates)
11. [Bybit-Specific Setup Instructions](#11-bybit-specific-setup-instructions)
12. [Testnet Configuration](#12-testnet-configuration)
13. [Common Pitfalls](#13-common-pitfalls)

---

## 1. Migration Strategy Overview

### 1.1 Core Principle

**Use CCXT as primary abstraction, keep Bybit-native client for performance-critical paths.**

The original blueprint already specified CCXT for portability. We exploit this — CCXT handles 80% of the migration automatically. The remaining 20% is Bybit-specific quirks.

### 1.2 Two-Tier Adapter Pattern

```
┌─────────────────────────────────────────────┐
│            Strategy Service                 │
└──────────────────┬──────────────────────────┘
                   │ uses
                   ▼
┌─────────────────────────────────────────────┐
│         VenueAdapter (abstract)             │  ← Already in blueprint §9.10
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴───────────┐
        ▼                      ▼
┌──────────────┐       ┌──────────────────┐
│ BybitAdapter │       │ BinanceAdapter   │
│  (PRIMARY)   │       │  (TESTNET ONLY)  │
└──────┬───────┘       └────────┬─────────┘
       │                        │
       ▼                        ▼
   ┌────────┐              ┌────────┐
   │  CCXT  │              │  CCXT  │
   │ +pybit │              │+python-│
   │        │              │ binance│
   └────────┘              └────────┘
```

**Why keep both:**
- Bybit = primary live trading
- Binance Testnet = development sandbox (Bybit testnet is decent but Binance testnet is more polished for dev)
- Future-proof for multi-venue (§9.10 of blueprint)

### 1.3 Migration Order

```
A. Config & naming      (15 min)  - Search/replace
B. Exchange adapter     (4 hr)    - Most important
C. Symbol & market data (2 hr)
D. Order execution      (3 hr)
E. Funding & futures    (2 hr)
F. WebSocket streams    (3 hr)
G. Testing              (4 hr)
H. Documentation        (1 hr)
```

---

## 2. Critical Differences: Binance vs Bybit

### 2.1 Quick Reference Table

| Aspect | Binance | Bybit |
|---|---|---|
| **API base URL** | `api.binance.com` | `api.bybit.com` |
| **Testnet URL** | `testnet.binance.vision` (spot)<br>`testnet.binancefuture.com` (futures) | `api-testnet.bybit.com` |
| **Python library** | `python-binance` | `pybit` (official) |
| **CCXT identifier** | `binance`, `binanceusdm` | `bybit` |
| **Symbol format (Spot)** | `BTCUSDT` | `BTCUSDT` (sama) |
| **Symbol format (Perp)** | `BTCUSDT` (USD-M futures) | `BTCUSDT` (linear perp) |
| **Account types** | Spot, Margin, USD-M, COIN-M | Unified Trading Account (UTA), Spot, Linear, Inverse |
| **API key permission** | Granular (Read/Trade/Withdraw/Margin) | Granular (Read/Trade/Withdraw/SubAccount) |
| **IP whitelist** | Optional but recommended | **Mandatory** for trading API |
| **Min notional (Spot)** | ~$5 USDT | $1-5 USDT (varies per pair) |
| **Min notional (Perp)** | $5 USDT typical | $1-5 USDT typical |
| **Funding interval** | 8 hours | 8 hours (same) |
| **Funding payment time** | 00:00, 08:00, 16:00 UTC | 00:00, 08:00, 16:00 UTC |
| **Maker fee (default)** | 0.1% (spot), 0.02% (perp) | 0.1% (spot), 0.02% (perp) |
| **Taker fee (default)** | 0.1% (spot), 0.05% (perp) | 0.1% (spot), 0.055% (perp) |
| **WebSocket public** | `wss://stream.binance.com` | `wss://stream.bybit.com/v5/public/linear` |
| **WebSocket private** | `wss://stream.binance.com:9443/ws` | `wss://stream.bybit.com/v5/private` |
| **Order types** | LIMIT, MARKET, STOP_LOSS, OCO, etc | Limit, Market, StopLoss, TakeProfit, conditional |
| **Position mode** | Hedge / One-way | Hedge / One-way (Bybit calls "Position Mode") |
| **OCO orders** | Native support | NOT native — must implement client-side |
| **Rate limits** | Weight-based (1200/min default) | Per-endpoint (varies, generally generous) |

### 2.2 Critical Conceptual Differences

**1. Account Architecture**

Bybit has the concept of **Unified Trading Account (UTA)**, which combines Spot, Linear (USDT perp), Inverse (Coin-M perp), and Options into one account. This is **different from Binance** which keeps them separate.

For our funding arb strategy this is actually **better** because:
- No need to transfer between Spot wallet and Futures wallet
- Same USDT balance can margin perp positions AND buy spot
- Capital efficiency much higher (critical for $100 capital)

**Decision:** Use UTA mode (default for new Bybit accounts). Set `accountType=UNIFIED` in API calls.

**2. Symbol Categorization**

Bybit V5 API requires you specify `category` for every call:
- `spot` — Spot trading
- `linear` — USDT/USDC perpetuals (most relevant for us)
- `inverse` — Coin-margined perpetuals
- `option` — Options

Binance doesn't need this, it infers from endpoint. Our adapter must add this parameter explicitly for Bybit calls.

**3. OCO Order Handling**

Binance supports native OCO (One-Cancels-Other) for stop-loss + take-profit. Bybit does **NOT** have native OCO.

**Solution:** Bybit supports attaching `stopLoss` and `takeProfit` parameters directly when placing the entry order (via `tpslMode=Full`). This achieves the same effect.

**4. Position Mode**

Both exchanges support hedge mode (long + short same symbol simultaneously) and one-way mode. **Default to One-Way mode** for the bot — simpler, less margin requirement, fewer edge cases.

```python
# At bot initialization, ensure position mode is set
await exchange.set_position_mode(hedged=False, symbol=None)  # one-way for all
```

---

## 3. Phase A: Configuration & Naming

### 3.1 Project Renaming

```bash
# In repository root, run these find/replace operations.
# Use ripgrep + sed, NOT global IDE replace (review changes).

# 1. Rename project references in non-code files
find . -type f \( -name "*.md" -o -name "*.yml" -o -name "*.yaml" -o -name "*.toml" \) \
  -not -path "*/node_modules/*" -not -path "*/.git/*" \
  -exec sed -i 's/AI-Quant-Binance-Bot/AI-Quant-Bybit-Bot/g' {} +

# 2. Rename in code comments and docstrings
find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) \
  -not -path "*/node_modules/*" \
  -exec sed -i 's/AI-Quant-Binance-Bot/AI-Quant-Bybit-Bot/g' {} +

# 3. Rename docker compose service references if any
sed -i 's/binance-bot/bybit-bot/g' docker-compose*.yml
```

### 3.2 Environment Variables Migration

**Update `.env.example`:**

```env
# ─── REMOVE THESE ───
# BINANCE_API_KEY=
# BINANCE_API_SECRET=
# BINANCE_TESTNET=false
# BINANCE_VIP_TIER=0

# ─── ADD THESE ───

# Primary venue (LIVE)
BYBIT_API_KEY=
BYBIT_API_SECRET=
BYBIT_TESTNET=false
BYBIT_VIP_TIER=0
BYBIT_ACCOUNT_TYPE=UNIFIED   # UNIFIED (recommended) or CLASSIC

# Development venue (TESTNET only - NEVER use real keys here)
BINANCE_TESTNET_API_KEY=     # For Phase 0-4 dev only
BINANCE_TESTNET_API_SECRET=
USE_BINANCE_FOR_DEV=false    # Set true only during dev phase

# Active venue selector
PRIMARY_VENUE=bybit          # bybit | binance
DEV_VENUE=bybit_testnet      # bybit_testnet | binance_testnet
```

### 3.3 Update `config/risk_policy.yaml`

Adjust fee assumptions to Bybit's structure:

```yaml
# Update fee section to reflect Bybit
fees:
  spot:
    maker_pct: 0.001          # 0.1%
    taker_pct: 0.001          # 0.1%
  linear_perp:
    maker_pct: 0.0002         # 0.02%
    taker_pct: 0.00055        # 0.055% (slightly higher than Binance)
  vip_tier_discounts:
    # See https://www.bybit.com/en/help-center/article/Bybit-VIP-Program
    vip0: 1.0
    vip1: 0.85
    vip2: 0.70
```

### 3.4 Update `config/capital_profiles.yaml`

```yaml
profiles:
  micro:
    # ... existing settings ...
    venue_specific:
      bybit:
        min_notional_buffer: 1.5
        preferred_account_type: UNIFIED
        use_unified_margin: true     # UTA capital efficiency
        avoid_pairs_below_volume_24h_usd: 30000000
```

### 3.5 Verification Checklist

```
[ ] All references to "Binance" in non-code files updated
[ ] .env.example has Bybit variables, Binance only as testnet/dev
[ ] risk_policy.yaml fees match Bybit
[ ] No code references to BINANCE_API_KEY in production paths
[ ] Project title in README updated
[ ] Docker service names updated
```

---

## 4. Phase B: Exchange Adapter Layer

### 4.1 Add Dependencies

**`backend/pyproject.toml`:**

```toml
[project]
dependencies = [
    # ... existing ...
    "ccxt>=4.4.0",          # Already present
    "pybit>=5.7.0",         # NEW - Official Bybit Python SDK
    # Keep python-binance for testnet
    "python-binance>=1.0.19",
]
```

### 4.2 Define Abstract Base Class

**`backend/services/venues/base.py`:**

```python
"""
Abstract venue adapter. All concrete venue implementations
must inherit from this and implement all abstract methods.

Critical: This abstraction must NEVER leak venue-specific types.
All return values are platform-neutral domain models.
"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel

# Platform-neutral domain models
class MarketSymbol(BaseModel):
    symbol: str               # Normalized: BTCUSDT
    base: str                 # BTC
    quote: str                # USDT
    type: Literal["spot", "perp"]
    min_notional: Decimal
    min_qty: Decimal
    qty_step: Decimal
    price_step: Decimal
    is_active: bool

class OrderRequest(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    type: Literal["limit", "market"]
    qty: Decimal
    price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    time_in_force: Literal["GTC", "IOC", "FOK", "PostOnly"] = "GTC"
    reduce_only: bool = False
    idempotency_key: str
    category: Literal["spot", "linear"] = "linear"

class OrderResponse(BaseModel):
    venue_order_id: str
    idempotency_key: str
    status: Literal["new", "partially_filled", "filled", "cancelled", "rejected"]
    raw: dict   # Original venue response for audit

class Position(BaseModel):
    symbol: str
    side: Literal["long", "short", "none"]
    qty: Decimal
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    leverage: Decimal
    category: Literal["spot", "linear"]

class FundingRateInfo(BaseModel):
    symbol: str
    current_rate: Decimal
    next_funding_time: int   # unix timestamp
    predicted_rate: Optional[Decimal]


class VenueAdapter(ABC):
    """All venue adapters implement this interface."""
    
    name: str   # e.g. "bybit", "binance"
    
    @abstractmethod
    async def initialize(self) -> None:
        """One-time setup. Verify API key permissions, set position mode, etc."""
        ...
    
    @abstractmethod
    async def verify_api_safety(self) -> None:
        """
        Boot-time security check. MUST raise SecurityError if:
        - API key has withdraw permission
        - IP whitelist not enabled
        - Position mode misconfigured
        """
        ...
    
    # Market data
    @abstractmethod
    async def get_symbols(self, category: str) -> list[MarketSymbol]: ...
    
    @abstractmethod
    async def get_ticker(self, symbol: str, category: str) -> dict: ...
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, category: str, depth: int) -> dict: ...
    
    @abstractmethod
    async def get_klines(self, symbol: str, category: str, 
                          interval: str, limit: int) -> list: ...
    
    @abstractmethod
    async def get_funding_rate(self, symbol: str) -> FundingRateInfo: ...
    
    @abstractmethod
    async def get_funding_rate_history(self, symbol: str, 
                                         limit: int) -> list[FundingRateInfo]: ...
    
    # Account
    @abstractmethod
    async def get_balance(self) -> dict[str, Decimal]: ...
    
    @abstractmethod
    async def get_positions(self) -> list[Position]: ...
    
    @abstractmethod
    async def get_open_orders(self, category: str) -> list: ...
    
    # Trading
    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResponse: ...
    
    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str, 
                            category: str) -> bool: ...
    
    @abstractmethod
    async def cancel_all_orders(self, category: str, 
                                  symbol: Optional[str] = None) -> int: ...
    
    @abstractmethod
    async def close_position(self, symbol: str, category: str) -> OrderResponse: ...
    
    # WebSocket
    @abstractmethod
    async def subscribe_klines(self, symbol: str, interval: str, 
                                 category: str, callback) -> None: ...
    
    @abstractmethod
    async def subscribe_orderbook(self, symbol: str, category: str, 
                                    callback) -> None: ...
    
    @abstractmethod
    async def subscribe_user_data(self, callback) -> None:
        """Position updates, order updates, balance updates."""
        ...
```

### 4.3 Implement Bybit Adapter

**`backend/services/venues/bybit_adapter.py`:**

```python
"""
Bybit venue adapter using pybit (official SDK) with CCXT fallback.

Architecture decisions:
- pybit for: order placement, account queries, WebSocket (lower latency)
- CCXT for: cross-venue data normalization where useful
- All methods async via asyncio.to_thread for pybit's sync calls

References:
- pybit docs: https://github.com/bybit-exchange/pybit
- Bybit V5 API: https://bybit-exchange.github.io/docs/v5/intro
"""
import asyncio
from decimal import Decimal
from typing import Optional
from pybit.unified_trading import HTTP, WebSocket
from .base import (
    VenueAdapter, MarketSymbol, OrderRequest, OrderResponse,
    Position, FundingRateInfo
)
from app.core.exceptions import SecurityError, OrderError


class BybitAdapter(VenueAdapter):
    name = "bybit"
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.testnet = testnet
        self._client = HTTP(
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret,
        )
        self._ws_public: Optional[WebSocket] = None
        self._ws_private: Optional[WebSocket] = None
    
    async def initialize(self) -> None:
        """One-time setup."""
        await self.verify_api_safety()
        
        # Set position mode to one-way (simpler)
        # Note: This may already be default for new accounts
        try:
            await asyncio.to_thread(
                self._client.switch_position_mode,
                category="linear",
                mode=0  # 0 = one-way, 3 = hedge
            )
        except Exception as e:
            # If already in correct mode, Bybit returns error - safe to ignore
            if "not modified" not in str(e).lower():
                raise
    
    async def verify_api_safety(self) -> None:
        """
        Boot-time security check. Verifies:
        1. API key does not have withdraw permission
        2. IP restriction is enabled
        """
        result = await asyncio.to_thread(self._client.get_api_key_information)
        
        if result.get("retCode") != 0:
            raise SecurityError(f"Cannot verify API key: {result}")
        
        info = result["result"]
        
        # Check 1: No withdraw permission
        permissions = info.get("permissions", {})
        if permissions.get("Wallet", []):  # Withdraw is under "Wallet"
            wallet_perms = permissions["Wallet"]
            if "AccountTransfer" in wallet_perms or "SubMemberTransfer" in wallet_perms:
                pass  # Internal transfers OK
            # The critical one to refuse:
            if "Withdraw" in wallet_perms:
                raise SecurityError(
                    "API key has Withdraw permission. ABORT. "
                    "Re-create key with Withdraw DISABLED."
                )
        
        # Check 2: IP restriction
        ips = info.get("ips", [])
        if not ips or ips == ["*"]:
            raise SecurityError(
                "API key has no IP restriction. ABORT. "
                "Add IP whitelist on Bybit before continuing."
            )
        
        # Check 3: Read + Trade only (warn if more)
        allowed_perm_groups = {"ContractTrade", "Spot", "Wallet", "Options", "Derivatives"}
        # We allow Read + Trade for spot/derivatives
        # Refuse if any unexpected high-privilege permission
    
    # ──────────────────────────────────────────────
    # Market Data
    # ──────────────────────────────────────────────
    
    async def get_symbols(self, category: str = "linear") -> list[MarketSymbol]:
        """category: 'spot' | 'linear' | 'inverse'"""
        result = await asyncio.to_thread(
            self._client.get_instruments_info,
            category=category
        )
        
        symbols = []
        for item in result["result"]["list"]:
            symbols.append(MarketSymbol(
                symbol=item["symbol"],
                base=item["baseCoin"],
                quote=item["quoteCoin"],
                type="spot" if category == "spot" else "perp",
                min_notional=Decimal(item.get("minOrderAmt", item.get("minNotionalValue", "0"))),
                min_qty=Decimal(item["lotSizeFilter"]["minOrderQty"]),
                qty_step=Decimal(item["lotSizeFilter"]["qtyStep"]),
                price_step=Decimal(item["priceFilter"]["tickSize"]),
                is_active=item["status"] == "Trading"
            ))
        return symbols
    
    async def get_ticker(self, symbol: str, category: str = "linear") -> dict:
        result = await asyncio.to_thread(
            self._client.get_tickers,
            category=category,
            symbol=symbol
        )
        return result["result"]["list"][0]
    
    async def get_orderbook(self, symbol: str, category: str = "linear", 
                              depth: int = 50) -> dict:
        result = await asyncio.to_thread(
            self._client.get_orderbook,
            category=category,
            symbol=symbol,
            limit=depth
        )
        return result["result"]
    
    async def get_klines(self, symbol: str, category: str = "linear",
                          interval: str = "1", limit: int = 200) -> list:
        """
        interval mapping (Bybit format):
        '1', '3', '5', '15', '30', '60', '120', '240', '360', '720', 'D', 'M', 'W'
        """
        result = await asyncio.to_thread(
            self._client.get_kline,
            category=category,
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        return result["result"]["list"]
    
    async def get_funding_rate(self, symbol: str) -> FundingRateInfo:
        ticker = await self.get_ticker(symbol, category="linear")
        return FundingRateInfo(
            symbol=symbol,
            current_rate=Decimal(ticker["fundingRate"]),
            next_funding_time=int(ticker["nextFundingTime"]),
            predicted_rate=None  # Bybit doesn't provide predicted explicitly
        )
    
    async def get_funding_rate_history(self, symbol: str, 
                                         limit: int = 200) -> list[FundingRateInfo]:
        result = await asyncio.to_thread(
            self._client.get_funding_rate_history,
            category="linear",
            symbol=symbol,
            limit=limit
        )
        return [
            FundingRateInfo(
                symbol=symbol,
                current_rate=Decimal(item["fundingRate"]),
                next_funding_time=int(item["fundingRateTimestamp"]),
                predicted_rate=None
            )
            for item in result["result"]["list"]
        ]
    
    # ──────────────────────────────────────────────
    # Account
    # ──────────────────────────────────────────────
    
    async def get_balance(self) -> dict[str, Decimal]:
        result = await asyncio.to_thread(
            self._client.get_wallet_balance,
            accountType="UNIFIED"
        )
        balances = {}
        for coin in result["result"]["list"][0]["coin"]:
            balances[coin["coin"]] = Decimal(coin["walletBalance"])
        return balances
    
    async def get_positions(self) -> list[Position]:
        result = await asyncio.to_thread(
            self._client.get_positions,
            category="linear",
            settleCoin="USDT"   # Required for "all positions" query
        )
        positions = []
        for item in result["result"]["list"]:
            if Decimal(item["size"]) == 0:
                continue
            positions.append(Position(
                symbol=item["symbol"],
                side="long" if item["side"] == "Buy" else "short",
                qty=Decimal(item["size"]),
                entry_price=Decimal(item["avgPrice"]),
                mark_price=Decimal(item["markPrice"]),
                unrealized_pnl=Decimal(item["unrealisedPnl"]),
                leverage=Decimal(item["leverage"]),
                category="linear"
            ))
        return positions
    
    async def get_open_orders(self, category: str = "linear") -> list:
        result = await asyncio.to_thread(
            self._client.get_open_orders,
            category=category,
            settleCoin="USDT" if category == "linear" else None
        )
        return result["result"]["list"]
    
    # ──────────────────────────────────────────────
    # Trading
    # ──────────────────────────────────────────────
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """
        Bybit order placement with full TP/SL support via 'tpslMode=Full'.
        
        IMPORTANT: idempotency_key is sent as 'orderLinkId' which Bybit
        uses to deduplicate orders within 24h window.
        """
        params = {
            "category": order.category,
            "symbol": order.symbol,
            "side": "Buy" if order.side == "buy" else "Sell",
            "orderType": "Limit" if order.type == "limit" else "Market",
            "qty": str(order.qty),
            "orderLinkId": order.idempotency_key,  # idempotency key
            "timeInForce": order.time_in_force,
            "reduceOnly": order.reduce_only,
        }
        
        if order.type == "limit":
            params["price"] = str(order.price)
        
        # Attach SL/TP if provided (Bybit native, no OCO needed)
        if order.stop_loss or order.take_profit:
            params["tpslMode"] = "Full"
            if order.stop_loss:
                params["stopLoss"] = str(order.stop_loss)
            if order.take_profit:
                params["takeProfit"] = str(order.take_profit)
        
        try:
            result = await asyncio.to_thread(
                self._client.place_order,
                **params
            )
        except Exception as e:
            raise OrderError(f"Bybit order failed: {e}") from e
        
        if result.get("retCode") != 0:
            raise OrderError(f"Bybit rejected order: {result.get('retMsg')}")
        
        return OrderResponse(
            venue_order_id=result["result"]["orderId"],
            idempotency_key=order.idempotency_key,
            status="new",
            raw=result
        )
    
    async def cancel_order(self, symbol: str, order_id: str,
                            category: str = "linear") -> bool:
        result = await asyncio.to_thread(
            self._client.cancel_order,
            category=category,
            symbol=symbol,
            orderId=order_id
        )
        return result.get("retCode") == 0
    
    async def cancel_all_orders(self, category: str = "linear",
                                  symbol: Optional[str] = None) -> int:
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol
        else:
            params["settleCoin"] = "USDT"
        
        result = await asyncio.to_thread(
            self._client.cancel_all_orders,
            **params
        )
        return len(result["result"].get("list", []))
    
    async def close_position(self, symbol: str,
                              category: str = "linear") -> OrderResponse:
        """Closes position with reduce-only market order."""
        positions = await self.get_positions()
        target = next((p for p in positions if p.symbol == symbol), None)
        
        if not target or target.side == "none":
            raise OrderError(f"No open position for {symbol}")
        
        close_side = "sell" if target.side == "long" else "buy"
        
        from uuid import uuid4
        return await self.place_order(OrderRequest(
            symbol=symbol,
            side=close_side,
            type="market",
            qty=target.qty,
            reduce_only=True,
            idempotency_key=f"close-{uuid4()}",
            category=category
        ))
    
    # ──────────────────────────────────────────────
    # WebSocket
    # ──────────────────────────────────────────────
    
    async def subscribe_klines(self, symbol: str, interval: str,
                                 category: str, callback) -> None:
        if self._ws_public is None:
            self._ws_public = WebSocket(
                testnet=self.testnet,
                channel_type=category,  # 'linear', 'spot', 'inverse'
            )
        self._ws_public.kline_stream(
            interval=interval,
            symbol=symbol,
            callback=callback
        )
    
    async def subscribe_orderbook(self, symbol: str, category: str,
                                    callback) -> None:
        if self._ws_public is None:
            self._ws_public = WebSocket(
                testnet=self.testnet,
                channel_type=category
            )
        self._ws_public.orderbook_stream(
            depth=50,
            symbol=symbol,
            callback=callback
        )
    
    async def subscribe_user_data(self, callback) -> None:
        if self._ws_private is None:
            self._ws_private = WebSocket(
                testnet=self.testnet,
                channel_type="private",
                api_key=self._client.api_key,
                api_secret=self._client.api_secret
            )
        self._ws_private.position_stream(callback=callback)
        self._ws_private.order_stream(callback=callback)
        self._ws_private.wallet_stream(callback=callback)
```

### 4.4 Implement Binance Adapter (Testnet only)

**`backend/services/venues/binance_adapter.py`:**

Keep existing Binance code but mark it clearly as **testnet/dev only**. This adapter exists for development sandbox and future multi-venue support.

```python
"""
Binance adapter — TESTNET / DEV USE ONLY.

This adapter is retained for:
1. Development sandbox (Binance testnet is more polished than Bybit testnet)
2. Future multi-venue cross-arbitrage (§9.10)

It must NEVER be used as primary live venue per migration decision.
"""
# ... existing Binance implementation, refactored to extend VenueAdapter ...
```

### 4.5 Venue Factory

**`backend/services/venues/__init__.py`:**

```python
from .base import VenueAdapter
from .bybit_adapter import BybitAdapter
from .binance_adapter import BinanceAdapter
from app.config import settings

def get_primary_venue() -> VenueAdapter:
    """Returns the configured primary trading venue."""
    if settings.PRIMARY_VENUE == "bybit":
        return BybitAdapter(
            api_key=settings.BYBIT_API_KEY,
            api_secret=settings.BYBIT_API_SECRET,
            testnet=settings.BYBIT_TESTNET
        )
    elif settings.PRIMARY_VENUE == "binance":
        # Should only happen in special cases
        return BinanceAdapter(
            api_key=settings.BINANCE_API_KEY,
            api_secret=settings.BINANCE_API_SECRET,
            testnet=settings.BINANCE_TESTNET
        )
    else:
        raise ValueError(f"Unknown PRIMARY_VENUE: {settings.PRIMARY_VENUE}")

def get_dev_venue() -> VenueAdapter:
    """Returns testnet venue for dev/paper trading."""
    if settings.DEV_VENUE == "binance_testnet":
        return BinanceAdapter(
            api_key=settings.BINANCE_TESTNET_API_KEY,
            api_secret=settings.BINANCE_TESTNET_API_SECRET,
            testnet=True
        )
    else:  # bybit_testnet
        return BybitAdapter(
            api_key=settings.BYBIT_API_KEY,
            api_secret=settings.BYBIT_API_SECRET,
            testnet=True
        )

__all__ = ["VenueAdapter", "BybitAdapter", "BinanceAdapter",
           "get_primary_venue", "get_dev_venue"]
```

### 4.6 Verification Checklist

```
[ ] base.py defines complete VenueAdapter abstract class
[ ] BybitAdapter implements ALL abstract methods
[ ] BinanceAdapter refactored to extend VenueAdapter (for testnet/dev)
[ ] verify_api_safety() refuses bot start if Withdraw enabled or no IP whitelist
[ ] place_order() supports stop_loss + take_profit attached natively
[ ] All Bybit calls include 'category' parameter
[ ] All idempotency keys passed via 'orderLinkId'
[ ] get_positions() filters out zero-size positions
[ ] Tests for adapter using pybit testnet pass
```

---

## 5. Phase C: Symbol & Market Data

### 5.1 Symbol Normalization

Both Binance and Bybit use `BTCUSDT` format for major pairs, but edge cases exist:

```python
# backend/services/venues/symbol_normalizer.py

class SymbolNormalizer:
    """Convert between venue-specific and canonical symbol formats."""
    
    @staticmethod
    def to_canonical(symbol: str, venue: str, category: str) -> str:
        """
        Returns canonical format: 'BTC-USDT-PERP' or 'BTC-USDT-SPOT'
        """
        # Bybit and Binance are mostly identical for major pairs
        # Edge cases: some Bybit perps have suffix like '1000PEPEUSDT'
        # Canonical handles these explicitly.
        ...
    
    @staticmethod
    def from_canonical(canonical: str, venue: str) -> tuple[str, str]:
        """
        Returns (symbol, category) for given venue.
        E.g. ('BTC-USDT-PERP', 'bybit') -> ('BTCUSDT', 'linear')
        """
        ...
```

### 5.2 Symbol Universe Manager Updates

**`backend/services/edge/universe_manager.py` changes:**

```python
# Update score_pair to use Bybit-specific filters

def score_pair(self, pair) -> PairScore:
    """
    Filters for Bybit linear perpetuals:
    - Daily volume: $20M - $200M (mid-cap zone)
    - Listed > 90 days
    - Status == "Trading" (Bybit term)
    - Not in maintenance
    - Has funding rate (i.e., is perpetual not futures-with-expiry)
    
    Bybit-specific: skip "delisting" status pairs even if technically active.
    """
```

### 5.3 Verification Checklist

```
[ ] Canonical symbol format defined and used in all internal models
[ ] Symbol Universe Manager pulls from Bybit instruments-info endpoint
[ ] Mid-cap filter ($20M-$200M) calibrated for Bybit volumes
[ ] Test: universe contains 50+ valid Bybit pairs
[ ] Test: symbols round-trip canonical ↔ Bybit format correctly
```

---

## 6. Phase D: Order Execution

### 6.1 Execution Service Updates

The `execution_service` from blueprint §6.4 must be updated:

**Key changes:**

1. Pass `category="linear"` (or "spot") to all Bybit calls
2. Use `orderLinkId` (Bybit's term) for idempotency keys
3. Don't attempt OCO orders — use Bybit's native TP/SL attachment
4. Handle Bybit's response format

**Critical pattern for SL/TP attachment:**

```python
# OLD (Binance OCO approach):
# 1. Place entry order
# 2. After fill, place separate OCO with SL + TP

# NEW (Bybit attached approach):
order = OrderRequest(
    symbol="BTCUSDT",
    side="buy",
    type="limit",
    qty=Decimal("0.01"),
    price=Decimal("50000"),
    stop_loss=Decimal("48000"),      # Attached at entry
    take_profit=Decimal("52000"),    # Attached at entry
    idempotency_key=str(uuid4()),
    category="linear"
)
response = await venue.place_order(order)
# Done. SL/TP automatically active when entry fills.
```

This is **better** than Binance's pattern because there's no race condition between entry fill and SL placement.

### 6.2 Position Reconciliation

Update the reconciliation loop (Section 2.3 of blueprint):

```python
# backend/services/execution/reconciliation.py

async def reconcile_with_venue():
    """
    Every 5 seconds: pull truth from Bybit, resolve discrepancies.
    
    Bybit-specific:
    - Use settleCoin='USDT' to query all linear positions at once
    - UTA: spot and perp balances queried via same API
    """
    venue = get_primary_venue()
    
    bybit_positions = await venue.get_positions()
    bybit_orders = await venue.get_open_orders(category="linear")
    bybit_balance = await venue.get_balance()
    
    # ... rest of reconciliation logic ...
```

### 6.3 Verification Checklist

```
[ ] All order placement uses idempotency keys via orderLinkId
[ ] SL/TP attached at entry, not separately
[ ] No code path attempts OCO orders
[ ] Reconciliation pulls from Bybit truth every 5s
[ ] Test: place + cancel order round-trip on testnet
[ ] Test: place order with SL/TP, verify they're active
[ ] Test: reduce-only flag works for closing positions
```

---

## 7. Phase E: Funding Rate & Futures Specific

### 7.1 Funding Arb Strategy Updates

**`backend/strategies/funding_arb/strategy.py`:**

```python
class FundingArbStrategy(Strategy):
    """
    Bybit-optimized funding arbitrage.
    
    Bybit advantages over Binance for this strategy:
    - UTA mode: same USDT margin for both legs (no transfer needed)
    - Higher capital efficiency (critical for $100 capital)
    - Simpler reconciliation (one balance, one position list)
    """
    
    async def generate_signal(self, market_data, params):
        # Get current funding rate from Bybit linear
        funding_info = await self.venue.get_funding_rate(symbol)
        
        if funding_info.current_rate < params["entry_funding_threshold_8h"]:
            return None
        
        # Check basis (spot vs perp price)
        spot_ticker = await self.venue.get_ticker(symbol, category="spot")
        perp_ticker = await self.venue.get_ticker(symbol, category="linear")
        
        basis = (Decimal(perp_ticker["lastPrice"]) - 
                 Decimal(spot_ticker["lastPrice"])) / Decimal(spot_ticker["lastPrice"])
        
        if abs(basis) > params["max_basis_at_entry"]:
            return None  # Basis too wide, skip
        
        # Generate paired signals: short perp + long spot
        return FundingArbSignal(
            perp_leg=Signal(symbol=symbol, side="short", category="linear", ...),
            spot_leg=Signal(symbol=symbol, side="long", category="spot", ...),
            entry_funding_rate=funding_info.current_rate,
            entry_basis=basis
        )
```

### 7.2 Funding Collection Tracking

Bybit credits funding directly to UTA balance every 8 hours. The bot must:

1. Snapshot balance before funding time (every 7:55, 15:55, 23:55 UTC)
2. Snapshot balance after funding (every 8:05, 16:05, 0:05 UTC)
3. Difference = funding paid/received
4. Persist to `funding_arb_positions.funding_collected_total`

```python
# backend/services/funding/collector.py

async def track_funding_collection():
    """Cron job at 5 minutes past each funding time."""
    
    funding_times_utc = ["00:05", "08:05", "16:05"]
    
    # For each active funding arb position:
    for arb_position in active_arb_positions:
        before_balance = arb_position.last_balance_snapshot
        after_balance = await venue.get_balance()
        
        funding_received = after_balance["USDT"] - before_balance["USDT"]
        # Adjust for any other PnL between snapshots
        # ...
        
        await update_funding_collected(arb_position.id, funding_received)
```

### 7.3 Verification Checklist

```
[ ] Funding rate fetched correctly from Bybit linear endpoint
[ ] Spot leg uses category="spot", perp leg uses category="linear"
[ ] UTA mode confirmed at boot (single balance for both legs)
[ ] Funding collection tracker runs every 8h + 5min
[ ] Test on testnet: open arb position, verify both legs placed correctly
[ ] Test: close arb position closes both legs atomically
```

---

## 8. Phase F: WebSocket Streams

### 8.1 Public Streams

**Bybit WebSocket URL structure:**

```
wss://stream.bybit.com/v5/public/linear      # USDT perpetual
wss://stream.bybit.com/v5/public/spot         # Spot
wss://stream.bybit.com/v5/public/inverse      # Coin-margined
wss://stream.bybit.com/v5/public/option       # Options

# Testnet:
wss://stream-testnet.bybit.com/v5/public/linear
```

The `pybit` library handles this internally. Just specify `channel_type`.

### 8.2 Subscription Topics

| Stream | Bybit Topic | Binance Equivalent |
|---|---|---|
| Klines | `kline.{interval}.{symbol}` | `{symbol}@kline_{interval}` |
| Orderbook | `orderbook.{depth}.{symbol}` | `{symbol}@depth{depth}` |
| Trades | `publicTrade.{symbol}` | `{symbol}@trade` |
| Tickers | `tickers.{symbol}` | `{symbol}@ticker` |
| Liquidations | `liquidation.{symbol}` | `{symbol}@forceOrder` |

### 8.3 Reconnection Strategy

Bybit WebSocket can disconnect. The `pybit` library has built-in reconnection but you must:

1. Set heartbeat interval to 20 seconds (Bybit recommends)
2. Implement gap detection on klines (compare last received timestamp)
3. On reconnect, fetch via REST any missed candles

```python
# backend/services/market_data/ws_manager.py

class BybitWSManager:
    HEARTBEAT_INTERVAL = 20  # seconds, Bybit recommendation
    
    async def on_disconnect(self):
        log.warning("Bybit WS disconnected, reconnecting...")
        await self.notify("ws_disconnect_bybit")
    
    async def on_reconnect(self):
        log.info("Bybit WS reconnected, filling gaps...")
        # Fetch via REST any missed candles
        await self.fill_kline_gaps()
```

### 8.4 Private Streams (User Data)

Bybit private streams require authentication. `pybit` handles signing automatically:

```python
ws_private = WebSocket(
    testnet=False,
    channel_type="private",
    api_key=key,
    api_secret=secret
)

ws_private.position_stream(callback=on_position_update)
ws_private.order_stream(callback=on_order_update)
ws_private.wallet_stream(callback=on_wallet_update)
ws_private.execution_stream(callback=on_execution_update)
```

### 8.5 Verification Checklist

```
[ ] Public WS subscribes to klines + orderbook successfully
[ ] Private WS subscribes to position/order/wallet streams
[ ] Reconnection tested: kill WS connection, verify reconnect within 5s
[ ] Gap detection tested: simulate missed candles, verify REST backfill
[ ] Heartbeat working (20s interval)
[ ] Test 24h continuous WS run, no leaks
```

---

## 9. Phase G: Testing & Validation

### 9.1 Test Strategy

**Three test layers:**

1. **Unit tests** — Pure logic, mock venue adapter
2. **Integration tests** — Use Bybit testnet, real API calls
3. **Smoke tests** — Run paper-trade scenarios end-to-end

### 9.2 Required Test Coverage

```python
# tests/integration/test_bybit_adapter.py

@pytest.mark.integration
class TestBybitAdapter:
    """All tests run against Bybit testnet with throwaway API key."""
    
    async def test_verify_api_safety_passes_clean_key(self):
        """Clean testnet key with no withdraw + IP whitelist passes."""
        ...
    
    async def test_verify_api_safety_refuses_withdraw_enabled(self):
        """Mock API response with withdraw permission, expect SecurityError."""
        ...
    
    async def test_get_symbols_returns_valid_universe(self):
        """Linear symbols list contains BTCUSDT and >100 pairs."""
        ...
    
    async def test_place_limit_order_with_sltp(self):
        """Place limit + SL + TP, verify all three params accepted."""
        ...
    
    async def test_idempotency_key_prevents_duplicates(self):
        """Place order twice with same orderLinkId, second is rejected."""
        ...
    
    async def test_cancel_order_after_placement(self):
        """Place → cancel round-trip works."""
        ...
    
    async def test_funding_rate_fetched(self):
        """get_funding_rate returns valid Decimal for BTCUSDT."""
        ...
    
    async def test_position_reconciliation(self):
        """Open position → query positions → matches."""
        ...
    
    async def test_close_position_with_reduce_only(self):
        """Open then close, verify position is zero after."""
        ...
```

### 9.3 Migration Validation Test

Create a single end-to-end test that validates the migration:

```python
# tests/integration/test_migration_smoke.py

@pytest.mark.smoke
async def test_funding_arb_full_cycle_on_bybit_testnet():
    """
    End-to-end smoke test:
    1. Initialize bot with Bybit testnet
    2. Verify API safety check passes
    3. Set position mode to one-way
    4. Identify high-funding pair (or use mock)
    5. Open arb position (short perp + long spot)
    6. Verify both legs placed
    7. Wait/simulate funding period
    8. Close arb position
    9. Verify both legs closed
    10. Verify final balance > initial (in mock or wait scenario)
    """
```

### 9.4 Performance Benchmarks

After migration, run these benchmarks and compare to Binance baseline:

| Metric | Binance Baseline | Bybit Target | Pass Criteria |
|---|---|---|---|
| Order placement latency (p50) | 50ms | 100ms | < 200ms |
| Order placement latency (p99) | 200ms | 300ms | < 500ms |
| WS message latency | 30ms | 50ms | < 150ms |
| Reconciliation cycle | 200ms | 250ms | < 500ms |
| Memory after 24h | <500MB | <500MB | < 800MB |

### 9.5 Verification Checklist

```
[ ] All unit tests pass
[ ] All integration tests pass on Bybit testnet
[ ] Smoke test: full funding arb cycle on testnet succeeds
[ ] Performance benchmarks meet criteria
[ ] 24h continuous run with no memory leaks
[ ] All circuit breakers tested with simulated Bybit failures
```

---

## 10. Phase H: Documentation Updates

### 10.1 Files to Update

```
[ ] README.md             - Project name, primary venue, setup steps
[ ] docs/ARCHITECTURE.md  - Venue adapter section, Bybit-specific notes
[ ] docs/DEPLOYMENT.md    - Bybit API setup instructions
[ ] docs/RUNBOOK.md       - Bybit-specific incident response
[ ] docs/STRATEGY_GUIDE.md- Funding arb on Bybit specifics
[ ] CHANGELOG.md          - Document migration
```

### 10.2 New Documentation File

Create **`docs/VENUE_GUIDE.md`** explaining:
- Why Bybit is primary
- How to switch to testnet
- How to add a new venue (for future multi-venue work)
- Known Bybit quirks

### 10.3 Update Blueprint

Update the main blueprint to reflect changes:

```diff
- ## 4. Tech Stack
- - python-binance — primary
- - CCXT — secondary

+ ## 4. Tech Stack
+ - pybit — primary (Bybit)
+ - python-binance — testnet/dev only
+ - CCXT — abstraction layer
```

---

## 11. Bybit-Specific Setup Instructions

### 11.1 Create Bybit Account

1. Go to https://www.bybit.com (or `https://www.bybit.com/en/invite/?ref=YOURREF` if you have referral)
2. Sign up with email + password + 2FA (Google Authenticator)
3. **Indonesia accessibility:** Bybit generally accessible from Indonesia without VPN
4. Complete KYC Level 1 (recommended for higher API limits):
   - Identity verification (KTP)
   - Selfie
   - Should complete within minutes to hours

### 11.2 Enable Unified Trading Account (UTA)

**This is critical for capital efficiency.**

1. After login → Account → Switch to Unified Trading Account
2. Confirm migration (one-way action, but recommended for our use case)
3. Verify UTA active: Profile shows "Unified Trading Account"

### 11.3 Create API Key

1. Profile → API Management → Create New Key
2. Select **System-generated API Keys**
3. Name: `aiq-bot-prod` (or `aiq-bot-testnet`)
4. **API key permissions** — set EXACTLY as below:

```
✅ Read-Write
   ✅ Orders          (place/cancel/query orders)
   ✅ Positions       (manage positions)
   ✅ Trade           (execute trades)
   ✅ Wallet (Read only - for balance queries)

❌ Withdrawal         ← MUST BE OFF
❌ Internal Transfer  ← OFF (we don't need it for UTA)
❌ Sub-account        ← OFF
❌ Affiliate          ← OFF
❌ Loan               ← OFF
❌ Spot Trading API   ← Wait, we DO need this for spot leg!
   ↑ Re-check: enable Spot Trading
```

**Corrected permissions for our use case:**

```
✅ Contract — Orders, Positions, Trade  (for perp leg)
✅ Spot — Trade                          (for spot leg)
✅ Wallet — Account Transfer             (UTA needs this internally)
✅ Wallet — Subaccount Transfer (OFF unless using sub-accounts)
❌ Withdraw                              ← ABSOLUTE OFF
```

5. **IP Restriction** — MANDATORY:
   - Toggle "Restrict access by IP address" ON
   - Add IP: your VPS IP (e.g., `203.0.113.45`)
   - For dev: also add your home/office IP
   - Bybit allows up to 10 IPs

6. Confirm with 2FA + email verification
7. **Copy API Key + Secret immediately** — Secret shown only once
8. Store in password manager + encrypted backup

### 11.4 First-Time Bot Setup

After creating API key:

```bash
# 1. Add to .env
echo "BYBIT_API_KEY=your-key-here" >> .env
echo "BYBIT_API_SECRET=your-secret-here" >> .env
echo "BYBIT_TESTNET=false" >> .env
echo "PRIMARY_VENUE=bybit" >> .env

# 2. Test connection
docker compose exec backend python -m scripts.test_bybit_connection

# Expected output:
# ✓ API key valid
# ✓ Withdraw permission DISABLED
# ✓ IP restriction ACTIVE
# ✓ Position mode: One-Way
# ✓ Account type: UNIFIED
# ✓ Available balance: 100.00 USDT
```

### 11.5 Deposit Funds

For first deposit ($100 starting capital):

1. Bybit → Assets → Deposit
2. Choose USDT (TRC20 if from Indonesian exchange like Indodax — cheaper fees)
3. Send from your source (Indodax, Tokocrypto, or another exchange)
4. Wait for confirmations (~5-15 min for TRC20)
5. Verify balance in UTA

**Recommended:** Don't deposit until bot is fully validated on testnet (Phase 5 of blueprint roadmap).

---

## 12. Testnet Configuration

### 12.1 Bybit Testnet

**URL:** https://testnet.bybit.com

1. Create separate account on testnet (different from mainnet)
2. Get free testnet USDT from faucet: https://testnet.bybit.com/app/user/api-management
3. Create API key with same permission structure as production
4. IP whitelist (or skip for testnet — less critical)

**.env for testnet:**

```env
BYBIT_API_KEY=<testnet-key>
BYBIT_API_SECRET=<testnet-secret>
BYBIT_TESTNET=true
```

### 12.2 Binance Testnet (For Dev Phase 0-4)

If preferred for dev (Binance testnet is more polished):

1. https://testnet.binance.vision → Generate API key
2. https://testnet.binancefuture.com → Generate Futures testnet key
3. Free fake USDT provided

**.env for Binance dev mode:**

```env
USE_BINANCE_FOR_DEV=true
DEV_VENUE=binance_testnet
BINANCE_TESTNET_API_KEY=<key>
BINANCE_TESTNET_API_SECRET=<secret>
```

### 12.3 Switching Modes

The codebase should support easy switching:

```bash
# Run on Bybit live
PRIMARY_VENUE=bybit BYBIT_TESTNET=false docker compose up

# Run on Bybit testnet
PRIMARY_VENUE=bybit BYBIT_TESTNET=true docker compose up

# Run on Binance testnet (dev only)
PRIMARY_VENUE=binance BINANCE_TESTNET=true docker compose up
```

---

## 13. Common Pitfalls

### 13.1 Forgetting `category` Parameter

**Symptom:** Bybit returns error `"category is required"`.

**Fix:** Every API call to Bybit V5 must include `category` parameter (`spot`, `linear`, `inverse`, or `option`).

```python
# WRONG
client.get_orderbook(symbol="BTCUSDT")

# RIGHT
client.get_orderbook(category="linear", symbol="BTCUSDT")
```

### 13.2 Idempotency Key Format

Bybit's `orderLinkId` has constraints:
- Max 36 characters
- Alphanumeric + hyphens only
- Must be unique per account within 24 hours

```python
# WRONG — UUID with curly braces from some libs
order_link_id = "{a1b2c3...}"

# RIGHT — clean UUID4 string
order_link_id = str(uuid.uuid4())   # 36 chars, hyphens, alphanumeric
```

### 13.3 UTA Mode Confusion

If account is in **Classic mode** (not UTA), spot and perp wallets are separate. Our bot assumes UTA. Verify at boot:

```python
async def verify_uta_mode():
    info = await client.get_account_info()
    if info["unifiedMarginStatus"] != 3:  # 3 = UTA Pro
        raise ConfigError("Account must be in Unified Trading Account mode")
```

### 13.4 Funding Rate Direction Confusion

In Bybit:
- **Positive funding rate** → Longs pay Shorts (we want to be **short** to receive)
- **Negative funding rate** → Shorts pay Longs (we want to be **long** to receive)

For our funding arb (capture positive rates):
- Short perp + Long spot → market neutral, collect funding

### 13.5 Position Size Decimal Precision

Bybit symbols have specific qty precision:

```python
# WRONG — too many decimals, will be rejected
qty = Decimal("0.0123456789")

# RIGHT — round to symbol's qtyStep
symbol_info = await venue.get_symbols("linear")
btc = next(s for s in symbol_info if s.symbol == "BTCUSDT")
qty = round_to_step(Decimal("0.0123456789"), btc.qty_step)
# E.g. if qty_step is 0.001, qty becomes 0.012
```

### 13.6 Spot Order Quantity vs Notional

Bybit Spot accepts orders by quantity OR by notional (USDT amount):

```python
# Buy 0.01 BTC (qty-based)
client.place_order(category="spot", symbol="BTCUSDT", side="Buy",
                   orderType="Market", qty="0.01")

# Buy $100 worth of BTC (notional-based, market order only)
client.place_order(category="spot", symbol="BTCUSDT", side="Buy",
                   orderType="Market", qty="100", marketUnit="quoteCoin")
```

For limit orders, always use base asset quantity. Adapter should normalize.

### 13.7 Rate Limit Differences

Bybit rate limits per endpoint, generally:
- 50 requests/second for public endpoints
- 10-20 requests/second for trade endpoints

Less generous than Binance's 1200/min total. Don't hammer Bybit:

```python
# Add semaphore in adapter
self._rate_limit = asyncio.Semaphore(10)  # max 10 concurrent

async def _rate_limited_call(self, fn, *args, **kwargs):
    async with self._rate_limit:
        return await asyncio.to_thread(fn, *args, **kwargs)
```

### 13.8 Decimal vs Float

Always use `Decimal` for prices/quantities. Bybit API returns strings:

```python
# WRONG
price = float(response["price"])   # Precision loss

# RIGHT
price = Decimal(response["price"])
```

---

## Migration Completion Checklist

After all phases complete, verify before going live:

```
PHASE A — Configuration
[ ] All Binance references updated to Bybit (or marked as testnet/dev)
[ ] .env structure clean
[ ] config files reflect Bybit fees + symbols

PHASE B — Adapter Layer
[ ] BybitAdapter implements full VenueAdapter interface
[ ] verify_api_safety() refuses unsafe keys
[ ] All abstract methods covered

PHASE C — Symbols
[ ] Universe Manager works with Bybit
[ ] Canonical symbol format used internally

PHASE D — Execution
[ ] Orders use orderLinkId for idempotency
[ ] SL/TP attached at entry (no separate OCO)
[ ] Reconciliation pulls from Bybit

PHASE E — Funding Arb
[ ] Funding rate fetched correctly
[ ] Spot + Perp legs use correct categories
[ ] UTA mode verified at boot

PHASE F — WebSocket
[ ] Public + Private streams work
[ ] Reconnection tested
[ ] 24h stability verified

PHASE G — Testing
[ ] Unit + integration tests pass
[ ] Smoke test on Bybit testnet succeeds
[ ] Performance benchmarks met

PHASE H — Documentation
[ ] All docs updated
[ ] Blueprint v2.1 patches applied
[ ] CHANGELOG entry added

PRE-LIVE
[ ] Bybit account KYC complete
[ ] UTA mode active
[ ] API key created with correct permissions
[ ] IP whitelist set
[ ] Withdrawal DISABLED (verified)
[ ] $100 deposited
[ ] Bot connected to mainnet successfully
[ ] All Phase 5 gate criteria from blueprint met
```

---

## Codex / Claude Code Master Prompt for Migration

```
You are migrating AI-Quant-Bot from Binance to Bybit as primary venue.

REFERENCE: BINANCE-TO-BYBIT-MIGRATION.md (this document)

ABSOLUTE RULES:
1. Follow phases A through H in order
2. Each phase has a verification checklist — confirm ALL items before next phase
3. CCXT abstraction stays — Bybit becomes primary, Binance becomes testnet/dev
4. NEVER use Binance for live trading after migration
5. All Bybit API calls MUST include category parameter
6. Idempotency keys go via orderLinkId (max 36 chars, alphanumeric+hyphens)
7. UTA mode is mandatory — verify at boot
8. Funding arb uses Bybit's native SL/TP attachment, NOT OCO
9. verify_api_safety() must refuse Withdraw permission and missing IP whitelist
10. All money math uses Decimal, never float

START WITH: Phase A (Configuration & Naming)

After each phase:
- Show files changed
- Run tests
- Confirm verification checklist
- Wait for user approval before next phase

Do NOT skip phases or combine them.
```

---

**End of Migration Guide**

*Migrate carefully. Test ruthlessly. Trade safely on Bybit.*
