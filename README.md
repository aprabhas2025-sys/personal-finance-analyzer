# Personal Finance Analyzer

Upload a bank/UPI statement CSV, get auto-categorized spending, anomaly and subscription
detection, and a next-month forecast. Runs fully locally.

## Quick start
```bash
pip install -r requirements.txt
python -m ml.generate_data      # creates data/*.csv (already included)
streamlit run app/app.py        # then click "Use sample data"
python -m pytest -q             # run tests
```

## Project layout
```
ml/        Person A: data + models
  schema.py         shared schema + category list (the contract; don't change silently)
  generate_data.py  synthetic statement generator with ground-truth labels
  api.py            categorize / find_anomalies / find_recurring / forecast  (dummy bodies until Days 2-4)
app/       Person B: Streamlit app
  cleaning.py       any bank CSV -> shared schema
  app.py            upload, metrics, table, monthly chart
data/      synthetic_labeled.csv (truth), synthetic_bank_export.csv (raw upload), eval_labeled.csv (300 rows, never train on it)
tests/
```

## Shared schema
`date, description, amount, type, category` where amount is always positive and type is `debit` or `credit`.

## Status
- [x] Day 1: schema, synthetic data, CSV upload + cleaning, app skeleton, tests
- [ ] Day 2: A: rule + ML categorizer (report F1 on data/eval_labeled.csv) | B: SQLite + table view
- [ ] Day 3: A: anomalies + recurring | B: dashboard charts
- [ ] Day 4: A: forecast + MAPE | B: anomaly/subscription pages, feedback button
- [ ] Day 5: metrics write-up, README screenshots, demo video

## Metrics (fill with real numbers)
| Metric | Value |
|---|---|
| Categorization macro-F1 (eval set) | TBD |
| Anomaly precision / recall | TBD |
| Forecast MAPE vs moving-average baseline | TBD |
