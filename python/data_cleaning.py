"""
data_cleaning.py
=================
Cleans every raw CSV produced by generate_data.py and writes clean versions
to data/processed/.

Cleaning steps performed (per table, where applicable):
    1. Missing-value detection and treatment
    2. Duplicate-row detection and removal
    3. Data-type correction
    4. Date conversion to ISO (YYYY-MM-DD)
    5. Invalid-value handling (negative prices/volumes, etc.)
    6. Categorical standardization (casing, whitespace)
    7. Outlier handling (IQR capping on numeric trade fields)
    8. Relationship / foreign-key validation against dimension tables

Run:
    python python/data_cleaning.py
"""

import os
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

TABLES = [
    "dim_exchange", "dim_instrument", "dim_strategy", "dim_trader", "dim_date",
    "fact_market_data", "fact_orders", "fact_trades", "fact_positions",
    "fact_portfolio_performance", "fact_risk_metrics", "fact_strategy_signals",
]

log = []


def report(msg):
    print(msg)
    log.append(msg)


def load(name):
    path = os.path.join(RAW_DIR, f"{name}.csv")
    return pd.read_csv(path)


# ----------------------------------------------------------------------------
# LOAD
# ----------------------------------------------------------------------------
report("=" * 60)
report("DATA CLEANING - QUANTITATIVE ALGORITHMIC TRADING ARCHITECTURE")
report("=" * 60)

data = {name: load(name) for name in TABLES}

# ----------------------------------------------------------------------------
# GENERIC CLEANING HELPERS
# ----------------------------------------------------------------------------


def clean_missing(df, name):
    before = df.isna().sum().sum()
    if before == 0:
        return df
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    object_cols = df.select_dtypes(include=["object"]).columns

    for col in numeric_cols:
        if df[col].isna().any():
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)

    for col in object_cols:
        if df[col].isna().any():
            mode_val = df[col].mode(dropna=True)
            fill_val = mode_val.iloc[0] if not mode_val.empty else "Unknown"
            df[col] = df[col].fillna(fill_val)

    report(f"  [{name}] filled {before} missing values (numeric->median, categorical->mode)")
    return df


def clean_duplicates(df, name, subset_id_col=None):
    before = len(df)
    if subset_id_col and subset_id_col in df.columns:
        df = df.drop_duplicates(subset=[subset_id_col], keep="first")
    else:
        df = df.drop_duplicates(keep="first")
    removed = before - len(df)
    if removed:
        report(f"  [{name}] removed {removed} duplicate rows")
    return df.reset_index(drop=True)


def standardize_categoricals(df, name, cols):
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
    return df


def convert_dates(df, name, cols):
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
    return df


def fix_negative(df, name, cols):
    for col in cols:
        if col in df.columns:
            n_neg = (df[col] < 0).sum()
            if n_neg:
                df[col] = df[col].abs()
                report(f"  [{name}] corrected {n_neg} negative values in '{col}' (took absolute value)")
    return df


def cap_outliers_iqr(df, name, cols):
    for col in cols:
        if col in df.columns:
            q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - 3 * iqr, q3 + 3 * iqr
            n_out = ((df[col] < lower) | (df[col] > upper)).sum()
            if n_out:
                df[col] = df[col].clip(lower, upper)
                report(f"  [{name}] capped {n_out} outliers in '{col}' using 3xIQR bounds")
    return df


# ----------------------------------------------------------------------------
# TABLE-SPECIFIC CLEANING
# ----------------------------------------------------------------------------
report("\nCleaning tables...")

# dim_date
data["dim_date"] = convert_dates(data["dim_date"], "dim_date", ["date"])
data["dim_date"]["year"] = data["dim_date"]["year"].astype(int)
data["dim_date"]["month"] = data["dim_date"]["month"].astype(int)

# dim_instrument
data["dim_instrument"] = standardize_categoricals(
    data["dim_instrument"], "dim_instrument",
    ["asset_class", "sector", "volatility_class", "liquidity_class"]
)

# fact_market_data
df = data["fact_market_data"]
df = clean_missing(df, "fact_market_data")
df = clean_duplicates(df, "fact_market_data", subset_id_col="market_data_id")
df = fix_negative(df, "fact_market_data", ["volume", "open_price", "high_price", "low_price", "close_price"])
df["volume"] = df["volume"].astype(int)
data["fact_market_data"] = df

# fact_orders
df = data["fact_orders"]
df = clean_missing(df, "fact_orders")
df = clean_duplicates(df, "fact_orders", subset_id_col="order_id")
df = standardize_categoricals(df, "fact_orders", ["order_type", "order_side", "order_status"])
df = convert_dates(df, "fact_orders", ["order_date"])
df = fix_negative(df, "fact_orders", ["order_price", "order_quantity"])
df["order_quantity"] = df["order_quantity"].astype(int)
data["fact_orders"] = df

# fact_trades
df = data["fact_trades"]
df = clean_missing(df, "fact_trades")
df = clean_duplicates(df, "fact_trades", subset_id_col="trade_id")
df = convert_dates(df, "fact_trades", ["entry_date", "exit_date"])
df = fix_negative(df, "fact_trades", ["entry_price", "exit_price", "quantity", "transaction_cost"])
df = cap_outliers_iqr(df, "fact_trades", ["quantity", "net_pnl", "return_percentage"])
df["quantity"] = df["quantity"].astype(int)
df["holding_period_days"] = df["holding_period_days"].astype(int)
data["fact_trades"] = df

# fact_positions
df = data["fact_positions"]
df = clean_missing(df, "fact_positions")
df = clean_duplicates(df, "fact_positions", subset_id_col="position_id")
df = standardize_categoricals(df, "fact_positions", ["position_type"])
df = convert_dates(df, "fact_positions", ["position_date"])
df = fix_negative(df, "fact_positions", ["entry_price", "current_price", "quantity"])
df["quantity"] = df["quantity"].astype(int)
data["fact_positions"] = df

# fact_portfolio_performance
df = data["fact_portfolio_performance"]
df = clean_missing(df, "fact_portfolio_performance")
df = clean_duplicates(df, "fact_portfolio_performance", subset_id_col="performance_id")
df = fix_negative(df, "fact_portfolio_performance", ["portfolio_value"])
data["fact_portfolio_performance"] = df

# fact_risk_metrics
df = data["fact_risk_metrics"]
df = clean_missing(df, "fact_risk_metrics")
df = clean_duplicates(df, "fact_risk_metrics", subset_id_col="risk_id")
df = fix_negative(df, "fact_risk_metrics", ["volatility", "risk_score"])
data["fact_risk_metrics"] = df

# fact_strategy_signals
df = data["fact_strategy_signals"]
df = clean_missing(df, "fact_strategy_signals")
df = clean_duplicates(df, "fact_strategy_signals", subset_id_col="signal_id")
df = standardize_categoricals(df, "fact_strategy_signals", ["signal_type", "expected_direction",
                                                              "actual_direction", "signal_result"])
df = convert_dates(df, "fact_strategy_signals", ["signal_date"])
data["fact_strategy_signals"] = df

# dim_exchange / dim_strategy / dim_trader — light standardization only
data["dim_exchange"] = clean_duplicates(data["dim_exchange"], "dim_exchange", subset_id_col="exchange_id")
data["dim_strategy"] = clean_duplicates(data["dim_strategy"], "dim_strategy", subset_id_col="strategy_id")
data["dim_trader"] = clean_duplicates(data["dim_trader"], "dim_trader", subset_id_col="trader_id")
data["dim_instrument"] = clean_duplicates(data["dim_instrument"], "dim_instrument", subset_id_col="instrument_id")

# ----------------------------------------------------------------------------
# RELATIONSHIP VALIDATION (post-clean, ensures processed data is still consistent)
# ----------------------------------------------------------------------------
report("\nValidating relationships in cleaned data...")

fk_checks = [
    ("fact_market_data.instrument_id", data["fact_market_data"]["instrument_id"].isin(data["dim_instrument"]["instrument_id"]).all()),
    ("fact_orders.trader_id", data["fact_orders"]["trader_id"].isin(data["dim_trader"]["trader_id"]).all()),
    ("fact_trades.order_id", data["fact_trades"]["order_id"].isin(data["fact_orders"]["order_id"]).all()),
    ("fact_positions.instrument_id", data["fact_positions"]["instrument_id"].isin(data["dim_instrument"]["instrument_id"]).all()),
    ("fact_portfolio_performance.trader_id", data["fact_portfolio_performance"]["trader_id"].isin(data["dim_trader"]["trader_id"]).all()),
    ("fact_risk_metrics.trader_id", data["fact_risk_metrics"]["trader_id"].isin(data["dim_trader"]["trader_id"]).all()),
    ("fact_strategy_signals.strategy_id", data["fact_strategy_signals"]["strategy_id"].isin(data["dim_strategy"]["strategy_id"]).all()),
]

for name, result in fk_checks:
    report(f"  {name:40s}: {'PASSED' if result else 'FAILED'}")

# ----------------------------------------------------------------------------
# SAVE
# ----------------------------------------------------------------------------
for name, df in data.items():
    df.to_csv(os.path.join(PROCESSED_DIR, f"{name}.csv"), index=False)

total_after = sum(len(df) for df in data.values())
report("\n" + "-" * 60)
report(f"Total records after cleaning: {total_after:,}")
report(f"Cleaned CSV files saved to: {PROCESSED_DIR}")
report("=" * 60)
