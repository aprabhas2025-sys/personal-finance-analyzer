# Personal Finance Analyzer

Upload a bank/UPI statement CSV, get auto-categorized spending, anomaly and subscription
detection, and a next-month forecast. Runs fully locally by default; an optional hosted demo is
described under [Deploy](#deploy-render-free-tier).

<!-- screenshots: add docs/dashboard.png, docs/forecast.png, docs/review.png and uncomment
![Dashboard](docs/dashboard.png)
-->

**Try it with no setup:** click *Use sample data*. The sample is synthetic, so every number below
describes synthetic data unless a row says REAL.

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
  theme.py / style.css  premium look: dark hero with light streaks, frosted-glass cards and tabs, serif-italic accents (CSS only, no images)
  config.py         local vs hosted mode (RENDER / FINANCE_HOSTED) and the matching privacy captions
  auth.py           accounts: email + password (scrypt hashes), lockout, delete account
  landing.py        landing page, sign-in and sign-up pages, and the login gate used by app.py
  db.py             SQLite storage; one file per account (data/accounts/<id>.db)
  budgets.py        monthly category budgets: spent vs limit, forecast-based warnings, suggested limits (pure pandas, tested)
  budgets_ui.py     the Budgets tab (limits are saved per session in the same SQLite file)
  chat_tools.py     read-only aggregate queries over the statement (spend, savings, merchants, subscriptions, anomalies, forecast)
  chatbot.py        'Ask' assistant: Gemini function calling over chat_tools, or keyword rules when AI is off / no key
  chat_ui.py        the Ask tab (AI is opt-in per session, 30 AI messages per session)
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
- [x] Day 5 (code): per-session storage, honest hosted/local privacy caption, no shared-model retraining when hosted, Render config
- [ ] Day 5 (yours): hand-label ~300 real rows and run `ml.real_eval`, screenshots in `docs/`, demo video (script in DEMO.md)

## Accounts, privacy and hosting
- **Flow:** landing page, then *Get started* (sign up) or *Sign in*, then the app. *Sign out* returns to the landing page. Refreshing the browser signs you out (no "remember me" yet).
- **Passwords** are never stored: only a salted scrypt hash (`app/auth.py`, standard library). Wrong email and wrong password show the same message, and 5 wrong passwords lock the account for 5 minutes.
- **Each account has its own data file** (`data/accounts/<id>.db`); users cannot see each other's data. *Clear stored data* empties it, and *Account > Delete my account* removes the account and its file.
- **Local (default):** nothing leaves your machine. Accounts and data are files under `data/` (`users.db`, `accounts/`, both gitignored).
- **Hosted (`RENDER` or `FINANCE_HOSTED=1`):** uploads and accounts live on the server's disk. On Render's free plan that disk is wiped on every restart or redeploy, so accounts disappear; point `FINANCE_DB_DIR` at a persistent disk if you need them to last. Prefer the sample data on a hosted demo.
- **Model retraining is local-only.** A retrained model is one global file shared by everyone using that server, so the hosted demo applies corrections to the user's own account (and same-merchant rows) but never retrains.
- Not built yet: email verification, password reset, "remember me". Open sign-up has no rate limit beyond the per-account lockout, so do not expose it publicly with real users without adding them.

## Budgets tab
Set a monthly limit per category (or click *Suggest from my average*: average monthly spend over complete months, +10%, rounded up to ₹100). Each category is then
marked **over** (latest month's spend above the limit), **will exceed** (next-month forecast above the limit), **near limit** (80%+ used) or **ok**.
Limits live only in the session's own DB file and are removed by *Clear stored data*. The forecast is the average of past months, so treat "will exceed" as a hint.
The Ask tab can answer "Am I over budget?".

## Ask tab (chat assistant)
Ask things like *"How much did I spend on Groceries last month?"*, *"What are my subscriptions?"* or *"How is my data stored?"*.
- **Free, no AI by default.** Without `GEMINI_API_KEY`, or with the checkbox off, answers come from keyword rules over the same functions.
- **AI mode (free tier):** Gemini (default `gemini-3.5-flash-lite`, override with `GEMINI_MODEL`; get a free key at Google AI Studio) answers by calling
  read-only tools that return **aggregates only**; raw transaction rows are never sent. Merchant names in tool results are sent to Google, and the tab says so.
  **Free-tier Gemini content may be used by Google to improve its products**, so use AI mode with sample data, not a real statement. Tool results are treated as data, not instructions.
- Numbers always come from the tools, not from the model's memory. If the API fails, it falls back to rules.
- Hosted: add `GEMINI_API_KEY` as a Render environment variable (secret). Each session is capped at 30 AI messages.
- Not evaluated yet: there is no accuracy number for the chat answers, so don't quote one.

## Metrics
Every row is synthetic unless it says REAL. Reports: `metrics/`.
| Metric | Value |
|---|---|
| Categorization macro-F1, synthetic eval | 1.00 (circular: pipeline check only, see metrics/categorizer_report.md) |
| Categorization macro-F1, REAL hand-labeled statement | TBD (run ml.real_eval) |
| Anomaly precision / recall (synthetic, mean of 10 unseen seeds; shipped = duplicates + z-score) | 0.79 / 0.81 (F1 0.80). Seed 42 reads 1.0 / 1.0 but is the seed it was debugged on. Synthetic truth, so not a real-world claim; see metrics/anomaly_report.md |
| Recurring-payment detection (9 injected monthly payments, 10 seeds) | precision 0.98 / recall 0.99, synthetic |
| Forecast total-spend MAPE vs 3-month moving-average baseline (synthetic, mean of 11 statements, rolling backtest) | 6.5% vs 7.2%: slightly better, but the gap is within seed-to-seed spread (about 3 points). Synthetic data has no trend, so this says the backtest works, not that the method wins on real statements. See metrics/forecast_report.md |
| Feedback loop: ML accuracy on other transactions of a corrected merchant (simulated user, synthetic) | about 15% before, about 99.7% after 1 correction per merchant. Shows corrections reach the model, not that it generalizes to uncorrected merchants. See metrics/feedback_report.md |

## Deploy (Render, free tier)
1. Make sure these are committed: `data/synthetic_bank_export.csv`, `data/synthetic_labeled.csv`, `data/eval_labeled.csv`, the trained `ml/models/categorizer.joblib`
   (only `categorizer_user.joblib` is gitignored), `render.yaml`, `.streamlit/config.toml`.
2. Push to GitHub. On render.com: **New + > Blueprint**, pick the repo. `render.yaml` sets the build/start commands and `FINANCE_HOSTED=1`.
   (Manual alternative: Web Service, build `pip install -r requirements.txt`, start
   `streamlit run app/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`, env var `FINANCE_HOSTED=1`.)
3. Open the URL, click *Use sample data*, check every tab, and confirm the caption says "hosted demo".
4. The free plan sleeps when idle (first load ~30-60 s) and has an ephemeral disk, which is fine because sessions are temporary by design.

Run the hosted configuration locally to check it: `FINANCE_HOSTED=1 streamlit run app/app.py`.

## Look and feel
Dark hero banner with soft light streaks, frosted-glass metric cards, a floating pill tab bar and serif-italic accents, all CSS (`app/style.css`), no images.
Fonts (Inter, Instrument Serif) load from Google Fonts and fall back to system fonts offline. Charts stay on white cards on purpose (readable, and tested).
Colours are CSS variables at the top of `style.css`; the Streamlit base theme is in `.streamlit/config.toml`. Respects `prefers-reduced-motion` and works at phone width.
