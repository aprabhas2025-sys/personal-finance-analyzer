"""Anomaly detection for a cleaned, categorized transaction table.

Four signals, each computed separately so evaluation can ablate them:
  dup       exact repeat of date + description + amount + type (keeps the first, flags the repeats)
  zscore    amount is far above what is normal for its (type, category): robust z on log(amount)
  iforest   Isolation Forest on [log amount, category z]; only counts when z is also elevated
  new_merch first-ever transaction at a merchant (after a 60-day warm-up) with an unusually large amount

Which signals are ON is decided by ACTIVE_SIGNALS below, based on the ablation in
ml/eval_anomalies.py (metrics/anomaly_report.md). iforest counts only when z > IF_MIN_Z as well.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ml.categorizer import merchant_key

Z_THRESHOLD = 3.5        # robust z on log(amount); 3.5 is the usual MAD outlier cutoff
MIN_GROUP = 8            # skip categories with fewer rows than this (too little history)
MIN_LOG_SCALE = 0.05     # floor for MAD in log space, so fixed-amount categories (rent) don't explode
IF_CONTAMINATION = 0.02
IF_MIN_Z = 2.0           # Isolation Forest alone is noisy, so it must agree with a mildly high z
NEW_MERCHANT_WARMUP_DAYS = 60
NEW_MERCHANT_MIN_SPAN_DAYS = 120
NEW_MERCHANT_AMOUNT_MULT = 2.0   # vs category median
SEED = 42
ALL_SIGNALS = ("dup", "zscore", "iforest", "new_merch")
ACTIVE_SIGNALS = ("dup", "zscore")   # best F1 in ml/eval_anomalies.py; add "iforest" for higher recall / lower precision


def _category_z(df: pd.DataFrame):
    """Robust z of log(amount) within each (type, category). Returns (z, typical_amount).

    Spread = max(MAD, IQR/1.349, upper-tail spread, floor). MAD alone collapses to ~0 when many
    rows share the category's minimum amount (e.g. a Rs.150 minimum delivery order) and the median
    sits on that floor, which would make every slightly larger row look extreme. The upper-tail term,
    (P90 - median)/1.2816, measures how far the normal right tail extends, which is what matters
    when only unusually LARGE amounts are being flagged. All three equal sigma for normal data.
    """
    logs = np.log(df["amount"].clip(lower=0.01))
    key = df["type"].astype(str) + "|" + df["category"].astype(str)
    g = logs.groupby(key)
    med = g.transform("median")
    mad = (logs - med).abs().groupby(key).transform("median") * 1.4826
    iqr = (g.transform(lambda s: s.quantile(0.75)) - g.transform(lambda s: s.quantile(0.25))) / 1.349
    upper = (g.transform(lambda s: s.quantile(0.90)) - med) / 1.2816
    scale = np.maximum(np.maximum(np.maximum(mad, iqr), upper), MIN_LOG_SCALE)
    z = (logs - med) / scale
    z[g.transform("size") < MIN_GROUP] = 0.0
    return z, np.exp(med)


def compute_signals(df: pd.DataFrame, signals=ALL_SIGNALS) -> pd.DataFrame:
    """Boolean signal columns + z + typical amount, aligned to df's row order (positional).
    Only the requested `signals` are computed; the others are all-False."""
    d = df.reset_index(drop=True)
    n = len(d)
    sig = pd.DataFrame(index=d.index)
    if n == 0:
        for c in ALL_SIGNALS:
            sig[c] = pd.Series(dtype=bool)
        sig["z"], sig["typical"] = pd.Series(dtype=float), pd.Series(dtype=float)
        return sig

    day = pd.to_datetime(d["date"]).dt.normalize()
    sig["dup"] = pd.DataFrame({"d": day, "s": d["description"], "a": d["amount"], "t": d["type"]}).duplicated(keep="first")

    z, typical = _category_z(d)
    sig["z"], sig["typical"] = z, typical
    is_debit = d["type"].eq("debit")
    sig["zscore"] = np.where(is_debit, z > Z_THRESHOLD, z.abs() > Z_THRESHOLD)

    # Isolation Forest (debits only: spending behaviour). Contamination is a prior, not a guarantee.
    sig["iforest"] = False
    deb = d[is_debit]
    if "iforest" in signals and len(deb) >= 50:
        X = np.column_stack([np.log(deb["amount"].clip(lower=0.01)), z[deb.index].clip(-10, 10)])
        flag = IsolationForest(n_estimators=200, contamination=IF_CONTAMINATION, random_state=SEED).fit_predict(X) == -1
        sig.loc[deb.index, "iforest"] = flag & (z[deb.index].to_numpy() > IF_MIN_Z)

    # New merchant with a large amount (only meaningful once there is enough history)
    sig["new_merch"] = False
    if "new_merch" in signals and (day.max() - day.min()).days >= NEW_MERCHANT_MIN_SPAN_DAYS:
        mk = d["description"].map(merchant_key)
        first = day.groupby(mk).transform("min")
        is_first_row = ~pd.DataFrame({"m": mk, "d": day}).duplicated(keep="first")
        late = first > day.min() + pd.Timedelta(days=NEW_MERCHANT_WARMUP_DAYS)
        big = d["amount"] >= NEW_MERCHANT_AMOUNT_MULT * typical
        sig["new_merch"] = (is_debit & is_first_row & late & big & (z > 0)).to_numpy()
    return sig


def combine(sig: pd.DataFrame, use=None) -> pd.Series:
    out = pd.Series(False, index=sig.index)
    for u in (ACTIVE_SIGNALS if use is None else use):
        out |= sig[u].astype(bool)
    return out


def _reasons(d: pd.DataFrame, sig: pd.DataFrame) -> list:
    reasons = []
    for i in range(len(d)):
        r = []
        if sig.at[i, "dup"]:
            r.append("duplicate of an earlier transaction (same day, description and amount)")
        amt, typ = d.at[i, "amount"], sig.at[i, "typical"]
        ratio = f"{amt / typ:.1f}x the typical {d.at[i, 'category']} amount (Rs.{typ:,.0f})"
        if sig.at[i, "zscore"]:
            r.append(f"amount Rs.{amt:,.0f} is {ratio}")
        elif sig.at[i, "iforest"]:
            r.append(f"statistically unusual amount: {ratio}")
        if sig.at[i, "new_merch"]:
            r.append("first transaction at a new merchant, and a large one")
        reasons.append("; ".join(r))
    return reasons


def find_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with `is_anomaly` (0/1) and `anomaly_reason` (str). Input is not mutated."""
    out = df.copy()
    d = df.reset_index(drop=True)
    sig = compute_signals(d, ACTIVE_SIGNALS)
    flag = combine(sig)
    out["is_anomaly"] = flag.astype(int).to_numpy()
    out["anomaly_reason"] = _reasons(d, sig) if len(d) else []
    out["anomaly_reason"] = np.where(out["is_anomaly"] == 1, out["anomaly_reason"], "")
    return out
