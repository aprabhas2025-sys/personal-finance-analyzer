"""Train + evaluate the categorizer.   Run:  python -m ml.train_categorizer

Reports (written to metrics/):
  1. Held-out eval set (data/eval_labeled.csv, never trained on): rules vs ML vs hybrid
  2. Unseen-merchant test: GroupKFold by merchant, so every test merchant is new to the model
Ships the hybrid model trained on everything except the eval set.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import GroupKFold

from ml import categorizer as C

ROOT = Path(__file__).resolve().parent.parent
DATA, METRICS = ROOT / "data", ROOT / "metrics"
KEY = ["date", "description", "amount", "type"]


def load_split():
    full = pd.read_csv(DATA / "synthetic_labeled.csv", parse_dates=["date"])
    ev = pd.read_csv(DATA / "eval_labeled.csv", parse_dates=["date"])
    k = lambda d: d[KEY].astype(str).agg("|".join, axis=1)
    held = k(full).isin(set(k(ev)))
    return full[~held].reset_index(drop=True), full[held].reset_index(drop=True)


def score(y_true, y_pred):
    return {"accuracy": round(accuracy_score(y_true, y_pred), 4),
            "macro_f1": round(f1_score(y_true, y_pred, average="macro", zero_division=0), 4),
            "weighted_f1": round(f1_score(y_true, y_pred, average="weighted", zero_division=0), 4)}


def unseen_merchant_cv(df, n_splits=5):
    """Train on some merchants, test on completely different ones."""
    groups = df["description"].map(C.merchant_key)
    true, preds = [], {"rules": [], "ml": [], "hybrid": []}
    for tr, te in GroupKFold(n_splits=n_splits).split(df, groups=groups):
        pipe = C.fit(df.iloc[tr])
        test = df.iloc[te]
        true += list(test["category"])
        for mode in preds:
            preds[mode] += C.predict(test, pipe, mode)[0]
    return {m: score(true, p) for m, p in preds.items()}


def main():
    METRICS.mkdir(exist_ok=True)
    train, ev = load_split()
    print(f"train rows: {len(train)} | eval rows: {len(ev)}")
    pipe = C.fit(train)

    results = {"eval_set": {}, "unseen_merchants": {}}
    hybrid_pred = None
    for mode in ("rules", "ml", "hybrid"):
        pred = C.predict(ev, pipe, mode)[0]
        results["eval_set"][mode] = score(ev["category"], pred)
        if mode == "hybrid":
            hybrid_pred = pred
    results["unseen_merchants"] = unseen_merchant_cv(train)

    # per-class report for the shipped (hybrid) model
    report = classification_report(ev["category"], hybrid_pred, zero_division=0, output_dict=True)
    results["per_class_hybrid"] = {k: {m: round(v, 3) for m, v in d.items()} for k, d in report.items()
                                   if isinstance(d, dict)}
    mism = ev.assign(pred=hybrid_pred).query("category != pred")[["description", "category", "pred"]]
    results["misclassified_hybrid"] = mism.head(20).to_dict("records")

    C.save(pipe)
    (METRICS / "categorizer_metrics.json").write_text(json.dumps(results, indent=2, default=str))

    def table(title, d):
        lines = [f"### {title}", "", "| Method | Accuracy | Macro-F1 | Weighted-F1 |", "|---|---|---|---|"]
        lines += [f"| {m} | {s['accuracy']} | {s['macro_f1']} | {s['weighted_f1']} |" for m, s in d.items()]
        return "\n".join(lines)

    md = [table(f"Held-out eval set (n={len(ev)})", results["eval_set"]), "",
          table("Unseen-merchant cross-validation (5-fold GroupKFold)", results["unseen_merchants"])]
    md += ["", "### How to read these numbers", "",
           "- The eval set is synthetic and built from the same merchant templates the rules were written against, "
           "so ~1.0 only proves the pipeline works end to end. **It is not a real-world accuracy claim.**",
           "- Unseen-merchant ML-only accuracy is near chance because synthetic merchant names carry no shared meaning. "
           "Real data and the user-correction loop (Day 4) are what improve this.",
           "- ML confidence is informative: below 0.5 it is almost always wrong, so low-confidence rows are flagged for review.",
           "- For a resume-grade number, hand-label real transactions and run `python -m ml.real_eval score <file>`."]
    (METRICS / "categorizer_report.md").write_text("\n".join(md))
    print("\n".join(md))
    print(f"\nMisclassified on eval (hybrid): {len(mism)}")
    if len(mism):
        print(mism.head(10).to_string(index=False))
    print(f"\nSaved model -> {C.MODEL_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
