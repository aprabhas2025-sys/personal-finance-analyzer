# Personal Finance Analyzer

Upload a bank/UPI statement CSV, get auto-categorized spending, anomaly and subscription
detection, and a next-month forecast. Runs fully locally.

## Quick start
```bash
pip install -r requirements.txt
python -m ml.generate_data      # creates data/*.csv (already included)
streamlit run app/app.py        # then click "Use sample data"
python -m ml.train_categorizer  # train + evaluate categorizer (writes metrics/)
python -m pytest -q             # run tests
python -m ml.eval_anomalies     # anomaly + recurring evaluation (writes metrics/anomaly_report.md)
python -m ml.eval_forecast      # forecast backtest vs moving-average baseline (metrics/forecast_report.md)
python -m ml.eval_feedback      # does the correction loop teach the model? (metrics/feedback_report.md)

# Real-data accuracy (the resume number):
python -m ml.real_eval export my_statement.csv to_label.csv   # label by hand, blind
python -m ml.real_eval score to_label.csv
```

## Project layout
```
ml/        Person A: data + models
  schema.py         shared schema + category list (the contract; don't change silently)
  generate_data.py  synthetic statement generator with ground-truth labels
  api.py            categorize / find_anomalies / find_recurring / forecast
  anomalies.py      duplicates + per-category robust z-score (+ optional Isolation Forest, new-merchant)
  recurring.py      periodic payment detection (subscriptions, EMIs, rent, bills)
  eval_anomalies.py multi-seed precision/recall + ablation
  forecast.py       monthly per-category forecast + rolling-origin backtest (4 methods)
  eval_forecast.py  backtest on 11 synthetic statements vs the moving-average baseline
  feedback.py       retrain from user corrections (saved to ml/models/categorizer_user.joblib, gitignored)
  eval_feedback.py  simulated-user evaluation of the correction loop
app/       Person B: Streamlit app
  cleaning.py       any bank CSV -> shared schema
  app.py            upload, metrics, table, charts, Dashboard tab
  charts.py         pure plotly figure functions (light theme only)
  dashboard.py      Dashboard tab: KPIs, charts, unusual transactions, recurring payments
  insights.py       Anomalies / Subscriptions / Forecast tabs + 'Review & correct categories' panel
  review.py         apply corrections: save, spread to same merchant, retrain, re-predict (no Streamlit, tested)
data/      synthetic_labeled.csv (truth), synthetic_bank_export.csv (raw upload), eval_labeled.csv (300 rows, never train on it)
tests/
```

## Shared schema
`date, description, amount, type, category` where amount is always positive and type is `debit` or `credit`.

## Status
- [x] Day 1: schema, synthetic data, CSV upload + cleaning, app skeleton, tests
- [x] Day 2: A: rules + TF-IDF/LR hybrid categorizer, evaluation | B: SQLite storage, filterable table, category chart
- [x] Day 3: A: anomalies + recurring | B: dashboard charts
- [x] Day 4: A: forecast + MAPE | B: anomaly/subscription pages, forecast chart, correction (feedback) panel
- [ ] Day 5: metrics write-up, README screenshots, demo video

## Metrics (fill with real numbers)
| Metric | Value |
|---|---|
| Categorization macro-F1, synthetic eval | 1.00 (circular: pipeline check only, see metrics/categorizer_report.md) |
| Categorization macro-F1, REAL hand-labeled statement | TBD (run ml.real_eval) |
| Anomaly precision / recall (synthetic, mean of 10 unseen seeds; shipped = duplicates + z-score) | 0.79 / 0.81 (F1 0.80). Seed 42 reads 1.0 / 1.0 but is the seed it was debugged on. Synthetic truth, so not a real-world claim; see metrics/anomaly_report.md |
| Recurring-payment detection (9 injected monthly payments, 10 seeds) | precision 0.98 / recall 0.99, synthetic |
| Forecast total-spend MAPE vs 3-month moving-average baseline (synthetic, mean of 11 statements, rolling backtest) | 6.5% vs 7.2%: slightly better, but the gap is within seed-to-seed spread (about 3 points). Synthetic data has no trend, so this says the backtest works, not that the method wins on real statements. See metrics/forecast_report.md |
| Feedback loop: ML accuracy on other transactions of a corrected merchant (simulated user, synthetic) | about 15% before, about 99.7% after 1 correction per merchant. Shows corrections reach the model, not that it generalizes to uncorrected merchants. See metrics/feedback_report.md |
