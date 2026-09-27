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


def fetch(symbol: str, interval: str, start: datetime, end: datetime) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{symbol}-{interval}.csv"
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    rows: list[list[str]] = []
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
        with urllib.request.urlopen(f"{URL}?{query}", timeout=30) as response:
            payload = json.load(response)
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


def main(argv: list[str]) -> int:
    symbols = argv[1:] or ["BTCUSDT"]
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 9, 26, tzinfo=timezone.utc)
    for symbol in symbols:
        fetch(symbol, "5m", start, end)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
