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

# Real-data accuracy (the resume number):
python -m ml.real_eval export my_statement.csv to_label.csv   # label by hand, blind
python -m ml.real_eval score to_label.csv
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
- [x] Day 2: A: rules + TF-IDF/LR hybrid categorizer, evaluation | B: SQLite storage, filterable table, category chart
- [ ] Day 3: A: anomalies + recurring | B: dashboard charts
- [ ] Day 4: A: forecast + MAPE | B: anomaly/subscription pages, feedback button
- [ ] Day 5: metrics write-up, README screenshots, demo video

## Metrics (fill with real numbers)
| Metric | Value |
|---|---|
| Categorization macro-F1, synthetic eval | 1.00 (circular: pipeline check only, see metrics/categorizer_report.md) |
| Categorization macro-F1, REAL hand-labeled statement | TBD (run ml.real_eval) |
| Anomaly precision / recall | TBD |
| Forecast MAPE vs moving-average baseline | TBD |
