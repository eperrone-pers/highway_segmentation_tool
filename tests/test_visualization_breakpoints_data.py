import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.breakpoints import (
    add_endpoints_to_mandatory_breakpoints,
    compute_breakpoint_line_specs,
    extract_attribute_breakpoints,
    extract_attribute_break_signatures,
    extract_gap_boundary_breakpoints,
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


def test_extract_gap_boundary_breakpoints_reads_expected_shape():
    route_results = {
        "input_data_analysis": {
            "gap_analysis": {
                "gap_segments": [
                    {"start": 10, "end": 20, "length": 10},
                    {"start": "30", "end": "40", "length": 10},
                ]
            }
        }
    }

    out = extract_gap_boundary_breakpoints(route_results)
    assert out == {10.0, 20.0, 30.0, 40.0}


def test_extract_attribute_breakpoints_reads_expected_shape():
    route_results = {
        "input_data_analysis": {
            "attribute_break_analysis": {
                "breakpoints": [15, "25"],
                "break_events": [{"x": 35}, {"x": "45"}],
            }
        }
    }

    out = extract_attribute_breakpoints(route_results)
    assert out == {15.0, 25.0, 35.0, 45.0}


def test_compute_breakpoint_line_specs_classifies_gap_vs_attribute_when_provided():
    breakpoints = [0, 10, 15, 20, 30]
    mandatory = {0, 10, 15, 20}  # 30 is analysis breakpoint
    gap_bps = {10, 20}
    attr_bps = {15}

    specs = compute_breakpoint_line_specs(
        breakpoints,
        mandatory,
        gap_breakpoints=gap_bps,
        attribute_breakpoints=attr_bps,
    )

    assert [s.kind for s in specs] == [
        "mandatory_other",
        "mandatory_gap",
        "mandatory_attribute",
        "mandatory_gap",
        "analysis",
    ]


def test_extract_attribute_break_signatures_prefers_signature_and_falls_back_to_changed_columns():
    route_results = {
        "input_data_analysis": {
            "attribute_break_analysis": {
                "break_events": [
                    {"x": 10, "signature": "District"},
                    {"x": "20", "changed_columns": ["County"]},
                    {"x": 30, "changed_columns": ["A", "B"], "signature": "A+B"},
                ]
            }
        }
    }

    out = extract_attribute_break_signatures(route_results)
    assert out[10.0] == "District"
    assert out[20.0] == "County"
    assert out[30.0] == "A+B"
