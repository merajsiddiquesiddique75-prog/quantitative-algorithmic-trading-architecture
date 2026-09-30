"""
analysis.py
===========
Runs quantitative trading analysis on the cleaned dataset (data/processed/)
and produces KPI, strategy, risk and trade-level outputs plus charts.

Run:
    python python/analysis.py

Outputs:
    output/kpi_summary.csv
    output/strategy_performance.csv
    output/risk_analysis.csv
    output/trade_analysis.csv
    output/business_insights.txt
    output/charts/*.png
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CHARTS_DIR = os.path.join(OUTPUT_DIR, "charts")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

plt.rcParams["figure.figsize"] = (10, 6)
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3

# ----------------------------------------------------------------------------
# LOAD
# ----------------------------------------------------------------------------
trades = pd.read_csv(os.path.join(PROCESSED_DIR, "fact_trades.csv"))
orders = pd.read_csv(os.path.join(PROCESSED_DIR, "fact_orders.csv"))
positions = pd.read_csv(os.path.join(PROCESSED_DIR, "fact_positions.csv"))
performance = pd.read_csv(os.path.join(PROCESSED_DIR, "fact_portfolio_performance.csv"))
risk = pd.read_csv(os.path.join(PROCESSED_DIR, "fact_risk_metrics.csv"))
signals = pd.read_csv(os.path.join(PROCESSED_DIR, "fact_strategy_signals.csv"))
strategies = pd.read_csv(os.path.join(PROCESSED_DIR, "dim_strategy.csv"))
instruments = pd.read_csv(os.path.join(PROCESSED_DIR, "dim_instrument.csv"))
traders = pd.read_csv(os.path.join(PROCESSED_DIR, "dim_trader.csv"))
dim_date = pd.read_csv(os.path.join(PROCESSED_DIR, "dim_date.csv"))

trades["entry_date"] = pd.to_datetime(trades["entry_date"])
trades["exit_date"] = pd.to_datetime(trades["exit_date"])

# ----------------------------------------------------------------------------
# 1. CORE KPIs (computed strictly from generated data - no invented numbers)
# ----------------------------------------------------------------------------
total_trades = len(trades)
winning_trades = int((trades["net_pnl"] > 0).sum())
losing_trades = int((trades["net_pnl"] <= 0).sum())
win_rate = round(winning_trades / total_trades * 100, 2)

gross_pnl = round(trades["gross_pnl"].sum(), 2)
net_pnl = round(trades["net_pnl"].sum(), 2)
avg_trade_pnl = round(trades["net_pnl"].mean(), 2)
avg_return_pct = round(trades["return_percentage"].mean(), 4)

# Sharpe ratio computed from daily portfolio returns (annualized, rf=0)
daily_returns = performance["daily_return"]
sharpe_ratio = round((daily_returns.mean() / daily_returns.std()) * np.sqrt(252), 3) if daily_returns.std() > 0 else 0.0

# Maximum drawdown from cumulative portfolio value series (aggregated across traders)
portfolio_by_date = performance.groupby("date_id")["portfolio_value"].sum().sort_index()
running_max = portfolio_by_date.cummax()
drawdown_series = (portfolio_by_date - running_max) / running_max
max_drawdown = round(drawdown_series.min() * 100, 2)

# Overall portfolio return (start vs end of aggregated portfolio value)
portfolio_return = round((portfolio_by_date.iloc[-1] / portfolio_by_date.iloc[0] - 1) * 100, 2)

# Volatility - annualized std dev of daily returns
volatility = round(daily_returns.std() * np.sqrt(252) * 100, 2)

# Profit factor = gross profit / gross loss
gross_profit = trades.loc[trades["net_pnl"] > 0, "net_pnl"].sum()
gross_loss = abs(trades.loc[trades["net_pnl"] <= 0, "net_pnl"].sum())
profit_factor = round(gross_profit / gross_loss, 3) if gross_loss > 0 else np.inf

avg_holding_period = round(trades["holding_period_days"].mean(), 2)

# Strategy efficiency score: composite of win rate, profit factor and avg return (0-100 scale)
strategy_efficiency_score = round(
    (win_rate * 0.4) + (min(profit_factor, 5) / 5 * 100 * 0.35) + (min(max(avg_return_pct, -10), 10) + 10) / 20 * 100 * 0.25,
    2,
)

kpi_summary = pd.DataFrame([
    {"kpi": "Total Trades", "value": total_trades},
    {"kpi": "Winning Trades", "value": winning_trades},
    {"kpi": "Losing Trades", "value": losing_trades},
    {"kpi": "Win Rate (%)", "value": win_rate},
    {"kpi": "Gross P&L", "value": gross_pnl},
    {"kpi": "Net P&L", "value": net_pnl},
    {"kpi": "Average Trade P&L", "value": avg_trade_pnl},
    {"kpi": "Average Return (%)", "value": avg_return_pct},
    {"kpi": "Sharpe Ratio (annualized)", "value": sharpe_ratio},
    {"kpi": "Maximum Drawdown (%)", "value": max_drawdown},
    {"kpi": "Portfolio Return (%)", "value": portfolio_return},
    {"kpi": "Volatility (annualized %)", "value": volatility},
    {"kpi": "Profit Factor", "value": profit_factor},
    {"kpi": "Average Holding Period (days)", "value": avg_holding_period},
    {"kpi": "Strategy Efficiency Score", "value": strategy_efficiency_score},
])
kpi_summary.to_csv(os.path.join(OUTPUT_DIR, "kpi_summary.csv"), index=False)

# ----------------------------------------------------------------------------
# 2. STRATEGY PERFORMANCE
# ----------------------------------------------------------------------------
trades_s = trades.merge(strategies, on="strategy_id", how="left")

strategy_perf = trades_s.groupby(["strategy_id", "strategy_name", "strategy_type", "risk_level"]).agg(
    total_trades=("trade_id", "count"),
    winning_trades=("net_pnl", lambda x: (x > 0).sum()),
    net_pnl=("net_pnl", "sum"),
    avg_return_pct=("return_percentage", "mean"),
    avg_holding_period=("holding_period_days", "mean"),
).reset_index()

strategy_perf["win_rate_pct"] = round(strategy_perf["winning_trades"] / strategy_perf["total_trades"] * 100, 2)
strategy_perf["net_pnl"] = strategy_perf["net_pnl"].round(2)
strategy_perf["avg_return_pct"] = strategy_perf["avg_return_pct"].round(4)
strategy_perf["avg_holding_period"] = strategy_perf["avg_holding_period"].round(2)
strategy_perf = strategy_perf.sort_values("net_pnl", ascending=False)
strategy_perf.to_csv(os.path.join(OUTPUT_DIR, "strategy_performance.csv"), index=False)

# ----------------------------------------------------------------------------
# 3. RISK ANALYSIS
# ----------------------------------------------------------------------------
risk_s = risk.merge(strategies, on="strategy_id", how="left").merge(traders, on="trader_id", how="left")

risk_analysis = risk_s.groupby(["strategy_id", "strategy_name", "risk_level"]).agg(
    avg_volatility=("volatility", "mean"),
    avg_sharpe_ratio=("sharpe_ratio", "mean"),
    avg_max_drawdown=("maximum_drawdown", "mean"),
    avg_value_at_risk=("value_at_risk", "mean"),
    avg_risk_score=("risk_score", "mean"),
).reset_index().round(4)
risk_analysis = risk_analysis.sort_values("avg_risk_score", ascending=False)
risk_analysis.to_csv(os.path.join(OUTPUT_DIR, "risk_analysis.csv"), index=False)

# ----------------------------------------------------------------------------
# 4. TRADE ANALYSIS (by instrument)
# ----------------------------------------------------------------------------
trades_i = trades.merge(instruments, on="instrument_id", how="left")

trade_analysis = trades_i.groupby(["instrument_id", "instrument_symbol", "asset_class", "sector"]).agg(
    total_trades=("trade_id", "count"),
    winning_trades=("net_pnl", lambda x: (x > 0).sum()),
    net_pnl=("net_pnl", "sum"),
    avg_return_pct=("return_percentage", "mean"),
    total_volume=("quantity", "sum"),
).reset_index()
trade_analysis["win_rate_pct"] = round(trade_analysis["winning_trades"] / trade_analysis["total_trades"] * 100, 2)
trade_analysis["net_pnl"] = trade_analysis["net_pnl"].round(2)
trade_analysis["avg_return_pct"] = trade_analysis["avg_return_pct"].round(4)
trade_analysis = trade_analysis.sort_values("net_pnl", ascending=False)
trade_analysis.to_csv(os.path.join(OUTPUT_DIR, "trade_analysis.csv"), index=False)

# ----------------------------------------------------------------------------
# 5. BUSINESS INSIGHTS (auto-generated from actual computed results)
# ----------------------------------------------------------------------------
best_strategy = strategy_perf.iloc[0]
worst_strategy = strategy_perf.iloc[-1]
best_instrument = trade_analysis.iloc[0]
riskiest_strategy = risk_analysis.iloc[0]

insights = f"""BUSINESS INSIGHTS - QUANTITATIVE ALGORITHMIC TRADING ARCHITECTURE
{"=" * 65}

1. OVERALL PERFORMANCE
   - {total_trades:,} total trades executed across {instruments.shape[0]} instruments
     and {strategies.shape[0]} strategies.
   - Win rate stands at {win_rate}% ({winning_trades:,} winning / {losing_trades:,} losing trades).
   - Net P&L across the analyzed period: {net_pnl:,.2f}.
   - Profit factor of {profit_factor} indicates the ratio of gross profit to gross loss.

2. STRATEGY INSIGHTS
   - Best performing strategy by net P&L: "{best_strategy['strategy_name']}"
     ({best_strategy['strategy_type']}, {best_strategy['risk_level']} risk) with net P&L of
     {best_strategy['net_pnl']:,.2f} and a win rate of {best_strategy['win_rate_pct']}%.
   - Weakest performing strategy by net P&L: "{worst_strategy['strategy_name']}"
     with net P&L of {worst_strategy['net_pnl']:,.2f}.

3. RISK INSIGHTS
   - Highest average risk score strategy: "{riskiest_strategy['strategy_name']}"
     (avg risk score {riskiest_strategy['avg_risk_score']}, avg Sharpe {riskiest_strategy['avg_sharpe_ratio']}).
   - Portfolio-level maximum drawdown observed: {max_drawdown}%.
   - Annualized portfolio volatility: {volatility}%.
   - Annualized Sharpe ratio: {sharpe_ratio}.

4. INSTRUMENT INSIGHTS
   - Top performing instrument by net P&L: {best_instrument['instrument_symbol']}
     ({best_instrument['asset_class']} / {best_instrument['sector']}) with net P&L of
     {best_instrument['net_pnl']:,.2f} and win rate {best_instrument['win_rate_pct']}%.

5. RECOMMENDATIONS
   - Reallocate capital toward strategies with consistently higher win rate and
     profit factor (see strategy_performance.csv), while trimming exposure to
     the weakest-performing strategy identified above.
   - Investigate the highest-risk-score strategy for position sizing adjustments,
     given its risk profile relative to its realized Sharpe ratio.
   - Monitor drawdown periods closely and consider a volatility-based stop
     mechanism for high-volatility-class instruments.
   - Use signal accuracy from fact_strategy_signals.csv to further filter
     entries for strategies with below-average signal correctness.
"""

with open(os.path.join(OUTPUT_DIR, "business_insights.txt"), "w") as f:
    f.write(insights)

# ----------------------------------------------------------------------------
# 6. CHARTS
# ----------------------------------------------------------------------------
# Chart 1: Portfolio value trend
plt.figure()
plt.plot(portfolio_by_date.index, portfolio_by_date.values, color="#2563eb", linewidth=1.5)
plt.title("Aggregated Portfolio Value Over Time")
plt.xlabel("Date ID")
plt.ylabel("Portfolio Value")
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "portfolio_value_trend.png"), dpi=120)
plt.close()

# Chart 2: Strategy P&L comparison
plt.figure()
plt.barh(strategy_perf["strategy_name"], strategy_perf["net_pnl"], color="#16a34a")
plt.title("Net P&L by Strategy")
plt.xlabel("Net P&L")
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "strategy_pnl_comparison.png"), dpi=120)
plt.close()

# Chart 3: Win vs Loss distribution
plt.figure()
plt.pie([winning_trades, losing_trades], labels=["Winning Trades", "Losing Trades"],
        autopct="%1.1f%%", colors=["#16a34a", "#dc2626"])
plt.title("Winning vs Losing Trades")
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "win_loss_distribution.png"), dpi=120)
plt.close()

# Chart 4: Drawdown over time
plt.figure()
plt.fill_between(drawdown_series.index, drawdown_series.values * 100, color="#dc2626", alpha=0.5)
plt.title("Portfolio Drawdown Over Time")
plt.xlabel("Date ID")
plt.ylabel("Drawdown (%)")
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "drawdown_over_time.png"), dpi=120)
plt.close()

# Chart 5: Risk score by strategy
plt.figure()
plt.bar(risk_analysis["strategy_name"], risk_analysis["avg_risk_score"], color="#f59e0b")
plt.xticks(rotation=45, ha="right")
plt.title("Average Risk Score by Strategy")
plt.ylabel("Avg Risk Score")
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "risk_score_by_strategy.png"), dpi=120)
plt.close()

# ----------------------------------------------------------------------------
# SUMMARY PRINT
# ----------------------------------------------------------------------------
print("=" * 60)
print("QUANTITATIVE ANALYSIS COMPLETE")
print("=" * 60)
print(kpi_summary.to_string(index=False))
print("-" * 60)
print(f"Outputs saved to: {OUTPUT_DIR}")
print(f"Charts saved to : {CHARTS_DIR}")
print("=" * 60)
