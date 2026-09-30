-- ============================================================================
-- analysis_queries.sql
-- Quantitative Algorithmic Trading Architecture - Analysis Queries
-- ============================================================================
-- 20 queries covering SELECT/WHERE/GROUP BY/HAVING/ORDER BY/CASE, aggregations,
-- JOINs, multi-table JOINs, subqueries, CTEs, window functions, date analysis,
-- ranking, running totals, strategy/risk/portfolio analysis.
-- No stored procedures, triggers, transactions, indexes, or views are used.
-- ============================================================================

USE quant_trading_db;

-- 1. Basic SELECT + WHERE: all filled Buy orders above 50,000 quantity
SELECT order_id, order_date, trader_id, instrument_id, order_quantity, order_price
FROM fact_orders
WHERE order_side = 'Buy' AND order_status = 'Filled' AND order_quantity > 4000
ORDER BY order_quantity DESC;

-- 2. Aggregation + GROUP BY: total and average net P&L per strategy
SELECT strategy_id,
       COUNT(*)              AS total_trades,
       SUM(net_pnl)           AS total_net_pnl,
       ROUND(AVG(net_pnl), 2) AS avg_net_pnl
FROM fact_trades
GROUP BY strategy_id
ORDER BY total_net_pnl DESC;

-- 3. GROUP BY + HAVING: strategies with more than 4,000 trades and positive P&L
SELECT strategy_id,
       COUNT(*)      AS total_trades,
       SUM(net_pnl)  AS total_net_pnl
FROM fact_trades
GROUP BY strategy_id
HAVING COUNT(*) > 4000 AND SUM(net_pnl) > 0
ORDER BY total_net_pnl DESC;

-- 4. CASE expression: classify trades by outcome and size
SELECT trade_id,
       net_pnl,
       CASE
           WHEN net_pnl > 5000 THEN 'Large Win'
           WHEN net_pnl > 0    THEN 'Small Win'
           WHEN net_pnl > -5000 THEN 'Small Loss'
           ELSE 'Large Loss'
       END AS pnl_category
FROM fact_trades
ORDER BY net_pnl DESC
LIMIT 100;

-- 5. Simple JOIN: trades with instrument details
SELECT t.trade_id, i.instrument_symbol, i.asset_class, t.net_pnl, t.return_percentage
FROM fact_trades t
JOIN dim_instrument i ON t.instrument_id = i.instrument_id
ORDER BY t.net_pnl DESC
LIMIT 50;

-- 6. Multi-table JOIN: trade detail with strategy, trader and instrument
SELECT t.trade_id,
       tr.trader_name,
       s.strategy_name,
       i.instrument_symbol,
       t.entry_date,
       t.exit_date,
       t.net_pnl
FROM fact_trades t
JOIN dim_trader tr     ON t.trader_id = tr.trader_id
JOIN dim_strategy s    ON t.strategy_id = s.strategy_id
JOIN dim_instrument i  ON t.instrument_id = i.instrument_id
ORDER BY t.net_pnl DESC
LIMIT 50;

-- 7. Subquery in WHERE: trades with net P&L above the overall average
SELECT trade_id, strategy_id, net_pnl
FROM fact_trades
WHERE net_pnl > (SELECT AVG(net_pnl) FROM fact_trades)
ORDER BY net_pnl DESC
LIMIT 100;

-- 8. Correlated subquery: instruments whose average trade return beats their sector average
SELECT i.instrument_symbol, i.sector,
       (SELECT ROUND(AVG(t.return_percentage), 4)
        FROM fact_trades t WHERE t.instrument_id = i.instrument_id) AS instrument_avg_return
FROM dim_instrument i
WHERE (SELECT AVG(t.return_percentage) FROM fact_trades t WHERE t.instrument_id = i.instrument_id) >
      (SELECT AVG(t2.return_percentage)
       FROM fact_trades t2
       JOIN dim_instrument i2 ON t2.instrument_id = i2.instrument_id
       WHERE i2.sector = i.sector);

-- 9. CTE: strategy-level win rate
WITH strategy_stats AS (
    SELECT strategy_id,
           COUNT(*) AS total_trades,
           SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) AS wins
    FROM fact_trades
    GROUP BY strategy_id
)
SELECT s.strategy_name,
       ss.total_trades,
       ss.wins,
       ROUND(ss.wins / ss.total_trades * 100, 2) AS win_rate_pct
FROM strategy_stats ss
JOIN dim_strategy s ON s.strategy_id = ss.strategy_id
ORDER BY win_rate_pct DESC;

-- 10. CTE + window function: rank traders by total net P&L
WITH trader_pnl AS (
    SELECT trader_id, SUM(net_pnl) AS total_net_pnl
    FROM fact_trades
    GROUP BY trader_id
)
SELECT trader_id,
       total_net_pnl,
       RANK() OVER (ORDER BY total_net_pnl DESC) AS pnl_rank
FROM trader_pnl;

-- 11. Window function: running total of daily portfolio P&L (trader 1)
SELECT date_id,
       daily_return,
       SUM(daily_return) OVER (ORDER BY date_id) AS running_return
FROM fact_portfolio_performance
WHERE trader_id = 1
ORDER BY date_id;

-- 12. Window function: moving average of closing price (7-day) per instrument
SELECT instrument_id,
       date_id,
       close_price,
       ROUND(AVG(close_price) OVER (
           PARTITION BY instrument_id ORDER BY date_id
           ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
       ), 2) AS moving_avg_7d
FROM fact_market_data
WHERE instrument_id = 1
ORDER BY date_id;

-- 13. Date analysis: monthly trade volume and P&L
SELECT d.year, d.month, d.month_name,
       COUNT(t.trade_id) AS total_trades,
       SUM(t.net_pnl)    AS total_net_pnl
FROM fact_trades t
JOIN dim_date d ON d.date_id = (SELECT date_id FROM dim_date WHERE date = t.entry_date)
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;

-- 13b. Date analysis (alternate form): monthly trade volume and P&L via direct date JOIN
SELECT d.year, d.month, d.month_name,
       COUNT(t.trade_id) AS total_trades,
       SUM(t.net_pnl)    AS total_net_pnl
FROM fact_trades t
JOIN dim_date d ON d.date = t.entry_date
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;

-- 14. Ranking within groups: top 3 trades per strategy by net P&L
SELECT *
FROM (
    SELECT trade_id, strategy_id, net_pnl,
           ROW_NUMBER() OVER (PARTITION BY strategy_id ORDER BY net_pnl DESC) AS rn
    FROM fact_trades
) ranked
WHERE rn <= 3
ORDER BY strategy_id, net_pnl DESC;

-- 15. Strategy analysis: risk-adjusted performance (P&L per unit of avg risk score)
SELECT s.strategy_name,
       ROUND(SUM(t.net_pnl), 2)            AS total_net_pnl,
       ROUND(AVG(r.risk_score), 2)         AS avg_risk_score,
       ROUND(SUM(t.net_pnl) / NULLIF(AVG(r.risk_score), 0), 2) AS pnl_per_risk_point
FROM fact_trades t
JOIN dim_strategy s ON s.strategy_id = t.strategy_id
JOIN fact_risk_metrics r ON r.strategy_id = t.strategy_id
GROUP BY s.strategy_name
ORDER BY pnl_per_risk_point DESC;

-- 16. Risk analysis: average Sharpe ratio and max drawdown by risk level
SELECT s.risk_level,
       ROUND(AVG(r.sharpe_ratio), 3)      AS avg_sharpe_ratio,
       ROUND(AVG(r.maximum_drawdown), 4)  AS avg_max_drawdown,
       ROUND(AVG(r.volatility), 4)        AS avg_volatility
FROM fact_risk_metrics r
JOIN dim_strategy s ON s.strategy_id = r.strategy_id
GROUP BY s.risk_level
ORDER BY avg_sharpe_ratio DESC;

-- 17. Portfolio analysis: best single trading day per trader (by portfolio_value)
SELECT trader_id, date_id, portfolio_value
FROM (
    SELECT trader_id, date_id, portfolio_value,
           ROW_NUMBER() OVER (PARTITION BY trader_id ORDER BY portfolio_value DESC) AS rn
    FROM fact_portfolio_performance
) x
WHERE rn = 1
ORDER BY portfolio_value DESC;

-- 18. Portfolio vs benchmark: cumulative outperformance by trader (latest date)
SELECT trader_id,
       cumulative_return,
       benchmark_return,
       ROUND(cumulative_return - benchmark_return, 4) AS excess_return
FROM fact_portfolio_performance
WHERE date_id = (SELECT MAX(date_id) FROM fact_portfolio_performance)
ORDER BY excess_return DESC;

-- 19. Signal accuracy by strategy
SELECT s.strategy_name,
       COUNT(*) AS total_signals,
       SUM(CASE WHEN sig.signal_result = 'Correct' THEN 1 ELSE 0 END) AS correct_signals,
       ROUND(SUM(CASE WHEN sig.signal_result = 'Correct' THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS accuracy_pct
FROM fact_strategy_signals sig
JOIN dim_strategy s ON s.strategy_id = sig.strategy_id
GROUP BY s.strategy_name
ORDER BY accuracy_pct DESC;

-- 20. Instrument-level performance combining trades and market volatility
-- (market volatility pre-aggregated per instrument first, to avoid a fan-out
--  join between fact_trades and fact_market_data)
WITH instrument_volatility AS (
    SELECT instrument_id, ROUND(AVG(volatility), 4) AS avg_market_volatility
    FROM fact_market_data
    GROUP BY instrument_id
)
SELECT i.instrument_symbol,
       i.asset_class,
       COUNT(t.trade_id)         AS total_trades,
       ROUND(SUM(t.net_pnl), 2)  AS total_net_pnl,
       iv.avg_market_volatility
FROM fact_trades t
JOIN dim_instrument i ON i.instrument_id = t.instrument_id
JOIN instrument_volatility iv ON iv.instrument_id = t.instrument_id
GROUP BY i.instrument_symbol, i.asset_class, iv.avg_market_volatility
ORDER BY total_net_pnl DESC;
