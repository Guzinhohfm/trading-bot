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
  - no 4h fechado: `EMA50 > EMA200`, `close > EMA200` e `EMA50` atual maior que a `EMA50` de 5 candles de 4h atras
  - no 1h, o candle anterior tocou ou perdeu a EMA20: `low anterior <= EMA20 anterior`
  - `40 <= RSI14 <= 55`
  - no 1h, a recuperacao fecha: `close > EMA20` e `close > high do candle de 1h anterior`
- A inclinacao da EMA50 e apenas `EMA50[t] > EMA50[t-5]`. Nao ha piso percentual.
- Volume e a distancia ate a maxima recente nao entram nesta versao.
- Posicao aberta, perda diaria e cooldown nao bloqueiam o BUY aqui. O risco e o backtest fazem isso.
- A estrategia nao emite **SELL**. Stop e take profit fecham a operacao.
- Qualquer regra falsa, ou indicador ausente, devolve **HOLD**.
- `explain` devolve `BUY` ou `HOLD` e marca cada regra que falhou.
- Os limites de RSI 40 e 55 entram. Low igual a EMA20 anterior conta como toque.

## Outros ativos

ETH, SOL, BNB, TRX, XRP e DOGE foram medidos com esta mesma regra. O resultado esta em `specs/07-ativos.md`. Nenhum substitui BTCUSDT e nenhum muda os limites desta spec.

## Fora de escopo

Stop, take profit, tamanho da posicao, cooldown e kill switch.
