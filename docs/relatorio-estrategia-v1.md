# Estratégia V1 — regra e resultado

BTCUSDT, somente compra. A estratégia lê o mercado e devolve `BUY` ou `HOLD`. Stop e take profit fecham a operação. Ela não emite `SELL`.

O alvo desta versão é 10% (2 para 1). A regra de entrada não mudou entre 2024, 2025 e 2026. Live continua fechado. `VALIDATION_PASSED` continua `false`.

## O que cada peça faz

| Peça | Função |
| --- | --- |
| EMA50 e EMA200 no 4h | Qual é o regime do mercado? |
| Candle anterior toca a EMA20 | Houve correção até a média? |
| RSI14 entre 40 e 55 | A correção ainda está na faixa que queremos? |
| Close acima da EMA20 e da máxima anterior | O mercado mostrou recuperação? |
| Stop de 5% | Quanto aceitamos perder? |
| Take profit de 10% | Qual é o objetivo da operação? |

O pullback deixou de ser “preço a até 1,5% da EMA20”. Agora o candle anterior precisa tocar ou perder a EMA20 (`low <= EMA20` daquele candle) e o atual precisa fechar acima dela. Gatilho, faixas de RSI, volume e resistência ficam para os passos seguintes.

## Tendência no 4h

Usa o último candle de 4 horas já fechado. As três condições precisam ser verdadeiras:

- `EMA50 > EMA200`
- `close > EMA200`
- `EMA50` atual maior que a `EMA50` de 5 candles de 4h atrás

A inclinação é só essa comparação. Não há um percentual mínimo. Volume e distância até uma máxima recente não entram nesta versão.

## Entrada no 1h

O sinal nasce no fechamento do candle de 1 hora. A compra só sai quando a tendência de 4h já passou e estas condições também passam:

- o candle de 1h anterior tocou ou perdeu a EMA20: `low anterior <= EMA20 anterior`
- `40 <= RSI14 <= 55`
- `close > EMA20`
- `close > máxima do candle de 1h anterior`

O toque inclui o low exatamente na EMA20. Os limites de RSI 40 e 55 entram. Indicador ausente ou qualquer regra falsa devolve `HOLD`.

Posição aberta, perda diária e cooldown não bloqueiam o sinal aqui. O risco recusa a ordem depois.

## Risco

Capital de referência: 5.000. Opera só BTCUSDT.

- Stop: 5% abaixo da entrada. Entrada 100.000 vira stop 95.000.
- Take profit: 2 vezes essa distância. A mesma entrada vira alvo 110.000.
- Risco por trade: 1% do capital, 50 nesse exemplo, antes de taxa, slippage e gap.
- Tamanho: `min(risco / 5%, capital disponível)`. No exemplo, 1.000.
- Perda diária: realizado do dia UTC mais não realizado. Pausa entradas novas quando o dia perde 2% ou mais do patrimônio no início do dia. A posição já aberta pode sair.
- Depois de um stop, novas entradas esperam 6 horas.
- Quantidade desce para o step da Binance.

O tamanho usa os 5.000 iniciais, não o patrimônio do momento. Por isso o líquido das janelas separadas quase coincide com o da curva contínua.

## Como o backtest preenche a ordem

- A entrada acontece no open do candle seguinte.
- Compra efetiva = preço × (1 + 0,05%). Venda efetiva = preço × (1 − 0,05%).
- Taxa: 0,10% em cada lado.
- Líquido = bruto − taxas − slippage.
- Se o mesmo candle toca o stop e o take profit, a saída é o stop. Se o open abre além do stop, o fill usa o open e o relatório soma isso em Gap.
- Os candles de 5 minutos são juntados em barras de 1 hora no relógio UTC.
- Cada janela aquece 120 dias antes da data inicial e só conta operação dentro do período. O arquivo é `data/BTCUSDT-5m.csv`, com candles desde 03/09/2023.

O funil só avança o candle que passou na etapa anterior. A lista de “condições que falharam” conta falhas simultâneas e não diz, sozinha, qual filtro deve sair.

## Janelas independentes

Cada uma recomeça com 5.000. Comando: `python scripts/run_windows.py`.

| Medida | 2024 | 2025 | 2026 até 25/09 |
| --- | --- | --- | --- |
| Trades | 22 | 10 | 6 |
| Wins | 10 | 3 | 3 |
| Losses | 12 | 7 | 3 |
| Win rate | 45,45% | 30,00% | 50,00% |
| Gross P&L | 399,94 | -49,91 | 149,91 |
| Fees | 44,39 | 19,94 | 12,14 |
| Slippage | 22,19 | 9,97 | 6,07 |
| Risco planejado | 1.099,65 | 499,64 | 299,87 |
| Perda realizada | 634,87 | 370,19 | 158,71 |
| Gap | 0,00 | 0,00 | 0,00 |
| Net P&L | 333,37 | -79,81 | 131,70 |
| Return | 6,67% | -1,60% | 2,63% |
| Max drawdown | 7,75% | 4,11% | 3,30% |
| Profit factor | 1,67 | 0,86 | 2,00 |
| Avg trade | 15,15 | -7,98 | 21,95 |
| Avg winner | 96,82 | 96,79 | 96,80 |
| Avg loser | 52,91 | 52,88 | 52,90 |
| Expectancy | 15,15 | -7,98 | 21,95 |
| Maior sequência | 8 perdas | 3 perdas | 2 perdas |
| Candles lidos | 8.784 | 8.760 | 6.432 |
| Sinais BUY | 156 | 121 | 76 |

Funil, na ordem em que a regra corta:

| Etapa | 2024 | 2025 | 2026 |
| --- | --- | --- | --- |
| Candles 1h | 8.784 | 8.760 | 6.432 |
| Tendência 4h | 4.056 | 2.788 | 1.913 |
| Pullback | 2.186 | 1.595 | 1.105 |
| RSI 40–55 | 1.437 | 1.063 | 693 |
| Recuperação | 156 | 121 | 76 |
| Risco aceitou | 22 | 10 | 7 |
| Trades fechados | 22 | 10 | 6 |

Em 2026 o risco aceitou 7 entradas e 6 fecharam até 25/09. Uma posição seguia aberta no fim da janela e não entra no líquido.

O pullback novo cortou candles, e não cortou os trades que já fechavam. Em 2024 a tendência deixa passar 4.056 candles e o toque na EMA20 deixa 2.186. Desses, 1.437 ainda estão com RSI na faixa e 156 recuperam. O líquido de cada janela ficou igual ao da versão com a distância de 1,5%.

## Curva contínua

De 01/01/2024 a 25/09/2026, um único capital de 5.000, sem reiniciar o ano.

| Medida | Valor |
| --- | --- |
| Trades | 38 |
| Wins | 16 |
| Losses | 22 |
| Win rate | 42,11% |
| Net P&L | 385,25 |
| Return | 7,70% |
| Max drawdown | 7,75% |
| Profit factor | 1,45 |
| Expectancy | 10,14 |
| Maior sequência | 8 perdas |
| Risco planejado | 1.899,16 |
| Perda realizada | 1.163,77 |
| Gap | 0,00 |
| Sinais BUY | 353 |
| Risco aceitou | 39 |

O ganho médio ficou perto de 96,80 e a perda média perto de 52,90. Isso é o 2 para 1 depois da taxa e do slippage. Nenhum stop abriu além do preço do stop: Gap ficou em zero.

2025 continua negativo. A validação de 2026 fecha positiva no líquido, com 6 trades. Isso não liga paper nem live.

## Passo 2 — comparação de gatilho

A regra congelada continua sendo o gatilho A: `close > EMA20` e `close > máxima anterior`. Os outros dois foram medidos nas mesmas janelas, com o mesmo pullback, o mesmo RSI e o mesmo alvo de 10%.

| Gatilho | Janela | Trades | Líquido | Retorno | Profit factor | Sinais |
| --- | --- | --- | --- | --- | --- | --- |
| A previous_high | 2024 | 22 | 333,37 | 6,67% | 1,67 | 156 |
| A previous_high | 2025 | 10 | -79,81 | -1,60% | 0,86 | 121 |
| A previous_high | 2026 | 6 | 131,70 | 2,63% | 2,00 | 76 |
| A previous_high | contínuo | 38 | 385,25 | 7,70% | 1,45 | 353 |
| B só EMA20 | 2024 | 24 | 227,57 | 4,55% | 1,43 | 417 |
| B só EMA20 | 2025 | 12 | -35,89 | -0,72% | 1,00 | 264 |
| B só EMA20 | 2026 | 6 | 131,72 | 2,63% | 2,00 | 177 |
| B só EMA20 | contínuo | 42 | 323,40 | 6,47% | 1,36 | 858 |
| C EMA20 e candle positivo | 2024 | 24 | 227,55 | 4,55% | 1,43 | 294 |
| C EMA20 e candle positivo | 2025 | 11 | -132,73 | -2,65% | 0,75 | 205 |
| C EMA20 e candle positivo | 2026 | 6 | 131,72 | 2,63% | 2,00 | 127 |
| C EMA20 e candle positivo | contínuo | 41 | 226,54 | 4,53% | 1,28 | 626 |

B e C aumentam os sinais. O número de trades fechados sobe pouco, e o líquido contínuo fica pior que o do gatilho A. Em 2026 os três fecham os mesmos 6 trades, com o mesmo líquido. Nenhum dos três tira 2025 do prejuízo.

## Passo 3 — comparação de RSI

A regra congelada continua `40 <= RSI14 <= 55`, com o gatilho A e o pullback do candle anterior. As outras faixas foram medidas nas mesmas janelas.

| RSI | Janela | Trades | Líquido | Retorno | Profit factor | Sinais |
| --- | --- | --- | --- | --- | --- | --- |
| 40–55 | 2024 | 22 | 333,37 | 6,67% | 1,67 | 156 |
| 40–55 | 2025 | 10 | -79,81 | -1,60% | 0,86 | 121 |
| 40–55 | 2026 | 6 | 131,70 | 2,63% | 2,00 | 76 |
| 40–55 | contínuo | 38 | 385,25 | 7,70% | 1,45 | 353 |
| 35–55 | 2024 | 22 | 333,37 | 6,67% | 1,67 | 156 |
| 35–55 | 2025 | 10 | -79,81 | -1,60% | 0,86 | 121 |
| 35–55 | 2026 | 6 | 131,70 | 2,63% | 2,00 | 76 |
| 35–55 | contínuo | 38 | 385,25 | 7,70% | 1,45 | 353 |
| 35–60 | 2024 | 26 | 121,72 | 2,43% | 1,25 | 294 |
| 35–60 | 2025 | 10 | 69,80 | 1,40% | 1,33 | 214 |
| 35–60 | 2026 | 6 | 131,71 | 2,63% | 2,00 | 127 |
| 35–60 | contínuo | 42 | 323,23 | 6,46% | 1,36 | 635 |
| 40–60 | 2024 | 26 | 121,72 | 2,43% | 1,25 | 294 |
| 40–60 | 2025 | 10 | 69,80 | 1,40% | 1,33 | 214 |
| 40–60 | 2026 | 6 | 131,71 | 2,63% | 2,00 | 127 |
| 40–60 | contínuo | 42 | 323,23 | 6,46% | 1,36 | 635 |

Baixar o piso de 40 para 35 não acrescenta nenhum sinal. Subir o teto para 60 deixa 2025 positivo e aumenta os sinais, mas o líquido de 2024 cai de 333,37 para 121,72 e a curva contínua cai de 385,25 para 323,23. Em 2026 os trades fechados continuam 6. A faixa oficial permanece 40–55.

## Passo 4 — volume

A regra oficial continua sem filtro de volume. A variante exige `volume >= 110%` da média de 20 candles, com o mesmo gatilho A, o mesmo pullback e o RSI 40–55.

| Volume | Janela | Trades | Líquido | Retorno | Profit factor | Sinais |
| --- | --- | --- | --- | --- | --- | --- |
| sem filtro | 2024 | 22 | 333,37 | 6,67% | 1,67 | 156 |
| sem filtro | 2025 | 10 | -79,81 | -1,60% | 0,86 | 121 |
| sem filtro | 2026 | 6 | 131,70 | 2,63% | 2,00 | 76 |
| sem filtro | contínuo | 38 | 385,25 | 7,70% | 1,45 | 353 |
| 110% da média | 2024 | 15 | 104,81 | 2,10% | 1,33 | 34 |
| 110% da média | 2025 | 10 | -79,96 | -1,60% | 0,86 | 30 |
| 110% da média | 2026 | 4 | 87,78 | 1,76% | 2,00 | 15 |
| 110% da média | contínuo | 29 | 112,63 | 2,25% | 1,22 | 79 |

O filtro corta sinais e piora o líquido em 2024, em 2026 e na curva contínua. 2025 continua negativo, com os mesmos 10 trades. A regra oficial permanece sem esse filtro.

## Passo 5 — resistência

A regra oficial continua sem filtro de resistência. A variante só compra se a máxima dos últimos 20 candles de 4 horas fechados ficar pelo menos 10% acima do fechamento atual. É o espaço até o alvo. Gatilho, pullback, RSI e volume ficam como na regra oficial.

| Resistência | Janela | Trades | Líquido | Retorno | Profit factor | Sinais |
| --- | --- | --- | --- | --- | --- | --- |
| sem filtro | 2024 | 22 | 333,37 | 6,67% | 1,67 | 156 |
| sem filtro | 2025 | 10 | -79,81 | -1,60% | 0,86 | 121 |
| sem filtro | 2026 | 6 | 131,70 | 2,63% | 2,00 | 76 |
| sem filtro | contínuo | 38 | 385,25 | 7,70% | 1,45 | 353 |
| espaço de 10% | 2024 | 0 | 0,00 | 0,00% | n/a | 0 |
| espaço de 10% | 2025 | 0 | 0,00 | 0,00% | n/a | 0 |
| espaço de 10% | 2026 | 0 | 0,00 | 0,00% | n/a | 0 |
| espaço de 10% | contínuo | 0 | 0,00 | 0,00% | n/a | 0 |

A máxima é calculada: em 2024, 8.705 candles de 1 hora já tinham 20 candles de 4 horas, e 324 tinham a máxima pelo menos 10% acima do preço. Nenhum desses 324 também passou na tendência, no pullback, no RSI e na recuperação. A interseção fica vazia. A regra oficial permanece sem esse filtro.

## Passo 6 — diário dos 38 trades

A regra oficial não mudou. Cada trade da curva contínua agora guarda o RSI do sinal, o RSI anterior, a separação `(EMA50 − EMA200) / EMA200`, a inclinação da EMA50 em 5 candles de 4 horas, o ATR de 4 horas dividido pelo fechamento, o drawdown na entrada e a hora UTC. O líquido continua 385,25 em 38 trades.

Os 16 ganhos fecham no alvo, cerca de 96,80 cada. As 22 perdas fecham no stop, cerca de −52,90 cada. A duração não separa os dois lados: há stop em 1 hora e alvo depois de centenas de horas.

| Grupo | Trades | Líquido | Acerto | Separação média | Inclinação média | ATR médio |
| --- | --- | --- | --- | --- | --- | --- |
| ganhos | 16 | 1.549,02 | 100% | 4,66% | 1,02% | 1,56% |
| perdas | 22 | −1.163,77 | 0% | 4,28% | 0,69% | 1,47% |
| 2024 | 22 | 333,37 | 45,45% | 6,04% | 0,84% | 1,69% |
| 2025 | 10 | −79,81 | 30,00% | 2,39% | 0,70% | 1,26% |
| 2026 | 6 | 131,70 | 50,00% | 2,03% | 0,98% | 1,27% |

Nos 38 trades o RSI sobe entre o candle anterior e o candle do sinal. Exigir RSI em alta não corta nenhuma operação. A diferença de ATR entre ganho e perda é 1,56% contra 1,47%.

A separação e a inclinação também não pedem um corte novo:

- Separação abaixo de 0,50%: 9 trades, líquido 272,42, acerto 55,56%.
- Separação de 0,50% a 1%: 2 trades, líquido 43,95.
- Separação de 1% a 2%: 4 trades, líquido −211,65, nenhum ganho.
- Separação de 2% ou mais: 23 trades, líquido 280,53, acerto 43,48%.
- Inclinação abaixo de 0,25%: 6 trades, líquido 281,52, acerto 66,67%.
- Inclinação de 0,50% ou mais: 25 trades, líquido 174,54, acerto 40%.

O ano ruim, 2025, entra com tendência mais fraca (2,39%) do que 2024 (6,04%). 2026 também entra fraco (2,03%) e fecha positivo. Uma inclinação mínima tiraria o grupo que mais ganhou. A faixa de 1% a 2% perdeu os 4 trades, e quatro operações não bastam para virar regra. A regra oficial permanece a mesma.

## Passo 7 — amostra maior e matriz da V2

O histórico de 5 minutos agora começa em 17/08/2017. A V1 foi medida de novo em cada ano, com capital reiniciado em 5.000. A matriz da V2 fica ao lado: gatilho, faixa de RSI, volume e resistência não mudam. Separação, inclinação, RSI em alta, qualidade do candle, ATR e uma tendência diária são testes. Nenhum deles virou a regra padrão.

| Ano | Trades | Líquido | Retorno | Profit factor | Expectativa | Drawdown |
| --- | --- | --- | --- | --- | --- | --- |
| 2018 | 11 | −132,86 | −2,66% | 0,75 | −12,08 | 4,51% |
| 2019 | 24 | 227,54 | 4,55% | 1,43 | 9,48 | 5,88% |
| 2020 | 25 | 623,89 | 12,48% | 2,17 | 24,96 | 4,41% |
| 2021 | 32 | 552,85 | 11,06% | 1,76 | 17,28 | 4,32% |
| 2022 | 11 | −432,32 | −8,65% | 0,20 | −39,30 | 9,15% |
| 2023 | 14 | 457,17 | 9,14% | 2,67 | 32,66 | 4,73% |
| 2024 | 22 | 333,37 | 6,67% | 1,67 | 15,15 | 7,75% |
| 2025 | 10 | −79,81 | −1,60% | 0,86 | −7,98 | 4,11% |
| 2026 | 6 | 131,70 | 2,63% | 2,00 | 21,95 | 3,30% |

2018, 2022 e 2025 fecham no negativo. 2022 é o pior ano, com profit factor 0,20. A curva 2018–2021, sem reiniciar o capital, fecha em 93 trades, líquido 1.368,25 e profit factor 1,65. A curva 2022–2023 fica em 25 trades, líquido 24,85 e profit factor 1,13: o ganho de 2023 quase só cobre 2022.

Um fator por vez, nas janelas de busca (2018–2021), confirmação (2022–2023) e na janela já vista (2024–2026):

| Variante | Busca | Confirmação | Já vista |
| --- | --- | --- | --- |
| V1 | 93 / 1.368,25 / 1,65 | 25 / 24,85 / 1,13 | 38 / 385,25 / 1,45 |
| separação 0,25% | 89 / 1.430,20 / 1,71 | 22 / 33,84 / 1,14 | 39 / 332,34 / 1,39 |
| separação 0,50% | 85 / 1.342,36 / 1,70 | 22 / 33,84 / 1,14 | 36 / 191,70 / 1,27 |
| separação 1% | 82 / 1.351,35 / 1,73 | 22 / 33,83 / 1,14 | 34 / −2,02 / 1,09 |
| separação 2% | 79 / 1.360,34 / 1,76 | 15 / −45,03 / 1,00 | 30 / 59,86 / 1,16 |
| inclinação 0,10% | 91 / 1.474,07 / 1,71 | 23 / 130,68 / 1,29 | 37 / 438,16 / 1,52 |
| inclinação 0,25% | 82 / 1.201,58 / 1,64 | 22 / 183,59 / 1,38 | 36 / 41,87 / 1,13 |
| inclinação 0,50% | 75 / 973,04 / 1,57 | 19 / 42,81 / 1,17 | 27 / 218,44 / 1,37 |
| RSI em alta | 93 / 1.368,25 / 1,65 | 25 / 24,85 / 1,13 | 38 / 385,25 / 1,45 |
| candle positivo | 93 / 1.368,25 / 1,65 | 25 / 24,85 / 1,13 | 38 / 385,25 / 1,45 |
| fechamento no topo 30% | 93 / 1.218,44 / 1,58 | 23 / −19,07 / 1,07 | 34 / 297,49 / 1,40 |
| fechamento no topo 20% | 82 / 752,32 / 1,42 | 20 / −10,10 / 1,08 | 35 / 94,99 / 1,18 |
| ATR de 1% a 2,5% | 59 / 621,71 / 1,47 | 22 / −115,93 / 0,93 | 34 / 297,38 / 1,40 |
| tendência no diário | 115 / 204,18 / 1,15 | 12 / 263,46 / 2,00 | 44 / 217,51 / 1,26 |

Cada célula é trades, líquido e profit factor. RSI em alta e candle positivo repetem a V1 nas três janelas: o gatilho atual já entra nesses casos. Topo do candle e faixa de ATR pioram a confirmação. A tendência diária aumenta os trades e reduz o líquido de 2018–2021 de 1.368,25 para 204,18.

A inclinação mínima de 0,10% é a única variante que melhora as três janelas. O degrau seguinte, 0,25%, cai para 41,87 na janela já vista. Uma mudança pequena desfaz o ganho, então esse piso não entra na regra. A separação mínima melhora a busca e pouco a confirmação, e piora 2024–2026. A V1 continua oficial.

## Método de longo prazo

A curva única de 01/01/2018 a 25/09/2026, com o capital seguindo de um ano para o outro, é a medida longa. Comprar BTC em 01/01/2018 e segurar até 26/09/2026 rendeu 521,33%. A V1 rendeu 37,50% no mesmo intervalo, com o dinheiro parado fora das operações.

| Regra | Trades | Líquido | Retorno | Profit factor | Expectativa | Drawdown |
| --- | --- | --- | --- | --- | --- | --- |
| V1 | 157 | 1.875,17 | 37,50% | 1,53 | 11,94 | 9,06% |
| V1 e diário em alta | 113 | 1.358,25 | 27,17% | 1,53 | 12,02 | 7,76% |

Exigir que o diário também esteja em alta (EMA50 acima da EMA200, fechamento acima da EMA200 e EMA50 subindo) zera 2022, que era o pior ano. Também zera 2026, que era positivo, e corta boa parte de 2019, 2020 e 2021. 2024 e 2025 ficam iguais, inclusive a perda de 2025. O profit factor continua 1,53 e o lucro cai de 1.875,17 para 1.358,25.

O método que o histórico sustenta é a V1, sem filtro extra:

- BTCUSDT, só compra.
- Tendência no candle de 4 horas já fechado: EMA50 acima da EMA200, fechamento acima da EMA200, EMA50 acima da EMA50 de 5 candles atrás.
- Entrada no candle de 1 hora: a mínima anterior tocou a EMA20, o RSI ficou entre 40 e 55, e o fechamento superou a EMA20 e a máxima anterior.
- Stop em −5%, alvo em +10%, risco de 1% sobre os 5.000 iniciais, pausa no dia em −2%, 6 horas de espera depois de um stop, uma posição.
- Sem volume, sem resistência, sem piso percentual de inclinação e sem trava diária.

Nesse caminho houve 157 trades, cerca de 12 por ano. A expectativa é 11,94 por trade depois de taxa e slippage. O pior recuo da curva foi 9,06%. 2018, 2022 e 2025 fazem parte desse resultado. O ritmo fica perto de 4% ao ano, bem abaixo de segurar o BTC. É uma curva positiva com perda controlada, não um substituto de ficar comprado no ativo. Paper, testnet e live continuam desligados.

## SOL isolada

A mesma V1, sem mudar stop, alvo, RSI nem gatilho. Capital de 5.000 por ano. O arquivo começa em 03/09/2020; a medição começa em 01/01/2021 para ter aquecimento. SOL não entra na curva do BTC.

| Ano | Trades | Líquido | Retorno | Profit factor | Expectativa | Drawdown | Sinais |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | 95 | −575,17 | −11,50% | 0,91 | −6,05 | 15,73% | 195 |
| 2022 | 12 | −36,85 | −0,74% | 1,00 | −3,07 | 6,87% | 32 |
| 2023 | 48 | 447,65 | 8,95% | 1,42 | 9,33 | 7,93% | 155 |
| 2024 | 38 | −364,73 | −7,29% | 0,81 | −9,60 | 9,38% | 145 |
| 2025 | 25 | −125,64 | −2,51% | 0,94 | −5,03 | 7,39% | 90 |
| 2026 | 12 | −186,23 | −3,72% | 0,67 | −15,52 | 6,08% | 68 |
| 2021–2026 | 230 | −841,00 | −16,82% | 0,98 | −3,66 | 21,81% | 685 |

Só 2023 fecha positivo. A curva contínua perde 841,00. Segurar SOL de 01/01/2021 a 25/09/2026 rendeu 7.810,24%. A regra não viaja para a SOL. Os parâmetros continuam os do BTC.

## ETH isolado

A mesma V1, sem mudar stop, alvo, RSI nem gatilho. Capital de 5.000 por ano. O arquivo começa em 03/09/2017; a medição começa em 01/01/2018. ETH não entra na curva do BTC nem na da SOL.

| Ano | Trades | Líquido | Retorno | Profit factor | Expectativa | Drawdown | Sinais |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2018 | 17 | −1,16 | −0,02% | 1,09 | −0,07 | 6,84% | 45 |
| 2019 | 28 | 314,69 | 6,29% | 1,50 | 11,24 | 4,79% | 113 |
| 2020 | 36 | 490,43 | 9,81% | 1,60 | 13,62 | 5,57% | 170 |
| 2021 | 42 | 323,19 | 6,46% | 1,36 | 7,70 | 6,03% | 155 |
| 2022 | 14 | −141,88 | −2,84% | 0,80 | −10,13 | 5,44% | 48 |
| 2023 | 19 | −106,93 | −2,14% | 0,92 | −5,63 | 8,33% | 143 |
| 2024 | 23 | −168,83 | −3,38% | 0,87 | −7,34 | 11,97% | 151 |
| 2025 | 17 | −1,08 | −0,02% | 1,09 | −0,06 | 5,17% | 75 |
| 2026 | 7 | 78,86 | 1,58% | 1,50 | 11,27 | 3,98% | 87 |
| 2018–2026 | 203 | 787,26 | 15,75% | 1,22 | 3,88 | 12,24% | 987 |

A curva contínua fecha positiva: 787,26, profit factor 1,22. 2022, 2023 e 2024 fecham no negativo. 2018 e 2025 ficam quase no zero porque a taxa e o slippage comem um lucro bruto pequeno. Segurar ETH de 01/01/2018 a 25/09/2026 rendeu 269,92%. O ETH aguenta a regra melhor do que a SOL e pior do que o BTC. Os parâmetros continuam os do BTC. As três moedas seguem separadas.

## Fila para teste isolado

Preço de abertura em janeiro de 2021 contra o fechamento de setembro de 2026, no candle mensal da Binance. Entrar na lista não autoriza a mistura nem uma ordem. O teste isolado de cada um está nas seções seguintes. A regra é a mesma V1, o capital reinicia em 5.000 e os parâmetros não mudam.

| Par | Variação desde jan/2021 | Por que entrou |
| --- | --- | --- |
| BNBUSDT | 1.964% | Livro fundo e histórico longo na Binance |
| TRXUSDT | 1.148% | Alta contínua e liquidez |
| XRPUSDT | 581% | Um dos maiores volumes em USDT |
| DOGEUSDT | 1.920% | Alta longa, com passo de 1 unidade |

Ficaram de fora ZEC (+2.345%, alta recente e instável), AVAX (+235%), ADA (+37%) e LINK (+24%). A SOL já mostrou que subir muito no preço não faz a V1 lucrar. O símbolo oficial do robô continua BTCUSDT.

## BNB isolado

A mesma V1. O arquivo começa em 06/11/2017. A medição começa em 01/01/2019, o primeiro ano com 120 dias de aquecimento. BNB não entra na curva do BTC.

| Ano | Trades | Líquido | Retorno | Profit factor | Expectativa | Drawdown | Sinais |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 38 | 374,16 | 7,48% | 1,44 | 9,85 | 4,45% | 135 |
| 2020 | 39 | 474,27 | 9,49% | 1,54 | 12,16 | 4,48% | 185 |
| 2021 | 61 | 514,03 | 10,28% | 1,39 | 8,43 | 6,40% | 210 |
| 2022 | 16 | −247,70 | −4,95% | 0,67 | −15,48 | 6,86% | 63 |
| 2023 | 12 | 113,70 | 2,27% | 1,43 | 9,48 | 6,33% | 104 |
| 2024 | 33 | −398,68 | −7,97% | 0,75 | −12,08 | 11,12% | 215 |
| 2025 | 23 | −19,31 | −0,39% | 1,07 | −0,84 | 6,72% | 179 |
| 2026 | 9 | 122,62 | 2,45% | 1,60 | 13,62 | 3,46% | 84 |
| 2019–2026 | 231 | 933,08 | 18,66% | 1,23 | 4,04 | 17,52% | 1.175 |

A curva contínua fecha positiva: 933,08, profit factor 1,23. 2022, 2024 e 2025 fecham no negativo. O drawdown de 17,52% é quase o dobro do BTC. Segurar BNB de 01/01/2019 a 25/09/2026 rendeu 12.761,07%. A regra lucra, e fica bem atrás de ficar comprado.

## TRX isolado

A mesma V1. O arquivo começa em 11/06/2018. A medição começa em 01/01/2019. TRX não entra na curva do BTC nem na do BNB.

| Ano | Trades | Líquido | Retorno | Profit factor | Expectativa | Drawdown | Sinais |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 29 | −237,53 | −4,75% | 0,85 | −8,19 | 8,28% | 86 |
| 2020 | 39 | 391,72 | 7,83% | 1,45 | 10,04 | 4,93% | 137 |
| 2021 | 53 | 449,25 | 8,99% | 1,39 | 8,48 | 7,29% | 189 |
| 2022 | 16 | 38,92 | 0,78% | 1,17 | 2,43 | 4,88% | 70 |
| 2023 | 21 | 227,02 | 4,54% | 1,48 | 10,81 | 5,21% | 195 |
| 2024 | 25 | 168,38 | 3,37% | 1,32 | 6,74 | 6,55% | 153 |
| 2025 | 19 | −110,14 | −2,20% | 0,92 | −5,80 | 7,07% | 115 |
| 2026 | 6 | 280,48 | 5,61% | 3,97 | 46,75 | 1,87% | 117 |
| 2019–2026 | 207 | 1.260,78 | 25,22% | 1,30 | 6,09 | 10,15% | 1.062 |

A curva contínua é a melhor da fila: 1.260,78, profit factor 1,30, drawdown 10,15%. Só 2019 e 2025 fecham no negativo. 2026 tem 6 trades, então o profit factor 3,97 desse ano não sustenta uma mudança de regra. Segurar TRX de 01/01/2019 a 25/09/2026 rendeu 1.717,30%. O TRX aguenta a regra melhor do que o BNB e pior do que o BTC.

## XRP isolado

A mesma V1. O arquivo começa em 04/05/2018. A medição começa em 01/01/2019. XRP não entra nas curvas anteriores.

| Ano | Trades | Líquido | Retorno | Profit factor | Expectativa | Drawdown | Sinais |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 24 | −525,42 | −10,51% | 0,52 | −21,89 | 11,07% | 86 |
| 2020 | 36 | 186,45 | 3,73% | 1,27 | 5,18 | 6,73% | 161 |
| 2021 | 49 | 399,27 | 7,99% | 1,38 | 8,15 | 5,97% | 112 |
| 2022 | 21 | −364,60 | −7,29% | 0,62 | −17,36 | 7,58% | 84 |
| 2023 | 26 | −330,13 | −6,60% | 0,73 | −12,70 | 10,61% | 127 |
| 2024 | 29 | 410,96 | 8,22% | 1,62 | 14,17 | 6,52% | 115 |
| 2025 | 18 | −653,29 | −13,07% | 0,25 | −36,29 | 13,10% | 72 |
| 2026 | 9 | −326,74 | −6,53% | 0,25 | −36,30 | 8,47% | 48 |
| 2019–2026 | 213 | −1.256,49 | −25,13% | 0,92 | −5,90 | 30,45% | 805 |

A curva contínua perde 1.256,49. O drawdown chega a 30,45%. Só 2020, 2021 e 2024 fecham positivos. Segurar XRP de 01/01/2019 a 25/09/2026 rendeu 349,21%. A regra não viaja para o XRP.

## DOGE isolado

A mesma V1. O arquivo começa em 05/07/2019. A medição começa em 01/01/2020. DOGE não entra nas curvas anteriores.

| Ano | Trades | Líquido | Retorno | Profit factor | Expectativa | Drawdown | Sinais |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 28 | 112,46 | 2,25% | 1,22 | 4,02 | 5,94% | 126 |
| 2021 | 45 | −590,11 | −11,80% | 0,72 | −13,11 | 11,80% | 134 |
| 2022 | 18 | −54,77 | −1,10% | 1,00 | −3,04 | 4,68% | 37 |
| 2023 | 30 | −91,92 | −1,84% | 1,00 | −3,06 | 8,12% | 122 |
| 2024 | 45 | 463,00 | 9,26% | 1,46 | 10,29 | 9,33% | 124 |
| 2025 | 23 | −618,45 | −12,37% | 0,42 | −26,89 | 12,85% | 65 |
| 2026 | 9 | −27,40 | −0,55% | 1,00 | −3,04 | 4,45% | 31 |
| 2020–2026 | 199 | −712,36 | −14,25% | 0,98 | −3,58 | 20,59% | 639 |

A curva contínua perde 712,36. Só 2020 e 2024 fecham positivos. Segurar DOGE de 01/01/2020 a 25/09/2026 rendeu 4.828,05%. O preço subiu e a regra perdeu, o mesmo desenho da SOL.

Nenhum dos quatro substitui o BTC. O símbolo oficial continua BTCUSDT. Os parâmetros continuam os da V1. As curvas seguem separadas.

## Contas juntas

Cada linha é uma conta de 5.000. A soma não é uma carteira: uma posição só não segura trades que abrem na mesma hora. O alvo de cada trade continua +10%, cerca de 97 USDT. Juntar pares não aumenta esse alvo.

De 29/08/2026 a 25/09/2026:

| Par | Trades | Líquido |
| --- | --- | --- |
| BTCUSDT | 1 | 96,79 |
| ETHUSDT | 1 | 96,82 |
| BNBUSDT | 2 | 43,88 |
| DOGEUSDT | 2 | 43,85 |
| TRXUSDT | 1 | −53,03 |
| XRPUSDT | 4 | −62,03 |
| SOLUSDT | 2 | −105,95 |

BTC, ETH e SOL somam 87,67. Sobre 15.000, 0,58%. O BTC sozinho fez 1,94% sobre 5.000. Sem a SOL, as outras seis somam 166,28, ou 0,55% sobre 30.000. BTC, ETH e BNB abriram em 29/08/2026 às 15:00 UTC.

De 01/01/2020 a 25/09/2026, sem a SOL:

| Par | Trades | Líquido | Retorno | Profit factor |
| --- | --- | --- | --- | --- |
| BTCUSDT | 122 | 1.780,49 | 35,61% | 1,64 |
| TRXUSDT | 178 | 1.498,31 | 29,97% | 1,38 |
| BNBUSDT | 193 | 558,92 | 11,18% | 1,19 |
| ETHUSDT | 158 | 473,75 | 9,48% | 1,19 |
| DOGEUSDT | 199 | −712,36 | −14,25% | 0,98 |
| XRPUSDT | 189 | −731,07 | −14,62% | 0,97 |

A soma das seis contas é 2.868,05, ou 9,56% sobre 30.000. BTC, ETH, BNB e TRX somam 4.311,47, ou 21,56% sobre 20.000. O BTC sozinho fez 35,61% sobre 5.000.

## O que fica

Por capital aplicado, segurar o BTC foi o maior resultado deste histórico: 521,33% de 01/01/2018 a 26/09/2026. A V1 no mesmo intervalo rendeu 37,50%.

Dentro do robô, a versão mais rentável é a V1 só no BTCUSDT: 1.875,17, profit factor 1,53, expectativa 11,94 e drawdown 9,06%. O caminho oficial continua esse. Os outros pares ficam medidos e fora da curva. Paper, testnet e live continuam desligados. O serviço de paper residente observa o BTC por semanas para conferir o diário, e uma semana boa não autoriza ordem.
