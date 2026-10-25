"""Transaction categorizer: keyword rules + TF-IDF/logistic-regression, combined as a hybrid.

  rules   -> high precision, zero training, brittle on unseen merchants
  ML      -> learns from labeled data, generalizes via character n-grams
  hybrid  -> rule if one fires, otherwise ML (this is what ships)
"""
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from ml.schema import UNCATEGORIZED

MODEL_PATH = Path(__file__).resolve().parent / "models" / "categorizer.joblib"

# (category, regex, restrict to type or None). First match wins, so order matters.
RULES = [
    ("Salary",        r"\bSALARY\b|\bPAYROLL\b", "credit"),
    ("Rent",          r"\bRENT\b|\bLANDLORD\b", "debit"),
    ("EMI",           r"\bEMI\b|\bLOAN\b|\bNACH\b", "debit"),
    ("Subscriptions", r"NETFLIX|SPOTIFY|AMAZON PRIME|YOUTUBE PREMIUM|HOTSTAR|ZEE5|SONYLIV|APPLE\.COM/BILL|GOOGLE ONE", "debit"),
    ("Utilities",     r"ELECTRICITY|BESCOM|BROADBAND|FIBERNET|AIRTEL|\bJIO\b|POSTPAID|WATER BILL|PIPED GAS|\bVI\b PREPAID", "debit"),
    ("Food Delivery", r"SWIGGY|ZOMATO|EATSURE|FAASOS", "debit"),
    ("Groceries",     r"BIGBASKET|BLINKIT|DMART|ZEPTO|RELIANCE FRESH|GROFERS|MORE SUPERMARKET", "debit"),
    ("Fuel",          r"INDIAN OIL|HPCL|BHARAT PETROLEUM|PETROL|SHELL", "debit"),
    ("Transport",     r"UBER|\bOLA\b|RAPIDO|METRO|BMTC|NAMMA", "debit"),
    ("Dining Out",    r"BARBEQUE|CAFE COFFEE DAY|STARBUCKS|DOMINOS|MCDONALD|KFC|RESTAURANT|PIZZA", "debit"),
    ("Entertainment", r"BOOKMYSHOW|PVR|INOX|CINEMA", "debit"),
    ("Health",        r"PHARMACY|MEDPLUS|\b1MG\b|PRACTO|HOSPITAL|CLINIC|APOLLO", "debit"),
    ("Travel",        r"IRCTC|MAKEMYTRIP|REDBUS|IXIGO|AIRLINES|INDIGO|CLEARTRIP", "debit"),
    ("Education",     r"UDEMY|COURSERA|CROSSWORD|UNACADEMY|BYJU|SCHOOL|TUITION", "debit"),
    ("Shopping",      r"AMAZON|FLIPKART|MYNTRA|AJIO|LIFESTYLE|NYKAA|MEESHO", "debit"),
    ("Transfers",     r"^(NEFT|IMPS)\b|/PAYMENT$", "debit"),
    ("Other Income",  r".*", "credit"),     # any other credit
]
_COMPILED = [(c, re.compile(p), t) for c, p, t in RULES]

# Tokens that carry no merchant identity (used for normalizing and grouping)
_NOISE = {"UPI", "POS", "NEFT", "IMPS", "ACH", "D", "ORDER", "TICKET", "BLR", "MUM", "DEL", "HYD", "CHN", "PUNE"}


def normalize(desc: str, typ: str = "debit") -> str:
    """'UPI/SWIGGY*BLR/84667' -> 'UPI SWIGGY BLR TYPEDEBIT' (ids removed, type kept as a token)."""
    s = re.sub(r"\d+", " ", str(desc).upper())
    s = re.sub(r"[^A-Z ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()      # (kept outside the f-string for Python <3.12)
    return f"{s} TYPE{str(typ).upper()}"


def merchant_key(desc: str) -> str:
    """First meaningful token, e.g. 'POS DMART BLR' -> 'DMART'. Used to hold out whole merchants in evaluation."""
    toks = [t for t in normalize(desc).split() if t not in _NOISE and not t.startswith("TYPE")]
    return toks[0] if toks else "UNKNOWN"


def rule_category(desc: str, typ: str):
    """Return a category if a rule fires, else None."""
    d = str(desc).upper()
    for cat, rx, t in _COMPILED:
        if (t is None or t == typ) and rx.search(d):
            return cat
    return None


def build_pipeline() -> Pipeline:
    feats = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)),
    ])
    clf = LogisticRegression(C=10, max_iter=2000, class_weight="balanced")
    return Pipeline([("features", feats), ("clf", clf)])


def _texts(df):
    return [normalize(d, t) for d, t in zip(df["description"], df["type"])]


def fit(df: pd.DataFrame) -> Pipeline:
    pipe = build_pipeline()
    pipe.fit(_texts(df), df["category"])
    return pipe


def predict(df: pd.DataFrame, pipe=None, mode="hybrid"):
    """Return (categories, confidences, sources). mode: 'rules' | 'ml' | 'hybrid'."""
    n = len(df)
    rules = [rule_category(d, t) for d, t in zip(df["description"], df["type"])]
    cats, conf, src = [UNCATEGORIZED] * n, np.zeros(n), ["none"] * n

    if mode in ("ml", "hybrid") and pipe is not None:
        proba = pipe.predict_proba(_texts(df))
        best = proba.argmax(axis=1)
        for i in range(n):
            cats[i], conf[i], src[i] = pipe.classes_[best[i]], float(proba[i, best[i]]), "ml"
    if mode in ("rules", "hybrid"):
        for i, r in enumerate(rules):
            if r is not None:
                cats[i], conf[i], src[i] = r, 1.0, "rule"
    return cats, conf, src


def save(pipe, path=MODEL_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, path)


def load(path=MODEL_PATH):
    return joblib.load(path) if Path(path).exists() else None
