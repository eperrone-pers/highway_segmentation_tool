import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from visualization.zoom_decisions import (
    compute_paged_xlim,
    should_cache_default_limits,
    should_show_segmentation_paging_arrows,
)


def test_should_cache_default_limits_matches_existing_behavior():
    assert should_cache_default_limits(x_zoom_enabled=False) is True
    assert should_cache_default_limits(x_zoom_enabled=True) is False


def test_should_show_segmentation_paging_arrows_only_when_zoomed():
    full = (0.0, 100.0)

    assert should_show_segmentation_paging_arrows(full_xlim=full, cur_xlim=(0.0, 100.0)) is False
    assert should_show_segmentation_paging_arrows(full_xlim=full, cur_xlim=(10.0, 90.0)) is True


def test_should_show_segmentation_paging_arrows_handles_reversed_limits():
    full = (100.0, 0.0)
    assert should_show_segmentation_paging_arrows(full_xlim=full, cur_xlim=(90.0, 10.0)) is True


def test_compute_paged_xlim_none_when_not_zoomed_or_missing_full():
    assert compute_paged_xlim(full_xlim=None, cur_xlim=(0.0, 10.0), direction=1) is None
    assert compute_paged_xlim(full_xlim=(0.0, 100.0), cur_xlim=(0.0, 100.0), direction=1) is None


def test_compute_paged_xlim_pages_and_clamps():
    full = (0.0, 100.0)
    cur = (10.0, 30.0)  # span=20

    assert compute_paged_xlim(full_xlim=full, cur_xlim=cur, direction=1) == (30.0, 50.0)
    assert compute_paged_xlim(full_xlim=full, cur_xlim=cur, direction=-1) == (0.0, 20.0)

    # Clamp at right boundary
    cur2 = (80.0, 100.0)
    assert compute_paged_xlim(full_xlim=full, cur_xlim=cur2, direction=1) == (80.0, 100.0)


def test_compute_paged_xlim_handles_reversed_current_limits():
    full = (0.0, 100.0)
    cur = (30.0, 10.0)
    assert compute_paged_xlim(full_xlim=full, cur_xlim=cur, direction=1) == (30.0, 50.0)
