# Trading bot

Robo long-only de BTCUSDT. Calcula indicadores, a estrategia de tendencia no 4h e pullback no 1h, o risco e um backtest. Nao envia ordem real.

Stop de 5% do preco, alvo de 10% (2 para 1), risco de 1% por trade e pausa do dia em -2%. Depois de um stop, o robo espera 6 horas. A tendencia vem do candle de 4 horas ja fechado; a entrada, do candle de 1 hora, depois que o candle anterior tocou a EMA20 e o atual fechou acima dela e da maxima anterior. O caminho ate uma ordem real esta em `specs/06-ate-a-ordem-real.md`. O passo atual e o paper residente de BTCUSDT, sem envio.

Parametros iniciais de pesquisa, sem promessa de resultado.

## Documentacao

As regras estao em `specs/`. As medidas da V1 e dos outros pares estao em `docs/relatorio-estrategia-v1.md` e em `specs/07-ativos.md`. O simbolo oficial continua BTCUSDT. O HTML compilado fica em `docs/index.html`. Depois de mudar um Markdown:

```text
python scripts/build_docs.py
```

## Python na imagem

O codigo roda em `python:3.12-slim`. Nao e preciso instalar Python no Windows.

```text
docker compose run --rm --no-deps app pytest -q
docker compose run --rm --no-deps app python scripts/run_windows.py
docker compose run --rm --no-deps app python -m app.main backtest --symbol BTCUSDT --csv data/BTCUSDT-5m.csv --start 2026-01-01 --end 2026-09-25 --capital 5000
```

`scripts/run_windows.py` imprime o treino (2024-2025) e a validacao (2026). Sai 0 so quando o net da validacao e positivo. Isso nao liga `VALIDATION_PASSED`.

## Banco

Copie `.env.example` para `.env` e defina `POSTGRES_PASSWORD`. No servidor:

```text
docker compose up -d db
```

O Postgres 16 do Compose publica a porta **5433** no Windows, porque a 5432 ja e do PostgreSQL local. Dentro da rede Docker o app continua em `db:5432`.

O Postgres aplica `db/schema.sql` na primeira criacao do volume.

## Flags de modo

No `.env`:

- `MODE=backtest` para pesquisa. `paper` relê um CSV e nao envia ordem.
- `VALIDATION_PASSED=false`. Testnet e live continuam recusados.
- `LIVE_ENABLED=false` ate uma ordem real ser autorizada de proposito.

```text
docker compose run --rm --no-deps app python -m app.main paper --symbol BTCUSDT --csv data/BTCUSDT-5m.csv --start 2026-01-01 --end 2026-09-25 --capital 5000
docker compose run --rm app python -m app.main sync-public --symbol BTCUSDT --days 7 --capital 5000
docker compose up -d paper
```

O aviso no Telegram e opcional. Sem token, o paper segue igual e nao envia mensagem. Para ligar: crie o bot com `@BotFather` (`/newbot`), envie `/start` para ele, copie o `chat.id` em `https://api.telegram.org/botSEU_TOKEN/getUpdates`, preencha `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` no `.env` e rode `docker compose restart paper`. A primeira leitura so marca o diario atual. O passo a passo ate a ordem real esta em `specs/06-ate-a-ordem-real.md`.

## CSV de backtest

Colunas: `timestamp,open,high,low,close,volume`.

Os candles publicos de 5 minutos ficam em `data/`, fora do git. Para baixar de novo:

```text
python scripts/fetch_klines.py
```

As janelas de pesquisa juntam esses candles em barras de 1 hora.
