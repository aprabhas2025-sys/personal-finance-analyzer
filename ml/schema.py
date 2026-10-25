"""Shared contract between Person A (ml/) and Person B (app/).
Agree on this on Day 1 and do not change it without telling each other."""

# Final cleaned schema every function receives/returns
COLUMNS = ["date", "description", "amount", "type", "category"]
# date:        datetime64, transaction date
# description: str, raw merchant/narration text (whitespace-cleaned)
# amount:      float, ALWAYS positive
# type:        "debit" (money out) or "credit" (money in)
# category:    one of CATEGORIES, or "Uncategorized" before the model runs

UNCATEGORIZED = "Uncategorized"

CATEGORIES = [
    "Food Delivery", "Dining Out", "Groceries", "Transport", "Fuel",
    "Shopping", "Entertainment", "Subscriptions", "Utilities", "Rent",
    "EMI", "Health", "Travel", "Education", "Transfers",
    "Salary", "Other Income",
]
