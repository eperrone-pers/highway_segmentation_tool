"""Unit tests for AnalysisResult.to_route_result_dict().

Covers the four method shapes (single-objective, multi-objective, constrained,
AASHTO CDA) and preprocessing log flattening.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from analysis.base import AnalysisResult


def _base_result(**overrides) -> AnalysisResult:
    """Build a minimal single-objective AnalysisResult for testing."""
    defaults = dict(
        method_name="Test Method",
        method_key="single",
        route_id="R1",
        all_solutions=[{
            "chromosome": [0.0, 1.0, 2.0],
            "fitness": 0.75,
            "objective_values": [0.75],
            "num_segments": 2,
            "avg_segment_length": 1.0,
        }],
        optimization_stats={},
        mandatory_breakpoints=[0.0, 2.0],
        processing_time=3.5,
        input_parameters={},
        data_summary={"data_points": 10},
    )
    defaults.update(overrides)
    return AnalysisResult(**defaults)


class TestToRouteResultDictCommonKeys:
    def test_returns_dict(self):
        result = _base_result().to_route_result_dict()
        assert isinstance(result, dict)

    def test_route_id_and_method_key(self):
        d = _base_result(route_id="ABC", method_key="single").to_route_result_dict()
        assert d["route_id"] == "ABC"
        assert d["method_key"] == "single"

    def test_best_fitness_scalar(self):
        d = _base_result().to_route_result_dict()
        assert d["best_fitness"] == 0.75

    def test_best_fitness_from_deviation_fitness(self):
        result = _base_result(all_solutions=[{
            "chromosome": [0.0, 1.0],
            "fitness": [0.5, 1.0],
            "deviation_fitness": 0.42,
            "objective_values": [0.5, 1.0],
        }])
        d = result.to_route_result_dict()
        assert d["best_fitness"] == 0.42

    def test_best_fitness_list_fallback(self):
        result = _base_result(all_solutions=[{
            "chromosome": [0.0, 1.0],
            "fitness": [0.3, 0.7],
            "objective_values": [0.3, 0.7],
        }])
        d = result.to_route_result_dict()
        assert d["best_fitness"] == 0.3

    def test_execution_time(self):
        d = _base_result(processing_time=9.1).to_route_result_dict()
        assert d["execution_time"] == 9.1

    def test_mandatory_breakpoints(self):
        d = _base_result(mandatory_breakpoints=[0.0, 5.0]).to_route_result_dict()
        assert d["mandatory_breakpoints"] == [0.0, 5.0]

    def test_best_segments_from_num_segments(self):
        d = _base_result().to_route_result_dict()
        assert d["best_segments"] == 2

    def test_best_segments_from_segments_list(self):
        result = _base_result(all_solutions=[{
            "chromosome": [0.0, 1.0, 2.0],
            "fitness": 0.5,
            "objective_values": [0.5],
            "segments": [{"start": 0.0, "end": 1.0}, {"start": 1.0, "end": 2.0}],
        }])
        d = result.to_route_result_dict()
        assert d["best_segments"] == 2

    def test_preprocessing_log_flattened(self):
        result = _base_result(preprocessing_modification_log=[
            [{"type": "removal", "index": 0}],
            [{"type": "cap", "index": 3}],
        ])
        d = result.to_route_result_dict()
        assert d["preprocessing_modification_log"] == [
            {"type": "removal", "index": 0},
            {"type": "cap", "index": 3},
        ]

    def test_preprocessing_log_empty(self):
        d = _base_result().to_route_result_dict()
        assert d["preprocessing_modification_log"] == []


class TestToRouteResultDictMultiObjective:
    def _multi_result(self) -> AnalysisResult:
        return AnalysisResult(
            method_name="NSGA-II",
            method_key="multi",
            route_id="R2",
            all_solutions=[
                {"chromosome": [0.0, 1.0], "fitness": [-0.5, 1.0], "objective_values": [-0.5, 1.0]},
                {"chromosome": [0.0, 2.0], "fitness": [-0.8, 2.0], "objective_values": [-0.8, 2.0]},
            ],
            optimization_stats={
                "pareto_front_size": 2,
                "best_deviation_fitness": -0.8,
                "best_segment_count": 1,
            },
            mandatory_breakpoints=[],
            processing_time=10.0,
            input_parameters={},
            data_summary={},
        )

    def test_pareto_keys_present(self):
        d = self._multi_result().to_route_result_dict()
        assert "all_solutions" in d
        assert "pareto_front_size" in d
        assert "best_deviation_fitness" in d
        assert "best_segment_count" in d

    def test_pareto_front_size(self):
        d = self._multi_result().to_route_result_dict()
        assert d["pareto_front_size"] == 2

    def test_all_solutions_length(self):
        d = self._multi_result().to_route_result_dict()
        assert len(d["all_solutions"]) == 2

    def test_single_objective_has_no_pareto_keys(self):
        d = _base_result(method_key="single").to_route_result_dict()
        assert "all_solutions" not in d
        assert "pareto_front_size" not in d


class TestToRouteResultDictConstrained:
    def _constrained_result(self) -> AnalysisResult:
        return _base_result(
            method_key="constrained",
            all_solutions=[{
                "chromosome": [0.0, 1.5, 3.0],
                "fitness": 0.6,
                "objective_values": [0.6],
                "num_segments": 2,
                "avg_segment_length": 1.5,
                "unconstrained_fitness": 0.9,
                "length_deviation": 0.3,
            }],
            input_parameters={
                "target_avg_length": 1.5,
                "length_tolerance": 0.2,
            },
        )

    def test_constrained_keys_present(self):
        d = self._constrained_result().to_route_result_dict()
        assert "best_unconstrained_fitness" in d
        assert "length_deviation" in d
        assert "target_avg_length" in d
        assert "tolerance" in d

    def test_constrained_values(self):
        d = self._constrained_result().to_route_result_dict()
        assert d["best_unconstrained_fitness"] == 0.9
        assert d["length_deviation"] == 0.3
        assert d["target_avg_length"] == 1.5
        assert d["tolerance"] == 0.2

    def test_single_has_no_constrained_keys(self):
        d = _base_result().to_route_result_dict()
        assert "best_unconstrained_fitness" not in d
        assert "length_deviation" not in d


class TestToRouteResultDictAashto:
    def _aashto_result(self) -> AnalysisResult:
        return _base_result(
            method_key="aashto_cda",
            all_solutions=[{
                "chromosome": [0.0, 1.0, 2.0],
                "fitness": 0.0,
                "objective_values": [0.0],
                "num_segments": 2,
                "avg_segment_length": 1.0,
            }],
            input_parameters={
                "alpha": 0.05,
                "method": 2,
                "use_segment_length": True,
            },
            optimization_stats={"some_stat": 42},
        )

    def test_aashto_keys_present(self):
        d = self._aashto_result().to_route_result_dict()
        assert "analysis_method" in d
        assert "statistical_parameters" in d
        assert "all_solutions" in d
        assert "method_stats" in d

    def test_aashto_analysis_method_label(self):
        d = self._aashto_result().to_route_result_dict()
        assert d["analysis_method"] == "AASHTO Enhanced CDA"

    def test_aashto_statistical_parameters(self):
        d = self._aashto_result().to_route_result_dict()
        sp = d["statistical_parameters"]
        assert sp["alpha"] == 0.05
        assert sp["error_estimation_method"] == 2
        assert sp["use_segment_length"] is True

    def test_single_has_no_aashto_keys(self):
        d = _base_result(method_key="single").to_route_result_dict()
        assert "analysis_method" not in d
        assert "statistical_parameters" not in d


class TestToRouteResultDictHistory:
    def test_fitness_history_included_when_present(self):
        result = _base_result(optimization_stats={
            "best_fitness_history": [0.9, 0.8, 0.75],
        })
        d = result.to_route_result_dict()
        assert d["fitness_history"] == [0.9, 0.8, 0.75]

    def test_length_history_included_when_present(self):
        result = _base_result(optimization_stats={
            "avg_length_history": [1.2, 1.1, 1.0],
        })
        d = result.to_route_result_dict()
        assert d["length_history"] == [1.2, 1.1, 1.0]

    def test_history_absent_when_not_in_stats(self):
        d = _base_result(optimization_stats={}).to_route_result_dict()
        assert "fitness_history" not in d
        assert "length_history" not in d
