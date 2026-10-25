### Forecast backtest (11 synthetic statements, 6 rolling folds each, mean ± std)

| Method | Total-spend MAPE | Category WAPE | Beats baseline (WAPE) in |
|---|---|---|---|
| moving_avg_3 (baseline) | 7.2% ± 3.4% | 23.1% ± 2.6% | - |
| mean_all (shipped) | 6.5% ± 2.6% | 21.4% ± 1.8% | 9/11 seeds |
| ses | 7.7% ± 3.0% | 23.7% ± 2.7% | 5/11 seeds |
| ets_damped | 8.6% ± 3.3% | 26.3% ± 2.9% | 1/11 seeds |

Shipped method `mean_all` vs baseline `moving_avg_3`: total-spend MAPE 6.5% vs 7.2%, category WAPE 21.4% vs 23.1%.

### How to read these numbers

- Total-spend MAPE is the number to quote (month-level, directly interpretable). Category WAPE is the weighted category-level error. Per-category MAPE is not reported because zero-spend months make it undefined.
- The synthetic generator has no trend or seasonality, so spend is noise around a fixed level. A long-run average is close to optimal there, and fancier models (exponential smoothing, damped trend) can only chase the noise. **This says the pipeline and backtest work, not that the shipped method is best on real statements.**
- Real statements with a trend (salary hike, rising rent) or seasonality (festival months) can favour smoothing or trend models. With only ~12 months of data none of this can be validated well; the Forecast tab shows the same backtest on the user's own upload when there are at least 8 months.
- Prophet was not used: heavy install (cmdstan) and it needs far more than 12 monthly points.