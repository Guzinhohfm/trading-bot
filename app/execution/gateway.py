"""Ponto unico de envio. O paper usa a versao que recusa."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str
    quantity: Decimal


class DisabledGateway:
    """Nao ha cliente HTTP. Qualquer envio e erro."""

    def submit(self, request: OrderRequest) -> None:
        del request
        raise RuntimeError("Ordem real bloqueada. Paper nao envia ordem.")
