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


class FakeRoot:
    def __init__(self):
        self._geometry = "800x600"

    def geometry(self, value=None):
        if value is None:
            return self._geometry
        self._geometry = value


def _make_minimal_app_for_params():
    app = SimpleNamespace()

    app.settings = {
        "files": {"data_file_path": "", "save_file_path": ""},
        "optimization": {
            "optimization_method": "multi",
            "custom_save_name": "highway_segmentation",
            "dynamic_parameters_by_method": {},
        },
        "ui_state": {},
    }

    app.root = FakeRoot()

    # FileManager expects these for filename-only display in the UI
    app.data_file = FakeVar("")
    app.save_file = FakeVar("")

    # Framework/global UI variables
    app.x_column = FakeVar("milepoint")
    app.y_column = FakeVar("structural_strength_ind")
    app.gap_threshold = FakeVar(0.5)
    app.route_column = FakeVar("None - treat as single route")
    app.selected_routes = []
    app.custom_save_name = FakeVar("highway_segmentation")

    # Method selection
    app.method_dropdown = SimpleNamespace(get=lambda: "Multi-Objective NSGA-II")
    app.optimization_method = "multi"

    # Callbacks
    app.on_method_change = Mock()

    return app


@pytest.mark.unit
def test_save_parameters_writes_structured_json(tmp_path, monkeypatch):
    app = _make_minimal_app_for_params()

    # Simulate persistence of active method params before saving
    def _persist(method_key):
        app.settings.setdefault("optimization", {}).setdefault("dynamic_parameters_by_method", {})
        app.settings["optimization"]["dynamic_parameters_by_method"][method_key] = {
            "population_size": 111,
            "num_generations": 22,
        }

    app._persist_dynamic_parameters_for_method = _persist

    fm = FileManager(app)
    fm.set_data_file_path("C:/data.csv")
    fm.set_save_file_path("C:/out")

    out_file = tmp_path / "params.json"

    # Mock dialog + messagebox
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda *a, **k: str(out_file))
    showinfo = Mock()
    showerror = Mock()
    monkeypatch.setattr("tkinter.messagebox.showinfo", showinfo)
    monkeypatch.setattr("tkinter.messagebox.showerror", showerror)

    fm.save_parameters()

    assert showerror.call_count == 0
    assert out_file.exists()

    data = json.loads(out_file.read_text(encoding="utf-8"))

    assert set(data.keys()) == {"files", "ui_state", "optimization"}
    assert data["files"]["data_file_path"] == "C:/data.csv"
    assert data["files"]["save_file_path"] == "C:/out"

    assert data["optimization"]["optimization_method"] == "multi"
    # FileManager derives this from the save path
    assert data["optimization"]["custom_save_name"] == "out"

    store = data["optimization"]["dynamic_parameters_by_method"]
    assert store["multi"]["population_size"] == 111
    assert store["multi"]["num_generations"] == 22


@pytest.mark.unit
def test_load_parameters_structured_restores_state(tmp_path, monkeypatch):
    app = _make_minimal_app_for_params()

    config = {
        "files": {"data_file_path": "C:/in.csv", "save_file_path": "C:/out"},
        "ui_state": {
            "x_column": "milepoint",
            "y_column": "structural_strength_ind",
            "gap_threshold": 0.25,
            "route_column": "route",
            "selected_routes": ["US-35"],
            "window_geometry": "900x700",
        },
        "optimization": {
            "optimization_method": "multi",
            "custom_save_name": "my_run",
            "dynamic_parameters_by_method": {"multi": {"population_size": 200}},
        },
    }

    in_file = tmp_path / "params.json"
    in_file.write_text(json.dumps(config), encoding="utf-8")

    fm = FileManager(app)

    # Avoid file I/O inside FileManager while still asserting calls
    fm.set_data_file_path = Mock()
    fm.load_csv_columns = Mock()
    fm.set_save_file_path = Mock()

    monkeypatch.setattr("tkinter.filedialog.askopenfilename", lambda *a, **k: str(in_file))
    showinfo = Mock()
    showerror = Mock()
    monkeypatch.setattr("tkinter.messagebox.showinfo", showinfo)
    monkeypatch.setattr("tkinter.messagebox.showerror", showerror)

    fm.load_parameters()

    assert showerror.call_count == 0
    fm.set_data_file_path.assert_called_once_with("C:/in.csv")
    fm.load_csv_columns.assert_called_once()
    fm.set_save_file_path.assert_called_once_with("C:/out")

    assert app.x_column.get() == "milepoint"
    assert app.y_column.get() == "structural_strength_ind"
    assert app.gap_threshold.get() == 0.25
    assert app.route_column.get() == "route"
    assert app.selected_routes == ["US-35"]
    assert app.root.geometry() == "900x700"

    assert app.custom_save_name.get() == "my_run"
    assert app.settings["optimization"]["dynamic_parameters_by_method"]["multi"]["population_size"] == 200
    assert app.on_method_change.call_count == 1


@pytest.mark.unit
def test_load_parameters_legacy_flat_is_rejected(tmp_path, monkeypatch):
    app = _make_minimal_app_for_params()

    # Provide a UIBuilder stub so ParameterManager can refresh without error
    app.ui_builder = SimpleNamespace(refresh_dynamic_params_grid=Mock())

    # Use the real ParameterManager mapping logic (filters by method config)
    app.parameter_manager = ParameterManager(app)

    legacy = {
        "optimization_method": "multi",
        "custom_save_name": "legacy_run",
        "x_column": "milepoint",
        "y_column": "structural_strength_ind",
        "gap_threshold": 0.5,
        "population_size": 123,
        "num_generations": 77,
        "crossover_rate": 0.8,
        "mutation_rate": 0.05,
        "cache_clear_interval": 50,
    }

    in_file = tmp_path / "legacy.json"
    in_file.write_text(json.dumps(legacy), encoding="utf-8")

    fm = FileManager(app)

    monkeypatch.setattr("tkinter.filedialog.askopenfilename", lambda *a, **k: str(in_file))
    showinfo = Mock()
    showerror = Mock()
    monkeypatch.setattr("tkinter.messagebox.showinfo", showinfo)
    monkeypatch.setattr("tkinter.messagebox.showerror", showerror)

    fm.load_parameters()

    # Legacy flat parameter files are no longer supported.
    assert showerror.call_count == 1
    assert showinfo.call_count == 0
