import sys
from pathlib import Path

import pandas as pd

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_loader import filter_data_by_route


def test_filter_data_by_route_treats_route_as_string():
    df = pd.DataFrame(
        {
            "x": [0.0, 0.1, 0.2, 0.0],
            "y": [1, 2, 3, 4],
            "ROUTE_ID": [268296608, 268296608, 268296608, 999],
        }
    )

    filtered = filter_data_by_route(df, "ROUTE_ID", "268296608")
    assert len(filtered) == 3
    assert set(filtered["ROUTE_ID"].tolist()) == {268296608}


def test_filter_data_by_route_strips_whitespace():
    df = pd.DataFrame({"route": [" A ", "B", "A"], "x": [0, 1, 2]})
    filtered = filter_data_by_route(df, "route", "A")
    assert len(filtered) == 2


def test_filter_data_by_route_preserves_leading_zeros():
    """Route identifiers are categorical strings; leading zeros must be significant."""
    df = pd.DataFrame({"route_id": ["00123", "123", "00123"], "x": [0, 1, 2]})
    filtered = filter_data_by_route(df, "route_id", "00123")
    assert len(filtered) == 2
    assert set(filtered["route_id"].tolist()) == {"00123"}
