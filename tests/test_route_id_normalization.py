import sys
from pathlib import Path
from unittest.mock import Mock

import pandas as pd

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from optimization_controller import OptimizationController


def test_numeric_route_ids_match_string_selection(monkeypatch):
    """Ensure numeric route IDs in data still match UI string selections."""

    app = Mock()

    # Minimum required app surface for _run_optimization_worker up to route preparation
    app.parameter_manager = Mock()
    app.parameter_manager.get_optimization_parameters.return_value = {
        "optimization_method": "single",
        # These may be absent for some methods, but worker reads them via .get()
        "min_length": None,
        "max_length": None,
    }

    app.gap_threshold = Mock()
    app.gap_threshold.get.return_value = 0.1

    app.route_column = Mock()
    app.route_column.get.return_value = "ROUTE_ID"

    app.x_column = Mock()
    app.x_column.get.return_value = "OFFSET_FROM"

    app.y_column = Mock()
    app.y_column.get.return_value = "NM_AVG_IRI"

    app.file_manager = Mock()
    app.file_manager.get_data_file_path.return_value = "NMI40 Segmentation Test.csv"

    app.stop_requested = False

    # Selected routes from UI are strings
    app.selected_routes = ["268296608"]

    # But the dataframe may have numeric route IDs
    route_df = pd.DataFrame(
        {
            "OFFSET_FROM": [0.0, 0.1, 0.2, 0.0],
            "NM_AVG_IRI": [111.0, 116.0, 49.0, 10.0],
            "ROUTE_ID": [268296608, 268296608, 268296608, 999],
        }
    )
    app.data = Mock()
    app.data.route_data = route_df

    # Logging + root.after used in finally
    app.log_message = Mock()
    app.root = Mock()
    app.root.after = Mock()

    controller = OptimizationController(app)

    def _fake_prepare_multi_route_analyses(
        data,
        route_column,
        routes_to_process,
        x_column,
        y_column,
        gap_threshold,
        _is_single_route_mode,
    ):
        assert routes_to_process == ["268296608"]
        return []  # Stop worker early (no heavy analysis)

    monkeypatch.setattr(controller, "_prepare_multi_route_analyses", _fake_prepare_multi_route_analyses)

    controller._run_optimization_worker()

    # Should not have started with 0 routes
    logged_messages = [args[0] for (args, kwargs) in app.log_message.call_args_list]
    assert any("Starting optimization for 1 route(s)" in m for m in logged_messages)
    assert any("Processing single route: 268296608" in m for m in logged_messages)
