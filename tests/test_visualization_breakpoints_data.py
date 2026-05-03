import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.breakpoints import (
    add_endpoints_to_mandatory_breakpoints,
    compute_breakpoint_line_specs,
    extract_mandatory_breakpoints,
    split_breakpoints_by_mandatory,
)


def test_split_breakpoints_by_mandatory_preserves_order():
    breakpoints = [5, 1, 3, 2]
    mandatory = {1, 3}

    mandatory_bps, analysis_bps = split_breakpoints_by_mandatory(breakpoints, mandatory)

    assert mandatory_bps == [1, 3]
    assert analysis_bps == [5, 2]


def test_split_breakpoints_by_mandatory_int_float_equivalence():
    breakpoints = [1.0, 2.0, 3.0]
    mandatory = {2}  # int

    mandatory_bps, analysis_bps = split_breakpoints_by_mandatory(breakpoints, mandatory)

    assert mandatory_bps == [2.0]
    assert analysis_bps == [1.0, 3.0]


def test_split_breakpoints_by_mandatory_empty_inputs():
    mandatory_bps, analysis_bps = split_breakpoints_by_mandatory([], [])
    assert mandatory_bps == []
    assert analysis_bps == []


def test_extract_mandatory_breakpoints_defaults_empty():
    assert extract_mandatory_breakpoints(None) == set()
    assert extract_mandatory_breakpoints({}) == set()


def test_extract_mandatory_breakpoints_reads_expected_shape():
    route_results = {
        "input_data_analysis": {
            "mandatory_segments": {"mandatory_breakpoints": [1, 2, 3]}
        }
    }
    assert extract_mandatory_breakpoints(route_results) == {1, 2, 3}


def test_add_endpoints_to_mandatory_breakpoints_adds_and_sorts():
    mandatory = {5.0}
    out = add_endpoints_to_mandatory_breakpoints(mandatory, route_start=0.0, route_end=10.0)
    assert out == [0.0, 5.0, 10.0]


def test_compute_breakpoint_line_specs_preserves_order_and_labels_once():
    breakpoints = [5, 1, 3, 2]
    mandatory = {1, 3}

    specs = compute_breakpoint_line_specs(breakpoints, mandatory)

    assert [s.x for s in specs] == [float(b) for b in breakpoints]
    assert [s.kind for s in specs] == ["analysis", "mandatory", "mandatory", "analysis"]
    assert [s.label for s in specs] == [
        "Analysis Breakpoints",
        "Mandatory Breakpoints",
        "",
        "",
    ]


def test_compute_breakpoint_line_specs_custom_labels():
    specs = compute_breakpoint_line_specs([1, 2], {2}, mandatory_label="M", analysis_label="A")
    assert [s.label for s in specs] == ["A", "M"]


def test_compute_breakpoint_line_specs_coerces_numeric_strings_and_classifies_mandatory():
    specs = compute_breakpoint_line_specs(["10", "20"], {20})
    assert [s.x for s in specs] == [10.0, 20.0]
    assert [s.kind for s in specs] == ["analysis", "mandatory"]


def test_compute_breakpoint_line_specs_skips_invalid_breakpoints():
    specs = compute_breakpoint_line_specs(["bad", 1, None, "2"], {2})
    assert [s.x for s in specs] == [1.0, 2.0]
