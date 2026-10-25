"""Does the correction loop actually teach the model?   Run:  python -m ml.eval_feedback

Simulation on synthetic data, with the ground-truth label standing in for the user:
  1. hold out ~30% of merchants; train the ML model on the rest (the model has never seen those merchants)
  2. measure ML-only accuracy on held-out rows                                  -> "before"
  3. 'user' corrects K random transactions per held-out merchant; retrain with them (ml.feedback)
  4. measure ML-only accuracy on the REMAINING held-out rows (corrected rows excluded) -> "after"
ML-only mode is used because that is the path rule-less merchants take; in the synthetic data the rules are
circular and would hide the effect.  Repeated over several random merchant splits.

CAVEAT: this shows corrections transfer to OTHER TRANSACTIONS OF THE SAME MERCHANT. It does not show the model
generalizes to merchants nobody has corrected (synthetic merchant names carry no shared meaning, so it cannot).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml import categorizer as C, feedback
from ml.recurring import recurring_key
from ml.train_categorizer import load_split

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "metrics"
KS = [1, 3]
TRIALS = 10


def one_trial(full, seed, k):
    rng = np.random.default_rng(seed)
    key = full["description"].map(recurring_key)
    merchants = np.array(sorted(key.unique()))
    held = set(rng.choice(merchants, size=max(1, int(0.3 * len(merchants))), replace=False))
    is_held = key.isin(held)
    train, test = full[~is_held], full[is_held].copy()
    test["key"] = key[is_held]

    def acc(pipe, rows):
        return float(np.mean(np.array(C.predict(rows, pipe, "ml")[0]) == rows["category"].to_numpy()))

    before_pipe = C.fit(train)
    corr_idx = test.groupby("key", group_keys=False).apply(lambda g: g.sample(min(k, len(g)), random_state=int(rng.integers(1e9)))).index
    corrections = test.loc[corr_idx, ["description", "type", "category"]]
    remaining = test.drop(index=corr_idx)
    after_pipe = feedback.train_with_corrections(train, corrections)
    return acc(before_pipe, remaining), acc(after_pipe, remaining), len(held), len(corrections)


def main():
    METRICS.mkdir(exist_ok=True)
    train_part, _ = load_split()
    out = {}
    for k in KS:
        res = [one_trial(train_part, 100 + t, k) for t in range(TRIALS)]
        b, a = [r[0] for r in res], [r[1] for r in res]
        out[k] = {"before": (float(np.mean(b)), float(np.std(b))), "after": (float(np.mean(a)), float(np.std(a))),
                  "held_merchants": res[0][2], "corrections": res[0][3]}
    (METRICS / "feedback_metrics.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    md = [f"### Feedback loop simulation ({TRIALS} random merchant splits, ML-only accuracy on remaining rows of held-out merchants)", "",
          "| Corrections per merchant | Held-out merchants | Total corrections | Accuracy before | Accuracy after |", "|---|---|---|---|---|"]
    md += [f"| {k} | {v['held_merchants']} | ~{v['corrections']} | {v['before'][0]:.1%} ± {v['before'][1]:.1%} | {v['after'][0]:.1%} ± {v['after'][1]:.1%} |"
           for k, v in out.items()]
    md += ["", "### How to read these numbers", "",
           "- 'Before' is the ML model on merchants it has never seen (near chance is expected: synthetic merchant names carry no shared meaning).",
           "- 'After' is on OTHER transactions from the merchants the simulated user corrected. A jump here shows corrections do reach the model; "
           "it is not evidence the model generalizes to merchants nobody has corrected.",
           "- The user is simulated with ground-truth labels, so real users' mistakes or inconsistent corrections are not modelled.",
           "- Rules run before ML in the shipped hybrid, so a correction to a rule-matched merchant is applied to the current statement by "
           "merchant propagation, not by retraining."]
    (METRICS / "feedback_report.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
