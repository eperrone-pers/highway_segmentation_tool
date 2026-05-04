import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.gap_analysis_data import extract_gap_analysis, should_show_gap_info_once


def test_extract_gap_analysis_defaults_when_missing():
    info = extract_gap_analysis(None)
    assert info.gap_segments == []
    assert info.total_gaps == 0


def test_extract_gap_analysis_reads_expected_shape():
    route_results = {
        "input_data_analysis": {
            "gap_analysis": {
                "gap_segments": [{"start": 1, "end": 2}],
                "total_gaps": 3,
            }
        }
    }

    info = extract_gap_analysis(route_results)
    assert info.gap_segments == [{"start": 1, "end": 2}]
    assert info.total_gaps == 3


def test_extract_gap_analysis_coerces_total_gaps_to_int():
    route_results = {"input_data_analysis": {"gap_analysis": {"gap_segments": [], "total_gaps": "2"}}}
    info = extract_gap_analysis(route_results)
    assert info.total_gaps == 2


def test_should_show_gap_info_once_only_once_per_route():
    should, shown = should_show_gap_info_once(route_id="R1", total_gaps=1, already_shown_routes=set())
    assert should is True
    assert "R1" in shown

    should2, shown2 = should_show_gap_info_once(route_id="R1", total_gaps=1, already_shown_routes=shown)
    assert should2 is False
    assert shown2 == shown


def test_should_show_gap_info_once_requires_positive_total_gaps():
    should, shown = should_show_gap_info_once(route_id="R1", total_gaps=0, already_shown_routes=set())
    assert should is False
    assert shown == set()
