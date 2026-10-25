"""A + B together: real sample CSV -> clean -> categorize -> SQLite -> anomalies/recurring -> charts -> Streamlit app."""
from pathlib import Path

import pandas as pd
import pytest

from app import charts, db
from app.cleaning import clean_transactions
from ml import api

DATA = Path(__file__).resolve().parent.parent / "data"
APP = Path(__file__).resolve().parent.parent / "app" / "app.py"


def test_pipeline_end_to_end(tmp_path):
    raw = pd.read_csv(DATA / "synthetic_bank_export.csv", dtype=str)
    df, _ = clean_transactions(raw)
    df = api.categorize(df)
    db.replace_all(df, tmp_path / "t.db")
    stored = db.load(tmp_path / "t.db")
    an = api.find_anomalies(stored.drop(columns=["id"]))
    rec = api.find_recurring(stored)
    truth = pd.read_csv(DATA / "synthetic_labeled.csv", parse_dates=["date"])
    assert len(an) == len(stored) == len(truth)
    assert an["is_anomaly"].sum() >= 12                              # all injected anomalies surface via the real pipeline
    assert len(rec) == 9
    assert charts.fig_income_vs_spend(stored) is not None


def test_streamlit_app_runs_with_sample_data(tmp_path, monkeypatch):
    AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
    monkeypatch.setattr(db, "DEFAULT_PATH", tmp_path / "app.db")
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception
    at.sidebar.button[0].click().run()                               # "Use sample data"
    assert not at.exception, [e.value for e in at.exception]
    assert [t.label for t in at.tabs][:2] == ["Dashboard", "Transactions"]
    labels = [m.label for m in at.metric]
    assert {"Savings rate", "Unusual transactions", "Recurring payments"} <= set(labels)
    rec = next(m for m in at.metric if m.label == "Recurring payments")
    assert rec.value == "9"
