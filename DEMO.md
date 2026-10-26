# Demo video script (~2 minutes)

Record at 1080p, browser zoom 110%, sample data loaded fresh. Say "synthetic" out loud the first time you show a number.

| Time | On screen | Say |
|---|---|---|
| 0:00 | Landing page, then *Get started*: create an account | "A landing page and real sign-up. Passwords are stored hashed." |
| 0:10 | After sign-up you land in the app; caption visible | "Personal finance analyzer: upload a bank or UPI statement CSV and get categories, unusual charges, subscriptions and a forecast. Runs locally; this hosted demo keeps each visitor's data separate." |
| 0:15 | Click *Use sample data*; metrics row appears | "This is a synthetic statement with known labels, so I can measure accuracy honestly." |
| 0:25 | **Dashboard** tab: savings rate, income vs spend, categories | "Savings rate and where the money goes, month by month." |
| 0:45 | **Transactions** tab; tick *Needs review only* | "Rules handle known merchants; an ML model handles the rest and flags low-confidence rows for review." |
| 1:00 | **Anomalies** tab | "Flags duplicate charges and amounts far outside what is normal for the category. On synthetic data about 0.8 precision and recall; a prompt to check, not proof." |
| 1:15 | **Subscriptions** tab | "Finds regular payments and their monthly commitment: 0.98 precision, 0.99 recall on synthetic data." |
| 1:30 | **Forecast** tab, scroll to the backtest table | "Next month's spend, with a rolling backtest on the user's own data. On synthetic data it is only slightly better than a moving average, and I say so." |
| 1:40 | **Budgets** tab: click *Suggest from my average*, Save | "Set budgets in one click; it warns when a category is over, or forecast to exceed next month." |
| 1:45 | **Transactions > Review & correct**: fix one row, apply | "Fix one merchant and it spreads to that merchant's other rows. Run locally, the model also retrains from the correction." |
| 2:00 | README metrics table | "Real-data accuracy: <fill in after ml.real_eval>. Everything else is synthetic and labelled that way." |

Do not show a real statement on screen unless you have redacted it.
