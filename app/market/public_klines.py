"""Candles fechados da API publica. Sem chave e sem ordem."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.market.candles import Candle

URL = "https://api.binance.com/api/v3/klines"
LIMIT = 1000
INTERVAL_MS = {"1h": 60 * 60 * 1000, "5m": 5 * 60 * 1000}


def parse_closed_klines(payload: list, *, now: datetime, interval: str) -> list[Candle]:
    step = INTERVAL_MS[interval]
    now_ms = int(now.timestamp() * 1000)
    candles: list[Candle] = []
    for row in payload:
        open_ms = int(row[0])
        close_ms = int(row[6])
        if close_ms >= now_ms or open_ms + step > now_ms:
            continue
        candles.append(
            Candle(
                timestamp=datetime.fromtimestamp(open_ms / 1000, tz=timezone.utc),
                open=Decimal(row[1]),
                high=Decimal(row[2]),
                low=Decimal(row[3]),
                close=Decimal(row[4]),
                volume=Decimal(row[5]),
            )
        )
    return candles


def fetch_closed_klines(
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    *,
    now: datetime | None = None,
    urlopen=urllib.request.urlopen,
) -> list[Candle]:
    """GET /api/v3/klines. O candle que ainda nao fechou fica de fora."""
    if interval not in INTERVAL_MS:
        raise ValueError(f"Intervalo nao suportado: {interval}")
    moment = now or datetime.now(timezone.utc)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    candles: list[Candle] = []
    cursor = start_ms
    while cursor < end_ms:
        query = urllib.parse.urlencode(
            {
                "symbol": symbol,
                "interval": interval,
                "startTime": cursor,
                "endTime": end_ms,
                "limit": LIMIT,
            }
        )
        with urlopen(f"{URL}?{query}", timeout=60) as response:
            payload = json.load(response)
        if not payload:
            break
        candles.extend(parse_closed_klines(payload, now=moment, interval=interval))
        cursor = int(payload[-1][0]) + INTERVAL_MS[interval]
        if len(payload) < LIMIT:
            break
    unique = {candle.timestamp: candle for candle in candles}
    return [unique[key] for key in sorted(unique)]


def public_window(days: int, *, now: datetime, warmup_days: int = 120) -> tuple[datetime, datetime, datetime]:
    end = now.astimezone(timezone.utc)
    trade_from = end - timedelta(days=days)
    start = trade_from - timedelta(days=warmup_days)
    return start, end, trade_from
