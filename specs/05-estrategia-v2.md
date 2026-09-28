# Estrategia V2

## Objetivo

Medir, ao lado da V1, se regime, qualidade da recuperacao e ATR mudam o resultado. A V1 continua sendo a regra padrao. Nenhum numero desta matriz substitui a V1 so porque ficou melhor numa janela.

## O que permanece

- Gatilho `previous_high`: `close > EMA20` e `close > high` anterior.
- RSI entre 40 e 55.
- Sem filtro de volume.
- Sem filtro de resistencia dos ultimos 20 candles de 4 horas.
- Stop 5%, alvo 10%, risco 1%, pausa diaria em -2%, cooldown de 6 horas, uma posicao.

## O que a matriz varia

Cada item abaixo so entra quando o teste pede. O padrao de cada um reproduz a V1.

- Separacao `(EMA50 - EMA200) / EMA200` em 0%, 0,25%, 0,50%, 1% e 2%.
- Inclinacao `(EMA50[t] - EMA50[t-5]) / EMA50[t-5]` em 0%, 0,10%, 0,25% e 0,50%.
- RSI atual maior que o RSI anterior.
- Qualidade do candle: sem filtro, candle positivo, fechamento no topo 30% ou no topo 20%.
- ATR de 4 horas sobre o fechamento de 4 horas: sem filtro, pelo menos 1%, no maximo 2,5%, ou entre 1% e 2,5%.
- Uma variante separada usa o diario para a tendencia e mantem 4 horas e 1 hora como estao. Ela nao entra na matriz dos outros filtros.

## Amostra

A V1 e a matriz sao lidas em anos independentes desde 2018, com capital reiniciado em 5000. A escolha de parametro, se algum dia houver, olha 2018–2021 e so depois 2022–2023. 2024–2026 ja foi usado para desenhar a V1 e fica como janela ja vista.

## Aprovacao

Uma configuracao so merece conversa se, na busca e na confirmacao, o liquido for positivo, o profit factor passar de 1, a expectativa por trade for positiva e houver trades suficientes. Ela tambem precisa continuar razoavel quando a separacao ou a inclinacao vizinha muda pouco. Isso nao liga paper, testnet nem live.
