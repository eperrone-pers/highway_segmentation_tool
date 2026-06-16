"""Unit tests for DebFeasibilityConstrainedMethod internals."""

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

from analysis.methods.deb_feasibility_constrained import DebFeasibilityConstrainedMethod
from data_loader import analyze_route_gaps

METHOD = DebFeasibilityConstrainedMethod()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

X_COL = "milepoint"
Y_COL = "value"


def _route(n=30, seed=7):
    rng = np.random.default_rng(seed)
    x = np.linspace(0.0, 10.0, n)
    y = 3.0 + rng.normal(0, 0.3, n)
    df = pd.DataFrame({X_COL: x, Y_COL: y})
    return analyze_route_gaps(df, X_COL, Y_COL, route_id="TEST", gap_threshold=2.0)


# ---------------------------------------------------------------------------
# _deb_better
# ---------------------------------------------------------------------------


class TestDebBetter:
    """Verify all four branches of Deb's comparison rules."""

    def test_feasible_beats_infeasible(self):
        # Rule 1: feasible always dominates infeasible regardless of fitness
        assert DebFeasibilityConstrainedMethod._deb_better(True, 0.0, 0.1, False, 5.0, 99.9)

    def test_infeasible_loses_to_feasible(self):
        # Rule 1 (symmetric): infeasible never beats feasible
        assert not DebFeasibilityConstrainedMethod._deb_better(False, 5.0, 99.9, True, 0.0, 0.1)

    def test_both_feasible_higher_fitness_wins(self):
        # Rule 2: both feasible → compare objective (higher base_fitness wins)
        assert DebFeasibilityConstrainedMethod._deb_better(True, 0.0, 2.0, True, 0.0, 1.0)
        assert not DebFeasibilityConstrainedMethod._deb_better(True, 0.0, 1.0, True, 0.0, 2.0)

    def test_both_infeasible_lower_violation_wins(self):
        # Rule 3: both infeasible → prefer smaller violation
        assert DebFeasibilityConstrainedMethod._deb_better(False, 1.0, 5.0, False, 2.0, 5.0)
        assert not DebFeasibilityConstrainedMethod._deb_better(False, 2.0, 5.0, False, 1.0, 5.0)

    def test_both_infeasible_equal_violation_fitness_tiebreak(self):
        # Rule 3 tiebreak: equal violation → higher base_fitness wins
        assert DebFeasibilityConstrainedMethod._deb_better(False, 1.0, 2.0, False, 1.0, 1.0)
        assert not DebFeasibilityConstrainedMethod._deb_better(False, 1.0, 1.0, False, 1.0, 2.0)

    def test_equal_feasible_equal_fitness_returns_false(self):
        # Strictly better — equal is not better
        assert not DebFeasibilityConstrainedMethod._deb_better(True, 0.0, 1.0, True, 0.0, 1.0)


# ---------------------------------------------------------------------------
# _best_index_deb
# ---------------------------------------------------------------------------


class TestBestIndexDeb:
    def test_empty_returns_zero(self):
        assert DebFeasibilityConstrainedMethod._best_index_deb([], [], []) == 0

    def test_single_element_returns_zero(self):
        assert DebFeasibilityConstrainedMethod._best_index_deb([True], [0.0], [1.0]) == 0

    def test_feasible_beats_infeasible(self):
        # Index 0 infeasible, index 1 feasible → expect 1
        feasible = [False, True]
        violations = [3.0, 0.0]
        fitnesses = [10.0, 1.0]  # infeasible has higher raw fitness — should still lose
        assert DebFeasibilityConstrainedMethod._best_index_deb(feasible, violations, fitnesses) == 1

    def test_all_feasible_highest_fitness_wins(self):
        feasible = [True, True, True]
        violations = [0.0, 0.0, 0.0]
        fitnesses = [1.0, 5.0, 3.0]
        assert DebFeasibilityConstrainedMethod._best_index_deb(feasible, violations, fitnesses) == 1

    def test_all_infeasible_lowest_violation_wins(self):
        feasible = [False, False, False]
        violations = [3.0, 1.0, 2.0]
        fitnesses = [1.0, 1.0, 1.0]
        assert DebFeasibilityConstrainedMethod._best_index_deb(feasible, violations, fitnesses) == 1


# ---------------------------------------------------------------------------
# _elitist_selection_deb
# ---------------------------------------------------------------------------


class TestElitistSelectionDeb:
    def _make_pop(self, n, seed=1):
        rng = np.random.default_rng(seed)
        return [list(rng.random(3)) for _ in range(n)]

    def test_output_size_matches_population(self):
        pop = self._make_pop(6)
        fitnesses = [float(i) for i in range(6)]
        violations = [0.0] * 6
        offspring = self._make_pop(6, seed=2)
        off_fit = [float(i) for i in range(6)]
        off_viol = [0.0] * 6

        result = METHOD._elitist_selection_deb(
            pop, fitnesses, violations, offspring, off_fit, off_viol, elite_ratio=0.2
        )
        assert len(result) == len(pop)

    def test_feasible_preferred_over_infeasible(self):
        # Population: all infeasible with high fitness
        # Offspring: all feasible with low fitness
        # Expect offspring to dominate output
        pop = [[float(i)] for i in range(4)]
        fitnesses = [10.0] * 4
        violations = [5.0] * 4  # all infeasible

        offspring = [[float(i + 10)] for i in range(4)]
        off_fit = [0.5] * 4
        off_viol = [0.0] * 4  # all feasible

        result = METHOD._elitist_selection_deb(
            pop, fitnesses, violations, offspring, off_fit, off_viol, elite_ratio=0.5
        )
        # All selected should come from offspring (the feasible ones)
        offspring_set = {tuple(c) for c in offspring}
        assert all(tuple(c) in offspring_set for c in result)

    def test_elite_ratio_preserves_at_least_one(self):
        pop = self._make_pop(4)
        fitnesses = [1.0, 2.0, 3.0, 4.0]
        violations = [0.0] * 4
        offspring = self._make_pop(4, seed=3)
        off_fit = [0.1] * 4
        off_viol = [0.0] * 4

        # Very small elite_ratio — should still keep at least 1
        result = METHOD._elitist_selection_deb(
            pop, fitnesses, violations, offspring, off_fit, off_viol, elite_ratio=0.01
        )
        assert len(result) == 4


# ---------------------------------------------------------------------------
# run_analysis smoke test
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_run_analysis_returns_valid_result():
    """Smoke test: run_analysis completes and returns a well-formed AnalysisResult."""
    ra = _route(n=20)
    result = METHOD.run_analysis(
        ra,
        route_id="TEST",
        x_column=X_COL,
        y_column=Y_COL,
        gap_threshold=2.0,
        min_length=0.5,
        max_length=5.0,
        population_size=5,
        num_generations=3,
        target_avg_length=2.0,
    )

    assert result.method_key == "constrained_deb"
    assert result.route_id == "TEST"
    assert len(result.all_solutions) > 0


@pytest.mark.unit
def test_run_analysis_segment_count_consistency():
    """segment count in each solution must equal len(chromosome) - 1."""
    ra = _route(n=20)
    result = METHOD.run_analysis(
        ra,
        route_id="TEST",
        x_column=X_COL,
        y_column=Y_COL,
        gap_threshold=2.0,
        min_length=0.5,
        max_length=5.0,
        population_size=5,
        num_generations=3,
        target_avg_length=2.0,
    )

    for sol in result.all_solutions:
        chrom = sol["chromosome"]
        reported = sol["num_segments"]
        expected = len(chrom) - 1
        assert reported == expected, (
            f"num_segments={reported} but len(chromosome)-1={expected}; chromosome={chrom}"
        )
