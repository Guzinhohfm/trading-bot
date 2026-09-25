from decimal import Decimal


def ema(values: list[Decimal], period: int) -> list[Decimal | None]:
    """EMA com semente na media simples dos primeiros `period` valores."""
    if period < 1:
        raise ValueError("period deve ser >= 1")
    result: list[Decimal | None] = [None] * len(values)
    if len(values) < period:
        return result
    alpha = Decimal(2) / Decimal(period + 1)
    seed = sum(values[:period], Decimal("0")) / Decimal(period)
    result[period - 1] = seed
    previous = seed
    for index in range(period, len(values)):
        current = alpha * values[index] + (Decimal(1) - alpha) * previous
        result[index] = current
        previous = current
    return result


def true_range(
    high: Decimal,
    low: Decimal,
    previous_close: Decimal,
) -> Decimal:
    return max(high - low, abs(high - previous_close), abs(low - previous_close))


def atr(
    highs: list[Decimal],
    lows: list[Decimal],
    closes: list[Decimal],
    period: int,
) -> list[Decimal | None]:
    """ATR com true range da spec e suavizacao de Wilder (RMA)."""
    if period < 1:
        raise ValueError("period deve ser >= 1")
    length = len(closes)
    result: list[Decimal | None] = [None] * length
    if length < period + 1 or len(highs) != length or len(lows) != length:
        if len(highs) != length or len(lows) != length:
            raise ValueError("high, low e close precisam ter o mesmo tamanho")
        return result

    ranges: list[Decimal] = []
    for index in range(1, length):
        ranges.append(true_range(highs[index], lows[index], closes[index - 1]))

    if len(ranges) < period:
        return result

    first = sum(ranges[:period], Decimal("0")) / Decimal(period)
    atr_index = period
    result[atr_index] = first
    previous = first
    for offset, current_range in enumerate(ranges[period:], start=period + 1):
        current = (previous * Decimal(period - 1) + current_range) / Decimal(period)
        result[offset] = current
        previous = current
    return result


def rsi(closes: list[Decimal], period: int) -> list[Decimal | None]:
    """RSI de Wilder. Valores ausentes ficam None; os demais ficam entre 0 e 100."""
    if period < 1:
        raise ValueError("period deve ser >= 1")
    result: list[Decimal | None] = [None] * len(closes)
    if len(closes) < period + 1:
        return result

    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for index in range(1, len(closes)):
        change = closes[index] - closes[index - 1]
        gains.append(change if change > 0 else Decimal("0"))
        losses.append(-change if change < 0 else Decimal("0"))

    avg_gain = sum(gains[:period], Decimal("0")) / Decimal(period)
    avg_loss = sum(losses[:period], Decimal("0")) / Decimal(period)
    result[period] = _rsi_from_averages(avg_gain, avg_loss)

    for offset, (gain, loss) in enumerate(
        zip(gains[period:], losses[period:], strict=True),
        start=period + 1,
    ):
        avg_gain = (avg_gain * Decimal(period - 1) + gain) / Decimal(period)
        avg_loss = (avg_loss * Decimal(period - 1) + loss) / Decimal(period)
        result[offset] = _rsi_from_averages(avg_gain, avg_loss)
    return result


def average_volume(volumes: list[Decimal], period: int) -> list[Decimal | None]:
    if period < 1:
        raise ValueError("period deve ser >= 1")
    result: list[Decimal | None] = [None] * len(volumes)
    if len(volumes) < period:
        return result
    window = sum(volumes[:period], Decimal("0"))
    result[period - 1] = window / Decimal(period)
    for index in range(period, len(volumes)):
        window += volumes[index] - volumes[index - period]
        result[index] = window / Decimal(period)
    return result


def _rsi_from_averages(avg_gain: Decimal, avg_loss: Decimal) -> Decimal:
    if avg_loss == 0:
        return Decimal("100") if avg_gain > 0 else Decimal("0")
    relative = avg_gain / avg_loss
    value = Decimal("100") - (Decimal("100") / (Decimal("1") + relative))
    if value < 0:
        return Decimal("0")
    if value > 100:
        return Decimal("100")
    return value
