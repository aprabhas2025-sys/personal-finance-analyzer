import numpy as np
import pandas as pd
import pytest

from ml import api, anomalies as A
from ml.generate_data import generate


def _tx(rows):
    return pd.DataFrame(rows, columns=["date", "description", "amount", "type", "category"]).assign(
        date=lambda d: pd.to_datetime(d["date"]))


def _base(n=30, cat="Groceries"):
    rng = np.random.default_rng(0)
    days = pd.date_range("2026-01-01", periods=n, freq="3D")
    return [(d, f"UPI/BIGBASKET/{i}", float(rng.integers(300, 500)), "debit", cat) for i, d in enumerate(days)]


def test_contract_columns_and_no_mutation():
    df = generate()
    before = df.copy()
    out = api.find_anomalies(df)
    assert {"is_anomaly", "anomaly_reason"} <= set(out.columns)
    assert set(out["is_anomaly"].unique()) <= {0, 1}
    assert len(out) == len(df)
    pd.testing.assert_frame_equal(df, before)                       # input untouched
    assert (out.loc[out.is_anomaly == 0, "anomaly_reason"] == "").all()
    assert (out.loc[out.is_anomaly == 1, "anomaly_reason"] != "").all()


def test_exact_duplicate_flagged_original_kept():
    rows = _base() + [(pd.Timestamp("2026-02-01"), "UPI/ZOMATO/55", 250.0, "debit", "Food Delivery")] * 2
    out = api.find_anomalies(_tx(rows))
    dup = out[out["description"] == "UPI/ZOMATO/55"]
    assert list(dup["is_anomaly"]) == [0, 1] and "duplicate" in dup["anomaly_reason"].iloc[1]


def test_oversized_spend_flagged_normal_not():
    rows = _base() + [(pd.Timestamp("2026-04-20"), "UPI/BIGBASKET/999", 6000.0, "debit", "Groceries")]
    out = api.find_anomalies(_tx(rows))
    assert out.iloc[-1]["is_anomaly"] == 1 and "typical Groceries" in out.iloc[-1]["anomaly_reason"]
    assert out.iloc[:-1]["is_anomaly"].sum() == 0


def test_fixed_amount_category_small_change_not_flagged_but_big_jump_is():
    rent = [(pd.Timestamp(2026, m, 1), "NEFT-RENT-LANDLORD 21", 18000.0, "debit", "Rent") for m in range(1, 11)]
    assert api.find_anomalies(_tx(rent))["is_anomaly"].sum() == 0
    jump = rent + [(pd.Timestamp(2026, 11, 1), "NEFT-RENT-LANDLORD 21", 30000.0, "debit", "Rent")]
    assert api.find_anomalies(_tx(jump)).iloc[-1]["is_anomaly"] == 1


def test_small_categories_are_skipped_not_crashed():
    rows = [(pd.Timestamp("2026-01-01"), "X", 100.0, "debit", "Travel"), (pd.Timestamp("2026-01-02"), "Y", 90000.0, "debit", "Travel")]
    assert api.find_anomalies(_tx(rows))["is_anomaly"].sum() == 0    # < MIN_GROUP rows: no basis to judge


def test_empty_frame():
    out = api.find_anomalies(_tx([]))
    assert len(out) == 0 and {"is_anomaly", "anomaly_reason"} <= set(out.columns)


def test_nondefault_index_is_handled():
    rows = _base() + [(pd.Timestamp("2026-04-20"), "UPI/BIGBASKET/999", 6000.0, "debit", "Groceries")]
    df = _tx(rows)
    df.index = df.index + 500
    out = api.find_anomalies(df)
    assert out.iloc[-1]["is_anomaly"] == 1 and list(out.index) == list(df.index)


def test_shipped_config_on_seed42_matches_ground_truth():
    df = generate()
    out = api.find_anomalies(df)
    pred, truth = out["is_anomaly"].to_numpy() == 1, df["is_anomaly"].to_numpy() == 1
    assert (pred & truth).sum() == 12 and pred.sum() <= 14            # regression guard (seed 42, not a general claim)


def test_heldout_seeds_floor():
    """Guards against regressions only: loose floors well under the measured ~0.79 / ~0.81."""
    p, r = [], []
    for s in range(1, 6):
        df = generate(seed=s)
        pred = api.find_anomalies(df)["is_anomaly"].to_numpy() == 1
        truth = df["is_anomaly"].to_numpy() == 1
        tp = (pred & truth).sum()
        p.append(tp / max(pred.sum(), 1)); r.append(tp / truth.sum())
    assert np.mean(p) > 0.6 and np.mean(r) > 0.65


def test_iforest_signal_runs_and_is_gated_by_z():
    df = generate()
    sig = A.compute_signals(df, A.ALL_SIGNALS)
    assert sig["iforest"].sum() > 0
    assert (sig.loc[sig["iforest"], "z"] > A.IF_MIN_Z).all()
