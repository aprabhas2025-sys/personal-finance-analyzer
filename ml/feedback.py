"""Feedback loop: learn from the user's category corrections.

  train_with_corrections(base, corrections)   pure: base training data + corrections (repeated) -> fitted pipeline
  retrain_with_corrections(corrections)       saves it to api.USER_MODEL_PATH and tells api to reload

Corrections are repeated REPEAT times so a handful of corrections is not drowned out by ~1,100 base rows.
Important limitation: the hybrid model checks keyword RULES first, so a correction only changes what the ML
path predicts (merchants no rule matches). Rule-matched merchants are fixed for the current statement by
merchant propagation in app/review.py, not by retraining.
"""
import pandas as pd

from ml import api, categorizer as C
from ml.schema import CATEGORIES

REPEAT = 5
NEEDED = ["description", "type", "category"]


def clean_corrections(corrections: pd.DataFrame) -> pd.DataFrame:
    c = corrections[NEEDED].dropna()
    c = c[c["category"].isin(CATEGORIES)]
    key = [C.normalize(d, t) + "|" + k for d, t, k in zip(c["description"], c["type"], c["category"])]
    return c.loc[~pd.Series(key, index=c.index).duplicated()].reset_index(drop=True)   # same merchant text counts once


def train_with_corrections(base: pd.DataFrame, corrections: pd.DataFrame, repeat: int = REPEAT):
    corr = clean_corrections(corrections) if corrections is not None and len(corrections) else corrections
    parts = [base[NEEDED]] if base is not None and len(base) else []
    if corr is not None and len(corr):
        parts += [corr] * repeat
    if not parts:
        raise ValueError("Nothing to train on: no base data and no corrections.")
    return C.fit(pd.concat(parts, ignore_index=True))


def _base_training_data():
    try:
        from ml.train_categorizer import load_split
        return load_split()[0]            # synthetic data minus the held-out eval set
    except Exception:
        return None                       # data files missing: fall back to corrections only


def retrain_with_corrections(corrections: pd.DataFrame, model_path=None, base=None):
    """Retrain, save to the user-model path and reload api. Returns the fitted pipeline."""
    pipe = train_with_corrections(_base_training_data() if base is None else base, corrections)
    C.save(pipe, model_path or api.USER_MODEL_PATH)
    api.reload_model()
    return pipe
