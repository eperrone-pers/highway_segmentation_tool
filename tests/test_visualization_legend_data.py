import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.graph_styling import dedupe_legend_entries


def test_dedupe_legend_entries_preserves_first_label_order_and_last_handle():
    labels = ["A", "B", "A", "C"]
    handles = ["h1", "h2", "h3", "h4"]

    out_labels, out_handles = dedupe_legend_entries(labels, handles)

    assert out_labels == ["A", "B", "C"]
    # For label 'A' keep last handle 'h3'
    assert out_handles == ["h3", "h2", "h4"]


def test_dedupe_legend_entries_empty():
    out_labels, out_handles = dedupe_legend_entries([], [])
    assert out_labels == []
    assert out_handles == []
