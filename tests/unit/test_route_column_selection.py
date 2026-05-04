import pytest

from route_utils import ROUTE_COLUMN_NONE_SENTINEL, normalize_route_column_selection


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        (ROUTE_COLUMN_NONE_SENTINEL, None),
        (f"  {ROUTE_COLUMN_NONE_SENTINEL}  ", None),
        ("route_id", "route_id"),
        ("  route_id  ", "route_id"),
        ("none", "none"),  # do not treat generic 'none' as the UI sentinel
        (123, "123"),
    ],
)
def test_normalize_route_column_selection(value, expected):
    assert normalize_route_column_selection(value) == expected
