import pandas as pd

from data_loader import analyze_route_gaps


def test_attribute_must_break_creates_breakpoint_at_next_x():
    df = pd.DataFrame(
        {
            "x": [0.0, 1.0, 2.0, 3.0],
            "y": [10.0, 11.0, 12.0, 13.0],
            "district": ["A", "A", "B", "B"],
        }
    )

    ra = analyze_route_gaps(df, "x", "y", route_id="r", gap_threshold=100.0, must_break_columns=["district"])

    # Change occurs between x=1 and x=2 -> breakpoint at 2.0
    assert 2.0 in ra.mandatory_breakpoints
    assert ra.attribute_breakpoints == [2.0]
    assert ra.attribute_break_events == [{"x": 2.0, "changed_columns": ["district"], "signature": "district"}]


def test_attribute_must_break_null_transitions_count_as_change():
    df = pd.DataFrame(
        {
            "x": [0.0, 1.0, 2.0, 3.0],
            "y": [10.0, 11.0, 12.0, 13.0],
            "pavement": ["asphalt", None, None, "concrete"],
        }
    )

    ra = analyze_route_gaps(df, "x", "y", route_id="r", gap_threshold=100.0, must_break_columns=["pavement"])

    # asphalt -> None at x=1.0
    # None -> concrete at x=3.0
    assert ra.attribute_breakpoints == [1.0, 3.0]
    assert {1.0, 3.0}.issubset(set(ra.mandatory_breakpoints))


def test_attribute_must_break_multiple_columns_signature_when_both_change():
    df = pd.DataFrame(
        {
            "x": [0.0, 1.0, 2.0],
            "y": [10.0, 11.0, 12.0],
            "district": ["A", "B", "B"],
            "pavement": ["X", "Y", "Y"],
        }
    )

    ra = analyze_route_gaps(
        df,
        "x",
        "y",
        route_id="r",
        gap_threshold=100.0,
        must_break_columns=["pavement", "district"],
    )

    # Both change between row0 and row1 -> breakpoint at x=1.0
    assert ra.attribute_break_events == [
        {"x": 1.0, "changed_columns": ["district", "pavement"], "signature": "district|pavement"}
    ]


def test_attribute_must_break_ignores_missing_columns():
    df = pd.DataFrame({"x": [0.0, 1.0, 2.0], "y": [1.0, 2.0, 3.0], "a": ["x", "y", "y"]})

    ra = analyze_route_gaps(df, "x", "y", route_id="r", gap_threshold=100.0, must_break_columns=["a", "missing"])
    assert ra.must_break_columns_used == ["a"]
