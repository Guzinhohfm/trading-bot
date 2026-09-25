# Risco

## Objetivo

Impedir que um sinal BUY vire uma operacao inadequada e calcular stop, take profit e tamanho pelo risco.

## Invariantes

- `stop_distance = ATR * 1.5`
- `stop = entry - stop_distance` para long
- `take_profit = entry + stop_distance * 2`
- `risk_amount = capital * 1%`
- `position_size = min(risk_amount / (stop_distance / entry), capital disponivel)`
- Exemplo: entrada 100000, ATR 800, capital 5000 produzem stop 98800, take profit 102400 e tamanho `5000000 / 1200`.
- Rejeita a entrada quando ha posicao aberta no ativo, perda diaria no limite, kill switch, capital insuficiente ou stop invalido (`entry <= stop` depois de alinhar o tick).
- Perda diaria = P&L realizado do dia UTC + P&L nao realizado. Pausa quando `daily_pnl <= -3%` do patrimonio no inicio do dia UTC. Posicao ja aberta continua podendo sair.
- Quantidade desce para o step size. Nao passa do notional minimo nem da quantidade minima.

## Fora de escopo

Envio de ordem para a exchange.
