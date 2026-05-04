import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.graph_styling import default_segmentation_axis_style


def test_default_segmentation_axis_style_matches_existing_ui_values():
    style = default_segmentation_axis_style()
    assert style.grid_alpha == 0.2
    assert style.major_x_nbins == 10
    assert style.major_x_prune == "both"
    assert style.major_y_nbins == 8
    assert style.major_y_prune == "both"
    assert style.minor_x_nbins == 20
    assert style.minor_y_nbins == 16
