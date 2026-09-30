# Power BI Dashboard — Quantitative Algorithmic Trading Architecture

This guide walks you through building a 3-page Power BI dashboard on top of the
`fact_*` / `dim_*` tables produced by this project (either loaded into MySQL
via `sql/schema.sql` + `sql/load_data.sql`, or imported directly from
`data/processed/*.csv`).

---

## 1. Connecting Data

**Option A — From MySQL**
1. Home → Get Data → More → Database → MySQL database.
2. Server: `localhost` (or your DB host), Database: `quant_trading_db`.
3. Select all `dim_*` and `fact_*` tables → Load.

**Option B — From CSV**
1. Home → Get Data → Text/CSV.
2. Import every file in `data/processed/`.

## 2. Data Model / Relationships

Build a star schema with these relationships (all single-direction,
one-dimension-to-many-fact):

| From (fact)                        | Column         | To (dimension)      | Column          |
|-------------------------------------|----------------|----------------------|-----------------|
| fact_market_data                    | instrument_id  | dim_instrument       | instrument_id   |
| fact_market_data                    | date_id        | dim_date             | date_id         |
| fact_orders                         | trader_id      | dim_trader           | trader_id       |
| fact_orders                         | strategy_id    | dim_strategy         | strategy_id     |
| fact_orders                         | instrument_id  | dim_instrument       | instrument_id   |
| fact_trades                         | trader_id      | dim_trader           | trader_id       |
| fact_trades                         | strategy_id    | dim_strategy         | strategy_id     |
| fact_trades                         | instrument_id  | dim_instrument       | instrument_id   |
| fact_positions                      | trader_id      | dim_trader           | trader_id       |
| fact_positions                      | strategy_id    | dim_strategy         | strategy_id     |
| fact_positions                      | instrument_id  | dim_instrument       | instrument_id   |
| fact_portfolio_performance          | trader_id      | dim_trader           | trader_id       |
| fact_portfolio_performance          | strategy_id    | dim_strategy         | strategy_id     |
| fact_portfolio_performance          | date_id        | dim_date             | date_id         |
| fact_risk_metrics                   | trader_id      | dim_trader           | trader_id       |
| fact_risk_metrics                   | strategy_id    | dim_strategy         | strategy_id     |
| fact_risk_metrics                   | date_id        | dim_date             | date_id         |
| fact_strategy_signals               | strategy_id    | dim_strategy         | strategy_id     |
| fact_strategy_signals               | instrument_id  | dim_instrument       | instrument_id   |
| dim_instrument                      | exchange_id    | dim_exchange         | exchange_id     |

`fact_trades.entry_date` and `fact_trades.exit_date` are text/date columns —
optionally also relate `fact_trades[entry_date]` to `dim_date[date]` (mark
`dim_date` as a **Date Table** first via Modeling → Mark as Date Table).

---

## 3. DAX Measures

Create these in a dedicated measure table (`_Measures`) for the Trades /
KPIs used across all three pages. All measures reference only columns that
exist in `fact_trades`, `fact_orders`, `fact_portfolio_performance`,
`fact_risk_metrics`, and `fact_strategy_signals`.

### Trading KPIs

**Total Trades**
```
Total Trades = COUNTROWS(fact_trades)
```
Explanation: Counts every row in the trade fact table.
Recommended visual: Card.

**Winning Trades**
```
Winning Trades = CALCULATE(COUNTROWS(fact_trades), fact_trades[net_pnl] > 0)
```
Explanation: Counts trades with a positive net P&L.
Recommended visual: Card.

**Losing Trades**
```
Losing Trades = CALCULATE(COUNTROWS(fact_trades), fact_trades[net_pnl] <= 0)
```
Explanation: Counts trades with a zero or negative net P&L.
Recommended visual: Card.

**Win Rate %**
```
Win Rate % = DIVIDE([Winning Trades], [Total Trades], 0)
```
Explanation: Share of trades that were profitable.
Recommended visual: Card / gauge.

**Gross P&L**
```
Gross P&L = SUM(fact_trades[gross_pnl])
```
Explanation: Total P&L before transaction costs.
Recommended visual: Card.

**Net P&L**
```
Net P&L = SUM(fact_trades[net_pnl])
```
Explanation: Total P&L after transaction costs.
Recommended visual: Card / KPI visual.

**Average Trade P&L**
```
Average Trade P&L = AVERAGE(fact_trades[net_pnl])
```
Explanation: Mean net P&L per trade.
Recommended visual: Card.

**Average Return %**
```
Average Return % = AVERAGE(fact_trades[return_percentage])
```
Explanation: Mean percentage return per trade.
Recommended visual: Card.

**Profit Factor**
```
Profit Factor =
VAR GrossProfit = CALCULATE(SUM(fact_trades[net_pnl]), fact_trades[net_pnl] > 0)
VAR GrossLoss = CALCULATE(SUM(fact_trades[net_pnl]), fact_trades[net_pnl] <= 0)
RETURN DIVIDE(GrossProfit, ABS(GrossLoss), 0)
```
Explanation: Ratio of total gains to total losses.
Recommended visual: Card.

**Average Holding Period**
```
Average Holding Period = AVERAGE(fact_trades[holding_period_days])
```
Explanation: Mean number of days a trade was held.
Recommended visual: Card.

### Portfolio / Risk Measures

**Portfolio Value**
```
Portfolio Value = SUM(fact_portfolio_performance[portfolio_value])
```
Explanation: Aggregated portfolio value for the current filter context.
Recommended visual: Line chart over `dim_date[date]`.

**Portfolio Return %**
```
Portfolio Return % =
VAR FirstVal = CALCULATE(SUM(fact_portfolio_performance[portfolio_value]), FIRSTDATE(dim_date[date]))
VAR LastVal  = CALCULATE(SUM(fact_portfolio_performance[portfolio_value]), LASTDATE(dim_date[date]))
RETURN DIVIDE(LastVal - FirstVal, FirstVal, 0)
```
Explanation: Percentage change in portfolio value across the selected period.
Recommended visual: Card.

**Average Sharpe Ratio**
```
Average Sharpe Ratio = AVERAGE(fact_risk_metrics[sharpe_ratio])
```
Explanation: Mean Sharpe ratio across the filtered risk records.
Recommended visual: Card.

**Average Maximum Drawdown**
```
Average Maximum Drawdown = AVERAGE(fact_risk_metrics[maximum_drawdown])
```
Explanation: Mean maximum drawdown value.
Recommended visual: Card.

**Average Volatility**
```
Average Volatility = AVERAGE(fact_risk_metrics[volatility])
```
Explanation: Mean volatility across filtered risk records.
Recommended visual: Card / line chart.

**Average Risk Score**
```
Average Risk Score = AVERAGE(fact_risk_metrics[risk_score])
```
Explanation: Mean composite risk score.
Recommended visual: Bar chart by strategy.

**Average Value at Risk**
```
Average Value at Risk = AVERAGE(fact_risk_metrics[value_at_risk])
```
Explanation: Mean VaR across filtered risk records.
Recommended visual: Card.

### Signal Measures

**Signal Accuracy %**
```
Signal Accuracy % =
DIVIDE(
    CALCULATE(COUNTROWS(fact_strategy_signals), fact_strategy_signals[signal_result] = "Correct"),
    COUNTROWS(fact_strategy_signals),
    0
)
```
Explanation: Share of strategy signals whose actual direction matched the
expected direction.
Recommended visual: Card / bar chart by strategy.

---

## 4. Page 1 — Executive Trading Overview

**KPI cards (top row):** Total Trades, Net P&L, Win Rate %, Portfolio
Return %, Average Sharpe Ratio, Average Maximum Drawdown, Average Volatility.

**Charts:**
- **Trading activity trend** — Line chart: `dim_date[date]` (axis) vs
  `Total Trades` (value), sliced by `fact_orders`.
- **P&L trend** — Line chart: `dim_date[date]` (axis) vs `Net P&L`,
  from `fact_trades[exit_date]` joined to `dim_date`.
- **Strategy performance** — Clustered bar chart: `dim_strategy[strategy_name]`
  vs `Net P&L`.
- **Instrument performance** — Bar chart: `dim_instrument[instrument_symbol]`
  vs `Net P&L` (Top N filter = 10).
- **Winning vs losing trades** — Donut chart using `Winning Trades` and
  `Losing Trades` measures.

## 5. Page 2 — Strategy & Trade Analysis

**Show:**
- **Strategy-wise P&L** — Bar chart: `dim_strategy[strategy_name]` vs `Net P&L`.
- **Strategy-wise Win Rate** — Bar chart: `dim_strategy[strategy_name]` vs `Win Rate %`.
- **Trade frequency** — Column chart: `dim_date[month_name]` vs `Total Trades`.
- **Average return** — Bar chart: `dim_strategy[strategy_name]` vs `Average Return %`.
- **Holding period** — Bar chart: `dim_strategy[strategy_name]` vs `Average Holding Period`.
- **Instrument performance** — Table: `instrument_symbol`, `asset_class`,
  `Net P&L`, `Win Rate %`.
- **Monthly performance** — Line chart: `dim_date[month_name]` vs `Net P&L`.

Add slicers for `dim_strategy[strategy_type]`, `dim_strategy[risk_level]`,
and `dim_date[year]`.

## 6. Page 3 — Risk & Portfolio Analysis

**Show:**
- **Portfolio value** — Line chart: `dim_date[date]` vs `Portfolio Value`.
- **Cumulative return** — Line chart: `dim_date[date]` vs
  `AVERAGE(fact_portfolio_performance[cumulative_return])`.
- **Drawdown** — Area chart: `dim_date[date]` vs `Average Maximum Drawdown`.
- **Volatility** — Line chart: `dim_date[date]` vs `Average Volatility`.
- **Sharpe Ratio** — Bar chart: `dim_strategy[strategy_name]` vs `Average Sharpe Ratio`.
- **Risk Score** — Bar chart: `dim_strategy[strategy_name]` vs `Average Risk Score`.
- **Strategy risk comparison** — Matrix: rows = `strategy_name`, columns =
  `risk_level`, values = `Average Risk Score`, `Average Sharpe Ratio`.
- **Instrument risk** — Scatter chart: `Average Volatility` (x) vs `Net P&L` (y),
  bubble size = `Total Trades`, legend = `dim_instrument[asset_class]`.

### Recommended Actions (text box on Page 3)
- Reduce position sizing for strategies with high `Average Risk Score` but
  below-target `Average Sharpe Ratio`.
- Reallocate capital toward strategies combining high `Win Rate %` and high
  `Profit Factor`.
- Investigate instruments with high `Average Volatility` and negative `Net P&L`
  for possible exclusion or tighter stops.
- Track `Signal Accuracy %` per strategy monthly to catch model/strategy decay early.

---

## 7. Screenshots

Place exported dashboard screenshots in `powerbi/screenshots/` (e.g.
`page1_overview.png`, `page2_strategy.png`, `page3_risk.png`) so they can be
embedded in the main project `README.md`.
