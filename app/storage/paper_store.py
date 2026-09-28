"""Grava candles, decisoes e trades simulados. Nao envia ordem."""

from decimal import Decimal
from urllib.parse import unquote, urlparse

from app.config.settings import Settings
from app.market.candles import Candle
from app.paper.records import CandleNote
from backtesting.broker import ClosedTrade


def connection_kwargs(database_url: str) -> dict[str, object]:
    parsed = urlparse(database_url.replace("postgresql+psycopg://", "postgresql://", 1))
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "dbname": parsed.path.lstrip("/"),
    }


def save_public_run(
    settings: Settings,
    *,
    symbol: str,
    candles: list[Candle],
    notes: list[CandleNote],
    trades: tuple[ClosedTrade, ...] | list[ClosedTrade],
    summary: str,
) -> dict[str, int]:
    import psycopg

    with psycopg.connect(**connection_kwargs(settings.database_url)) as conn:
        _ensure_decision_key(conn)
        candle_count = _upsert_candles(conn, symbol, settings.timeframe, candles)
        decision_count = _upsert_decisions(conn, symbol, settings.timeframe, notes)
        trade_count = _replace_paper_trades(conn, symbol, trades)
        conn.execute(
            "INSERT INTO bot_logs (level, message) VALUES ('INFO', %s)",
            (summary,),
        )
        conn.commit()
    return {"candles": candle_count, "decisions": decision_count, "trades": trade_count}


def _ensure_decision_key(conn) -> None:
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS decisions_symbol_timeframe_mode_idx
        ON decisions (symbol, timeframe, candle_open_time, mode)
        """
    )


def _upsert_candles(conn, symbol: str, timeframe: str, candles: list[Candle]) -> int:
    rows = [
        (symbol, timeframe, candle.timestamp, candle.open, candle.high, candle.low, candle.close, candle.volume)
        for candle in candles
    ]
    if not rows:
        return 0
    conn.cursor().executemany(
        """
        INSERT INTO candles (symbol, timeframe, open_time, open, high, low, close, volume, closed)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true)
        ON CONFLICT (symbol, timeframe, open_time) DO UPDATE
        SET open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            closed = true
        """,
        rows,
    )
    return len(rows)


def _upsert_decisions(conn, symbol: str, timeframe: str, notes: list[CandleNote]) -> int:
    rows = [
        (
            symbol,
            timeframe,
            note.open_time,
            "paper",
            note.signal,
            note.close,
            note.volume,
            note.ema20,
            note.ema50,
            note.rsi,
            note.atr,
            note.avg_volume,
            note.price_distance,
            note.trend_ok,
            note.rsi_ok,
            note.volume_ok,
            note.price_ok,
            note.risk_decision,
            note.risk_reason,
        )
        for note in notes
    ]
    if not rows:
        return 0
    conn.cursor().executemany(
        """
        INSERT INTO decisions (
            symbol, timeframe, candle_open_time, mode, signal, close, volume,
            ema20, ema50, rsi14, atr14, avg_volume20, price_distance,
            trend_ok, rsi_ok, volume_ok, price_ok, risk_decision, risk_reason
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol, timeframe, candle_open_time, mode) DO UPDATE
        SET signal = EXCLUDED.signal,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            ema20 = EXCLUDED.ema20,
            ema50 = EXCLUDED.ema50,
            rsi14 = EXCLUDED.rsi14,
            atr14 = EXCLUDED.atr14,
            avg_volume20 = EXCLUDED.avg_volume20,
            price_distance = EXCLUDED.price_distance,
            trend_ok = EXCLUDED.trend_ok,
            rsi_ok = EXCLUDED.rsi_ok,
            volume_ok = EXCLUDED.volume_ok,
            price_ok = EXCLUDED.price_ok,
            risk_decision = EXCLUDED.risk_decision,
            risk_reason = EXCLUDED.risk_reason
        """,
        rows,
    )
    return len(rows)


def _replace_paper_trades(conn, symbol: str, trades: tuple[ClosedTrade, ...] | list[ClosedTrade]) -> int:
    conn.execute(
        """
        DELETE FROM trades
        WHERE order_id IN (
            SELECT id FROM orders WHERE mode = 'paper' AND symbol = %s AND client_order_id LIKE 'paper-%%'
        )
        """,
        (symbol,),
    )
    conn.execute(
        "DELETE FROM orders WHERE mode = 'paper' AND symbol = %s AND client_order_id LIKE 'paper-%%'",
        (symbol,),
    )
    count = 0
    for trade in trades:
        buy_id = _insert_order(
            conn,
            symbol,
            "BUY",
            trade.quantity,
            trade.entry_market,
            f"paper-{symbol}-{trade.opened_at.isoformat()}-BUY",
        )
        sell_id = _insert_order(
            conn,
            symbol,
            "SELL",
            trade.quantity,
            trade.exit_market,
            f"paper-{symbol}-{trade.closed_at.isoformat()}-SELL",
        )
        _insert_trade(conn, buy_id, symbol, "BUY", trade.quantity, trade.entry_market, Decimal("0"), Decimal("0"), None, trade.opened_at)
        _insert_trade(
            conn,
            sell_id,
            symbol,
            "SELL",
            trade.quantity,
            trade.exit_market,
            trade.fees,
            trade.slippage,
            trade.net_pnl,
            trade.closed_at,
        )
        count += 1
    return count


def _insert_order(conn, symbol: str, side: str, quantity: Decimal, price: Decimal, client_order_id: str) -> int:
    row = conn.execute(
        """
        INSERT INTO orders (client_order_id, symbol, side, type, quantity, price, status, mode)
        VALUES (%s, %s, %s, 'MARKET', %s, %s, 'FILLED', 'paper')
        RETURNING id
        """,
        (client_order_id, symbol, side, quantity, price),
    ).fetchone()
    return int(row[0])


def _insert_trade(conn, order_id, symbol, side, quantity, price, fee, slippage, realized, traded_at) -> None:
    conn.execute(
        """
        INSERT INTO trades (
            order_id, symbol, side, quantity, price, fee, slippage, realized_pnl, status, strategy, traded_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'FILLED', 'ema_rsi_atr_volume', %s)
        """,
        (order_id, symbol, side, quantity, price, fee, slippage, realized, traded_at),
    )
