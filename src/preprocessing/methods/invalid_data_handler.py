"""
Invalid Data Handler Preprocessing Method

Handles missing or non-numeric Y values before analysis runs. Intended to run
in the Pre-Gap preprocessing slot so data is clean before gap detection and
segmentation occur.

Three strategies are supported for bad Y values:
- drop: Remove the row entirely.
- moving_average: Replace with the average of up to N valid neighbors on each side.
- linear_interpolate: Estimate by linear interpolation between the nearest valid
  readings on each side.

Rows at the start or end of a route that have no valid neighbor on one side fall
back to "drop" for moving_average and linear_interpolate strategies.
"""

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np
import pandas as pd

from preprocessing.base import (
    DataModificationContext,
    PreprocessingMethodBase,
    PreprocessingResult,
    create_processed_route_analysis,
)

if TYPE_CHECKING:
    from data_loader import RouteAnalysis

_logger = logging.getLogger(__name__)


class InvalidDataHandlerPreprocessor(PreprocessingMethodBase):
    """
    Handles missing or non-numeric Y values before analysis.

    Must be configured in the Pre-Gap preprocessing slot so that data is
    clean before gap detection and segmentation occur.

    Parameters:
        y_strategy: How to handle rows with missing/non-numeric Y values.
            "drop" removes them; "moving_average" replaces with the mean of
            nearby valid values; "linear_interpolate" estimates by position.
        window_size: Number of valid neighbors to collect on each side when
            using the moving_average strategy (minimum 1, no upper bound).
        enable_threshold: When True, skip the route if the fraction of bad-Y
            rows exceeds threshold_percent.
        threshold_percent: Maximum allowed percentage of bad-Y rows before
            the route is skipped (requires enable_threshold=True).
    """

    @property
    def preprocess_key(self) -> str:
        return "invalid_data_handler"

    @property
    def preprocess_name(self) -> str:
        return "Invalid Data Handler"

    @property
    def description(self) -> str:
        return (
            "Handles missing or non-numeric Y values before analysis. "
            "Must be configured in the Pre-Gap preprocessing slot. "
            "Strategies: Drop row, Moving Average (N neighbors each side), "
            "or Linear Interpolate between nearest valid readings."
        )

    def process(
        self,
        route_analysis: "RouteAnalysis",
        x_column: str,
        y_column: str,
        log_callback=None,
        **parameters,
    ) -> PreprocessingResult:
        """
        Apply invalid data handling to route data.

        Args:
            route_analysis: RouteAnalysis object with route data.
            x_column: Name of the X-axis column (e.g., "Milepoint").
            y_column: Name of the Y-axis column (e.g., "IRI").
            log_callback: Optional callable for progress messages.
            **parameters: Method parameters (y_strategy, window_size,
                enable_threshold, threshold_percent).

        Returns:
            PreprocessingResult with modified route analysis and complete
            modification log.

        Raises:
            ValueError: If enable_threshold is True and the fraction of
                bad-Y rows exceeds threshold_percent.
        """
        log = log_callback or _logger.debug

        y_strategy = parameters.get("y_strategy", "drop")
        window_size = int(parameters.get("window_size", 3))
        enable_threshold = bool(parameters.get("enable_threshold", False))
        threshold_percent = float(parameters.get("threshold_percent", 10.0))

        df = route_analysis.route_data.copy()
        original_y = df[y_column].values.copy()

        df_sorted = df.sort_values(x_column).reset_index(drop=True)

        nan_y_mask = df_sorted[y_column].isna()
        nan_y_count = int(nan_y_mask.sum())
        total_points = len(df_sorted)

        log(
            f"Invalid Data Handler start for route {route_analysis.route_id}: "
            f"strategy={y_strategy}, nan_y_count={nan_y_count}/{total_points}"
        )

        if nan_y_count == 0:
            processed_analysis = create_processed_route_analysis(
                route_analysis, df_sorted, x_column, y_column
            )
            return PreprocessingResult(
                processed_route_analysis=processed_analysis,
                modification_log=[],
                preprocessing_metadata=self._build_metadata(
                    y_strategy, window_size, enable_threshold, threshold_percent,
                    nan_y_count, total_points, 0,
                ),
                original_y_values=original_y.tolist(),
                modifications_summary="Invalid Data Handler: no missing Y values found",
            )

        if enable_threshold:
            bad_fraction_pct = nan_y_count / total_points * 100
            if bad_fraction_pct > threshold_percent:
                raise ValueError(
                    f"Route '{route_analysis.route_id}': {nan_y_count} of {total_points} Y values "
                    f"({bad_fraction_pct:.1f}%) are missing or non-numeric, exceeding the configured "
                    f"threshold of {threshold_percent}%. Fix the input data or raise the threshold."
                )

        ctx = DataModificationContext(
            df_sorted, x_column, y_column, route_analysis.mandatory_breakpoints
        )

        modifications_count = 0

        mandatory_bps = route_analysis.mandatory_breakpoints or set()

        if y_strategy == "drop":
            modifications_count = self._apply_drop(ctx, df_sorted, x_column, y_column, nan_y_mask, mandatory_bps)
        elif y_strategy == "moving_average":
            modifications_count = self._apply_moving_average(
                ctx, df_sorted, x_column, y_column, nan_y_mask, window_size, mandatory_bps
            )
        elif y_strategy == "linear_interpolate":
            modifications_count = self._apply_linear_interpolate(
                ctx, df_sorted, x_column, y_column, nan_y_mask, mandatory_bps
            )

        df_processed = ctx.get_modified_data()
        modification_log = ctx.get_modification_log()

        processed_analysis = create_processed_route_analysis(
            route_analysis, df_processed, x_column, y_column
        )

        action_word = "dropped" if y_strategy == "drop" else "imputed"
        summary = (
            f"Invalid Data Handler ({y_strategy}): {action_word} {modifications_count} "
            f"row{'s' if modifications_count != 1 else ''} with missing/non-numeric Y values"
        )

        log(
            f"Invalid Data Handler complete for route {route_analysis.route_id}: "
            f"modifications={modifications_count}, points_before={total_points}, "
            f"points_after={len(df_processed)}"
        )

        return PreprocessingResult(
            processed_route_analysis=processed_analysis,
            modification_log=modification_log,
            preprocessing_metadata=self._build_metadata(
                y_strategy, window_size, enable_threshold, threshold_percent,
                nan_y_count, total_points, modifications_count,
            ),
            original_y_values=original_y.tolist(),
            modifications_summary=summary,
        )

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    def _apply_drop(
        self,
        ctx: DataModificationContext,
        df: pd.DataFrame,
        x_column: str,
        y_column: str,
        nan_y_mask: pd.Series,
        mandatory_breakpoints: set,
    ) -> int:
        """Remove all rows with NaN Y values (skips mandatory breakpoints)."""
        count = 0
        for x_val in df.loc[nan_y_mask, x_column]:
            fval = float(x_val)
            if fval in mandatory_breakpoints:
                continue
            ctx.remove_point(fval, reason="missing/non-numeric Y value")
            count += 1
        return count

    def _apply_moving_average(
        self,
        ctx: DataModificationContext,
        df: pd.DataFrame,
        x_column: str,
        y_column: str,
        nan_y_mask: pd.Series,
        window_size: int,
        mandatory_breakpoints: set,
    ) -> int:
        """Replace NaN Y values with the mean of up to window_size valid neighbors each side."""
        count = 0
        y_values = df[y_column].values.copy()
        x_values = df[x_column].values

        for idx in df.index[nan_y_mask]:
            neighbors = self._collect_neighbors(y_values, idx, window_size)
            x_val = float(x_values[idx])

            if not neighbors:
                if x_val in mandatory_breakpoints:
                    continue
                ctx.remove_point(x_val, reason="missing Y value — no valid neighbors for moving average")
                count += 1
                continue

            new_y = float(np.mean(neighbors))
            ctx.modify_y_value(
                x_val,
                new_y,
                reason=f"moving average of {len(neighbors)} valid neighbor{'s' if len(neighbors) != 1 else ''}",
                modification_type="y_value_changed",
            )
            count += 1

        return count

    def _apply_linear_interpolate(
        self,
        ctx: DataModificationContext,
        df: pd.DataFrame,
        x_column: str,
        y_column: str,
        nan_y_mask: pd.Series,
        mandatory_breakpoints: set,
    ) -> int:
        """Replace NaN Y values with linear interpolation between nearest valid neighbors."""
        count = 0
        y_values = df[y_column].values.copy()
        x_values = df[x_column].values

        for idx in df.index[nan_y_mask]:
            prev_pair, next_pair = self._find_bracket(y_values, x_values, idx)
            x_val = float(x_values[idx])

            if prev_pair is None or next_pair is None:
                if x_val in mandatory_breakpoints:
                    continue
                ctx.remove_point(
                    x_val,
                    reason="missing Y value — no valid neighbor on one side for interpolation",
                )
                count += 1
                continue

            prev_x, prev_y = prev_pair
            next_x, next_y = next_pair

            if next_x == prev_x:
                new_y = float((prev_y + next_y) / 2)
            else:
                t = (x_val - prev_x) / (next_x - prev_x)
                new_y = float(prev_y + t * (next_y - prev_y))

            ctx.modify_y_value(
                x_val,
                new_y,
                reason=f"linear interpolation between x={prev_x} and x={next_x}",
                modification_type="point_interpolated",
            )
            count += 1

        return count

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_neighbors(y_values: np.ndarray, center_idx: int, window_size: int) -> List[float]:
        """Collect up to window_size valid (non-NaN) Y values on each side of center_idx."""
        neighbors: List[float] = []

        # Look backward
        collected = 0
        i = center_idx - 1
        while i >= 0 and collected < window_size:
            if not np.isnan(y_values[i]):
                neighbors.append(float(y_values[i]))
                collected += 1
            i -= 1

        # Look forward
        collected = 0
        i = center_idx + 1
        while i < len(y_values) and collected < window_size:
            if not np.isnan(y_values[i]):
                neighbors.append(float(y_values[i]))
                collected += 1
            i += 1

        return neighbors

    @staticmethod
    def _find_bracket(
        y_values: np.ndarray,
        x_values: np.ndarray,
        center_idx: int,
    ) -> Tuple[Optional[Tuple[float, float]], Optional[Tuple[float, float]]]:
        """Find the nearest valid (non-NaN) Y value before and after center_idx."""
        prev_pair: Optional[Tuple[float, float]] = None
        i = center_idx - 1
        while i >= 0:
            if not np.isnan(y_values[i]):
                prev_pair = (float(x_values[i]), float(y_values[i]))
                break
            i -= 1

        next_pair: Optional[Tuple[float, float]] = None
        i = center_idx + 1
        while i < len(y_values):
            if not np.isnan(y_values[i]):
                next_pair = (float(x_values[i]), float(y_values[i]))
                break
            i += 1

        return prev_pair, next_pair

    @staticmethod
    def _build_metadata(
        y_strategy: str,
        window_size: int,
        enable_threshold: bool,
        threshold_percent: float,
        nan_y_count: int,
        total_points: int,
        modifications_count: int,
    ) -> dict:
        return {
            "method_key": "invalid_data_handler",
            "method_name": "Invalid Data Handler",
            "y_strategy": y_strategy,
            "window_size": window_size,
            "enable_threshold": enable_threshold,
            "threshold_percent": threshold_percent,
            "nan_y_count": nan_y_count,
            "points_before": total_points,
            "points_after": total_points - nan_y_count if y_strategy == "drop" else total_points,
            "modifications_count": modifications_count,
        }
