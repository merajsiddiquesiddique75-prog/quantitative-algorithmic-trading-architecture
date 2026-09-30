-- ============================================================================
-- schema.sql
-- Quantitative Algorithmic Trading Architecture - MySQL Schema
-- ============================================================================
-- This schema exactly matches the columns produced by python/generate_data.py
-- and cleaned by python/data_cleaning.py (data/processed/*.csv).
-- ============================================================================

DROP DATABASE IF EXISTS quant_trading_db;
CREATE DATABASE quant_trading_db;
USE quant_trading_db;

-- ----------------------------------------------------------------------------
-- DIMENSION TABLES
-- ----------------------------------------------------------------------------

CREATE TABLE dim_exchange (
    exchange_id     INT PRIMARY KEY,
    exchange_name   VARCHAR(50) NOT NULL,
    country         VARCHAR(50) NOT NULL,
    currency        VARCHAR(10) NOT NULL,
    market_timezone VARCHAR(50) NOT NULL
);

CREATE TABLE dim_instrument (
    instrument_id     INT PRIMARY KEY,
    instrument_symbol VARCHAR(20) NOT NULL,
    instrument_name   VARCHAR(100) NOT NULL,
    asset_class       VARCHAR(30) NOT NULL,
    sector            VARCHAR(30) NOT NULL,
    exchange_id       INT NOT NULL,
    volatility_class  VARCHAR(20) NOT NULL,
    liquidity_class   VARCHAR(20) NOT NULL,
    CONSTRAINT fk_instrument_exchange
        FOREIGN KEY (exchange_id) REFERENCES dim_exchange(exchange_id)
);

CREATE TABLE dim_strategy (
    strategy_id          INT PRIMARY KEY,
    strategy_name        VARCHAR(50) NOT NULL,
    strategy_type        VARCHAR(30) NOT NULL,
    risk_level            VARCHAR(20) NOT NULL,
    holding_period_type   VARCHAR(20) NOT NULL
);

CREATE TABLE dim_trader (
    trader_id         INT PRIMARY KEY,
    trader_name       VARCHAR(50) NOT NULL,
    experience_level  VARCHAR(20) NOT NULL,
    trading_style     VARCHAR(20) NOT NULL
);

CREATE TABLE dim_date (
    date_id     INT PRIMARY KEY,
    date        DATE NOT NULL,
    year        INT NOT NULL,
    month       INT NOT NULL,
    month_name  VARCHAR(15) NOT NULL,
    quarter     INT NOT NULL,
    week        INT NOT NULL,
    day_name    VARCHAR(15) NOT NULL
);

-- ----------------------------------------------------------------------------
-- FACT TABLES
-- ----------------------------------------------------------------------------

CREATE TABLE fact_market_data (
    market_data_id  INT PRIMARY KEY,
    instrument_id   INT NOT NULL,
    date_id         INT NOT NULL,
    open_price      DECIMAL(14,2) NOT NULL,
    high_price      DECIMAL(14,2) NOT NULL,
    low_price       DECIMAL(14,2) NOT NULL,
    close_price     DECIMAL(14,2) NOT NULL,
    volume          BIGINT NOT NULL,
    volatility      DECIMAL(8,4) NOT NULL,
    daily_return    DECIMAL(10,6) NOT NULL,
    CONSTRAINT fk_market_instrument FOREIGN KEY (instrument_id) REFERENCES dim_instrument(instrument_id),
    CONSTRAINT fk_market_date       FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
);

CREATE TABLE fact_orders (
    order_id        INT PRIMARY KEY,
    order_date      DATE NOT NULL,
    trader_id       INT NOT NULL,
    strategy_id     INT NOT NULL,
    instrument_id   INT NOT NULL,
    order_type      VARCHAR(20) NOT NULL,
    order_side      VARCHAR(10) NOT NULL,
    order_quantity  INT NOT NULL,
    order_price     DECIMAL(14,2) NOT NULL,
    order_status    VARCHAR(20) NOT NULL,
    CONSTRAINT fk_orders_trader     FOREIGN KEY (trader_id) REFERENCES dim_trader(trader_id),
    CONSTRAINT fk_orders_strategy   FOREIGN KEY (strategy_id) REFERENCES dim_strategy(strategy_id),
    CONSTRAINT fk_orders_instrument FOREIGN KEY (instrument_id) REFERENCES dim_instrument(instrument_id)
);

CREATE TABLE fact_trades (
    trade_id             INT PRIMARY KEY,
    order_id             INT NOT NULL,
    instrument_id        INT NOT NULL,
    trader_id            INT NOT NULL,
    strategy_id          INT NOT NULL,
    entry_date           DATE NOT NULL,
    exit_date            DATE NOT NULL,
    entry_price          DECIMAL(14,2) NOT NULL,
    exit_price           DECIMAL(14,2) NOT NULL,
    quantity             INT NOT NULL,
    gross_pnl            DECIMAL(16,2) NOT NULL,
    transaction_cost     DECIMAL(14,2) NOT NULL,
    net_pnl              DECIMAL(16,2) NOT NULL,
    return_percentage    DECIMAL(10,4) NOT NULL,
    holding_period_days  INT NOT NULL,
    CONSTRAINT fk_trades_order      FOREIGN KEY (order_id) REFERENCES fact_orders(order_id),
    CONSTRAINT fk_trades_instrument FOREIGN KEY (instrument_id) REFERENCES dim_instrument(instrument_id),
    CONSTRAINT fk_trades_trader     FOREIGN KEY (trader_id) REFERENCES dim_trader(trader_id),
    CONSTRAINT fk_trades_strategy   FOREIGN KEY (strategy_id) REFERENCES dim_strategy(strategy_id)
);

CREATE TABLE fact_positions (
    position_id     INT PRIMARY KEY,
    instrument_id   INT NOT NULL,
    trader_id       INT NOT NULL,
    strategy_id     INT NOT NULL,
    position_date   DATE NOT NULL,
    position_type   VARCHAR(10) NOT NULL,
    quantity        INT NOT NULL,
    entry_price     DECIMAL(14,2) NOT NULL,
    current_price   DECIMAL(14,2) NOT NULL,
    unrealized_pnl  DECIMAL(16,2) NOT NULL,
    CONSTRAINT fk_positions_instrument FOREIGN KEY (instrument_id) REFERENCES dim_instrument(instrument_id),
    CONSTRAINT fk_positions_trader     FOREIGN KEY (trader_id) REFERENCES dim_trader(trader_id),
    CONSTRAINT fk_positions_strategy   FOREIGN KEY (strategy_id) REFERENCES dim_strategy(strategy_id)
);

CREATE TABLE fact_portfolio_performance (
    performance_id     INT PRIMARY KEY,
    trader_id          INT NOT NULL,
    strategy_id        INT NOT NULL,
    date_id            INT NOT NULL,
    portfolio_value    DECIMAL(16,2) NOT NULL,
    daily_return       DECIMAL(10,6) NOT NULL,
    cumulative_return  DECIMAL(10,4) NOT NULL,
    benchmark_return   DECIMAL(10,4) NOT NULL,
    CONSTRAINT fk_perf_trader   FOREIGN KEY (trader_id) REFERENCES dim_trader(trader_id),
    CONSTRAINT fk_perf_strategy FOREIGN KEY (strategy_id) REFERENCES dim_strategy(strategy_id),
    CONSTRAINT fk_perf_date     FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
);

CREATE TABLE fact_risk_metrics (
    risk_id            INT PRIMARY KEY,
    trader_id          INT NOT NULL,
    strategy_id        INT NOT NULL,
    date_id            INT NOT NULL,
    volatility         DECIMAL(8,4) NOT NULL,
    sharpe_ratio       DECIMAL(8,3) NOT NULL,
    maximum_drawdown   DECIMAL(8,4) NOT NULL,
    value_at_risk      DECIMAL(14,2) NOT NULL,
    risk_score         DECIMAL(6,1) NOT NULL,
    CONSTRAINT fk_risk_trader   FOREIGN KEY (trader_id) REFERENCES dim_trader(trader_id),
    CONSTRAINT fk_risk_strategy FOREIGN KEY (strategy_id) REFERENCES dim_strategy(strategy_id),
    CONSTRAINT fk_risk_date     FOREIGN KEY (date_id) REFERENCES dim_date(date_id)
);

CREATE TABLE fact_strategy_signals (
    signal_id            INT PRIMARY KEY,
    instrument_id        INT NOT NULL,
    strategy_id          INT NOT NULL,
    signal_date          DATE NOT NULL,
    signal_type          VARCHAR(20) NOT NULL,
    signal_strength      DECIMAL(6,3) NOT NULL,
    expected_direction   VARCHAR(10) NOT NULL,
    actual_direction     VARCHAR(10) NOT NULL,
    signal_result        VARCHAR(15) NOT NULL,
    CONSTRAINT fk_signals_instrument FOREIGN KEY (instrument_id) REFERENCES dim_instrument(instrument_id),
    CONSTRAINT fk_signals_strategy   FOREIGN KEY (strategy_id) REFERENCES dim_strategy(strategy_id)
);
