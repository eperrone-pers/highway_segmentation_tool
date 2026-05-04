import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from file_manager import FileManager
from parameter_manager import ParameterManager


class FakeVar:
    def __init__(self, value=None):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


@pytest.mark.unit
def test_load_and_plot_results_restores_method_and_params(tmp_path, monkeypatch):
    # Minimal app harness
    app = SimpleNamespace()
    app._last_file_directory = ""
    app.log_message = Mock()

    app.settings = {
        "optimization": {
            "optimization_method": "single",
            "custom_save_name": "highway_segmentation",
            "dynamic_parameters_by_method": {},
        },
        "files": {},
        "ui_state": {},
    }

    app.x_column = FakeVar("")
    app.y_column = FakeVar("")
    app.route_column = FakeVar("")
    app.gap_threshold = FakeVar(0.5)
    app.custom_save_name = FakeVar("")
    app.selected_routes = []

    # Provide dropdown + UIBuilder hooks (best-effort)
    app.method_dropdown = SimpleNamespace(
        set=Mock(),
        get=Mock(return_value="Multi-Objective NSGA-II"),
    )
    app.ui_builder = SimpleNamespace(
        set_method_description=Mock(),
        refresh_dynamic_params_grid=Mock(),
    )

    app.optimization_method = "single"
    app._migrate_method_key = lambda k: k

    app.parameter_manager = ParameterManager(app)

    # Results JSON fixture
    results = {
        "analysis_metadata": {
            "analysis_method": "multi",
            "input_file_info": {
                "column_info": {"x_column": "BDFO", "y_column": "SCI", "route_column": "RDB"}
            },
        },
        "input_parameters": {
            "optimization_method_config": {"method_key": "multi", "display_name": "Multi-Objective NSGA-II"},
            "method_parameters": {
                "min_length": 1.1,
                "max_length": 2.2,
                "population_size": 123,
                "num_generations": 77,
                "crossover_rate": 0.8,
                "mutation_rate": 0.05,
                "gap_threshold": 0.25,
                "cache_clear_interval": 50,
            },
            "route_processing": {
                "x_column": "BDFO",
                "y_column": "SCI",
                "route_column": "RDB",
                "selected_routes": ["R1"],
                "custom_save_name": "prev_run",
            },
        },
        "route_results": [],
    }

    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps(results), encoding="utf-8")

    # Patch the exact module reference used by FileManager
    monkeypatch.setattr(
        "file_manager.filedialog.askopenfilename", lambda *_args, **_kwargs: str(results_path)
    )

    # Avoid actually opening windows
    monkeypatch.setattr(
        "visualization_ui.show_enhanced_visualization", lambda *_args, **_kwargs: None
    )

    fm = FileManager(app)
    fm.load_and_plot_results()

    assert app.optimization_method == "multi"
    assert app.gap_threshold.get() == 0.25
    assert app.custom_save_name.get() == "prev_run"

    store = app.settings["optimization"]["dynamic_parameters_by_method"]["multi"]
    assert store["population_size"] == 123
    assert store["num_generations"] == 77

    # UI refresh called
    assert app.ui_builder.refresh_dynamic_params_grid.call_count >= 1
