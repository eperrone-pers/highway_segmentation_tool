"""PELT segmentation method (ruptures) integrated into the extensible framework.

This implements a deterministic, single-solution change-point segmentation method
using PELT from the `ruptures` library.

Key integration constraints:
- Gap-aware: respects RouteAnalysis.mandatory_breakpoints and never segments across gaps.
- Framework-compliant: returns AnalysisResult with a `chromosome` (milepoint breakpoints).
- Lazy dependency: `ruptures` is imported at runtime so the app can start even if the
  package is not installed.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..base import AnalysisMethodBase, AnalysisResult
from ..utils.segment_metrics import average_length_excluding_gap_segments
from config import get_optimization_method


def _rolling_smooth(values: np.ndarray, window_pts: int, method: str) -> np.ndarray:
    window_pts = int(max(1, window_pts))
    series = pd.Series(values)
    rolling = series.rolling(window=window_pts, center=True, min_periods=1)
    if method == "median":
        return rolling.median().to_numpy()
    return rolling.mean().to_numpy()


def _estimate_spacing_miles(xs: np.ndarray) -> float:
    if xs is None or len(xs) < 2:
        return 0.0
    diffs = np.diff(xs.astype(float))
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if len(diffs) == 0:
        return 0.0
    return float(np.median(diffs))


def _is_gap_segment(start: float, end: float, gap_segments: List) -> bool:
    tol = 1e-6
    for gap in gap_segments or []:
        try:
            gs, ge = float(gap[0]), float(gap[1])
        except Exception:
            continue
        if abs(start - gs) <= tol and abs(end - ge) <= tol:
            return True
    return False


def _snap_to_existing_x(sorted_x: np.ndarray, target: float, lo: float, hi: float) -> Optional[float]:
    """Snap a target milepoint to the nearest existing x value within (lo, hi).

    Returns None if no x value falls in the open interval.
    """
    if sorted_x is None or len(sorted_x) == 0:
        return None
    left = int(np.searchsorted(sorted_x, lo, side="right"))
    right = int(np.searchsorted(sorted_x, hi, side="left"))
    if left >= right:
        return None
    idx = int(np.searchsorted(sorted_x[left:right], target, side="left")) + left
    if idx >= right:
        idx = right - 1
    # Compare neighbor for nearest
    cand = [idx]
    if idx - 1 >= left:
        cand.append(idx - 1)
    best = min(cand, key=lambda i: abs(float(sorted_x[i]) - float(target)))
    return float(sorted_x[best])


def _enforce_max_segment_length(
    breakpoints: List[float],
    sorted_x: np.ndarray,
    gap_segments: List,
    mandatory_breakpoints: List[float],
    min_length: float,
    max_length: float,
    log,
) -> List[float]:
    """Split overlong (non-gap) segments by inserting additional breakpoints.

    - Does not split gap segments.
    - Snaps inserted breakpoints to the nearest existing data x values.
    - Tries to respect min_length spacing from neighboring breakpoints.
    """
    if not breakpoints or len(breakpoints) < 2:
        return breakpoints
    if max_length <= 0:
        return breakpoints
    if min_length < 0:
        min_length = 0.0

    mandatory_set = set(float(x) for x in (mandatory_breakpoints or []))
    out: List[float] = list(breakpoints)

    # Safety cap to avoid infinite loops if snapping can't make progress
    max_insertions = 5000
    insertions = 0
    i = 0
    while i < len(out) - 1:
        start = float(out[i])
        end = float(out[i + 1])
        seg_len = end - start

        if seg_len <= max_length + 1e-12:
            i += 1
            continue

        if _is_gap_segment(start, end, gap_segments):
            i += 1
            continue

        # Choose a target split point and snap it to an existing x value.
        target = start + max_length
        lo = start + min_length
        hi = end - min_length
        snapped = _snap_to_existing_x(sorted_x, target, lo, hi)
        if snapped is None:
            log(
                f"[WARN] Could not split overlong segment [{start:.3f}, {end:.3f}] "
                f"(len={seg_len:.3f}) due to sparse data / min_length constraints."
            )
            i += 1
            continue

        # Avoid inserting duplicates or mandatory-conflict weirdness.
        if snapped in mandatory_set:
            # If snapped point is mandatory, it's already expected as a boundary.
            if snapped not in out:
                out.append(snapped)
                out = sorted(set(out))
            i += 1
            continue

        if snapped <= start + 1e-12 or snapped >= end - 1e-12:
            log(
                f"[WARN] Split candidate collapsed to endpoints for segment [{start:.3f}, {end:.3f}]."
            )
            i += 1
            continue

        if snapped in out:
            i += 1
            continue

        out.append(snapped)
        out = sorted(set(out))
        insertions += 1
        if insertions >= max_insertions:
            log("[WARN] Max-length enforcement hit insertion cap; stopping split loop.")
            break

        # Do not increment i: we want to re-check the newly created sub-segment.

    return out


class PeltSegmentationMethod(AnalysisMethodBase):
    @property
    def method_name(self) -> str:
        return "PELT Segmentation (ruptures)"

    @property
    def method_key(self) -> str:
        return "pelt_segmentation"

    def run_analysis(
        self,
        data: Any,
        route_id: str,
        x_column: str,
        y_column: str,
        gap_threshold: float,
        **kwargs,
    ) -> AnalysisResult:
        if not hasattr(data, "route_data"):
            raise TypeError(
                "PeltSegmentationMethod.run_analysis expects a RouteAnalysis object (with .route_data). "
                "Use analyze_route_gaps(...) to build one from a DataFrame."
            )

        start_time = time.time()

        method_config = get_optimization_method(self.method_key)
        param_defaults = {param.name: param.default_value for param in method_config.parameters}

        model = kwargs.get("model", param_defaults["model"])
        penalty = float(kwargs.get("penalty", param_defaults["penalty"]))
        jump = int(kwargs.get("jump", param_defaults["jump"]))
        smooth_window_miles = kwargs.get("smooth_window_miles", param_defaults["smooth_window_miles"])
        smoothing_method = kwargs.get("smoothing_method", param_defaults["smoothing_method"])
        # Segment constraints use framework-style names for consistency
        min_length = float(kwargs.get("min_length", param_defaults["min_length"]))
        max_length = float(kwargs.get("max_length", param_defaults["max_length"]))
        enable_diagnostic_output = bool(
            kwargs.get("enable_diagnostic_output", param_defaults["enable_diagnostic_output"])
        )

        log_callback = kwargs.get("log_callback", None)
        stop_callback = kwargs.get("stop_callback", None)

        def log(message: str) -> None:
            if log_callback:
                log_callback(message)

        if penalty <= 0:
            raise ValueError(f"penalty must be > 0 (got {penalty})")
        if jump <= 0:
            raise ValueError(f"jump must be >= 1 (got {jump})")
        if min_length < 0:
            raise ValueError(f"min_length must be >= 0 (got {min_length})")
        if max_length < 0:
            raise ValueError(f"max_length must be >= 0 (got {max_length})")
        if max_length > 0 and max_length < min_length:
            raise ValueError(
                f"max_length must be >= min_length when max_length > 0 (got min_length={min_length}, max_length={max_length})"
            )
        if smooth_window_miles is not None and float(smooth_window_miles) < 0:
            raise ValueError(
                f"smooth_window_miles must be >= 0 or None (got {smooth_window_miles})"
            )

        try:
            import ruptures as rpt  # lazy dependency
        except Exception as e:
            import sys
            raise ImportError(
                "The 'ruptures' package is required for PELT segmentation. "
                f"Current interpreter: {sys.executable}. "
                "Install it with: python -m pip install ruptures "
                "(or more explicitly: <that interpreter> -m pip install ruptures)."
            ) from e

        route_analysis = data
        route_data = route_analysis.route_data
        if x_column not in route_data.columns:
            raise ValueError(
                f"x_column={x_column!r} not found in RouteAnalysis.route_data columns: {list(route_data.columns)!r}"
            )
        if y_column not in route_data.columns:
            raise ValueError(
                f"y_column={y_column!r} not found in RouteAnalysis.route_data columns: {list(route_data.columns)!r}"
            )

        x_values = route_data[x_column].to_numpy(dtype=float)
        y_values = route_data[y_column].to_numpy(dtype=float)
        mandatory_breakpoints = sorted(route_analysis.mandatory_breakpoints)

        total_sections = max(0, len(mandatory_breakpoints) - 1)
        # Throttle progress logs to avoid spamming when there are many short sections.
        # Aim for ~20 updates, but always at least one per section for very small counts.
        progress_every = 1
        if total_sections > 0:
            progress_every = max(1, total_sections // 20)
        last_progress_ts = 0.0

        log(f"Initializing PELT segmentation for route {route_id}...")
        if smooth_window_miles is None:
            log("Smoothing: OFF")
        else:
            log(f"Smoothing: {smoothing_method} ({float(smooth_window_miles):.3f} miles)")

        internal_breakpoints: List[float] = []
        section_diagnostics: List[Dict[str, Any]] = []
        eps = 1e-9

        for section_idx, (section_start, section_end) in enumerate(
            zip(mandatory_breakpoints, mandatory_breakpoints[1:])
        ):
            if stop_callback and stop_callback():
                log("[STOPPED] PELT segmentation stopped by user.")
                break

            # Progress update (throttled by section count and time)
            if total_sections > 0:
                now = time.time()
                if (section_idx % progress_every == 0) or (now - last_progress_ts >= 3.0):
                    pct = int(round(100.0 * float(section_idx) / float(total_sections)))
                    log(
                        f"PELT progress: section {section_idx + 1}/{total_sections} ({pct}%) "
                        f"[{float(section_start):.3f}, {float(section_end):.3f}]"
                    )
                    last_progress_ts = now

            section_mask = (x_values >= section_start) & (x_values <= section_end)
            section_x = x_values[section_mask]
            section_y = y_values[section_mask]

            if len(section_x) < 3:
                continue

            dx = _estimate_spacing_miles(section_x)
            if dx <= 0:
                dx = float(section_end - section_start) / float(max(1, len(section_x) - 1))
            if dx <= 0:
                continue

            if smooth_window_miles is None or float(smooth_window_miles) <= 0:
                section_signal = section_y
                smooth_window_pts = 1
            else:
                smooth_window_pts = int(max(1, round(float(smooth_window_miles) / dx)))
                section_signal = _rolling_smooth(section_y, smooth_window_pts, str(smoothing_method))

            min_size = int(max(2, round(float(min_length) / dx)))

            # If the section is too short to satisfy the minimum segment size constraint,
            # do not call the library (it may raise depending on model/parameters).
            # We still keep mandatory breakpoints, so skipping is safe.
            if len(section_signal) < (2 * min_size):
                if enable_diagnostic_output:
                    section_diagnostics.append(
                        {
                            "section_index": int(section_idx),
                            "section_bounds": [float(section_start), float(section_end)],
                            "datapoints": int(len(section_signal)),
                            "estimated_spacing": float(dx),
                            "smooth_window_pts": int(smooth_window_pts),
                            "min_size_pts": int(min_size),
                            "jump": int(jump),
                            "penalty": float(penalty),
                            "model": str(model),
                            "internal_breakpoints": [],
                            "skipped": True,
                            "skip_reason": "section too short for min_size",
                        }
                    )
                continue

            try:
                # This call can be the slow part; log once per section (already throttled above)
                # so users can see the app is actively working.
                algo = rpt.Pelt(model=str(model), min_size=min_size, jump=jump).fit(section_signal)
                bkpts = algo.predict(pen=penalty)
            except Exception as section_error:
                log(
                    f"[WARN] PELT failed on section {section_idx + 1} "
                    f"[{section_start:.3f}, {section_end:.3f}] with error: {section_error}"
                )
                if enable_diagnostic_output:
                    section_diagnostics.append(
                        {
                            "section_index": int(section_idx),
                            "section_bounds": [float(section_start), float(section_end)],
                            "datapoints": int(len(section_signal)),
                            "estimated_spacing": float(dx),
                            "smooth_window_pts": int(smooth_window_pts),
                            "min_size_pts": int(min_size),
                            "jump": int(jump),
                            "penalty": float(penalty),
                            "model": str(model),
                            "internal_breakpoints": [],
                            "skipped": True,
                            "skip_reason": f"error: {type(section_error).__name__}: {section_error}",
                        }
                    )
                continue

            # bkpts are end indices (exclusive) and include the final n
            section_internal = []
            n = len(section_signal)
            for b in bkpts:
                b = int(b)
                if b <= 0 or b >= n:
                    continue
                bp_mile = float(section_x[b])
                if (section_start + eps) < bp_mile < (section_end - eps):
                    section_internal.append(bp_mile)

            internal_breakpoints.extend(section_internal)

            if enable_diagnostic_output:
                section_diagnostics.append(
                    {
                        "section_index": int(section_idx),
                        "section_bounds": [float(section_start), float(section_end)],
                        "datapoints": int(len(section_signal)),
                        "estimated_spacing": float(dx),
                        "smooth_window_pts": int(smooth_window_pts),
                        "min_size_pts": int(min_size),
                        "jump": int(jump),
                        "penalty": float(penalty),
                        "model": str(model),
                        "internal_breakpoints": section_internal,
                    }
                )

        all_breakpoints = np.unique(
            np.array(list(mandatory_breakpoints) + internal_breakpoints, dtype=float)
        )
        all_breakpoints = np.sort(all_breakpoints)
        breakpoints_list = all_breakpoints.tolist()

        if total_sections > 0:
            log(f"PELT progress: completed {min(total_sections, section_idx + 1)}/{total_sections} sections (100%)")

        # Enforce max segment length via post-processing split (do not split gap segments).
        # This keeps the method aligned with the framework's min/max segment length constraints.
        breakpoints_list = _enforce_max_segment_length(
            breakpoints_list,
            np.sort(np.unique(x_values)),
            getattr(route_analysis, "gap_segments", []),
            mandatory_breakpoints,
            min_length=min_length,
            max_length=max_length,
            log=log,
        )

        segment_lengths = [
            breakpoints_list[i + 1] - breakpoints_list[i] for i in range(len(breakpoints_list) - 1)
        ]
        avg_excluding_gaps = average_length_excluding_gap_segments(
            breakpoints_list,
            getattr(route_analysis, "gap_segments", []),
        )

        diagnostics: Dict[str, Any] = {
            "algorithm": "PELT (ruptures)",
            "architecture": "segmented_processing",
        }
        if enable_diagnostic_output:
            diagnostics["section_details"] = section_diagnostics

        return AnalysisResult(
            method_name=self.method_name,
            method_key=self.method_key,
            route_id=route_id,
            all_solutions=[
                {
                    "chromosome": breakpoints_list,
                    "fitness": 0.0,
                    "avg_segment_length": float(avg_excluding_gaps),
                    "num_segments": int(max(0, len(breakpoints_list) - 1)),
                    "segmentation": {
                        "breakpoints": breakpoints_list,
                        "segment_count": int(len(segment_lengths)),
                        "segment_lengths": segment_lengths,
                        "total_length": (breakpoints_list[-1] - breakpoints_list[0])
                        if len(breakpoints_list) >= 2
                        else 0.0,
                        "average_segment_length": float(avg_excluding_gaps),
                        "segment_details": [],
                    },
                }
            ],
            mandatory_breakpoints=list(mandatory_breakpoints),
            optimization_stats=diagnostics,
            processing_time=time.time() - start_time,
            input_parameters={
                "model": str(model),
                "penalty": float(penalty),
                "jump": int(jump),
                "smooth_window_miles": smooth_window_miles,
                "smoothing_method": str(smoothing_method),
                "min_length": float(min_length),
                "max_length": float(max_length),
                "enable_diagnostic_output": bool(enable_diagnostic_output),
                "gap_threshold": float(gap_threshold),
            },
            data_summary={
                "total_data_points": int(len(route_analysis.route_data)),
                "data_range": {
                    "x_min": float(route_analysis.data_range.get("x_min")),
                    "x_max": float(route_analysis.data_range.get("x_max")),
                    "y_min": float(route_analysis.data_range.get("y_min")),
                    "y_max": float(route_analysis.data_range.get("y_max")),
                },
                "gap_analysis": {
                    "total_gaps": int(len(getattr(route_analysis, "gap_segments", []))),
                    "gap_segments": [
                        {"start": float(g[0]), "end": float(g[1]), "length": float(g[1] - g[0])}
                        for g in getattr(route_analysis, "gap_segments", [])
                    ],
                    "total_gap_length": float(
                        sum((g[1] - g[0]) for g in getattr(route_analysis, "gap_segments", []))
                    ),
                },
            },
        )
