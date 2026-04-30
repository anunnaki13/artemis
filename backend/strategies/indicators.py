from decimal import Decimal


def simple_moving_average(values: list[Decimal], period: int) -> Decimal | None:
    if period <= 0 or len(values) < period:
        return None
    return sum(values[-period:]) / Decimal(period)

