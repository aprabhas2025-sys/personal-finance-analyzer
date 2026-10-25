"""Synthetic bank-statement generator (pure pandas/numpy, no extra deps).

Run:  python -m ml.generate_data
Outputs (in data/):
  synthetic_labeled.csv     cleaned schema + is_anomaly ground truth (Person A: training/eval)
  synthetic_bank_export.csv bank-style raw CSV (Date, Narration, Debit, Credit, Balance) to test upload
  eval_labeled.csv          300-row held-out sample for the F1 report (never train on this)
"""
import random
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
VOLUME = 2.6   # scales random-spend frequency (~1,500 rows over 12 months)
OUT = Path(__file__).resolve().parent.parent / "data"
CITIES = ["BLR", "MUM", "DEL", "HYD", "CHN", "PUNE"]
PEOPLE = ["RAHUL SHARMA", "PRIYA NAIR", "AMIT VERMA", "SNEHA RAO", "KARAN MEHTA", "ANJALI IYER"]

# category -> (merchant templates, (min, max) amount, avg transactions per month)
RANDOM_SPEND = {
    "Food Delivery": (["UPI/SWIGGY*{c}/{n}", "UPI/ZOMATO*{c}/{n}", "ZOMATO ORDER {n}", "SWIGGY INSTAMART {n}"], (150, 900), 9),
    "Dining Out":    (["POS {c} BARBEQUE NATION", "UPI/CAFE COFFEE DAY/{n}", "POS STARBUCKS {c}", "UPI/DOMINOS PIZZA/{n}"], (250, 2200), 4),
    "Groceries":     (["UPI/BIGBASKET/{n}", "UPI/BLINKIT*{c}/{n}", "POS DMART {c}", "UPI/ZEPTO/{n}", "POS RELIANCE FRESH {c}"], (200, 3500), 8),
    "Transport":     (["UPI/UBER INDIA/{n}", "UPI/OLA CABS/{n}", "UPI/RAPIDO/{n}", "BMTC METRO RECHARGE {n}"], (60, 600), 10),
    "Fuel":          (["POS INDIAN OIL {c}", "POS HPCL PETROL PUMP {c}", "UPI/BHARAT PETROLEUM/{n}"], (500, 3000), 2),
    "Shopping":      (["AMAZON PAY INDIA {n}", "UPI/FLIPKART/{n}", "POS MYNTRA {c}", "UPI/AJIO/{n}", "POS LIFESTYLE {c}"], (300, 6000), 3),
    "Entertainment": (["UPI/BOOKMYSHOW/{n}", "POS PVR CINEMAS {c}", "UPI/INOX LEISURE/{n}"], (200, 1200), 1.5),
    "Health":        (["UPI/APOLLO PHARMACY/{n}", "POS MEDPLUS {c}", "UPI/1MG/{n}", "POS PRACTO CONSULT {n}"], (100, 2500), 1.5),
    "Travel":        (["IRCTC TICKET {n}", "UPI/MAKEMYTRIP/{n}", "UPI/REDBUS/{n}", "UPI/IXIGO/{n}"], (400, 7000), 0.8),
    "Education":     (["UPI/UDEMY/{n}", "UPI/COURSERA/{n}", "POS CROSSWORD BOOKS {c}"], (300, 3000), 0.6),
    "Transfers":     (["UPI/{p}/{n}/PAYMENT", "NEFT-{p}-{n}", "IMPS/{p}/{n}"], (200, 8000), 2),
}
# (category, description template, fixed amount or None for variable, typical day of month)
FIXED_MONTHLY = [
    ("Rent", "NEFT-RENT-LANDLORD {l}", 18000, 1),
    ("EMI", "ACH D- HDFC BANK LTD EMI {n}", 7450, 5),
    ("Subscriptions", "UPI/NETFLIX COM/{n}", 649, 8),
    ("Subscriptions", "UPI/SPOTIFY INDIA/{n}", 119, 12),
    ("Subscriptions", "UPI/AMAZON PRIME/{n}", 299, 15),
    ("Subscriptions", "UPI/YOUTUBE PREMIUM/{n}", 129, 20),
    ("Utilities", "BESCOM ELECTRICITY BILL {n}", None, 10),
    ("Utilities", "UPI/AIRTEL POSTPAID/{n}", 599, 14),
    ("Utilities", "ACT FIBERNET BROADBAND {n}", 1049, 3),
]


def _fmt(tpl, rng):
    return tpl.format(c=rng.choice(CITIES), n=rng.randint(1000, 999999),
                      p=rng.choice(PEOPLE), l=rng.randint(10, 99))


def generate(months=12, end="2026-10-31", seed=SEED):
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    month_starts = list(pd.period_range(end=pd.Timestamp(end), periods=months, freq="M").start_time)
    rows = []

    for ms in month_starts:
        dim = ms.days_in_month
        day = lambda d: ms + pd.Timedelta(days=min(d, dim) - 1)

        rows.append((day(1), f"NEFT-SALARY-TECHNOVA SOLUTIONS-{rng.randint(1000, 9999)}", 85000.0, "credit", "Salary", 0))
        if rng.random() < 0.35:
            rows.append((day(rng.randint(10, 25)), f"UPI/{rng.choice(PEOPLE)}/{rng.randint(1000, 99999)}/REFUND",
                         float(rng.randint(300, 4000)), "credit", "Other Income", 0))

        for cat, tpl, amt, d in FIXED_MONTHLY:
            a = amt if amt else rng.randint(800, 2400)
            dd = min(max(d + rng.choice([-1, 0, 0, 1]), 1), dim)
            rows.append((day(dd), _fmt(tpl, rng), float(a), "debit", cat, 0))

        for cat, (tpls, (lo, hi), freq) in RANDOM_SPEND.items():
            for _ in range(nrng.poisson(freq * VOLUME)):
                amt = round(float(np.clip(nrng.lognormal(np.log((lo + hi) / 9), 0.55), lo, hi)), 2)
                rows.append((day(rng.randint(1, dim)), _fmt(rng.choice(tpls), rng), amt, "debit", cat, 0))

    df = pd.DataFrame(rows, columns=["date", "description", "amount", "type", "category", "is_anomaly"])

    # Inject ground-truth anomalies (used for Person A's Day 3 evaluation)
    pool = df[(df.type == "debit") & (~df.category.isin(["Rent", "EMI", "Subscriptions"]))]
    idx = list(pool.sample(12, random_state=seed).index)
    for i in idx[:8]:                                   # unusually large spend
        df.loc[i, "amount"] = round(df.loc[i, "amount"] * rng.uniform(5, 9), 2)
        df.loc[i, "is_anomaly"] = 1
    dups = df.loc[idx[8:]].copy()                       # duplicate charge, same day
    dups["is_anomaly"] = 1
    df = pd.concat([df, dups], ignore_index=True)

    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].astype(float)
    df["is_anomaly"] = df["is_anomaly"].astype(int)
    return df.sort_values("date", kind="stable").reset_index(drop=True)


def to_bank_export(df, start_balance=50000):
    """Mimic a real bank CSV: separate Debit/Credit columns, running balance, dd/mm/yyyy dates."""
    bal, out = start_balance, []
    for r in df.itertuples():
        bal += r.amount if r.type == "credit" else -r.amount
        out.append({
            "Date": r.date.strftime("%d/%m/%Y"),
            "Narration": r.description,
            "Debit": f"{r.amount:,.2f}" if r.type == "debit" else "",
            "Credit": f"{r.amount:,.2f}" if r.type == "credit" else "",
            "Balance": f"{bal:,.2f}",
        })
    return pd.DataFrame(out)


def main():
    OUT.mkdir(exist_ok=True)
    df = generate()
    df.to_csv(OUT / "synthetic_labeled.csv", index=False)
    to_bank_export(df).to_csv(OUT / "synthetic_bank_export.csv", index=False)
    df.sample(300, random_state=7).sort_values("date").to_csv(OUT / "eval_labeled.csv", index=False)
    print(f"Generated {len(df)} transactions, {df.date.min().date()} to {df.date.max().date()}")
    print(df.category.value_counts().to_string())
    print(f"Injected anomalies: {df.is_anomaly.sum()}")


if __name__ == "__main__":
    main()
