-- ============================================================================
-- load_data.sql
-- Loads the cleaned CSV files (data/processed/) into quant_trading_db.
-- ============================================================================
-- IMPORTANT:
--   1. Run schema.sql first.
--   2. Update the file paths below to the absolute path of your local
--      data/processed/ folder before running.
--   3. Your MySQL client/server must allow LOCAL INFILE:
--        mysql --local-infile=1 -u root -p quant_trading_db < sql/load_data.sql
--      and the server variable must be enabled:
--        SET GLOBAL local_infile = 1;
-- ============================================================================

USE quant_trading_db;

SET GLOBAL local_infile = 1;
SET FOREIGN_KEY_CHECKS = 0;

-- Replace /path/to/project/ below with the absolute path to your project folder.
-- On Windows use forward slashes, e.g. C:/Users/you/quantitative-algorithmic-trading-architecture/

LOAD DATA LOCAL INFILE '/path/to/project/data/processed/dim_exchange.csv'
INTO TABLE dim_exchange
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/path/to/project/data/processed/dim_instrument.csv'
INTO TABLE dim_instrument
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/path/to/project/data/processed/dim_strategy.csv'
INTO TABLE dim_strategy
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/path/to/project/data/processed/dim_trader.csv'
INTO TABLE dim_trader
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/path/to/project/data/processed/dim_date.csv'
INTO TABLE dim_date
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/path/to/project/data/processed/fact_market_data.csv'
INTO TABLE fact_market_data
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/path/to/project/data/processed/fact_orders.csv'
INTO TABLE fact_orders
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/path/to/project/data/processed/fact_trades.csv'
INTO TABLE fact_trades
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/path/to/project/data/processed/fact_positions.csv'
INTO TABLE fact_positions
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/path/to/project/data/processed/fact_portfolio_performance.csv'
INTO TABLE fact_portfolio_performance
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/path/to/project/data/processed/fact_risk_metrics.csv'
INTO TABLE fact_risk_metrics
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/path/to/project/data/processed/fact_strategy_signals.csv'
INTO TABLE fact_strategy_signals
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

SET FOREIGN_KEY_CHECKS = 1;

-- Quick sanity check after loading
SELECT 'dim_exchange' AS table_name, COUNT(*) AS row_count FROM dim_exchange
UNION ALL SELECT 'dim_instrument', COUNT(*) FROM dim_instrument
UNION ALL SELECT 'dim_strategy', COUNT(*) FROM dim_strategy
UNION ALL SELECT 'dim_trader', COUNT(*) FROM dim_trader
UNION ALL SELECT 'dim_date', COUNT(*) FROM dim_date
UNION ALL SELECT 'fact_market_data', COUNT(*) FROM fact_market_data
UNION ALL SELECT 'fact_orders', COUNT(*) FROM fact_orders
UNION ALL SELECT 'fact_trades', COUNT(*) FROM fact_trades
UNION ALL SELECT 'fact_positions', COUNT(*) FROM fact_positions
UNION ALL SELECT 'fact_portfolio_performance', COUNT(*) FROM fact_portfolio_performance
UNION ALL SELECT 'fact_risk_metrics', COUNT(*) FROM fact_risk_metrics
UNION ALL SELECT 'fact_strategy_signals', COUNT(*) FROM fact_strategy_signals;
