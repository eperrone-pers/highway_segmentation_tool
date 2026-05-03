import numpy as np

from src.visualization.segmentation_data import (
    compute_segment_average_lines,
    preprocess_gap_intervals,
    segments_outside_gaps,
)


def test_preprocess_gap_intervals_filters_and_sorts():
    gaps = [
        {"start": 10, "end": 12},
        {"start": None, "end": 5},
        {"start": 3, "end": 3},  # invalid (start == end)
        {"start": 1, "end": 2},
        {"start": "4", "end": "6"},
        {"start": "bad", "end": 9},
    ]

    intervals = preprocess_gap_intervals(gaps)
    assert intervals == [(1.0, 2.0), (4.0, 6.0), (10.0, 12.0)]


def test_segments_outside_gaps_excludes_overlaps():
    segments = [(0.0, 5.0), (5.0, 10.0), (10.0, 15.0)]
    gaps = [(5.5, 9.0)]

    valid = segments_outside_gaps(segments, gaps)
    assert valid == [(0.0, 5.0), (10.0, 15.0)]


def test_compute_segment_average_lines_basic():
    x = np.array([0.0, 1.0, 2.0, 6.0, 7.0, 10.0])
    y = np.array([0.0, 1.0, 2.0, 6.0, 7.0, 10.0])

    lines = compute_segment_average_lines(x_data=x, y_data=y, breakpoints=[0.0, 5.0, 10.0], gap_segments=[])

    assert len(lines) == 2
    assert (lines[0].start_x, lines[0].end_x) == (0.0, 5.0)
    assert lines[0].avg_y == 1.0
    assert lines[0].label == "Segment Averages"

    assert (lines[1].start_x, lines[1].end_x) == (5.0, 10.0)
    assert lines[1].avg_y == float(np.mean([6.0, 7.0, 10.0]))
    assert lines[1].label == ""


def test_compute_segment_average_lines_excludes_gap_overlaps():
    x = np.array([0.0, 1.0, 2.0, 6.0, 7.0, 10.0])
    y = np.array([0.0, 1.0, 2.0, 6.0, 7.0, 10.0])

    # Gap overlaps the second segment (5->10), so only the first line is computed.
    gap_segments = [{"start": 5.5, "end": 9.0}]
    lines = compute_segment_average_lines(x_data=x, y_data=y, breakpoints=[0.0, 5.0, 10.0], gap_segments=gap_segments)

    assert [(ln.start_x, ln.end_x) for ln in lines] == [(0.0, 5.0)]
    assert lines[0].avg_y == 1.0
    assert lines[0].label == "Segment Averages"
