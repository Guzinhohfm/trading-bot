# Risco

## Objetivo

Impedir que um sinal BUY vire uma operacao inadequada e calcular stop, take profit e tamanho pelo risco. O robo opera so BTCUSDT.

## Invariantes

- `stop_distance = entry * 5%`
- `stop = entry - stop_distance` para long
- `take_profit = entry + stop_distance * 2` (alvo 2 para 1)
- `risk_amount = capital * 1%`
- `position_size = min(risk_amount / 0.05, capital disponivel)`
- Exemplo: entrada 100000, capital 5000 produzem stop 95000, take profit 110000 e tamanho 1000.
- Rejeita a entrada quando ha posicao aberta no ativo, perda diaria no limite, meta diaria batida, kill switch, capital insuficiente ou stop invalido (`entry <= stop` depois de alinhar o tick).
- Perda diaria = P&L realizado do dia UTC + P&L nao realizado. Pausa novas entradas quando `daily_pnl <= -5%` do patrimonio no inicio do dia UTC. Posicao ja aberta continua podendo sair.
- Meta diaria = `+2%` do patrimonio no inicio do dia UTC (um trade de 2 para 1 com risco de 1%). Pausa novas entradas quando `daily_pnl >= 2%`. Posicao ja aberta continua podendo sair.
- Quantidade desce para o step size. Nao passa do notional minimo nem da quantidade minima.

## Fora de escopo

Envio de ordem para a exchange.
