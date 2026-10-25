"""Backtest forecast methods against the moving-average baseline.   Run:  python -m ml.eval_forecast

Rolling-origin (expanding window) backtest on synthetic statements: seed 42 plus 10 other seeds.
CAVEAT: the generator draws spend around fixed levels with random noise, so there is NO trend or
seasonality to find. That favours long-run averages and says little about real statements.
"""
import json
from pathlib import Path

import numpy as np

from ml import forecast as F
from ml.generate_data import generate

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "metrics"
SEEDS = [42] + list(range(1, 11))


def main():
    METRICS.mkdir(exist_ok=True)
    per_seed = {s: F.backtest(generate(seed=s)) for s in SEEDS}
    names = list(F.METHODS)
    agg = {}
    for n in names:
        tm = [per_seed[s][n]["total_mape"] for s in SEEDS]
        cw = [per_seed[s][n]["category_wape"] for s in SEEDS]
        agg[n] = {"total_mape": (float(np.mean(tm)), float(np.std(tm))), "category_wape": (float(np.mean(cw)), float(np.std(cw)))}
    base = agg[F.BASELINE]
    wins = {n: int(sum(per_seed[s][n]["category_wape"] < per_seed[s][F.BASELINE]["category_wape"] for s in SEEDS)) for n in names}

    results = {"per_seed": {str(s): v for s, v in per_seed.items()}, "aggregate": agg, "shipped": F.METHOD,
               "folds_per_seed": per_seed[42][F.BASELINE]["folds"]}
    (METRICS / "forecast_metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    md = [f"### Forecast backtest ({len(SEEDS)} synthetic statements, {results['folds_per_seed']} rolling folds each, mean ± std)", "",
          "| Method | Total-spend MAPE | Category WAPE | Beats baseline (WAPE) in |", "|---|---|---|---|"]
    for n in names:
        a = agg[n]
        tag = " (baseline)" if n == F.BASELINE else (" (shipped)" if n == F.METHOD else "")
        md.append(f"| {n}{tag} | {a['total_mape'][0]:.1%} ± {a['total_mape'][1]:.1%} | "
                  f"{a['category_wape'][0]:.1%} ± {a['category_wape'][1]:.1%} | "
                  f"{'-' if n == F.BASELINE else str(wins[n]) + '/' + str(len(SEEDS)) + ' seeds'} |")
    sh = agg[F.METHOD]
    md += ["", f"Shipped method `{F.METHOD}` vs baseline `{F.BASELINE}`: total-spend MAPE {sh['total_mape'][0]:.1%} vs {base['total_mape'][0]:.1%}, "
           f"category WAPE {sh['category_wape'][0]:.1%} vs {base['category_wape'][0]:.1%}.", "",
           "### How to read these numbers", "",
           "- Total-spend MAPE is the number to quote (month-level, directly interpretable). Category WAPE is the "
           "weighted category-level error. Per-category MAPE is not reported because zero-spend months make it undefined.",
           "- The synthetic generator has no trend or seasonality, so spend is noise around a fixed level. A long-run average "
           "is close to optimal there, and fancier models (exponential smoothing, damped trend) can only chase the noise. "
           "**This says the pipeline and backtest work, not that the shipped method is best on real statements.**",
           "- Real statements with a trend (salary hike, rising rent) or seasonality (festival months) can favour smoothing or trend "
           "models. With only ~12 months of data none of this can be validated well; the Forecast tab shows the same backtest on the "
           "user's own upload when there are at least 8 months.",
           "- Prophet was not used: heavy install (cmdstan) and it needs far more than 12 monthly points."]
    (METRICS / "forecast_report.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
