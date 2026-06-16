"""Unit tests for SingleObjectiveMethod."""

import os
import sys
import numpy as np
import pandas as pd
import pytest

current_file_dir = os.path.dirname(__file__)
tests_dir = os.path.dirname(current_file_dir)
project_root = os.path.dirname(tests_dir)
src_path = os.path.join(project_root, "src")

if src_path not in sys.path:
    sys.path.insert(0, src_path)

from analysis.methods.single_objective import SingleObjectiveMethod
from data_loader import analyze_route_gaps

METHOD = SingleObjectiveMethod()

X_COL = "milepoint"
Y_COL = "value"

_FAST_PARAMS = dict(
    min_length=0.5,
    max_length=5.0,
    population_size=5,
    num_generations=3,
)


def _route(n=30, seed=42):
    rng = np.random.default_rng(seed)
    x = np.linspace(0.0, 10.0, n)
    y = 3.0 + rng.normal(0, 0.3, n)
    df = pd.DataFrame({X_COL: x, Y_COL: y})
    return analyze_route_gaps(df, X_COL, Y_COL, route_id="TEST", gap_threshold=2.0)


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_run_analysis_returns_valid_result():
    ra = _route()
    result = METHOD.run_analysis(ra, "TEST", X_COL, Y_COL, 2.0, **_FAST_PARAMS)

    assert result.method_key == "single"
    assert result.route_id == "TEST"
    assert len(result.all_solutions) > 0


# ---------------------------------------------------------------------------
# Segment count consistency (6.3)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_best_solution_segment_count_consistent():
    """segment_count == len(chromosome) - 1 for the primary solution."""
    ra = _route()
    result = METHOD.run_analysis(ra, "TEST", X_COL, Y_COL, 2.0, **_FAST_PARAMS)

    best = result.all_solutions[0]
    chrom = best["chromosome"]
    assert best["segment_count"] == len(chrom) - 1, (
        f"Best solution: segment_count={best['segment_count']} but "
        f"len(chromosome)-1={len(chrom)-1}; chromosome={chrom}"
    )


@pytest.mark.unit
def test_secondary_solutions_segment_count_consistent():
    """segment_count == len(chromosome) - 1 for every secondary solution."""
    ra = _route()
    result = METHOD.run_analysis(ra, "TEST", X_COL, Y_COL, 2.0, **_FAST_PARAMS)

    for i, sol in enumerate(result.all_solutions[1:], start=1):
        chrom = sol["chromosome"]
        assert sol["segment_count"] == len(chrom) - 1, (
            f"Secondary solution #{i}: segment_count={sol['segment_count']} but "
            f"len(chromosome)-1={len(chrom)-1}; chromosome={chrom}"
        )
