from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from settings_manager import SettingsManager
from gui_main import HighwaySegmentationGUI


class FakeVar:
    def __init__(self, value=None):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class FakeRoot:
    def geometry(self):
        return "800x600"


@pytest.mark.unit
def test_settings_manager_defaults_do_not_include_legacy_globals():
    sm = SettingsManager()
    opt = sm.default_settings.get("optimization", {})

    forbidden = {
        "population_size",
        "num_generations",
        "mutation_rate",
        "crossover_rate",
        "elite_ratio",
        "target_avg_length",
        "penalty_weight",
        "length_tolerance",
        "cache_clear_interval",
        "enable_performance_stats",
        "min_length",
        "max_length",
        "gap_threshold",
        "alpha",
        "method",
        "use_segment_length",
        "min_segment_datapoints",
        "max_segments",
        "min_section_difference",
    }

    assert forbidden.isdisjoint(set(opt.keys()))


@pytest.mark.unit
def test_gui_autosave_prunes_legacy_optimization_keys():
    gui = SimpleNamespace()

    # Minimal settings structure with legacy keys present
    gui.settings = {
        "files": {"data_file_path": "", "save_file_path": ""},
        "optimization": {
            "optimization_method": "multi",
            "custom_save_name": "old",
            "dynamic_parameters_by_method": {"multi": {"population_size": 100}},
            "population_size": 999,
            "num_generations": 999,
            "mutation_rate": 0.9,
            "crossover_rate": 0.9,
            "min_length": 0.1,
            "gap_threshold": 0.1,
            "alpha": 0.01,
        },
        "ui_state": {"window_geometry": "", "x_column": "", "y_column": ""},
    }

    gui.file_manager = SimpleNamespace(
        get_data_file_path=lambda: "C:/in.csv",
        get_save_file_path=lambda: "C:/out",
    )

    gui.settings_manager = SimpleNamespace(save_settings=Mock(return_value=True))
    gui.root = FakeRoot()

    gui.custom_save_name = FakeVar("new")
    gui.x_column = FakeVar("x")
    gui.y_column = FakeVar("y")
    gui.gap_threshold = FakeVar(0.5)
    gui.route_column = FakeVar("route")
    gui.selected_routes = ["R1"]

    # Method key resolution
    gui.ui_builder = SimpleNamespace(method_dropdown=SimpleNamespace(get=lambda: "Multi-Objective NSGA-II"))
    gui._migrate_method_key = lambda k: k
    gui._get_selected_method_key_safe = lambda: "multi"

    # Called by _save_current_settings; keep it harmless
    gui._persist_dynamic_parameters_for_method = Mock()

    # Run the real method implementation on our duck-typed object
    HighwaySegmentationGUI._save_current_settings(gui)

    opt = gui.settings["optimization"]

    assert opt.get("optimization_method") == "multi"
    assert opt.get("custom_save_name") == "new"
    assert "dynamic_parameters_by_method" in opt

    # Legacy keys should be removed
    assert "population_size" not in opt
    assert "num_generations" not in opt
    assert "mutation_rate" not in opt
    assert "crossover_rate" not in opt
    assert "min_length" not in opt
    assert "gap_threshold" not in opt
    assert "alpha" not in opt
