import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.breakpoints import xlim_from_breakpoints


def test_xlim_from_breakpoints_returns_none_for_empty_or_single():
    assert xlim_from_breakpoints([]) is None
    assert xlim_from_breakpoints([1.0]) is None


def test_xlim_from_breakpoints_sorts_and_returns_min_max():
    assert xlim_from_breakpoints([10.0, 0.0, 5.0]) == (0.0, 10.0)


def test_xlim_from_breakpoints_returns_none_when_sort_fails():
    # Mixed incomparable types raise during sorting in Python 3.
    assert xlim_from_breakpoints(["1", 2]) is None


def test_xlim_from_breakpoints_coerces_numeric_strings_to_floats():
    assert xlim_from_breakpoints(["2", "1"]) == (1.0, 2.0)


def test_xlim_from_breakpoints_returns_none_for_non_numeric_strings():
    assert xlim_from_breakpoints(["a", "b"]) is None
