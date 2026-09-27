# Estrategia V1

## Objetivo

Transformar um candle de 1 hora fechado em `BUY` ou `HOLD` para BTCUSDT. A estrategia so le mercado. Ela nao precisa operar todo dia.

## Contrato

`analyze(candle, indicators, position_open) -> BUY | HOLD`

## Timeframes

- 4 horas define a tendencia, sempre no ultimo candle de 4 horas ja fechado.
- 1 hora procura a entrada.

## Invariantes

- **BUY** somente quando todas as regras abaixo sao verdadeiras:
  - no 4h: `EMA50 > EMA200`, `close > EMA200` e `EMA50` atual maior que a `EMA50` de 5 candles de 4h atras
  - no 1h: `|close - EMA20| / EMA20 <= 0.015`
  - `40 <= RSI14 <= 55`
  - `volume >= 1.1 * media de 20 volumes`
  - `close > high do candle anterior` e `close > EMA20`
  - a maxima dos ultimos 20 candles de 4h fechados e pelo menos `close * 1.10`
- Posicao aberta, perda diaria e cooldown nao bloqueiam o BUY aqui. O risco e o backtest fazem isso.
- A estrategia nao emite **SELL**. Stop e take profit fecham a operacao.
- Qualquer regra falsa, ou indicador ausente, devolve **HOLD**.
- Os limites de RSI 40 e 55 entram. Volume igual a 110% da media entra.

## Fora de escopo

Stop, take profit, tamanho da posicao, cooldown e kill switch.
