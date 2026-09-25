CREATE TYPE bot_mode AS ENUM ('backtest', 'paper', 'testnet', 'live');
CREATE TYPE bot_status AS ENUM ('running', 'paused');
CREATE TYPE order_side AS ENUM ('BUY', 'SELL');
CREATE TYPE order_status AS ENUM (
  'CREATED', 'SUBMITTED', 'PARTIALLY_FILLED',
  'FILLED', 'REJECTED', 'CANCELLED', 'EXPIRED'
);
CREATE TYPE signal_type AS ENUM ('BUY', 'SELL', 'HOLD');
CREATE TYPE risk_decision AS ENUM ('accepted', 'rejected');
CREATE TYPE position_status AS ENUM ('open', 'closed');
CREATE TYPE log_level AS ENUM ('DEBUG', 'INFO', 'WARNING', 'ERROR');

CREATE TABLE symbols (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  symbol        text NOT NULL UNIQUE,
  base_asset    text NOT NULL,
  quote_asset   text NOT NULL,
  tick_size     numeric(28, 12) NOT NULL,
  step_size     numeric(28, 12) NOT NULL,
  min_qty       numeric(28, 12) NOT NULL,
  min_notional  numeric(28, 12) NOT NULL,
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE candles (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  symbol      text NOT NULL,
  timeframe   text NOT NULL,
  open_time   timestamptz NOT NULL,
  open        numeric(28, 12) NOT NULL,
  high        numeric(28, 12) NOT NULL,
  low         numeric(28, 12) NOT NULL,
  close       numeric(28, 12) NOT NULL,
  volume      numeric(28, 12) NOT NULL,
  closed      boolean NOT NULL DEFAULT true,
  UNIQUE (symbol, timeframe, open_time)
);

CREATE TABLE bot_runtime (
  id                   smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  mode                 bot_mode NOT NULL,
  status               bot_status NOT NULL DEFAULT 'paused',
  kill_switch          boolean NOT NULL DEFAULT false,
  reference_capital    numeric(28, 12) NOT NULL,
  trading_day          date,
  day_start_equity     numeric(28, 12),
  daily_realized_pnl   numeric(28, 12) NOT NULL DEFAULT 0,
  updated_at           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE decisions (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  symbol            text NOT NULL,
  timeframe         text NOT NULL,
  candle_open_time  timestamptz NOT NULL,
  mode              bot_mode NOT NULL,
  signal            signal_type NOT NULL,
  close             numeric(28, 12) NOT NULL,
  volume            numeric(28, 12) NOT NULL,
  ema20             numeric(28, 12),
  ema50             numeric(28, 12),
  rsi14             numeric(28, 12),
  atr14             numeric(28, 12),
  avg_volume20      numeric(28, 12),
  price_distance    numeric(28, 12),
  trend_ok          boolean NOT NULL,
  rsi_ok            boolean NOT NULL,
  volume_ok         boolean NOT NULL,
  price_ok          boolean NOT NULL,
  risk_decision     risk_decision,
  risk_reason       text,
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX decisions_symbol_time_idx
  ON decisions (symbol, candle_open_time DESC);

CREATE TABLE positions (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  symbol            text NOT NULL,
  status            position_status NOT NULL,
  quantity          numeric(28, 12) NOT NULL,
  average_price     numeric(28, 12) NOT NULL,
  stop_price        numeric(28, 12),
  take_profit_price numeric(28, 12),
  fees              numeric(28, 12) NOT NULL DEFAULT 0,
  realized_pnl      numeric(28, 12) NOT NULL DEFAULT 0,
  opened_at         timestamptz NOT NULL DEFAULT now(),
  closed_at         timestamptz,
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX positions_one_open_per_symbol
  ON positions (symbol) WHERE status = 'open';

CREATE TABLE orders (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  binance_order_id  text UNIQUE,
  client_order_id   text NOT NULL UNIQUE,
  symbol            text NOT NULL,
  side              order_side NOT NULL,
  type              text NOT NULL,
  quantity          numeric(28, 12) NOT NULL,
  price             numeric(28, 12),
  status            order_status NOT NULL,
  mode              bot_mode NOT NULL,
  position_id       bigint REFERENCES positions (id),
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE trades (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  order_id      bigint NOT NULL REFERENCES orders (id),
  symbol        text NOT NULL,
  side          order_side NOT NULL,
  quantity      numeric(28, 12) NOT NULL,
  price         numeric(28, 12) NOT NULL,
  fee           numeric(28, 12) NOT NULL DEFAULT 0,
  slippage      numeric(28, 12) NOT NULL DEFAULT 0,
  realized_pnl  numeric(28, 12),
  status        order_status NOT NULL,
  strategy      text NOT NULL,
  traded_at     timestamptz NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX trades_traded_at_idx ON trades (traded_at DESC);

CREATE TABLE bot_logs (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  level      log_level NOT NULL,
  message    text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX bot_logs_created_at_idx ON bot_logs (created_at DESC);

INSERT INTO symbols (symbol, base_asset, quote_asset, tick_size, step_size, min_qty, min_notional)
VALUES
  ('BTCUSDT', 'BTC', 'USDT', 0.01, 0.00001, 0.00001, 5),
  ('ETHUSDT', 'ETH', 'USDT', 0.01, 0.0001, 0.0001, 5),
  ('SOLUSDT', 'SOL', 'USDT', 0.01, 0.001, 0.001, 5);

INSERT INTO bot_runtime (mode, status, reference_capital)
VALUES ('paper', 'paused', 5000);
