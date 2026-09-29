# Ate a ordem real

## Objetivo

Chegar a uma ordem na Binance sem pular etapa. Cada passo usa a regra V1 congelada. Nenhum passo liga `VALIDATION_PASSED` nem `LIVE_ENABLED`.

## Ordem

1. Paper local. O mesmo motor do backtest relê um CSV, simula fill, taxa e slippage, e imprime o relatorio. Nenhuma chamada de ordem.
2. Leitura publica. `sync-public` busca so candles fechados em `GET /api/v3/klines`, roda a V1 e grava candles, decisoes, trades simulados e uma linha em `bot_logs`. Sem chave e sem ordem. Repetir o comando atualiza o diario e acrescenta outra linha de resumo.
3. Paper residente. O mesmo `sync-public --resident`, em BTCUSDT. O processo espera a hora UTC fechar, espera 15 segundos e repete a leitura. Nao escolhe filtro novo.
4. Conferencia. Os trades do paper no mesmo CSV tem de bater com o backtest.
5. Observacao. O servico `paper` fica ligado por semanas, so em BTCUSDT, rejogando os ultimos 30 dias a cada hora fechada. O objetivo e ver se o diario ao vivo continua igual ao backtest. Uma semana boa nao autoriza a etapa seguinte e nao serve para trocar de ativo nem de filtro. A V1 fez cerca de 12 trades por ano, entao semanas podem fechar zero trades.
6. Testnet. Ordens assinadas apenas na URL de testnet, com `TESTNET_ENABLED=true`. Dinheiro ficticio da Binance.
7. Conta real. Chave sem permissao de saque, `LIVE_ENABLED=true` e `VALIDATION_PASSED=true`, ligados a mao, depois da testnet repetir o diario do paper.

Os passos 1, 2 e 3 estao implementados. O passo 3 fica de pe enquanto o servico `paper` estiver ligado.

Os proximos passos, ainda so com BTCUSDT e sem ordem real:

1. Conferencia. O trade do paper tem de bater com o backtest do mesmo candle. O paper ja usa esse motor. A checagem automatica separada ainda nao existe.
2. Observacao por semanas. O servico `paper` faz isso. Uma semana boa nao libera a etapa seguinte.
3. Testnet. Ordens assinadas so na URL de teste da Binance, com dinheiro ficticio.
4. Conta real. Chave sem permissao de saque, e so depois de ligar `LIVE_ENABLED` e `VALIDATION_PASSED` a mao.

## Invariantes

- Paper nao envia ordem. O gateway de paper recusa `submit`.
- Paper roda com `VALIDATION_PASSED=false`.
- Testnet e live continuam recusados sem `VALIDATION_PASSED=true`.
- Live continua recusado sem `LIVE_ENABLED=true`.
- `MODE=live` nao pode executar o comando de paper.
- A estrategia, o stop de 5%, o alvo de 10% e o risco de 1% sao os da V1. Este caminho nao escolhe filtro novo.

## Aviso no Telegram

Opcional. Cada compra nova ou saida fechada do paper manda uma mensagem. A primeira leitura so marca o diario que ja existe, entao o mesmo trade nao chega toda hora. Sem token, nada e enviado. Isso nao manda ordem na Binance e nao adianta a testnet.

Para ligar:

1. No Telegram, fale com `@BotFather`, use `/newbot` e copie o token.
2. Abra o bot e envie `/start`.
3. Abra `https://api.telegram.org/botSEU_TOKEN/getUpdates` e copie o `chat.id`.
4. Coloque os dois no `.env`, em `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`.
5. Rode `docker compose restart paper`.

## Fora deste passo

Dashboard, chave de API, URL de testnet e qualquer `POST /api/v3/order`.
