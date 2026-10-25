"""Score the categorizer on YOUR OWN real statement. This is the number that belongs on a resume.

Step 1 - export transactions to label by hand (blank category column, no predictions shown, so you label blind):
    python -m ml.real_eval export my_statement.csv to_label.csv
Step 2 - open to_label.csv, fill the `category` column using the names in ml/schema.py CATEGORIES
         (aim for 300+ rows), then:
    python -m ml.real_eval score to_label.csv
"""
import sys

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score

from app.cleaning import clean_transactions
from ml import categorizer as C
from ml.schema import CATEGORIES


def export(src, dst, n=400):
    df, _ = clean_transactions(pd.read_csv(src, dtype=str))
    out = df.sample(min(n, len(df)), random_state=1).sort_values("date")[["date", "description", "amount", "type"]]
    out["category"] = ""
    out.to_csv(dst, index=False)
    print(f"Wrote {len(out)} rows to {dst}. Fill the category column using: {CATEGORIES}")


def score(path):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[df["category"].notna() & (df["category"].astype(str).str.strip() != "")]
    bad = sorted(set(df["category"]) - set(CATEGORIES))
    if bad:
        sys.exit(f"Unknown categories in file: {bad}\nAllowed: {CATEGORIES}")
    pipe = C.load()
    print(f"Scoring {len(df)} hand-labeled transactions (model file loaded: {pipe is not None})\n")
    for mode in ("rules", "ml", "hybrid"):
        pred = C.predict(df, pipe, mode)[0]
        print(f"{mode:7s} accuracy={accuracy_score(df.category, pred):.3f}  "
              f"macro-F1={f1_score(df.category, pred, average='macro', zero_division=0):.3f}")
    print("\nPer-class (hybrid):")
    print(classification_report(df.category, C.predict(df, pipe, 'hybrid')[0], zero_division=0))


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "export":
        export(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 3 and sys.argv[1] == "score":
        score(sys.argv[2])
    else:
        print(__doc__)
