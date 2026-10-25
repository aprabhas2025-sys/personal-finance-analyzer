import pandas as pd
import pytest

from app.cleaning import CleaningError, clean_transactions, parse_amount
from ml.schema import COLUMNS


def test_parse_amount_variants():
    assert parse_amount("1,234.50") == 1234.5
    assert parse_amount("₹1,234.50") == 1234.5
    assert parse_amount("Rs. 500") == 500
    assert parse_amount("(500.00)") == -500
    assert parse_amount("500 Dr") == -500
    assert pd.isna(parse_amount(""))
    assert pd.isna(parse_amount(None))


def test_debit_credit_columns():
    raw = pd.DataFrame({"Date": ["05/11/2025", "06/11/2025"], "Narration": ["UPI/SWIGGY/1", "SALARY"],
                        "Debit": ["450.00", ""], "Credit": ["", "85,000.00"]})
    df, rep = clean_transactions(raw)
    assert list(df.columns) == COLUMNS
    assert df.loc[0, "type"] == "debit" and df.loc[0, "amount"] == 450
    assert df.loc[1, "type"] == "credit" and df.loc[1, "amount"] == 85000
    assert df.loc[0, "date"] == pd.Timestamp(2025, 11, 5)       # dd/mm/yyyy, not mm/dd


def test_signed_amount_column():
    raw = pd.DataFrame({"Txn Date": ["2025-11-05", "2025-11-06"], "Description": ["A", "B"], "Amount": ["-200", "300"]})
    df, _ = clean_transactions(raw)
    assert list(df["type"]) == ["debit", "credit"] and list(df["amount"]) == [200, 300]


def test_amount_with_drcr_column():
    raw = pd.DataFrame({"Date": ["05-11-2025", "06-11-2025"], "Particulars": ["A", "B"],
                        "Amount": ["200", "300"], "Dr/Cr": ["DR", "CR"]})
    df, _ = clean_transactions(raw)
    assert list(df["type"]) == ["debit", "credit"]


def test_bad_rows_dropped_and_reported():
    raw = pd.DataFrame({"Date": ["05/11/2025", "not a date", "07/11/2025"], "Narration": ["A", "B", ""],
                        "Debit": ["100", "100", "100"], "Credit": ["", "", ""]})
    df, rep = clean_transactions(raw)
    assert len(df) == 1 and rep["rows_dropped"] == 2


def test_duplicates_are_kept():          # duplicate charges are anomalies, not noise
    raw = pd.DataFrame({"Date": ["05/11/2025"] * 2, "Narration": ["UPI/X/1"] * 2, "Debit": ["99", "99"], "Credit": ["", ""]})
    df, _ = clean_transactions(raw)
    assert len(df) == 2


def test_missing_columns_raises():
    with pytest.raises(CleaningError):
        clean_transactions(pd.DataFrame({"foo": [1], "bar": [2]}))


def test_sample_file_roundtrip():
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "data"
    raw = pd.read_csv(p / "synthetic_bank_export.csv", dtype=str)
    truth = pd.read_csv(p / "synthetic_labeled.csv", parse_dates=["date"])
    df, rep = clean_transactions(raw)
    assert len(df) == len(truth) and rep["rows_dropped"] == 0
    assert abs(df["amount"].sum() - truth["amount"].sum()) < 1
