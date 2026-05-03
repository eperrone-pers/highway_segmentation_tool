"""Shared visualization utilities.

Keep this module light and safe to import. It should not import tkinter.
"""

from __future__ import annotations

from typing import Dict


def safe_print(message: str) -> None:
    """Print to console without crashing on Windows encoding limitations."""
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", errors="backslashreplace").decode("ascii"))


def default_colors() -> Dict[str, str]:
    """Return the standard color mapping used by the enhanced visualization."""
    # Pleasant color scheme - updated for better contrast
    return {
        'original_data': '#D3D3D3',      # Light gray (better contrast)
        'original_edge': '#A9A9A9',      # Dark gray edges
        'mandatory_bp': '#DC143C',       # Crimson (softer red)
        'analysis_bp': '#228B22',        # Forest green
        'segment_avg': '#0066CC',        # Bolder blue (was dodger blue)
        'pareto_normal': '#4169E1',      # Royal blue
        'pareto_selected': '#DC2626',    # Pleasant red (softer than primary)
        'pareto_border': '#191970',      # Midnight blue
        'grid': '#E5E5E5',              # Very light gray
        'text_secondary': '#696969',     # Dim gray
    }
