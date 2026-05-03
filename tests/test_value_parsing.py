import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from value_parsing import coerce_none_like, coerce_optional_numeric_text


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
