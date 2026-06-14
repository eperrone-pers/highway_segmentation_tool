"""Tests for the OptimizationHandler Protocol and lifecycle hook wiring.

Verifies that:
- FakeApp satisfies the OptimizationHandler protocol structurally.
- OptimizationController calls the correct lifecycle hooks at the right moments.
- State flags (is_running, stop_requested) are set correctly before/after hooks.
"""

from unittest.mock import MagicMock, patch

import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from optimization_handler import OptimizationHandler
from optimization_controller import OptimizationController
import gui_main as _gui_main_module


class FakeApp:
    """Minimal app stub that satisfies OptimizationHandler plus the non-protocol
    attributes OptimizationController reads from self.app."""

    # --- OptimizationHandler protocol ---
    is_running: bool = False
    stop_requested: bool = False

    def __init__(self):
        self.is_running = False
        self.stop_requested = False
        self.log_messages: list[str] = []
        self.errors: list[tuple] = []
        self.lifecycle_calls: list = []

        # Non-protocol attributes needed by the controller
        self.data = MagicMock()          # non-None → skip auto-load path
        self.file_manager = MagicMock()
        self.parameter_manager = MagicMock()
        self.parameter_manager.validate_and_show_errors.return_value = True
        self.root = MagicMock()
        self.root.after = MagicMock(side_effect=lambda _delay, fn: fn())
        self.optimization_method = "multi"
        self._active_method_key = "multi"
        self.settings = {}
        self.custom_save_name = MagicMock()
        self.custom_save_name.get.return_value = ""
        self.selected_routes = []
        self.route_column = MagicMock()
        self.route_column.get.return_value = "(none)"
        self.x_column = MagicMock()
        self.x_column.get.return_value = "x"
        self.y_column = MagicMock()
        self.y_column.get.return_value = "y"
        self.gap_threshold = MagicMock()
        self.gap_threshold.get.return_value = 0.5
        self.must_break_columns = []
        self.secondary_break_columns = []
        self.pregap_preprocess_panel = None
        self.primary_preprocess_panel = None
        self.secondary_preprocess_panel = None

    # --- Protocol methods ---

    def log_message(self, message: str) -> None:
        self.log_messages.append(message)

    def handle_error(self, title, exc=None, severity="error", show_messagebox=True) -> None:
        self.errors.append((title, exc, severity))

    def on_optimization_started(self) -> None:
        self.lifecycle_calls.append("started")

    def on_stop_requested(self) -> None:
        self.lifecycle_calls.append("stop_requested")

    def on_optimization_finished(self, stopped_early: bool) -> None:
        self.lifecycle_calls.append(("finished", stopped_early))


# ---------------------------------------------------------------------------
# Protocol structural checks
# ---------------------------------------------------------------------------

def test_fake_app_satisfies_protocol():
    """FakeApp must be recognised as an OptimizationHandler at runtime."""
    assert isinstance(FakeApp(), OptimizationHandler)


_REQUIRED_PROTOCOL_METHODS = [
    "log_message",
    "handle_error",
    "on_optimization_started",
    "on_stop_requested",
    "on_optimization_finished",
]


@pytest.mark.parametrize("method_name", _REQUIRED_PROTOCOL_METHODS)
def test_gui_class_defines_required_protocol_methods(method_name):
    """HighwaySegmentationGUI must define every method in OptimizationHandler.

    Checked at class level so no Tkinter display is required.
    """
    gui_cls = _gui_main_module.HighwaySegmentationGUI
    assert hasattr(gui_cls, method_name), (
        f"HighwaySegmentationGUI is missing protocol method '{method_name}'"
    )


# ---------------------------------------------------------------------------
# Lifecycle hook: on_optimization_started
# ---------------------------------------------------------------------------

@patch("optimization_controller.threading.Thread")
def test_start_optimization_calls_on_optimization_started(mock_thread_cls):
    """on_optimization_started() must be called once when start_optimization() fires."""
    mock_thread_cls.return_value = MagicMock()

    app = FakeApp()
    ctrl = OptimizationController(app)
    ctrl.start_optimization()

    assert "started" in app.lifecycle_calls
    assert app.is_running is True
    assert app.stop_requested is False


@patch("optimization_controller.threading.Thread")
def test_start_optimization_sets_flags_before_hook(mock_thread_cls):
    """is_running and stop_requested must be set before on_optimization_started is called."""
    states_at_hook = {}

    def capture_state():
        states_at_hook["is_running"] = app.is_running
        states_at_hook["stop_requested"] = app.stop_requested

    mock_thread_cls.return_value = MagicMock()
    app = FakeApp()
    app.on_optimization_started = capture_state  # type: ignore[method-assign]

    ctrl = OptimizationController(app)
    ctrl.start_optimization()

    assert states_at_hook["is_running"] is True
    assert states_at_hook["stop_requested"] is False


@patch("optimization_controller.threading.Thread")
def test_start_optimization_does_not_start_when_already_running(mock_thread_cls):
    """start_optimization() must be a no-op when is_running is already True."""
    mock_thread_cls.return_value = MagicMock()
    app = FakeApp()
    app.is_running = True

    ctrl = OptimizationController(app)
    ctrl.start_optimization()

    assert "started" not in app.lifecycle_calls
    assert mock_thread_cls.call_count == 0


# ---------------------------------------------------------------------------
# Lifecycle hook: on_stop_requested
# ---------------------------------------------------------------------------

def test_stop_optimization_calls_on_stop_requested():
    """on_stop_requested() must be called when stop_optimization() is invoked while running."""
    app = FakeApp()
    app.is_running = True

    ctrl = OptimizationController(app)
    ctrl.optimization_thread = MagicMock()
    ctrl.optimization_thread.is_alive.return_value = False

    ctrl.stop_optimization()

    assert "stop_requested" in app.lifecycle_calls
    assert app.stop_requested is True


def test_stop_optimization_noop_when_not_running():
    """stop_optimization() must be a no-op when is_running is False."""
    app = FakeApp()
    ctrl = OptimizationController(app)
    ctrl.stop_optimization()

    assert "stop_requested" not in app.lifecycle_calls


# ---------------------------------------------------------------------------
# Lifecycle hook: on_optimization_finished
# ---------------------------------------------------------------------------

def test_finalize_calls_on_optimization_finished_not_stopped():
    """_finalize_optimization(False) must call on_optimization_finished(False)."""
    app = FakeApp()
    app.is_running = True

    ctrl = OptimizationController(app)
    ctrl._finalize_optimization(stopped_early=False)

    assert ("finished", False) in app.lifecycle_calls
    assert app.is_running is False
    assert app.stop_requested is False


def test_finalize_calls_on_optimization_finished_stopped():
    """_finalize_optimization(True) must call on_optimization_finished(True)."""
    app = FakeApp()
    app.is_running = True

    ctrl = OptimizationController(app)
    ctrl._finalize_optimization(stopped_early=True)

    assert ("finished", True) in app.lifecycle_calls
    assert app.is_running is False


def test_finalize_clears_flags_before_hook():
    """is_running and stop_requested must be cleared before on_optimization_finished is called."""
    states_at_hook = {}

    def capture(stopped_early):
        states_at_hook["is_running"] = app.is_running
        states_at_hook["stop_requested"] = app.stop_requested
        states_at_hook["stopped_early"] = stopped_early

    app = FakeApp()
    app.is_running = True
    app.stop_requested = True
    app.on_optimization_finished = capture  # type: ignore[method-assign]

    ctrl = OptimizationController(app)
    ctrl._finalize_optimization(stopped_early=False)

    assert states_at_hook["is_running"] is False
    assert states_at_hook["stop_requested"] is False
