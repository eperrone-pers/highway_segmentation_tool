import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.graph_styling import pretty_axis_label


def test_pretty_axis_label_defaults_when_missing():
    assert pretty_axis_label(None, default="X") == "X"
    assert pretty_axis_label("", default="Y") == "Y"


def test_pretty_axis_label_formats_underscores_and_title_case():
    assert pretty_axis_label("mile_post", default="X") == "Mile Post"
    assert pretty_axis_label("IRI", default="Y") == "Iri"
