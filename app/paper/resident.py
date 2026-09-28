"""Dispara o mesmo sync-public quando a hora UTC fecha. Nao envia ordem."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

SETTLE_SECONDS = 15


def next_closed_hour(now: datetime, *, settle_seconds: int = SETTLE_SECONDS) -> datetime:
    """Proximo instante em que o candle de 1h ja fechou e a Binance ja publicou."""
    moment = now.astimezone(timezone.utc)
    hour = moment.replace(minute=0, second=0, microsecond=0)
    this_close = hour + timedelta(seconds=settle_seconds)
    if moment <= this_close:
        return this_close
    return hour + timedelta(hours=1, seconds=settle_seconds)


def run_resident(
    sync: Callable[[], int],
    *,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    sleep: Callable[[float], None] = time.sleep,
    cycles: int | None = None,
) -> int:
    done = 0
    while cycles is None or done < cycles:
        target = next_closed_hour(clock())
        delay = (target - clock()).total_seconds()
        print(f"Paper residente: proxima leitura {target:%Y-%m-%d %H:%M:%S} UTC.")
        if delay > 0:
            sleep(delay)
        try:
            code = sync()
        except Exception as exc:
            print(f"Paper residente: leitura falhou ({exc}). Aguarda a proxima hora.")
            code = 0
        done += 1
        if code:
            return code
    return 0
