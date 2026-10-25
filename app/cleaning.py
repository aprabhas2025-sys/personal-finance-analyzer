"""CSV cleaning: turn any common bank/UPI export into the shared schema.

Handles:
  * different header names (Date / Txn Date / Narration / Particulars / Remarks ...)
  * separate Debit/Credit columns OR one signed Amount column OR Amount + Dr/Cr column
  * amounts like "1,234.50", "₹1,234.50", "Rs. 500", "(500.00)", "500 Dr"
  * dates like dd/mm/yyyy, dd-mm-yyyy, yyyy-mm-dd, "05 Nov 2025"
"""
import re

import numpy as np
import pandas as pd

from ml.schema import COLUMNS, UNCATEGORIZED

ALIASES = {
    "date": ["date", "txn date", "transaction date", "value date", "posting date", "tran date"],
    "description": ["description", "narration", "particulars", "remarks", "details",
                    "transaction remarks", "transaction details", "merchant"],
    "debit": ["debit", "withdrawal", "withdrawal amt", "withdrawal amount", "dr", "debit amount", "money out"],
    "credit": ["credit", "deposit", "deposit amt", "deposit amount", "cr", "credit amount", "money in"],
    "amount": ["amount", "txn amount", "transaction amount"],
    "type": ["type", "dr/cr", "cr/dr", "transaction type", "txn type"],
    "category": ["category"],
}


class CleaningError(ValueError):
    """Raised with a user-friendly message when a file can't be understood."""


def _norm(name):
    return re.sub(r"\s+", " ", str(name).strip().lower())


def _find_columns(df):
    found, norm = {}, {_norm(c): c for c in df.columns}
    for canon, names in ALIASES.items():
        for n in names:
            if n in norm:
                found[canon] = norm[n]
                break
    return found


def parse_amount(value):
    """'₹1,234.50' -> 1234.5 ; '(500)' -> -500 ; '' -> NaN."""
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.number)):
        return float(value)
    s = str(value).strip()
    if not s:
        return np.nan
    neg = s.startswith("(") and s.endswith(")") or s.startswith("-") or bool(re.search(r"\bdr\b", s, re.I))
    s = re.sub(r"(?i)\b(rs|inr)\b\.?", "", s)      # drop currency words so "Rs." isn't read as a decimal point
    s = re.sub(r"[^\d.]", "", s)
    if s in ("", "."):
        return np.nan
    v = float(s)
    return -v if neg else v


def _parse_dates(series):
    s = series.astype(str).str.strip()
    iso = s.str.match(r"^\d{4}-\d{2}-\d{2}")
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    if iso.any():
        out[iso] = pd.to_datetime(s[iso], errors="coerce")
    if (~iso).any():
        out[~iso] = pd.to_datetime(s[~iso], dayfirst=True, errors="coerce")   # Indian dd/mm/yyyy
    return out


def clean_transactions(raw: pd.DataFrame):
    """Return (clean_df, report). clean_df follows ml.schema.COLUMNS."""
    cols = _find_columns(raw)
    missing = [c for c in ("date", "description") if c not in cols]
    if missing:
        raise CleaningError(
            f"Could not find a {' / '.join(missing)} column. Found columns: {list(raw.columns)}")

    df = pd.DataFrame({
        "date": _parse_dates(raw[cols["date"]]),
        "description": raw[cols["description"]].astype(str).str.replace(r"\s+", " ", regex=True).str.strip(),
    })

    # Work out amount + type
    if "debit" in cols or "credit" in cols:
        deb = raw[cols["debit"]].map(parse_amount) if "debit" in cols else pd.Series(np.nan, index=raw.index)
        cre = raw[cols["credit"]].map(parse_amount) if "credit" in cols else pd.Series(np.nan, index=raw.index)
        is_debit = deb.fillna(0).abs() > 0
        df["amount"] = np.where(is_debit, deb.abs(), cre.abs())
        df["type"] = np.where(is_debit, "debit", "credit")
        df.loc[deb.isna() & cre.isna(), "amount"] = np.nan
    elif "amount" in cols:
        amt = raw[cols["amount"]].map(parse_amount)
        if "type" in cols:
            t = raw[cols["type"]].astype(str).str.lower().str.strip()
            df["type"] = np.where(t.str.startswith(("dr", "d", "debit", "w")), "debit", "credit")
        else:
            df["type"] = np.where(amt < 0, "debit", "credit")   # signed amounts: negative = money out
        df["amount"] = amt.abs()
    else:
        raise CleaningError("Could not find amount columns (need Debit/Credit or Amount).")

    df["category"] = raw[cols["category"]].fillna(UNCATEGORIZED) if "category" in cols else UNCATEGORIZED

    n_in = len(df)
    bad = df["date"].isna() | df["amount"].isna() | (df["amount"] <= 0) | (df["description"] == "")
    df = df[~bad]
    df = df.sort_values("date", kind="stable").reset_index(drop=True)[COLUMNS]
    df["amount"] = df["amount"].astype(float)

    report = {
        "rows_in": n_in,
        "rows_out": len(df),
        "rows_dropped": int(bad.sum()),
        "date_range": (df.date.min(), df.date.max()) if len(df) else (None, None),
        "total_debit": float(df.loc[df.type == "debit", "amount"].sum()),
        "total_credit": float(df.loc[df.type == "credit", "amount"].sum()),
    }
    if len(df) == 0:
        raise CleaningError("No valid transactions found after cleaning. Check the date and amount formats.")
    return df, report
