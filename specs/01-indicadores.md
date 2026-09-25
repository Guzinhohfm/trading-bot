# Indicadores

## Objetivo

Calcular EMA, RSI, ATR e media de volume com o mesmo metodo no backtest e no robo.

## Invariantes

- EMA usa o fechamento. `alpha = 2 / (N + 1)`. A semente e a media simples dos primeiros N fechamentos. A partir dai, `EMA_t = alpha * Close_t + (1 - alpha) * EMA_{t-1}`.
- EMA20 usa `alpha = 2/21`. EMA50 usa `alpha = 2/51`.
- RSI 14 e a versao de Wilder. O resultado fica entre 0 e 100. Sem perdas medias o RSI vale 100.
- ATR 14 usa o true range `max(high-low, abs(high-close anterior), abs(low-close anterior))` e a suavizacao de Wilder. O primeiro ATR e a media dos primeiros 14 true ranges.
- Media de volume e a media simples dos ultimos 20 volumes, incluindo o candle atual.
- Serie mais curta que o periodo devolve `None` naquela posicao. Indicador ausente nao gera sinal.

## Fora de escopo

Nao ha sinal de compra nem acesso a rede neste modulo.
