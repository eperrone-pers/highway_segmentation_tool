import sys
from pathlib import Path

import pandas as pd

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.original_data_prep import prepare_numeric_xy_series


def test_prepare_numeric_xy_series_coerces_and_drops_non_numeric_rows():
    df = pd.DataFrame({"x": ["1", "bad", "3"], "y": ["10", "20", "bad"]})

    res = prepare_numeric_xy_series(df, x_col="x", y_col="y")

    assert res.error_message is None
    assert res.prepared_df is not None
    assert res.x_data.tolist() == [1.0]
    assert res.y_data.tolist() == [10.0]


def test_prepare_numeric_xy_series_returns_error_when_columns_missing():
    df = pd.DataFrame({"a": [1], "b": [2]})

    res = prepare_numeric_xy_series(df, x_col="x", y_col="y")

    assert res.prepared_df is None
    assert res.x_data is None
    assert res.y_data is None
    assert res.error_message


def test_prepare_numeric_xy_series_does_not_mutate_input_dataframe():
    df = pd.DataFrame({"x": ["1"], "y": ["2"]})
    original_dtypes = df.dtypes.copy()

    _ = prepare_numeric_xy_series(df, x_col="x", y_col="y")

    assert (df.dtypes == original_dtypes).all()


def test_prepare_numeric_xy_series_returns_no_data_when_all_rows_dropped():
    df = pd.DataFrame({"x": ["bad"], "y": ["also_bad"]})

    res = prepare_numeric_xy_series(df, x_col="x", y_col="y")

    assert res.prepared_df is None
    assert res.x_data is None
    assert res.y_data is None
