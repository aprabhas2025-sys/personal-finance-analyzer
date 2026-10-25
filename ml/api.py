"""INTERFACE CONTRACT between Person A and Person B.

Person B calls these three functions. Person A replaces the dummy bodies with the real
models on Days 2-4 (categorize: Day 2, anomalies + recurring: Day 3, forecast: Day 4). Signatures and return columns MUST NOT change.
"""
from pathlib import Path

import pandas as pd

from ml.schema import UNCATEGORIZED

# Model retrained from user corrections (Day 4). Kept separate from the shipped model so a deploy
# is never polluted, and gitignored. categorize() prefers it when it exists.
USER_MODEL_PATH = Path(__file__).resolve().parent / "models" / "categorizer_user.joblib"


REVIEW_THRESHOLD = 0.7   # below this, a prediction is flagged "needs review" in the app
_pipe = None


def categorize(df: pd.DataFrame) -> pd.DataFrame:
    """Fill `category` for rows that are Uncategorized using the hybrid (rules + ML) model.

    Also adds two columns: `confidence` (0-1; 1.0 when a rule fired) and `category_source`
    ('rule' | 'ml' | 'existing'). Rows that already have a category are left untouched.
    """
    global _pipe
    from ml import categorizer as C
    if _pipe is None:
        _pipe = C.load(USER_MODEL_PATH) or C.load()   # user-corrected model first; None -> rules-only fallback
    out = df.copy()
    todo = out["category"] == UNCATEGORIZED
    out["confidence"] = 1.0
    out["category_source"] = "existing"
    if todo.any():
        cats, conf, src = C.predict(out[todo], _pipe, "hybrid")
        out.loc[todo, "category"] = cats
        out.loc[todo, "confidence"] = conf
        out.loc[todo, "category_source"] = src
    return out


def reload_model():
    """Call after retraining so the next categorize() uses the new model."""
    global _pipe
    _pipe = None


def find_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with `is_anomaly` (0/1) and `anomaly_reason` (str) columns.

    Signals: duplicate charges, per-category robust z-score, Isolation Forest, new-merchant
    large spend. Details and thresholds live in ml/anomalies.py.
    """
    from ml import anomalies
    return anomalies.find_anomalies(df)


def find_recurring(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per recurring payment: merchant, avg_amount, frequency_days, last_seen, next_due."""
    from ml import recurring
    return recurring.find_recurring(df)


def forecast(df: pd.DataFrame) -> pd.DataFrame:
    """Return next-month forecast: columns category, forecast_amount (debit categories, largest first).

    Method chosen by rolling-origin backtest (ml/forecast.py, metrics/forecast_report.md).
    """
    from ml import forecast as F
    return F.forecast_table(df)
