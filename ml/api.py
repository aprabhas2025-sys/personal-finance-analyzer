"""INTERFACE CONTRACT between Person A and Person B.

Person B calls these three functions. Person A replaces the dummy bodies with the real
models on Days 2-4. Signatures and return columns MUST NOT change.
"""
import pandas as pd

from ml.schema import UNCATEGORIZED


def categorize(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with the `category` column filled in. (Day 2)"""
    out = df.copy()
    out["category"] = out["category"].where(out["category"] != UNCATEGORIZED, "Shopping")  # DUMMY
    return out


def find_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with `is_anomaly` (0/1) and `anomaly_reason` (str) columns. (Day 3)"""
    out = df.copy()
    out["is_anomaly"] = 0           # DUMMY
    out["anomaly_reason"] = ""
    return out


def find_recurring(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per recurring payment: merchant, avg_amount, frequency_days, last_seen, next_due. (Day 3)"""
    return pd.DataFrame(columns=["merchant", "avg_amount", "frequency_days", "last_seen", "next_due"])  # DUMMY


def forecast(df: pd.DataFrame) -> pd.DataFrame:
    """Return next-month forecast: columns category, forecast_amount. (Day 4)"""
    d = df[df["type"] == "debit"]
    m = d.groupby("category")["amount"].sum() / max(d["date"].dt.to_period("M").nunique(), 1)  # DUMMY: avg
    return m.rename("forecast_amount").reset_index()
