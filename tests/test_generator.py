import pandas as pd
from ml.generate_data import generate
from ml.schema import CATEGORIES


def test_generator_shape_and_labels():
    df = generate()
    assert 1200 <= len(df) <= 2000
    assert df["date"].dt.to_period("M").nunique() == 12
    assert set(df["category"]) <= set(CATEGORIES)
    assert (df["amount"] > 0).all()
    assert df["is_anomaly"].sum() == 12


def test_generator_is_deterministic():
    pd.testing.assert_frame_equal(generate(), generate())
