from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.market.candles import Candle


def aggregate_hours(candles: list[Candle]) -> list[Candle]:
    grouped: dict[datetime, list[Candle]] = {}
    order: list[datetime] = []
    for candle in candles:
        hour = candle.timestamp.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
        if hour not in grouped:
            order.append(hour)
            grouped[hour] = []
        grouped[hour].append(candle)

    bars: list[Candle] = []
    for hour in order:
        chunk = grouped[hour]
        bars.append(
            Candle(
                timestamp=hour,
                open=chunk[0].open,
                high=max(item.high for item in chunk),
                low=min(item.low for item in chunk),
                close=chunk[-1].close,
                volume=sum((item.volume for item in chunk), Decimal("0")),
            )
        )
    return bars


def load_candles(
    path: str | Path,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[Candle]:
    frame = pd.read_csv(path, dtype=str)
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"CSV sem colunas: {', '.join(sorted(missing))}")

    candles: list[Candle] = []
    for row in frame.itertuples(index=False):
        timestamp = _parse_timestamp(str(row.timestamp))
        if start is not None and timestamp < start:
            continue
        if end is not None and timestamp > end:
            continue
        candles.append(
            Candle(
                timestamp=timestamp,
                open=Decimal(row.open),
                high=Decimal(row.high),
                low=Decimal(row.low),
                close=Decimal(row.close),
                volume=Decimal(row.volume),
            )
        )
    return candles


def parse_range(start: str | None, end: str | None) -> tuple[datetime | None, datetime | None]:
    start_at = datetime.fromisoformat(start).replace(tzinfo=timezone.utc) if start else None
    end_at = None
    if end:
        end_at = datetime.fromisoformat(end).replace(tzinfo=timezone.utc) + timedelta(days=1) - timedelta(microseconds=1)
    return start_at, end_at


def _parse_timestamp(value: str) -> datetime:
    if value.isdigit():
        millis = int(value)
        seconds = millis / 1000 if millis > 10_000_000_000 else millis
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
