"""Avisa compra e saida novas no Telegram. Nao envia ordem."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from datetime import timezone

from app.config.settings import Settings
from backtesting.metrics import BacktestReport

URL = "https://api.telegram.org/bot{token}/sendMessage"


@dataclass(frozen=True)
class Notice:
    key: str
    text: str


def operation_notices(symbol: str, report: BacktestReport) -> list[Notice]:
    notices: list[Notice] = []
    for trade in report.closed_trades:
        opened = trade.opened_at.astimezone(timezone.utc)
        closed = trade.closed_at.astimezone(timezone.utc)
        notices.append(
            Notice(
                f"close:{symbol}:{opened.isoformat()}:{closed.isoformat()}",
                (
                    f"{symbol} paper\n"
                    f"Saida {trade.reason} {closed:%Y-%m-%d %H:%M} UTC\n"
                    f"Entrada {trade.entry_market} em {opened:%Y-%m-%d %H:%M} UTC\n"
                    f"Preco de saida {trade.exit_market}\n"
                    f"Liquido {trade.net_pnl:.2f} USDT\n"
                    "Nenhuma ordem enviada na Binance."
                ),
            )
        )
    position = report.open_position
    if position is not None:
        opened = position.opened_at.astimezone(timezone.utc)
        notices.append(
            Notice(
                f"open:{symbol}:{opened.isoformat()}",
                (
                    f"{symbol} paper\n"
                    f"Compra {opened:%Y-%m-%d %H:%M} UTC\n"
                    f"Preco {position.entry_market}\n"
                    f"Quantidade {position.quantity}\n"
                    f"Stop {position.stop}\n"
                    f"Alvo {position.take_profit}\n"
                    "Nenhuma ordem enviada na Binance."
                ),
            )
        )
    return notices


def pending_notices(symbol: str, report: BacktestReport, known: set[str]) -> list[Notice]:
    ready = f"ready:{symbol}"
    if ready not in known:
        return []
    return [notice for notice in operation_notices(symbol, report) if notice.key not in known]


def baseline_keys(symbol: str, report: BacktestReport) -> list[str]:
    return [f"ready:{symbol}", *[notice.key for notice in operation_notices(symbol, report)]]


def send_message(token: str, chat_id: str, text: str, *, urlopen=urllib.request.urlopen) -> None:
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode()
    request = urllib.request.Request(
        URL.format(token=token),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=20):
        return None


def notify_new_operations(
    settings: Settings,
    symbol: str,
    report: BacktestReport,
    *,
    urlopen=urllib.request.urlopen,
) -> int:
    """Manda so o que ainda nao foi avisado. A primeira leitura marca o diario atual."""
    token = settings.telegram_bot_token.strip()
    chat_id = settings.telegram_chat_id.strip()
    if not token or not chat_id:
        return 0
    from app.storage.paper_store import load_notice_keys, save_notice_keys

    try:
        known = load_notice_keys(settings)
        if f"ready:{symbol}" not in known:
            send_message(
                token,
                chat_id,
                (
                    f"Paper {symbol} ligado.\n"
                    "Avisos so quando uma operacao nova abrir ou fechar.\n"
                    "Nenhuma ordem e enviada na Binance."
                ),
                urlopen=urlopen,
            )
            save_notice_keys(settings, baseline_keys(symbol, report))
            print("Telegram: avisos ligados. Operacoes ja existentes nao sao reenviadas.")
            return 0
        fresh = pending_notices(symbol, report, known)
        sent = 0
        for notice in fresh:
            send_message(token, chat_id, notice.text, urlopen=urlopen)
            save_notice_keys(settings, [notice.key])
            sent += 1
        if sent:
            print(f"Telegram: {sent} aviso(s).")
        return sent
    except Exception as exc:
        print(f"Telegram: aviso falhou ({type(exc).__name__}).")
        return 0
