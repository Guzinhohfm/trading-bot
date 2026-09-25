# Trading bot

Robo de criptomoedas long-only. Esta primeira leva calcula indicadores, a estrategia EMA + RSI + ATR + volume, o risco e um backtest. Nao envia ordem real.

Parametros iniciais de pesquisa, sem promessa de resultado.

## Python na imagem

O codigo roda em `python:3.12-slim`. Nao e preciso instalar Python no Windows.

```text
docker compose run --rm --no-deps app pytest -q
docker compose run --rm --no-deps app python -m app.main backtest --symbol BTCUSDT --csv candles.csv --start 2024-01-01 --end 2024-12-31 --capital 5000
```

## Banco

Copie `.env.example` para `.env` e defina `POSTGRES_PASSWORD`. No servidor:

```text
docker compose up -d db
```

O Postgres 16 aplica `db/schema.sql` na primeira criacao do volume.

## CSV de backtest

Colunas: `timestamp,open,high,low,close,volume`.
