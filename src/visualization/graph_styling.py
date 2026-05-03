"""Pure helpers for graph styling.

This module groups together visualization-only rules that typically evolve
together:
- axis styling constants for segmentation plots
- axis label formatting
- legend de-duplication

Matplotlib rendering remains in `visualization_ui.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, TypeVar


@dataclass(frozen=True)
class SegmentationAxisStyle:
    grid_alpha: float = 0.2
    major_x_nbins: int = 10
    major_x_prune: str = "both"
    major_y_nbins: int = 8
    major_y_prune: str = "both"
    minor_x_nbins: int = 20
    minor_y_nbins: int = 16


def default_segmentation_axis_style() -> SegmentationAxisStyle:
    """Return the default styling constants used by the segmentation plot."""

    return SegmentationAxisStyle()


def pretty_axis_label(column_name: Optional[str], *, default: str) -> str:
    """Format a column name into a human-readable axis label.

    Mirrors the existing visualization behavior:
    - If column_name is falsy => use `default`.
    - Otherwise => replace '_' with spaces and title-case.
    """

    if not column_name:
        return default

    return str(column_name).replace("_", " ").title()


T = TypeVar("T")


def dedupe_legend_entries(
    labels: Sequence[str],
    handles: Sequence[T],
) -> Tuple[List[str], List[T]]:
    """Dedupe legend entries by label.

    Mirrors the existing UI behavior that used `dict(zip(labels, handles))`:
    - order is based on first occurrence of each label
    - the handle kept is the *last* handle seen for that label

    Returns (deduped_labels, deduped_handles).
    """

    by_label = dict(zip(labels, handles))
    return list(by_label.keys()), list(by_label.values())
