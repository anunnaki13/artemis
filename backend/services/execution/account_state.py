from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    MarketSnapshot,
    SpotAccountBalance,
    SpotExecutionFill,
    SpotOrderFillState,
    SpotSymbolPosition,
    Symbol,
)


def parse_decimal(value: object, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal(default)


async def estimate_asset_value_usd(session: AsyncSession, asset: str, total: Decimal) -> Decimal | None:
    if asset == "USDT":
        return total

    symbol = f"{asset}USDT"
    latest_snapshot = await session.scalar(
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol == symbol)
        .order_by(MarketSnapshot.timestamp.desc())
        .limit(1)
    )
    if latest_snapshot is None or latest_snapshot.last_price is None:
        return None
    return total * latest_snapshot.last_price


async def estimate_symbol_mark_price(session: AsyncSession, symbol: str) -> Decimal | None:
    latest_snapshot = await session.scalar(
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol == symbol)
        .order_by(MarketSnapshot.timestamp.desc())
        .limit(1)
    )
    if latest_snapshot is None:
        return None
    if latest_snapshot.last_price is not None:
        return latest_snapshot.last_price
    if latest_snapshot.bid_price is not None and latest_snapshot.ask_price is not None:
        return (latest_snapshot.bid_price + latest_snapshot.ask_price) / Decimal("2")
    return latest_snapshot.bid_price or latest_snapshot.ask_price


class SpotAccountStateService:
    async def refresh_position_mark(
        self,
        session: AsyncSession,
        position: SpotSymbolPosition,
    ) -> SpotSymbolPosition:
        mark_price = await estimate_symbol_mark_price(session, position.symbol)
        position.last_mark_price = mark_price
        if mark_price is None or position.net_quantity == Decimal("0"):
            position.market_value_usd = Decimal("0") if position.net_quantity == Decimal("0") else None
            position.unrealized_pnl_usd = Decimal("0") if position.net_quantity == Decimal("0") else None
            await session.flush()
            return position

        position.market_value_usd = mark_price * position.net_quantity
        if position.average_entry_price is None:
            position.unrealized_pnl_usd = None
        else:
            position.unrealized_pnl_usd = (mark_price - position.average_entry_price) * position.net_quantity
        await session.flush()
        return position

    async def refresh_all_position_marks(
        self,
        session: AsyncSession,
        positions: list[SpotSymbolPosition],
    ) -> list[SpotSymbolPosition]:
        refreshed: list[SpotSymbolPosition] = []
        for position in positions:
            refreshed.append(await self.refresh_position_mark(session, position))
        return refreshed

    @staticmethod
    def build_order_key(client_order_id: str | None, venue_order_id: str | None) -> str:
        if client_order_id:
            return f"client:{client_order_id}"
        if venue_order_id:
            return f"venue:{venue_order_id}"
        raise ValueError("client_order_id or venue_order_id is required")

    async def resolve_fill_state(
        self,
        session: AsyncSession,
        *,
        client_order_id: str | None,
        venue_order_id: str | None,
    ) -> SpotOrderFillState | None:
        if client_order_id is None and venue_order_id is None:
            return None

        conditions = []
        if client_order_id is not None:
            conditions.append(SpotOrderFillState.client_order_id == client_order_id)
        if venue_order_id is not None:
            conditions.append(SpotOrderFillState.venue_order_id == venue_order_id)
        if not conditions:
            return None
        fill_state: SpotOrderFillState | None = await session.scalar(
            select(SpotOrderFillState).where(or_(*conditions)).limit(1)
        )
        return fill_state

    async def get_or_create_fill_state(
        self,
        session: AsyncSession,
        *,
        symbol: str,
        side: str,
        client_order_id: str | None,
        venue_order_id: str | None,
    ) -> SpotOrderFillState:
        state = await self.resolve_fill_state(
            session,
            client_order_id=client_order_id,
            venue_order_id=venue_order_id,
        )
        if state is None:
            state = SpotOrderFillState(
                order_key=self.build_order_key(client_order_id, venue_order_id),
                symbol=symbol,
                side=side.upper(),
                client_order_id=client_order_id,
                venue_order_id=venue_order_id,
                cumulative_quantity=Decimal("0"),
                cumulative_quote_quantity=Decimal("0"),
                source_event="executionReport",
            )
            session.add(state)
        else:
            state.symbol = symbol
            state.side = side.upper()
            if client_order_id is not None:
                state.client_order_id = client_order_id
            if venue_order_id is not None:
                state.venue_order_id = venue_order_id
        return state

    async def apply_outbound_account_position(
        self,
        session: AsyncSession,
        balances: list[dict[str, Any]],
    ) -> list[SpotAccountBalance]:
        updated: list[SpotAccountBalance] = []
        for balance in balances:
            asset = str(balance.get("a", "")).upper()
            if not asset:
                continue
            free = parse_decimal(balance.get("f"))
            locked = parse_decimal(balance.get("l"))
            total = free + locked
            total_value_usd = await estimate_asset_value_usd(session, asset, total)
            current = await session.get(SpotAccountBalance, asset)
            if current is None:
                current = SpotAccountBalance(asset=asset)
                session.add(current)
            current.free = free
            current.locked = locked
            current.total = total
            current.total_value_usd = total_value_usd
            current.last_delta = None
            current.updated_at = datetime.now(tz=timezone.utc)
            current.source_event = "outboundAccountPosition"
            await session.flush()
            updated.append(current)
        return updated

    async def apply_balance_delta(
        self,
        session: AsyncSession,
        *,
        asset: str,
        delta: Decimal,
    ) -> SpotAccountBalance:
        balance = await session.get(SpotAccountBalance, asset)
        if balance is None:
            balance = SpotAccountBalance(
                asset=asset,
                free=Decimal("0"),
                locked=Decimal("0"),
                total=Decimal("0"),
                last_delta=delta,
                source_event="balanceUpdate",
            )
            session.add(balance)
        balance.free += delta
        balance.total = balance.free + balance.locked
        balance.last_delta = delta
        balance.updated_at = datetime.now(tz=timezone.utc)
        balance.source_event = "balanceUpdate"
        balance.total_value_usd = await estimate_asset_value_usd(session, asset, balance.total)
        await session.flush()
        return balance

    async def apply_fill_delta(
        self,
        session: AsyncSession,
        *,
        symbol: str,
        side: str,
        execution_intent_id: int | None,
        source_strategy: str | None,
        client_order_id: str | None,
        venue_order_id: str | None,
        trade_id: int | None,
        last_quantity: Decimal,
        last_quote_quantity: Decimal,
    ) -> SpotSymbolPosition:
        position = await session.get(SpotSymbolPosition, symbol)
        symbol_row = await session.get(Symbol, symbol)
        base_asset = symbol_row.base_asset if symbol_row is not None else symbol.removesuffix("USDT")
        quote_asset = symbol_row.quote_asset if symbol_row is not None else "USDT"
        if position is None:
            position = SpotSymbolPosition(
                symbol=symbol,
                base_asset=base_asset,
                quote_asset=quote_asset,
                net_quantity=Decimal("0"),
                average_entry_price=None,
                last_mark_price=None,
                quote_exposure_usd=Decimal("0"),
                market_value_usd=None,
                realized_notional=Decimal("0"),
                realized_pnl_usd=Decimal("0"),
                unrealized_pnl_usd=None,
                source_event="executionReport",
            )
            session.add(position)

        price = (last_quote_quantity / last_quantity) if last_quantity != Decimal("0") else Decimal("0")
        side_normalized = side.upper()
        realized_pnl_delta = Decimal("0")
        if side_normalized == "BUY":
            new_quantity = position.net_quantity + last_quantity
            existing_cost = (position.average_entry_price or Decimal("0")) * position.net_quantity
            incoming_cost = price * last_quantity
            position.net_quantity = new_quantity
            position.average_entry_price = (
                (existing_cost + incoming_cost) / new_quantity if new_quantity != Decimal("0") else None
            )
            position.quote_exposure_usd = (position.average_entry_price or Decimal("0")) * new_quantity
        else:
            quantity_closed = min(position.net_quantity, last_quantity)
            remaining_quantity = position.net_quantity - last_quantity
            entry_price = position.average_entry_price or Decimal("0")
            position.net_quantity = remaining_quantity if remaining_quantity > Decimal("0") else Decimal("0")
            position.realized_notional += last_quote_quantity
            realized_pnl_delta = (price - entry_price) * quantity_closed
            position.realized_pnl_usd += realized_pnl_delta
            if position.net_quantity == Decimal("0"):
                position.average_entry_price = None
                position.quote_exposure_usd = Decimal("0")
            else:
                position.quote_exposure_usd = (position.average_entry_price or Decimal("0")) * position.net_quantity

        position.updated_at = datetime.now(tz=timezone.utc)
        position.source_event = "executionReport"
        await self.refresh_position_mark(session, position)
        execution_fill = SpotExecutionFill(
            symbol=symbol,
            side=side_normalized,
            execution_intent_id=execution_intent_id,
            source_strategy=source_strategy,
            client_order_id=client_order_id,
            venue_order_id=venue_order_id,
            trade_id=trade_id,
            quantity=last_quantity,
            quote_quantity=last_quote_quantity,
            price=price,
            realized_pnl_usd=realized_pnl_delta,
            post_fill_net_quantity=position.net_quantity,
            post_fill_average_entry_price=position.average_entry_price,
            source_event="executionReport",
        )
        session.add(execution_fill)
        await session.flush()
        return position

    async def apply_execution_fill(
        self,
        session: AsyncSession,
        *,
        symbol: str,
        side: str,
        execution_intent_id: int | None = None,
        source_strategy: str | None = None,
        client_order_id: str | None,
        venue_order_id: str | None,
        cumulative_quantity: Decimal,
        cumulative_quote_quantity: Decimal,
        last_trade_id: int | None = None,
    ) -> SpotSymbolPosition | None:
        fill_state = await self.get_or_create_fill_state(
            session,
            symbol=symbol,
            side=side,
            client_order_id=client_order_id,
            venue_order_id=venue_order_id,
        )

        previous_quantity = fill_state.cumulative_quantity or Decimal("0")
        previous_quote_quantity = fill_state.cumulative_quote_quantity or Decimal("0")
        delta_quantity = cumulative_quantity - previous_quantity
        delta_quote_quantity = cumulative_quote_quantity - previous_quote_quantity

        if delta_quantity < Decimal("0") or delta_quote_quantity < Decimal("0"):
            fill_state.cumulative_quantity = cumulative_quantity
            fill_state.cumulative_quote_quantity = cumulative_quote_quantity
            fill_state.last_trade_id = last_trade_id
            fill_state.updated_at = datetime.now(tz=timezone.utc)
            fill_state.source_event = "executionReport"
            await session.flush()
            return None

        fill_state.cumulative_quantity = cumulative_quantity
        fill_state.cumulative_quote_quantity = cumulative_quote_quantity
        fill_state.last_trade_id = last_trade_id
        fill_state.updated_at = datetime.now(tz=timezone.utc)
        fill_state.source_event = "executionReport"

        if delta_quantity == Decimal("0") or delta_quote_quantity == Decimal("0"):
            await session.flush()
            return None

        return await self.apply_fill_delta(
            session,
            symbol=symbol,
            side=side,
            execution_intent_id=execution_intent_id,
            source_strategy=source_strategy,
            client_order_id=client_order_id,
            venue_order_id=venue_order_id,
            trade_id=last_trade_id,
            last_quantity=delta_quantity,
            last_quote_quantity=delta_quote_quantity,
        )
