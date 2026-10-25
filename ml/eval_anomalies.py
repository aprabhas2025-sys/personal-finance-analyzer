"""Evaluate anomaly + recurring detection against the generator's ground truth.   Run:  python -m ml.eval_anomalies

Anomalies: precision/recall/F1 per signal and per combination, on seed 42 and on 10 other seeds
(so the numbers are not just one lucky draw).  Recurring: does find_recurring recover the 9 fixed
monthly payments the generator injects, and nothing else?

IMPORTANT: ground truth comes from the same generator (oversized spend x5-9 and same-day duplicates).
These numbers show the detector works on those two anomaly types; they are NOT a real-world claim.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml import anomalies as A
from ml.generate_data import FIXED_MONTHLY, generate
from ml.recurring import find_recurring, recurring_key

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "metrics"
PRIMARY_SEED = 42
HELDOUT_SEEDS = list(range(1, 11))
VARIANTS = {
    "duplicates only": ("dup",),
    "z-score only": ("zscore",),
    "Isolation Forest only (z>2 gate)": ("iforest",),
    "new-merchant only": ("new_merch",),
    "dup + z-score (shipped)": ("dup", "zscore"),
    "dup + z-score + IForest": ("dup", "zscore", "iforest"),
    "all four": A.ALL_SIGNALS,
}


def prf(pred, truth):
    pred, truth = np.asarray(pred, bool), np.asarray(truth, bool)
    tp = int((pred & truth).sum())
    p = tp / pred.sum() if pred.sum() else 0.0
    r = tp / truth.sum() if truth.sum() else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"flagged": int(pred.sum()), "tp": tp, "precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3)}


def eval_anomalies(seed):
    df = generate(seed=seed)
    sig = A.compute_signals(df, A.ALL_SIGNALS)
    truth = df["is_anomaly"].to_numpy() == 1
    return {name: prf(A.combine(sig, use).to_numpy(), truth) for name, use in VARIANTS.items()}


def expected_recurring():
    return {recurring_key(tpl.format(n=1000, l=10)) for _, tpl, _, _ in FIXED_MONTHLY}


def eval_recurring(seed):
    df = generate(seed=seed)
    found = set(find_recurring(df)["merchant"])
    exp = expected_recurring()
    tp = len(found & exp)
    return {"found": len(found), "expected": len(exp), "tp": tp,
            "precision": round(tp / len(found), 3) if found else 0.0, "recall": round(tp / len(exp), 3),
            "false_positives": sorted(found - exp), "missed": sorted(exp - found)}


def main():
    METRICS.mkdir(exist_ok=True)
    primary = eval_anomalies(PRIMARY_SEED)
    held = [eval_anomalies(s) for s in HELDOUT_SEEDS]
    agg = {}
    for name in VARIANTS:
        row = {}
        for m in ("precision", "recall", "f1"):
            v = [h[name][m] for h in held]
            row[m] = (round(float(np.mean(v)), 3), round(float(np.std(v)), 3))
        row["flagged_mean"] = round(float(np.mean([h[name]["flagged"] for h in held])), 1)
        agg[name] = row
    rec_primary = eval_recurring(PRIMARY_SEED)
    rec_held = [eval_recurring(s) for s in HELDOUT_SEEDS]

    results = {"anomalies_seed42": primary, "anomalies_heldout_mean_std": agg,
               "recurring_seed42": rec_primary, "recurring_heldout": rec_held}
    (METRICS / "anomaly_metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    n_inj = int(generate(seed=PRIMARY_SEED)["is_anomaly"].sum())
    md = [f"### Anomaly detection (seed {PRIMARY_SEED}, {n_inj} injected anomalies)", "",
          "| Method | Flagged | True positives | Precision | Recall | F1 |", "|---|---|---|---|---|---|"]
    md += [f"| {n} | {r['flagged']} | {r['tp']} | {r['precision']} | {r['recall']} | {r['f1']} |" for n, r in primary.items()]
    md += ["", f"### Same methods on {len(HELDOUT_SEEDS)} other seeds (mean ± std)", "",
           "| Method | Avg flagged | Precision | Recall | F1 |", "|---|---|---|---|---|"]
    md += [f"| {n} | {r['flagged_mean']} | {r['precision'][0]} ± {r['precision'][1]} | "
           f"{r['recall'][0]} ± {r['recall'][1]} | {r['f1'][0]} ± {r['f1'][1]} |" for n, r in agg.items()]
    rp = np.mean([r["precision"] for r in rec_held]), np.mean([r["recall"] for r in rec_held])
    md += ["", "### Recurring payments (9 fixed monthly payments injected per statement)", "",
           f"- seed {PRIMARY_SEED}: precision {rec_primary['precision']}, recall {rec_primary['recall']} "
           f"(false positives: {rec_primary['false_positives'] or 'none'}; missed: {rec_primary['missed'] or 'none'})",
           f"- {len(HELDOUT_SEEDS)} other seeds: mean precision {rp[0]:.3f}, mean recall {rp[1]:.3f}", "",
           "### How to read these numbers", "",
           "- Ground truth is synthetic and has only two anomaly types (oversized spend x5-9, same-day duplicate). "
           "The detector is allowed to look for exactly those, so this is a **pipeline and tuning check, not a real-world accuracy claim**.",
           "- Seed 42 is the seed the detector was debugged on, so its 1.0 / 1.0 is optimistic. **Quote the multi-seed table.**",
           "- Isolation Forest is a real trade-off, not noise: across seeds it lifts recall (to ~0.97) but cuts precision "
           "(to ~0.61) because it fires on ordinary large-ish amounts too. The shipped default (dup + z-score) has the best F1; "
           "add the iforest signal to `ACTIVE_SIGNALS` in `ml/anomalies.py` if you would rather over-flag than miss one.",
           "- The new-merchant rule has ~0 precision and recall here. The synthetic data has no novel-merchant anomalies, "
           "so this cannot show whether it helps on real statements. It stays OFF and unproven.",
           "- A small injected anomaly can hide inside a category's normal range (e.g. a Rs.60 transport fare x5 = Rs.300), "
           "so recall below 1.0 on other seeds is expected and honest.",
           "- For a resume-grade number: flag anomalies by hand on a real statement and score against that."]
    (METRICS / "anomaly_report.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
