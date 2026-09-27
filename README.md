# Trading bot

Robo long-only de BTCUSDT. Calcula indicadores, a estrategia EMA + RSI + volume, o risco e um backtest. Nao envia ordem real.

Stop de 5% do preco, alvo de 10%, risco de 1% por trade e pausa do dia em -2%. Depois de um stop, o robo espera 6 horas. A tendencia vem do candle de 4 horas ja fechado; a entrada, do candle de 1 hora. Paper e testnet so depois da validacao de 2026 fechar positiva, com a regra congelada em 2024-2025.

Parametros iniciais de pesquisa, sem promessa de resultado.

## Documentacao

As regras estao em `specs/`. O HTML compilado fica em `docs/index.html`. Depois de mudar um Markdown:

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

- `MODE=backtest` para pesquisa
- `VALIDATION_PASSED=false` ate a validacao de 2026 fechar no positivo
- `LIVE_ENABLED=false` ate uma ordem real ser autorizada de proposito

Paper, testnet e live recusam subir sem `VALIDATION_PASSED=true`. Live ainda exige `LIVE_ENABLED=true`.

## CSV de backtest

Colunas: `timestamp,open,high,low,close,volume`.

Os candles publicos de 5 minutos ficam em `data/`, fora do git. Para baixar de novo:

```text
python scripts/fetch_klines.py
```

As janelas de pesquisa juntam esses candles em barras de 1 hora.
