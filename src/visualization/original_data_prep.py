"""Pure helpers for preparing original (route) data for plotting.

This module isolates pandas/numpy data cleaning from the matplotlib/UI layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PreparedXYSeries:
    x_data: Optional[np.ndarray]
    y_data: Optional[np.ndarray]
    prepared_df: Optional[pd.DataFrame]
    error_message: Optional[str] = None


def prepare_numeric_xy_series(
    route_data: Optional[pd.DataFrame],
    *,
    x_col: str,
    y_col: str,
) -> PreparedXYSeries:
    """Prepare numeric x/y arrays and a cleaned dataframe for plotting.

    Behavior mirrors the historic UI intent:
    - If route_data is None/empty => returns no data.
    - If x_col/y_col are missing => returns an error message.
    - Coerces x/y columns to numeric (errors='coerce'), drops rows with NaNs.
    - If everything is dropped => returns no data.

    The returned dataframe is a copy (does not mutate the caller's dataframe).
    """

    if route_data is None or route_data.empty:
        return PreparedXYSeries(x_data=None, y_data=None, prepared_df=None)

    if x_col not in route_data.columns or y_col not in route_data.columns:
        return PreparedXYSeries(
            x_data=None,
            y_data=None,
            prepared_df=None,
            error_message=(
                f"Original data is missing required columns: x_col={x_col!r}, y_col={y_col!r}. "
                "Showing breakpoints only."
            ),
        )

    prepared = route_data.copy()

    try:
        prepared[x_col] = pd.to_numeric(prepared[x_col], errors="coerce")
        prepared[y_col] = pd.to_numeric(prepared[y_col], errors="coerce")
        prepared = prepared.dropna(subset=[x_col, y_col])
    except Exception:
        # Preserve best-effort behavior: if conversion fails unexpectedly, treat
        # as no usable numeric data.
        return PreparedXYSeries(x_data=None, y_data=None, prepared_df=None)

    if prepared.empty:
        return PreparedXYSeries(x_data=None, y_data=None, prepared_df=None)

    x_data = prepared[x_col].values
    y_data = prepared[y_col].values

    return PreparedXYSeries(x_data=x_data, y_data=y_data, prepared_df=prepared)
