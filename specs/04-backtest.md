# Backtest

## Objetivo

Rodar a mesma estrategia e o mesmo risco sobre candles historicos e imprimir o relatorio da spec.

## Invariantes

- O sinal nasce no fechamento. A entrada acontece no open do candle seguinte.
- Compra efetiva = preco * (1 + slippage). Venda efetiva = preco * (1 - slippage).
- `Net P&L = Gross P&L - fees - slippage`.
- Se o mesmo candle toca o stop e o take profit, a saida e o stop. Se o open abre alem do stop, o fill usa o open.
- Saida por tendencia (`SELL` da estrategia) ocorre no fechamento, depois da checagem intra-bar.
- Perda diaria pausa entradas novas e ainda permite sair da posicao aberta.
- O relatorio mostra trades, wins, losses, win rate, gross, fees, slippage, net, return, max drawdown, profit factor, avg trade, avg winner, avg loser e expectancy.
- Profit factor = lucro bruto / abs(prejuizo bruto). Sem prejuizo, o fator fica indisponivel.
- Expectancy = probabilidade de ganho * media dos ganhos - probabilidade de perda * media das perdas (perda em valor positivo).
- Intervalos de treino e validacao sao apenas `--start` e `--end` distintos. Nao existe busca de parametros.

## Uso

```text
python -m app.main backtest --symbol BTCUSDT --csv candles.csv --start 2024-01-01 --end 2024-12-31 --capital 5000
```

O CSV tem as colunas `timestamp,open,high,low,close,volume`.
