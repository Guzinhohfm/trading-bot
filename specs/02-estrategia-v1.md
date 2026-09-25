# Estrategia V1

## Objetivo

Transformar um candle fechado em `BUY`, `SELL` ou `HOLD`. A estrategia so le mercado.

## Contrato

`analyze(candle, indicators, position_open) -> BUY | SELL | HOLD`

## Invariantes

- **BUY** somente quando as quatro regras sao verdadeiras ao mesmo tempo:
  - `EMA rapida > EMA lenta`
  - `35 <= RSI <= 55`
  - `volume > media de volume`
  - `|close - EMA rapida| / EMA rapida <= 0.01`
- Posicao aberta e limite diario nao bloqueiam o BUY aqui. O risco faz isso.
- **SELL** quando existe posicao aberta e `EMA rapida < EMA lenta`.
- Qualquer outra situacao, inclusive indicador ausente, devolve **HOLD**.
- Igualdade de volume com a media nao compra. Os limites de RSI 35 e 55 entram.

## Fora de escopo

Stop, take profit, tamanho da posicao e kill switch.
