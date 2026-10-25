"""Recurring-payment detection (subscriptions, EMIs, rent, bills).

A merchant counts as recurring when its debits repeat on a regular rhythm:
  * at least MIN_OCCURRENCES payments
  * the median gap is close to a known billing period (weekly / fortnightly / monthly / quarterly)
  * gaps are consistent (coefficient of variation <= GAP_CV_MAX), which rejects habits like
    "orders food a lot" where gaps are short and random
  * amounts are fairly stable (CV <= AMOUNT_CV_MAX); a bill that varies is still allowed
"""
import numpy as np
import pandas as pd

from ml.categorizer import _NOISE, normalize

MIN_OCCURRENCES = 3
PERIODS = [(7, 2), (14, 3), (30, 4), (91, 10)]   # (nominal days, tolerance)
GAP_CV_MAX = 0.20
AMOUNT_CV_MAX = 0.50
COLUMNS = ["merchant", "avg_amount", "frequency_days", "last_seen", "next_due"]


def recurring_key(desc: str) -> str:
    """Merchant identity for grouping: first two meaningful tokens.
    'UPI/AMAZON PRIME/123' -> 'AMAZON PRIME' (kept apart from 'AMAZON PAY INDIA 9' -> 'AMAZON PAY')."""
    toks = [t for t in normalize(desc).split() if t not in _NOISE and not t.startswith("TYPE")]
    return " ".join(toks[:2]) or "UNKNOWN"


def _matches_period(median_gap: float) -> bool:
    return any(abs(median_gap - nominal) <= tol for nominal, tol in PERIODS)


def find_recurring(df: pd.DataFrame) -> pd.DataFrame:
    """One row per recurring payment: merchant, avg_amount, frequency_days, last_seen, next_due."""
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNS)
    d = df[df["type"] == "debit"].copy()
    d["date"] = pd.to_datetime(d["date"]).dt.normalize()
    d = d.drop_duplicates(subset=["date", "description", "amount"])   # accidental double charges are not a rhythm
    d["key"] = d["description"].map(recurring_key)

    rows = []
    for key, g in d.groupby("key"):
        if len(g) < MIN_OCCURRENCES:
            continue
        g = g.sort_values("date")
        gaps = g["date"].diff().dt.days.dropna().to_numpy(dtype=float)
        if gaps.mean() <= 0 or not _matches_period(float(np.median(gaps))):
            continue
        if gaps.std() / gaps.mean() > GAP_CV_MAX:
            continue
        amt = g["amount"].to_numpy(dtype=float)
        if amt.std() / amt.mean() > AMOUNT_CV_MAX:
            continue
        freq = int(round(float(np.median(gaps))))
        last = g["date"].max()
        rows.append({"merchant": key, "avg_amount": round(float(amt.mean()), 2),
                     "frequency_days": freq, "last_seen": last, "next_due": last + pd.Timedelta(days=freq)})
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame(rows, columns=COLUMNS).sort_values("next_due").reset_index(drop=True)
