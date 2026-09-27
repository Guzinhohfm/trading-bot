# Estrategia V1

## Objetivo

Transformar um candle fechado em `BUY`, `SELL` ou `HOLD`. A estrategia so le mercado.

## Contrato

`analyze(candle, indicators, position_open) -> BUY | SELL | HOLD`

## Invariantes

- **BUY** somente quando as cinco regras sao verdadeiras ao mesmo tempo:
  - `EMA rapida > EMA lenta` no candle de 1 hora
  - o ultimo dia UTC ja fechado tambem tem `EMA rapida > EMA lenta` nos fechamentos diarios. O dia corrente nao entra
  - `35 <= RSI <= 55`
  - `volume > media de volume`
  - a minima tocou a EMA rapida e o fechamento voltou para cima: `low <= EMA rapida`, `close > EMA rapida` e `(EMA rapida - low) / EMA rapida <= 0.01`
- O sinal vale em qualquer hora do dia UTC. Nao ha janela de pregao.
- Posicao aberta e limite diario nao bloqueiam o BUY aqui. O risco faz isso.
- A estrategia nao emite **SELL**. Stop e take profit fecham a operacao.
- Qualquer outra situacao, inclusive indicador ausente, fechamento ainda na EMA ou abaixo dela, devolve **HOLD**.
- Igualdade de volume com a media nao compra. Os limites de RSI 35 e 55 entram. O pavio de 1% abaixo da EMA rapida entra. Fechamento igual a EMA nao compra.

## Fora de escopo

Stop, take profit, tamanho da posicao e kill switch.
