"""Read-only questions the chatbot can ask about the user's stored transactions. No Streamlit, no network, no LLM.

Every tool returns a small JSON-able dict of AGGREGATES (capped row counts), never the whole table, and never raises:
bad input comes back as {"error": ...} so the model can correct itself. `api` is injectable so tests need no trained models.
"""
import re

import pandas as pd

MAX_ROWS = 15
_CHANNELS = {"UPI", "POS", "NEFT", "IMPS", "RTGS", "ACH", "ATM", "ECS", "NACH", "DR", "CR", "TO", "BY"}


def _merchant(desc: str) -> str:
    try:
        from ml.recurring import recurring_key
        return recurring_key(desc)
    except Exception:                                  # ml package unavailable: skip channel prefixes and numbers
        words = [w for w in re.split(r"[^A-Z]+", str(desc).upper()) if len(w) > 1 and w not in _CHANNELS]
        return words[0] if words else str(desc).upper()[:20]


TOOL_SCHEMAS = [
    {"name": "spending_summary", "description": "Total spend (debits) in a period, optionally for one category, grouped by category, month or not at all.",
     "input_schema": {"type": "object", "properties": {
         "start": {"type": "string", "description": "YYYY-MM-DD, inclusive"}, "end": {"type": "string", "description": "YYYY-MM-DD, inclusive"},
         "category": {"type": "string"}, "group_by": {"type": "string", "enum": ["category", "month", "none"]}}}},
    {"name": "income_and_savings", "description": "Income (credits), spend (debits), net and savings rate per month and overall.",
     "input_schema": {"type": "object", "properties": {"start": {"type": "string"}, "end": {"type": "string"}}}},
    {"name": "top_merchants", "description": "Merchants with the highest total spend.",
     "input_schema": {"type": "object", "properties": {"n": {"type": "integer"}, "start": {"type": "string"}, "end": {"type": "string"},
                                                       "category": {"type": "string"}}}},
    {"name": "list_transactions", "description": "Largest individual transactions matching filters (max 15).",
     "input_schema": {"type": "object", "properties": {"start": {"type": "string"}, "end": {"type": "string"}, "category": {"type": "string"},
                                                       "search": {"type": "string", "description": "substring of the description"},
                                                       "min_amount": {"type": "number"}, "limit": {"type": "integer"}}}},
    {"name": "subscriptions", "description": "Detected recurring payments (subscriptions, EMIs, rent, bills) with monthly cost and next due date.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "anomalies", "description": "Transactions flagged as unusual: duplicate charges or amounts far above normal for their category.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "forecast", "description": "Forecast of next month's spend by category.",
     "input_schema": {"type": "object", "properties": {}}},
]


class ChatTools:
    def __init__(self, df: pd.DataFrame, api=None):
        self.df = df.copy()
        self.df["date"] = pd.to_datetime(self.df["date"])
        self._api = api
        self.categories = sorted(self.df["category"].dropna().unique())

    @property
    def api(self):
        if self._api is None:
            from ml import api
            self._api = api
        return self._api

    # ---------- plumbing ----------
    def run(self, name: str, args: dict | None = None) -> dict:
        fn = getattr(self, f"_t_{name}", None) if name in {t["name"] for t in TOOL_SCHEMAS} else None
        if fn is None:
            return {"error": f"unknown tool {name!r}"}
        try:
            return fn(**(args or {}))
        except (TypeError, ValueError) as e:
            return {"error": str(e)}
        except Exception as e:                                   # a broken model must not crash the chat
            return {"error": f"{name} failed: {type(e).__name__}"}

    def _slice(self, start=None, end=None, category=None, typ=None) -> pd.DataFrame:
        d = self.df
        if start:
            d = d[d["date"] >= pd.Timestamp(start)]
        if end:
            d = d[d["date"] <= pd.Timestamp(end)]
        if category:
            match = {c.lower(): c for c in self.categories}.get(str(category).lower())
            if match is None:
                raise ValueError(f"unknown category {category!r}; categories are {self.categories}")
            d = d[d["category"] == match]
        if typ:
            d = d[d["type"] == typ]
        return d

    def _period(self, d):
        return {"from": str(d["date"].min().date()), "to": str(d["date"].max().date())} if len(d) else None

    # ---------- tools ----------
    def _t_spending_summary(self, start=None, end=None, category=None, group_by="category"):
        d = self._slice(start, end, category, "debit")
        out = {"total_spend": round(float(d["amount"].sum()), 2), "transactions": int(len(d)), "period": self._period(d)}
        if group_by == "category":
            g = d.groupby("category")["amount"].agg(["sum", "count"]).sort_values("sum", ascending=False).head(MAX_ROWS)
        elif group_by == "month":
            g = d.groupby(d["date"].dt.to_period("M").astype(str))["amount"].agg(["sum", "count"])
        else:
            return out
        out["rows"] = [{"key": str(k), "amount": round(float(r["sum"]), 2), "count": int(r["count"])} for k, r in g.iterrows()]
        return out

    def _t_income_and_savings(self, start=None, end=None):
        d = self._slice(start, end)
        m = d.assign(month=d["date"].dt.to_period("M").astype(str)).pivot_table(index="month", columns="type", values="amount", aggfunc="sum", fill_value=0.0)
        inc, sp = float(d.loc[d.type == "credit", "amount"].sum()), float(d.loc[d.type == "debit", "amount"].sum())
        rows = [{"month": k, "income": round(float(r.get("credit", 0)), 2), "spend": round(float(r.get("debit", 0)), 2)} for k, r in m.iterrows()]
        return {"income": round(inc, 2), "spend": round(sp, 2), "net": round(inc - sp, 2),
                "savings_rate": round((inc - sp) / inc, 4) if inc > 0 else None, "months": rows[-12:]}

    def _t_top_merchants(self, n=10, start=None, end=None, category=None):
        d = self._slice(start, end, category, "debit")
        g = d.assign(m=d["description"].map(_merchant)).groupby("m")["amount"].agg(["sum", "count"]).sort_values("sum", ascending=False)
        n = max(1, min(int(n), MAX_ROWS))
        return {"merchants": [{"merchant": k, "amount": round(float(r["sum"]), 2), "count": int(r["count"])} for k, r in g.head(n).iterrows()]}

    def _t_list_transactions(self, start=None, end=None, category=None, search=None, min_amount=None, limit=10):
        d = self._slice(start, end, category)
        if search:
            d = d[d["description"].str.contains(str(search), case=False, regex=False)]
        if min_amount is not None:
            d = d[d["amount"] >= float(min_amount)]
        d = d.sort_values("amount", ascending=False).head(max(1, min(int(limit), MAX_ROWS)))
        return {"matches": int(len(d)), "transactions": [
            {"date": str(r.date.date()), "description": str(r.description)[:60], "amount": round(float(r.amount), 2), "type": r.type, "category": r.category}
            for r in d.itertuples()]}

    def _t_subscriptions(self):
        rec = self.api.find_recurring(self.df.drop(columns=["id"], errors="ignore"))
        if rec is None or rec.empty:
            return {"subscriptions": [], "note": "no recurring payments found (needs 3+ regular payments to one merchant)"}
        rec = rec.assign(monthly_cost=(rec["avg_amount"] * 30.44 / rec["frequency_days"]).round(2)).sort_values("monthly_cost", ascending=False)
        return {"monthly_commitment": round(float(rec["monthly_cost"].sum()), 2), "subscriptions": [
            {"merchant": str(r.merchant), "avg_amount": round(float(r.avg_amount), 2), "monthly_cost": float(r.monthly_cost),
             "every_days": int(r.frequency_days), "next_due": str(pd.Timestamp(r.next_due).date())} for r in rec.head(MAX_ROWS).itertuples()]}

    def _t_anomalies(self):
        an = self.api.find_anomalies(self.df.drop(columns=["id"], errors="ignore"))
        fl = an[an["is_anomaly"] == 1].sort_values("amount", ascending=False)
        return {"flagged": int(len(fl)), "total_amount": round(float(fl["amount"].sum()), 2),
                "note": "a prompt to check, not proof of a problem; only duplicates and unusually large amounts are detected",
                "transactions": [{"date": str(pd.Timestamp(r.date).date()), "description": str(r.description)[:60], "amount": round(float(r.amount), 2),
                                  "reason": str(r.anomaly_reason)} for r in fl.head(MAX_ROWS).itertuples()]}

    def _t_forecast(self):
        fc = self.api.forecast(self.df.drop(columns=["id"], errors="ignore"))
        if fc.empty:
            return {"error": "not enough spending history to forecast"}
        return {"forecast_total_next_month": round(float(fc["forecast_amount"].sum()), 2),
                "method": "average of all months (rolling backtest on synthetic data: 6.5% total-spend error vs 7.2% for a 3-month average)",
                "by_category": [{"category": r.category, "amount": round(float(r.forecast_amount), 2)} for r in fc.head(MAX_ROWS).itertuples()]}
