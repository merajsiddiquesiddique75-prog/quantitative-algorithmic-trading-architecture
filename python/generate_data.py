"""
generate_data.py
=================
Synthetic data generator for the Quantitative Algorithmic Trading Architecture
project.

This script builds a relationally consistent synthetic dataset that mimics a
real quantitative trading desk: instruments, exchanges, strategies, traders,
market data, orders, trades, positions, portfolio performance, risk metrics
and strategy signals.

Run:
    python python/generate_data.py

Output:
    CSV files written to data/raw/

The script prints a final validation block confirming the total record count
and referential integrity across all tables.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
SEED = 42
np.random.seed(SEED)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

N_EXCHANGE = 5
N_INSTRUMENT = 50
N_STRATEGY = 10
N_TRADER = 20
N_DAYS = 730  # ~2 trading years of calendar days

N_MARKET_DATA = N_INSTRUMENT * N_DAYS          # 36,500
N_ORDERS = 60_000
N_TRADES = 50_000
N_POSITIONS = 20_000
N_PORTFOLIO_PERF = N_TRADER * N_DAYS           # 14,600
N_RISK_WEEKS = N_DAYS // 7                     # 104
N_RISK_METRICS = N_TRADER * N_RISK_WEEKS       # 2,080
N_STRATEGY_SIGNALS = 16_005

EXPECTED_TOTAL = 200_000

START_DATE = datetime(2023, 1, 1)

# ----------------------------------------------------------------------------
# DIM: EXCHANGE
# ----------------------------------------------------------------------------
exchange_names = ["NYSE", "NASDAQ", "LSE", "NSE", "TSE"]
exchange_countries = ["USA", "USA", "UK", "India", "Japan"]
exchange_currencies = ["USD", "USD", "GBP", "INR", "JPY"]
exchange_tz = ["America/New_York", "America/New_York", "Europe/London",
               "Asia/Kolkata", "Asia/Tokyo"]

dim_exchange = pd.DataFrame({
    "exchange_id": range(1, N_EXCHANGE + 1),
    "exchange_name": exchange_names,
    "country": exchange_countries,
    "currency": exchange_currencies,
    "market_timezone": exchange_tz,
})

# ----------------------------------------------------------------------------
# DIM: INSTRUMENT
# ----------------------------------------------------------------------------
asset_classes = ["Equity", "ETF", "Forex", "Commodity", "Crypto", "Bond"]
sectors = ["Technology", "Financials", "Healthcare", "Energy", "Industrials",
           "Consumer", "Materials", "Utilities", "Real Estate", "Diversified"]
volatility_classes = ["Low", "Medium", "High"]
liquidity_classes = ["Low", "Medium", "High"]

instrument_symbols = [f"SYM{str(i).zfill(3)}" for i in range(1, N_INSTRUMENT + 1)]
instrument_names = [f"{sym} Corp" for sym in instrument_symbols]

dim_instrument = pd.DataFrame({
    "instrument_id": range(1, N_INSTRUMENT + 1),
    "instrument_symbol": instrument_symbols,
    "instrument_name": instrument_names,
    "asset_class": np.random.choice(asset_classes, N_INSTRUMENT),
    "sector": np.random.choice(sectors, N_INSTRUMENT),
    "exchange_id": np.random.randint(1, N_EXCHANGE + 1, N_INSTRUMENT),
    "volatility_class": np.random.choice(volatility_classes, N_INSTRUMENT, p=[0.4, 0.4, 0.2]),
    "liquidity_class": np.random.choice(liquidity_classes, N_INSTRUMENT, p=[0.2, 0.4, 0.4]),
})

# ----------------------------------------------------------------------------
# DIM: STRATEGY
# ----------------------------------------------------------------------------
strategy_names = [
    "Momentum Breakout", "Mean Reversion", "Pairs Trading", "Trend Following",
    "Statistical Arbitrage", "Swing Trading", "Scalping", "Value Rotation",
    "Volatility Arbitrage", "Market Making"
]
strategy_types = ["Momentum", "Mean Reversion", "Arbitrage", "Trend",
                   "Arbitrage", "Swing", "High Frequency", "Value",
                   "Arbitrage", "Market Making"]
risk_levels = ["Low", "Medium", "High", "Medium", "High", "Medium", "High",
               "Low", "High", "Medium"]
holding_periods = ["Short-Term", "Medium-Term", "Short-Term", "Long-Term",
                    "Short-Term", "Medium-Term", "Intraday", "Long-Term",
                    "Short-Term", "Intraday"]

dim_strategy = pd.DataFrame({
    "strategy_id": range(1, N_STRATEGY + 1),
    "strategy_name": strategy_names,
    "strategy_type": strategy_types,
    "risk_level": risk_levels,
    "holding_period_type": holding_periods,
})

# ----------------------------------------------------------------------------
# DIM: TRADER
# ----------------------------------------------------------------------------
experience_levels = ["Junior", "Mid", "Senior", "Expert"]
trading_styles = ["Aggressive", "Balanced", "Conservative"]

trader_names = [f"Trader_{i:02d}" for i in range(1, N_TRADER + 1)]

dim_trader = pd.DataFrame({
    "trader_id": range(1, N_TRADER + 1),
    "trader_name": trader_names,
    "experience_level": np.random.choice(experience_levels, N_TRADER, p=[0.3, 0.3, 0.25, 0.15]),
    "trading_style": np.random.choice(trading_styles, N_TRADER),
})

# ----------------------------------------------------------------------------
# DIM: DATE
# ----------------------------------------------------------------------------
date_range = [START_DATE + timedelta(days=i) for i in range(N_DAYS)]

dim_date = pd.DataFrame({
    "date_id": range(1, N_DAYS + 1),
    "date": [d.strftime("%Y-%m-%d") for d in date_range],
    "year": [d.year for d in date_range],
    "month": [d.month for d in date_range],
    "month_name": [d.strftime("%B") for d in date_range],
    "quarter": [(d.month - 1) // 3 + 1 for d in date_range],
    "week": [d.isocalendar()[1] for d in date_range],
    "day_name": [d.strftime("%A") for d in date_range],
})

# trading days only (exclude Sat/Sun) - used to bias fact generation realism
trading_day_ids = dim_date.loc[~dim_date["day_name"].isin(["Saturday", "Sunday"]), "date_id"].values

# ----------------------------------------------------------------------------
# FACT: MARKET DATA (random walk price per instrument across all days)
# ----------------------------------------------------------------------------
market_rows = []
market_id = 1
for inst_id in dim_instrument["instrument_id"]:
    vol_class = dim_instrument.loc[dim_instrument.instrument_id == inst_id, "volatility_class"].values[0]
    daily_vol = {"Low": 0.005, "Medium": 0.015, "High": 0.03}[vol_class]

    price = np.random.uniform(20, 500)
    returns = np.random.normal(0.0003, daily_vol, N_DAYS)
    prices = price * np.cumprod(1 + returns)

    open_p = prices * (1 + np.random.normal(0, daily_vol / 4, N_DAYS))
    close_p = prices
    high_p = np.maximum(open_p, close_p) * (1 + np.abs(np.random.normal(0, daily_vol / 3, N_DAYS)))
    low_p = np.minimum(open_p, close_p) * (1 - np.abs(np.random.normal(0, daily_vol / 3, N_DAYS)))
    volume = np.random.randint(10_000, 5_000_000, N_DAYS)

    daily_return = np.insert(np.diff(close_p) / close_p[:-1], 0, 0.0)

    for i in range(N_DAYS):
        market_rows.append((
            market_id, inst_id, i + 1,
            round(open_p[i], 2), round(high_p[i], 2), round(low_p[i], 2), round(close_p[i], 2),
            int(volume[i]), round(daily_vol, 4), round(daily_return[i], 6)
        ))
        market_id += 1

fact_market_data = pd.DataFrame(market_rows, columns=[
    "market_data_id", "instrument_id", "date_id", "open_price", "high_price",
    "low_price", "close_price", "volume", "volatility", "daily_return"
])
assert len(fact_market_data) == N_MARKET_DATA

# lookup for close price by (instrument_id, date_id) - used downstream for realism
price_lookup = fact_market_data.set_index(["instrument_id", "date_id"])["close_price"].to_dict()

# ----------------------------------------------------------------------------
# FACT: ORDERS
# ----------------------------------------------------------------------------
order_types = ["Market", "Limit", "Stop", "Stop-Limit"]
order_sides = ["Buy", "Sell"]
order_statuses = ["Filled", "Partially Filled", "Cancelled", "Rejected"]

o_trader = np.random.randint(1, N_TRADER + 1, N_ORDERS)
o_strategy = np.random.randint(1, N_STRATEGY + 1, N_ORDERS)
o_instrument = np.random.randint(1, N_INSTRUMENT + 1, N_ORDERS)
o_date = np.random.choice(trading_day_ids, N_ORDERS)
o_type = np.random.choice(order_types, N_ORDERS, p=[0.5, 0.35, 0.1, 0.05])
o_side = np.random.choice(order_sides, N_ORDERS)
o_qty = np.random.randint(10, 5000, N_ORDERS)
o_status = np.random.choice(order_statuses, N_ORDERS, p=[0.8, 0.1, 0.07, 0.03])

o_price = np.array([
    price_lookup.get((inst, d), np.random.uniform(20, 500)) * (1 + np.random.normal(0, 0.01))
    for inst, d in zip(o_instrument, o_date)
])

date_str_map = dim_date.set_index("date_id")["date"].to_dict()

fact_orders = pd.DataFrame({
    "order_id": range(1, N_ORDERS + 1),
    "order_date": [date_str_map[d] for d in o_date],
    "trader_id": o_trader,
    "strategy_id": o_strategy,
    "instrument_id": o_instrument,
    "order_type": o_type,
    "order_side": o_side,
    "order_quantity": o_qty,
    "order_price": np.round(o_price, 2),
    "order_status": o_status,
})

# ----------------------------------------------------------------------------
# FACT: TRADES (derived from a subset of filled orders)
# ----------------------------------------------------------------------------
filled_orders = fact_orders[fact_orders["order_status"] == "Filled"].copy()
trade_source = filled_orders.sample(n=N_TRADES, replace=True, random_state=SEED).reset_index(drop=True)

entry_date_id = np.array([
    dim_date.loc[dim_date["date"] == d, "date_id"].values[0] for d in trade_source["order_date"]
])
holding_days = np.random.randint(1, 60, N_TRADES)
exit_date_id = np.clip(entry_date_id + holding_days, 1, N_DAYS)

entry_price = trade_source["order_price"].values
strategy_ids_t = trade_source["strategy_id"].values
risk_level_map = dim_strategy.set_index("strategy_id")["risk_level"].to_dict()
strategy_vol = np.array([{"Low": 0.01, "Medium": 0.02, "High": 0.04}[risk_level_map[s]] for s in strategy_ids_t])

price_move = np.random.normal(0.001, strategy_vol, N_TRADES) * holding_days
exit_price = entry_price * (1 + price_move)

quantity = trade_source["order_quantity"].values
side_sign = np.where(trade_source["order_side"].values == "Buy", 1, -1)

gross_pnl = (exit_price - entry_price) * quantity * side_sign
transaction_cost = np.round(np.abs(entry_price * quantity) * 0.0008, 2)
net_pnl = gross_pnl - transaction_cost
return_pct = (net_pnl / (entry_price * quantity)) * 100

fact_trades = pd.DataFrame({
    "trade_id": range(1, N_TRADES + 1),
    "order_id": trade_source["order_id"].values,
    "instrument_id": trade_source["instrument_id"].values,
    "trader_id": trade_source["trader_id"].values,
    "strategy_id": strategy_ids_t,
    "entry_date": [date_str_map[d] for d in entry_date_id],
    "exit_date": [date_str_map[d] for d in exit_date_id],
    "entry_price": np.round(entry_price, 2),
    "exit_price": np.round(exit_price, 2),
    "quantity": quantity,
    "gross_pnl": np.round(gross_pnl, 2),
    "transaction_cost": transaction_cost,
    "net_pnl": np.round(net_pnl, 2),
    "return_percentage": np.round(return_pct, 4),
    "holding_period_days": holding_days,
})

# ----------------------------------------------------------------------------
# FACT: POSITIONS
# ----------------------------------------------------------------------------
p_instrument = np.random.randint(1, N_INSTRUMENT + 1, N_POSITIONS)
p_trader = np.random.randint(1, N_TRADER + 1, N_POSITIONS)
p_strategy = np.random.randint(1, N_STRATEGY + 1, N_POSITIONS)
p_date = np.random.choice(trading_day_ids, N_POSITIONS)
p_type = np.random.choice(["Long", "Short"], N_POSITIONS)
p_qty = np.random.randint(10, 3000, N_POSITIONS)

p_entry_price = np.array([
    price_lookup.get((i, d), np.random.uniform(20, 500)) for i, d in zip(p_instrument, p_date)
])
p_current_price = p_entry_price * (1 + np.random.normal(0, 0.02, N_POSITIONS))
p_sign = np.where(p_type == "Long", 1, -1)
p_unrealized = (p_current_price - p_entry_price) * p_qty * p_sign

fact_positions = pd.DataFrame({
    "position_id": range(1, N_POSITIONS + 1),
    "instrument_id": p_instrument,
    "trader_id": p_trader,
    "strategy_id": p_strategy,
    "position_date": [date_str_map[d] for d in p_date],
    "position_type": p_type,
    "quantity": p_qty,
    "entry_price": np.round(p_entry_price, 2),
    "current_price": np.round(p_current_price, 2),
    "unrealized_pnl": np.round(p_unrealized, 2),
})

# ----------------------------------------------------------------------------
# FACT: PORTFOLIO PERFORMANCE (per trader, per day)
# ----------------------------------------------------------------------------
perf_rows = []
perf_id = 1
for trader_id in dim_trader["trader_id"]:
    style = dim_trader.loc[dim_trader.trader_id == trader_id, "trading_style"].values[0]
    style_vol = {"Aggressive": 0.02, "Balanced": 0.012, "Conservative": 0.006}[style]
    strategy_id = np.random.randint(1, N_STRATEGY + 1)

    portfolio_value = 1_000_000.0
    cumulative_return = 0.0
    daily_returns = np.random.normal(0.0006, style_vol, N_DAYS)
    benchmark_returns = np.random.normal(0.0004, 0.01, N_DAYS)

    values = portfolio_value * np.cumprod(1 + daily_returns)
    cum_returns = (values / portfolio_value - 1) * 100
    cum_benchmark = (np.cumprod(1 + benchmark_returns) - 1) * 100

    for i in range(N_DAYS):
        perf_rows.append((
            perf_id, trader_id, strategy_id, i + 1,
            round(values[i], 2), round(daily_returns[i], 6),
            round(cum_returns[i], 4), round(cum_benchmark[i], 4)
        ))
        perf_id += 1

fact_portfolio_performance = pd.DataFrame(perf_rows, columns=[
    "performance_id", "trader_id", "strategy_id", "date_id", "portfolio_value",
    "daily_return", "cumulative_return", "benchmark_return"
])
assert len(fact_portfolio_performance) == N_PORTFOLIO_PERF

# ----------------------------------------------------------------------------
# FACT: RISK METRICS (per trader, per week)
# ----------------------------------------------------------------------------
risk_rows = []
risk_id = 1
week_date_ids = [i * 7 + 1 for i in range(N_RISK_WEEKS)]
for trader_id in dim_trader["trader_id"]:
    strategy_id = np.random.randint(1, N_STRATEGY + 1)
    for d in week_date_ids:
        volatility = round(np.random.uniform(0.08, 0.45), 4)
        sharpe = round(np.random.normal(1.1, 0.7), 3)
        max_dd = round(-abs(np.random.uniform(0.02, 0.35)), 4)
        var_95 = round(-abs(np.random.uniform(5000, 60000)), 2)
        risk_score = round(np.clip(np.random.normal(50, 20), 1, 100), 1)
        risk_rows.append((risk_id, trader_id, strategy_id, d, volatility, sharpe, max_dd, var_95, risk_score))
        risk_id += 1

fact_risk_metrics = pd.DataFrame(risk_rows, columns=[
    "risk_id", "trader_id", "strategy_id", "date_id", "volatility", "sharpe_ratio",
    "maximum_drawdown", "value_at_risk", "risk_score"
])
assert len(fact_risk_metrics) == N_RISK_METRICS

# ----------------------------------------------------------------------------
# FACT: STRATEGY SIGNALS
# ----------------------------------------------------------------------------
s_instrument = np.random.randint(1, N_INSTRUMENT + 1, N_STRATEGY_SIGNALS)
s_strategy = np.random.randint(1, N_STRATEGY + 1, N_STRATEGY_SIGNALS)
s_date = np.random.choice(trading_day_ids, N_STRATEGY_SIGNALS)
s_type = np.random.choice(["Buy Signal", "Sell Signal", "Hold Signal"], N_STRATEGY_SIGNALS, p=[0.4, 0.4, 0.2])
s_strength = np.round(np.random.uniform(0.1, 1.0, N_STRATEGY_SIGNALS), 3)
s_expected = np.where(s_type == "Buy Signal", "Up", np.where(s_type == "Sell Signal", "Down", "Flat"))

# actual direction is correct ~58% of the time (realistic edge, not perfect)
correct_mask = np.random.rand(N_STRATEGY_SIGNALS) < 0.58
directions = ["Up", "Down", "Flat"]
s_actual = np.where(
    correct_mask,
    s_expected,
    [directions[np.random.randint(0, 3)] for _ in range(N_STRATEGY_SIGNALS)]
)
s_result = np.where(s_actual == s_expected, "Correct", "Incorrect")

fact_strategy_signals = pd.DataFrame({
    "signal_id": range(1, N_STRATEGY_SIGNALS + 1),
    "instrument_id": s_instrument,
    "strategy_id": s_strategy,
    "signal_date": [date_str_map[d] for d in s_date],
    "signal_type": s_type,
    "signal_strength": s_strength,
    "expected_direction": s_expected,
    "actual_direction": s_actual,
    "signal_result": s_result,
})

# ----------------------------------------------------------------------------
# VALIDATION (performed on the clean, relationally-consistent base dataset
# BEFORE any data-quality issues are intentionally injected below)
# ----------------------------------------------------------------------------
_clean_tables = {
    "dim_exchange": dim_exchange,
    "dim_instrument": dim_instrument,
    "dim_strategy": dim_strategy,
    "dim_trader": dim_trader,
    "dim_date": dim_date,
    "fact_market_data": fact_market_data,
    "fact_orders": fact_orders,
    "fact_trades": fact_trades,
    "fact_positions": fact_positions,
    "fact_portfolio_performance": fact_portfolio_performance,
    "fact_risk_metrics": fact_risk_metrics,
    "fact_strategy_signals": fact_strategy_signals,
}

total_records = sum(len(df) for df in _clean_tables.values())

fk_checks = [
    ("dim_instrument.exchange_id", set(dim_instrument.exchange_id) <= set(dim_exchange.exchange_id)),
    ("fact_market_data.instrument_id", set(fact_market_data.instrument_id) <= set(dim_instrument.instrument_id)),
    ("fact_market_data.date_id", set(fact_market_data.date_id) <= set(dim_date.date_id)),
    ("fact_orders.trader_id", set(fact_orders.trader_id) <= set(dim_trader.trader_id)),
    ("fact_orders.strategy_id", set(fact_orders.strategy_id) <= set(dim_strategy.strategy_id)),
    ("fact_orders.instrument_id", set(fact_orders.instrument_id) <= set(dim_instrument.instrument_id)),
    ("fact_trades.order_id", set(fact_trades.order_id) <= set(fact_orders.order_id)),
    ("fact_trades.instrument_id", set(fact_trades.instrument_id) <= set(dim_instrument.instrument_id)),
    ("fact_trades.trader_id", set(fact_trades.trader_id) <= set(dim_trader.trader_id)),
    ("fact_trades.strategy_id", set(fact_trades.strategy_id) <= set(dim_strategy.strategy_id)),
    ("fact_positions.instrument_id", set(fact_positions.instrument_id) <= set(dim_instrument.instrument_id)),
    ("fact_positions.trader_id", set(fact_positions.trader_id) <= set(dim_trader.trader_id)),
    ("fact_positions.strategy_id", set(fact_positions.strategy_id) <= set(dim_strategy.strategy_id)),
    ("fact_portfolio_performance.trader_id", set(fact_portfolio_performance.trader_id) <= set(dim_trader.trader_id)),
    ("fact_portfolio_performance.strategy_id", set(fact_portfolio_performance.strategy_id) <= set(dim_strategy.strategy_id)),
    ("fact_portfolio_performance.date_id", set(fact_portfolio_performance.date_id) <= set(dim_date.date_id)),
    ("fact_risk_metrics.trader_id", set(fact_risk_metrics.trader_id) <= set(dim_trader.trader_id)),
    ("fact_risk_metrics.strategy_id", set(fact_risk_metrics.strategy_id) <= set(dim_strategy.strategy_id)),
    ("fact_risk_metrics.date_id", set(fact_risk_metrics.date_id) <= set(dim_date.date_id)),
    ("fact_strategy_signals.instrument_id", set(fact_strategy_signals.instrument_id) <= set(dim_instrument.instrument_id)),
    ("fact_strategy_signals.strategy_id", set(fact_strategy_signals.strategy_id) <= set(dim_strategy.strategy_id)),
]

all_fk_valid = all(result for _, result in fk_checks)

print("=" * 60)
print("QUANTITATIVE ALGORITHMIC TRADING ARCHITECTURE - DATA GENERATION")
print("=" * 60)
for name, df in _clean_tables.items():
    print(f"{name:35s}: {len(df):>8,} records")
print("-" * 60)
print(f"Total records generated: {total_records:,}")
print(f"Expected total records : {EXPECTED_TOTAL:,}")

if total_records == EXPECTED_TOTAL:
    print("Record count validation: PASSED")
else:
    print("Record count validation: FAILED")

print("-" * 60)
print("Foreign key validation:")
for name, result in fk_checks:
    print(f"  {name:40s}: {'PASSED' if result else 'FAILED'}")

print("-" * 60)
if total_records == EXPECTED_TOTAL and all_fk_valid:
    print("Validation: PASSED")
else:
    print("Validation: FAILED")
print("=" * 60)

# ----------------------------------------------------------------------------
# INTRODUCE REALISTIC DATA-QUALITY ISSUES (applied AFTER validation, so the
# 200,000-record / FK validation above always reflects the true base data).
# This gives python/data_cleaning.py genuine, demonstrable work to do:
# missing values, duplicate rows, inconsistent casing, outliers and
# negative values that should not physically occur.
# ----------------------------------------------------------------------------


def _dirty_missing(df, cols, frac=0.01):
    for col in cols:
        idx = df.sample(frac=frac, random_state=SEED).index
        df.loc[idx, col] = np.nan
    return df


def _dirty_duplicates(df, frac=0.005):
    dup_rows = df.sample(frac=frac, random_state=SEED)
    return pd.concat([df, dup_rows], ignore_index=True)


def _dirty_case(df, col, frac=0.02):
    idx = df.sample(frac=frac, random_state=SEED).index
    df.loc[idx, col] = df.loc[idx, col].str.lower()
    return df


fact_orders = _dirty_missing(fact_orders, ["order_price"], frac=0.01)
fact_trades = _dirty_missing(fact_trades, ["exit_price"], frac=0.01)
fact_positions = _dirty_missing(fact_positions, ["current_price"], frac=0.01)

fact_orders = _dirty_duplicates(fact_orders, frac=0.004)
fact_trades = _dirty_duplicates(fact_trades, frac=0.004)

fact_orders = _dirty_case(fact_orders, "order_status", frac=0.02)
fact_positions = _dirty_case(fact_positions, "position_type", frac=0.02)

outlier_idx = fact_trades.sample(n=25, random_state=SEED).index
fact_trades.loc[outlier_idx, "quantity"] = fact_trades.loc[outlier_idx, "quantity"] * 1000

neg_idx = fact_market_data.sample(n=15, random_state=SEED).index
fact_market_data.loc[neg_idx, "volume"] = -fact_market_data.loc[neg_idx, "volume"]

print(f"\nNote: minor data-quality issues (missing values, {len(fact_orders) - N_ORDERS + len(fact_trades) - N_TRADES}"
      f" duplicate rows, inconsistent casing, outliers) were intentionally injected")
print("into the RAW CSVs above the validated base counts, for python/data_cleaning.py to resolve.")

# ----------------------------------------------------------------------------
# SAVE ALL FILES (raw, includes intentionally injected data-quality issues)
# ----------------------------------------------------------------------------
tables = {
    "dim_exchange": dim_exchange,
    "dim_instrument": dim_instrument,
    "dim_strategy": dim_strategy,
    "dim_trader": dim_trader,
    "dim_date": dim_date,
    "fact_market_data": fact_market_data,
    "fact_orders": fact_orders,
    "fact_trades": fact_trades,
    "fact_positions": fact_positions,
    "fact_portfolio_performance": fact_portfolio_performance,
    "fact_risk_metrics": fact_risk_metrics,
    "fact_strategy_signals": fact_strategy_signals,
}

for name, df in tables.items():
    df.to_csv(os.path.join(RAW_DIR, f"{name}.csv"), index=False)

print(f"\nAll CSV files saved to: {RAW_DIR}")
