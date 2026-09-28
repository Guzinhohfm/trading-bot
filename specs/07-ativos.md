# Outros ativos

## Objetivo

Registrar o que a V1 fez fora do BTCUSDT. Esta spec nao troca a regra, nao mistura capital e nao autoriza ordem.

## Contrato

- O simbolo oficial continua BTCUSDT. `symbols` no settings continua `BTCUSDT`.
- Cada par foi medido sozinho, com capital de 5000, stop de 5%, alvo de 10% e risco de 1%.
- A medicao comeca no primeiro 1 de janeiro que tem 120 dias de aquecimento antes dele.
- Somar liquidos de contas separadas nao e uma carteira. Uma conta com uma posicao nao segura trades que abrem na mesma hora.
- Subir de preco nao e lucro da regra. Segurar o ativo e a curva da V1 sao contas diferentes.
- Nenhuma destas medidas liga `VALIDATION_PASSED` nem `LIVE_ENABLED`.

## Curva longa de cada par

Capital de 5000 em cada curva continua. O BTC vai de 01/01/2018 a 25/09/2026. Os outros pares comecam quando o aquecimento existe. Cada linha e trades, liquido, retorno, profit factor, drawdown e o rendimento de segurar o ativo.

- BTCUSDT, 2018 a 2026: 157 trades, 1.875,17, 37,50%, profit factor 1,53, drawdown 9,06%. Segurar rendeu 521,33%.
- TRXUSDT, 2019 a 2026: 207 trades, 1.260,78, 25,22%, profit factor 1,30, drawdown 10,15%. Segurar rendeu 1.717,30%.
- BNBUSDT, 2019 a 2026: 231 trades, 933,08, 18,66%, profit factor 1,23, drawdown 17,52%. Segurar rendeu 12.761,07%.
- ETHUSDT, 2018 a 2026: 203 trades, 787,26, 15,75%, profit factor 1,22, drawdown 12,24%. Segurar rendeu 269,92%.
- DOGEUSDT, 2020 a 2026: 199 trades, −712,36, −14,25%, profit factor 0,98, drawdown 20,59%. Segurar rendeu 4.828,05%.
- SOLUSDT, 2021 a 2026: 230 trades, −841,00, −16,82%, profit factor 0,98, drawdown 21,81%. Segurar rendeu 7.810,24%.
- XRPUSDT, 2019 a 2026: 213 trades, −1.256,49, −25,13%, profit factor 0,92, drawdown 30,45%. Segurar rendeu 349,21%.

O BTC e a melhor curva da regra por capital aplicado. O TRX e o melhor dos outros pares e fica abaixo do BTC em retorno, profit factor e drawdown. SOL e DOGE subiram muito no preco e a regra perdeu. XRP perdeu com drawdown de 30,45%.

Segurar o BTC no mesmo intervalo rendeu 521,33%. A V1 rendeu 37,50%, com o dinheiro parado fora das operacoes. O ritmo da regra fica perto de 4% ao ano.

## Mesma janela, contas separadas

De 01/01/2020 a 25/09/2026, cada par com os seus 5000. A SOL fica de fora desta soma.

- BTCUSDT: 122 trades, 1.780,49, 35,61%, profit factor 1,64.
- TRXUSDT: 178 trades, 1.498,31, 29,97%, profit factor 1,38.
- BNBUSDT: 193 trades, 558,92, 11,18%, profit factor 1,19.
- ETHUSDT: 158 trades, 473,75, 9,48%, profit factor 1,19.
- DOGEUSDT: 199 trades, −712,36, −14,25%, profit factor 0,98.
- XRPUSDT: 189 trades, −731,07, −14,62%, profit factor 0,97.

A soma das seis contas e 2.868,05, ou 9,56% sobre 30.000. BTC, ETH, BNB e TRX somam 4.311,47, ou 21,56% sobre 20.000. O BTC sozinho fez 35,61% sobre 5.000.

## Trinta dias

De 29/08/2026 a 25/09/2026, cada conta com 5.000. So trades fechados.

- BTCUSDT: 1 trade, 96,79.
- ETHUSDT: 1 trade, 96,82.
- BNBUSDT: 2 trades, 43,88.
- DOGEUSDT: 2 trades, 43,85.
- TRXUSDT: 1 trade, −53,03.
- XRPUSDT: 4 trades, −62,03.
- SOLUSDT: 2 trades, −105,95.

BTC, ETH e SOL somam 87,67. Sobre 15.000, 0,58%. O BTC sozinho fez 1,94% sobre 5.000. Sem a SOL, as outras seis somam 166,28, ou 0,55% sobre 30.000. BTC, ETH e BNB abriram em 29/08/2026 as 15:00 UTC. Uma posicao so nao recolhe os tres.

## Decisao

O caminho do robo continua a V1 em BTCUSDT. Os outros pares permanecem medidos e fora da curva oficial. O alvo de cada trade continua +10%, cerca de 97 USDT numa conta de 5.000. Juntar pares nao aumenta esse alvo.

Os filtros de quantidade desses pares podem existir na tabela `symbols` para um teste isolado futuro. Isso nao os coloca na operacao.

## Fora de escopo

Misturar capital, retunar stop, RSI ou gatilho por causa de outro par, e qualquer ordem.
