"""Baixa candles publicos da Binance para data/<symbol>-<interval>.csv."""

from __future__ import annotations

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data"
URL = "https://api.binance.com/api/v3/klines"
LIMIT = 1000


def _klines(symbol: str, interval: str, cursor: int, end_ms: int) -> list:
    query = urllib.parse.urlencode(
        {
            "symbol": symbol,
            "interval": interval,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": LIMIT,
        }
    )
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(f"{URL}?{query}", timeout=60) as response:
                return json.load(response)
        except (TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    if last_error is not None:
        raise last_error
    return []


def fetch(symbol: str, interval: str, start: datetime, end: datetime) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{symbol}-{interval}.csv"
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    rows: list[list[str]] = []
    cursor = start_ms
    while cursor < end_ms:
        payload = _klines(symbol, interval, cursor, end_ms)
        if not payload:
            break
        for candle in payload:
            rows.append(
                [
                    str(candle[0]),
                    candle[1],
                    candle[2],
                    candle[3],
                    candle[4],
                    candle[5],
                ]
            )
        cursor = int(payload[-1][0]) + 1
        time.sleep(0.05)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        writer.writerows(rows)
    print(f"{path.name} {len(rows)}")
    return path


def ensure_from(symbol: str, interval: str, start: datetime, end: datetime) -> Path:
    """Completa o CSV existente com o trecho anterior, sem baixar de novo o que ja esta no arquivo."""
    path = OUT_DIR / f"{symbol}-{interval}.csv"
    if not path.exists():
        return fetch(symbol, interval, start, end)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        existing = list(reader)
    if not existing:
        return fetch(symbol, interval, start, end)
    first = int(existing[0][0])
    start_ms = int(start.timestamp() * 1000)
    if first <= start_ms:
        print(f"{path.name} {len(existing)}")
        return path
    rows: list[list[str]] = []
    cursor = start_ms
    while cursor < first:
        payload = _klines(symbol, interval, cursor, first - 1)
        if not payload:
            break
        for candle in payload:
            rows.append([str(candle[0]), candle[1], candle[2], candle[3], candle[4], candle[5]])
        cursor = int(payload[-1][0]) + 1
        time.sleep(0.05)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        writer.writerows(rows)
        writer.writerows(existing)
    print(f"{path.name} {len(rows) + len(existing)}")
    return path


def main(argv: list[str]) -> int:
    symbols = argv[1:] or ["BTCUSDT"]
    start = datetime(2017, 8, 17, tzinfo=timezone.utc)
    end = datetime(2026, 9, 26, tzinfo=timezone.utc)
    for symbol in symbols:
        ensure_from(symbol, "5m", start, end)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
