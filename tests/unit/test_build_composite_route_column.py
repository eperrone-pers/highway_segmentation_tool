"""Unit tests for route_utils.build_composite_route_column."""

import numpy as np
import pandas as pd
import pytest

from route_utils import _COMPOSITE_ROUTE_COLUMN, build_composite_route_column


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _df(**kwargs):
    """Convenience factory: keyword args become DataFrame columns."""
    return pd.DataFrame(kwargs)


# ---------------------------------------------------------------------------
# Active-column resolution
# ---------------------------------------------------------------------------


def test_all_three_active_produces_composite():
    df = _df(RDB=["R1", "R1", "R2"], DIR=["NB", "NB", "SB"], LANE=["K1", "K6", "K1"])
    out, col, order = build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert col == _COMPOSITE_ROUTE_COLUMN
    assert order == ["RDB", "DIR", "LANE"]
    assert list(out[col]) == ["R1|NB|K1", "R1|NB|K6", "R2|SB|K1"]


def test_entirely_null_direction_dropped():
    df = _df(RDB=["R1", "R2"], DIR=[np.nan, np.nan], LANE=["K1", "K6"])
    out, col, order = build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert col == _COMPOSITE_ROUTE_COLUMN
    assert order == ["RDB", "LANE"]
    assert list(out[col]) == ["R1|K1", "R2|K6"]


def test_entirely_null_lane_dropped():
    df = _df(RDB=["R1", "R2"], DIR=["NB", "SB"], LANE=[np.nan, np.nan])
    out, col, order = build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert col == _COMPOSITE_ROUTE_COLUMN
    assert order == ["RDB", "DIR"]
    assert list(out[col]) == ["R1|NB", "R2|SB"]


def test_entirely_null_route_dropped_dir_lane_form_composite():
    df = _df(RDB=[np.nan, np.nan], DIR=["NB", "SB"], LANE=["K1", "K1"])
    out, col, order = build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert col == _COMPOSITE_ROUTE_COLUMN
    assert order == ["DIR", "LANE"]
    assert list(out[col]) == ["NB|K1", "SB|K1"]


def test_all_entirely_null_returns_single_route_mode():
    df = _df(RDB=[np.nan], DIR=[np.nan], LANE=[np.nan])
    out, col, order = build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert col is None
    assert order == []


def test_single_active_column_normalizes_to_synthetic_column():
    """Even with one active column, a synthetic column is produced so that
    null values become 'NULL' (consistent with composite mode).  component_order
    is a 1-element list so callers can always determine the source column."""
    df = _df(RDB=["R1", "R2"], DIR=[np.nan, np.nan], LANE=[np.nan, np.nan])
    out, col, order = build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert col == _COMPOSITE_ROUTE_COLUMN
    assert order == ["RDB"]
    assert _COMPOSITE_ROUTE_COLUMN in out.columns
    assert list(out[col]) == ["R1", "R2"]


def test_only_lane_active_normalizes_to_synthetic_column():
    df = _df(RDB=[np.nan], DIR=[np.nan], LANE=["K1"])
    out, col, order = build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert col == _COMPOSITE_ROUTE_COLUMN
    assert order == ["LANE"]
    assert list(out[col]) == ["K1"]


def test_none_column_args_are_skipped():
    """Passing None for direction/lane is valid — treated as not specified."""
    df = _df(RDB=["R1", "R2"])
    out, col, order = build_composite_route_column(df, "RDB", None, None)
    assert col == _COMPOSITE_ROUTE_COLUMN
    assert order == ["RDB"]
    assert list(out[col]) == ["R1", "R2"]


def test_two_active_columns_produces_composite():
    df = _df(RDB=["R1", "R2"], LANE=["K1", "K6"])
    out, col, order = build_composite_route_column(df, "RDB", None, "LANE")
    assert col == _COMPOSITE_ROUTE_COLUMN
    assert order == ["RDB", "LANE"]
    assert list(out[col]) == ["R1|K1", "R2|K6"]


# ---------------------------------------------------------------------------
# Null values within active columns
# ---------------------------------------------------------------------------


def test_null_direction_value_becomes_NULL_literal():
    df = _df(RDB=["R1", "R2"], DIR=["NB", np.nan], LANE=["K1", "K1"])
    out, col, _ = build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert list(out[col]) == ["R1|NB|K1", "R2|NULL|K1"]


def test_null_route_value_becomes_NULL_literal():
    df = _df(RDB=[np.nan, "R2"], DIR=["NB", "NB"], LANE=["K1", "K1"])
    out, col, _ = build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert list(out[col]) == ["NULL|NB|K1", "R2|NB|K1"]


def test_whitespace_only_value_treated_as_null():
    df = _df(RDB=["R1", "  "], DIR=["NB", "SB"], LANE=["K1", "K1"])
    out, col, _ = build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert list(out[col]) == ["R1|NB|K1", "NULL|SB|K1"]


def test_empty_string_value_treated_as_null():
    df = _df(RDB=["R1", ""], DIR=["NB", "SB"], LANE=["K1", "K1"])
    out, col, _ = build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert list(out[col]) == ["R1|NB|K1", "NULL|SB|K1"]


# ---------------------------------------------------------------------------
# Column-order preservation (route → direction → lane)
# ---------------------------------------------------------------------------


def test_component_order_matches_route_direction_lane():
    """component_order should always be route → direction → lane, never reordered."""
    df = _df(LANE=["K1"], DIR=["NB"], RDB=["R1"])
    out, col, order = build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert order == ["RDB", "DIR", "LANE"]
    assert list(out[col]) == ["R1|NB|K1"]


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_missing_route_column_raises():
    df = _df(RDB=["R1"])
    with pytest.raises(ValueError, match="NOPE"):
        build_composite_route_column(df, "NOPE", None, None)


def test_missing_direction_column_raises():
    df = _df(RDB=["R1"])
    with pytest.raises(ValueError, match="MISSING_DIR"):
        build_composite_route_column(df, "RDB", "MISSING_DIR", None)


def test_missing_lane_column_raises():
    df = _df(RDB=["R1"])
    with pytest.raises(ValueError, match="MISSING_LANE"):
        build_composite_route_column(df, "RDB", None, "MISSING_LANE")


# ---------------------------------------------------------------------------
# DataFrame immutability
# ---------------------------------------------------------------------------


def test_original_dataframe_not_mutated():
    df = _df(RDB=["R1"], DIR=["NB"], LANE=["K1"])
    original_cols = list(df.columns)
    build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert list(df.columns) == original_cols
    assert _COMPOSITE_ROUTE_COLUMN not in df.columns


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_single_row_dataframe():
    df = _df(RDB=["Route1"], DIR=["NB"], LANE=["K1"])
    out, col, order = build_composite_route_column(df, "RDB", "DIR", "LANE")
    assert list(out[col]) == ["Route1|NB|K1"]


def test_composite_key_used_by_downstream_list_routes():
    """The composite column should work transparently with list_routes()."""
    from route_utils import list_routes

    df = _df(RDB=["R1", "R1", "R2"], DIR=["NB", "SB", "NB"], LANE=["K1", "K1", "K6"])
    out, col, _ = build_composite_route_column(df, "RDB", "DIR", "LANE")
    routes = list_routes(out, col)
    assert sorted(routes) == ["R1|NB|K1", "R1|SB|K1", "R2|NB|K6"]
