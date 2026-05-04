import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from value_parsing import (
    coerce_none_like,
    coerce_optional_numeric_text,
    parse_optional_float,
    parse_optional_int,
)


def test_coerce_none_like_none_and_empty_strings():
    assert coerce_none_like(None) is None
    assert coerce_none_like("") is None
    assert coerce_none_like("   ") is None


def test_coerce_none_like_common_markers():
    assert coerce_none_like("None") is None
    assert coerce_none_like("(None)") is None
    assert coerce_none_like(" null ") is None


def test_coerce_none_like_preserves_non_none_text():
    assert coerce_none_like(" 268296608 ") == "268296608"
    assert coerce_none_like("RouteA") == "RouteA"


def test_coerce_none_like_does_not_treat_nan_as_none():
    # Important: keep 'nan' as a real value so invalid numeric input can be caught.
    assert coerce_none_like("nan") == "nan"
    assert coerce_none_like("NaN") == "NaN"


def test_coerce_optional_numeric_text_is_alias():
    assert coerce_optional_numeric_text("(None)") is None
    assert coerce_optional_numeric_text(" 1.25 ") == "1.25"


def test_parse_optional_float_missing_markers():
    assert parse_optional_float(None) is None
    assert parse_optional_float("") is None
    assert parse_optional_float("  ") is None
    assert parse_optional_float("(None)") is None
    assert parse_optional_float("null") is None
    assert parse_optional_float("None") is None


def test_parse_optional_float_rejects_nan_string():
    with pytest.raises(ValueError):
        parse_optional_float("nan")
    with pytest.raises(ValueError):
        parse_optional_float(" NaN ")


def test_parse_optional_float_parses_numbers():
    assert parse_optional_float(" 1.25 ") == 1.25
    assert parse_optional_float("3") == 3.0


def test_parse_optional_int_missing_markers():
    assert parse_optional_int("(None)") is None


def test_parse_optional_int_parses_integers_and_rejects_floats():
    assert parse_optional_int("3") == 3
    assert parse_optional_int("3.0") == 3
    with pytest.raises(ValueError):
        parse_optional_int("3.2")
