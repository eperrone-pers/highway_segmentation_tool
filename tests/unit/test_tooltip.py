"""Unit tests for tooltip.py.

Uses mocked Tkinter widgets so no display is required.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestParameterTreeTooltipBindings:
    def test_binds_motion_and_leave_on_construction(self):
        from tooltip import ParameterTreeTooltip

        tree = MagicMock()
        ParameterTreeTooltip(tree, lambda: {})

        bound_events = [c.args[0] for c in tree.bind.call_args_list]
        assert "<Motion>" in bound_events
        assert "<Leave>" in bound_events

    def test_uses_add_plus_to_preserve_existing_bindings(self):
        from tooltip import ParameterTreeTooltip

        tree = MagicMock()
        ParameterTreeTooltip(tree, lambda: {})

        for c in tree.bind.call_args_list:
            assert c.kwargs.get("add") == "+" or (len(c.args) >= 3 and c.args[2] == "+")


class TestParameterTreeTooltipMotion:
    def _make_event(self, y=10, x_root=100, y_root=200):
        event = MagicMock()
        event.y = y
        event.x_root = x_root
        event.y_root = y_root
        return event

    def test_unknown_iid_does_not_schedule_tooltip(self):
        from tooltip import ParameterTreeTooltip

        tree = MagicMock()
        tree.identify_row.return_value = "unknown_param"

        tip = ParameterTreeTooltip(tree, lambda: {})
        tip._on_motion(self._make_event())

        tree.after.assert_not_called()

    def test_known_iid_schedules_tooltip_after_delay(self):
        from tooltip import ParameterTreeTooltip, _DELAY_MS

        tree = MagicMock()
        tree.identify_row.return_value = "min_length"

        param_def = MagicMock()
        param_def.description = "Minimum segment length in miles"

        tip = ParameterTreeTooltip(tree, lambda: {"min_length": param_def})
        tip._on_motion(self._make_event())

        tree.after.assert_called_once()
        assert tree.after.call_args.args[0] == _DELAY_MS

    def test_same_iid_twice_does_not_reschedule(self):
        from tooltip import ParameterTreeTooltip

        tree = MagicMock()
        tree.identify_row.return_value = "min_length"

        param_def = MagicMock()
        param_def.description = "Min length"

        tip = ParameterTreeTooltip(tree, lambda: {"min_length": param_def})
        tip._current_iid = "min_length"  # already on this row

        tip._on_motion(self._make_event())

        tree.after.assert_not_called()

    def test_moving_to_new_iid_cancels_previous_pending(self):
        from tooltip import ParameterTreeTooltip

        tree = MagicMock()
        tree.identify_row.return_value = "max_length"

        param_def = MagicMock()
        param_def.description = "Max length"

        tip = ParameterTreeTooltip(tree, lambda: {"max_length": param_def})
        tip._current_iid = "min_length"
        tip._after_id = "pending-id"

        tip._on_motion(self._make_event())

        tree.after_cancel.assert_called_once_with("pending-id")

    def test_description_read_from_param_def(self):
        from tooltip import ParameterTreeTooltip

        tree = MagicMock()
        tree.identify_row.return_value = "alpha"

        param_def = MagicMock()
        param_def.description = "Significance level for the statistical test"

        captured = {}

        def fake_after(_delay, fn):
            captured["fn"] = fn
            return "after-id"

        tree.after.side_effect = fake_after

        tip = ParameterTreeTooltip(tree, lambda: {"alpha": param_def})
        tip._on_motion(self._make_event())

        assert "fn" in captured


class TestParameterTreeTooltipLeave:
    def test_leave_resets_current_iid(self):
        from tooltip import ParameterTreeTooltip

        tree = MagicMock()
        tip = ParameterTreeTooltip(tree, lambda: {})
        tip._current_iid = "some_param"

        tip._on_leave(MagicMock())

        assert tip._current_iid is None

    def test_leave_cancels_pending_after(self):
        from tooltip import ParameterTreeTooltip

        tree = MagicMock()
        tip = ParameterTreeTooltip(tree, lambda: {})
        tip._after_id = "pending-id"

        tip._on_leave(MagicMock())

        tree.after_cancel.assert_called_once_with("pending-id")

    def test_leave_clears_after_id(self):
        from tooltip import ParameterTreeTooltip

        tree = MagicMock()
        tip = ParameterTreeTooltip(tree, lambda: {})
        tip._after_id = "pending-id"

        tip._on_leave(MagicMock())

        assert tip._after_id is None


class TestAttachTooltip:
    def test_binds_enter_and_leave(self):
        from tooltip import attach_tooltip

        widget = MagicMock()
        attach_tooltip(widget, "Test description")

        bound_events = [c.args[0] for c in widget.bind.call_args_list]
        assert "<Enter>" in bound_events
        assert "<Leave>" in bound_events

    def test_uses_add_plus_to_preserve_existing_bindings(self):
        from tooltip import attach_tooltip

        widget = MagicMock()
        attach_tooltip(widget, "Test")

        for c in widget.bind.call_args_list:
            assert c.kwargs.get("add") == "+" or (len(c.args) >= 3 and c.args[2] == "+")

    def test_enter_schedules_show_after_delay(self):
        from tooltip import attach_tooltip, _DELAY_MS

        widget = MagicMock()
        attach_tooltip(widget, "Some tooltip text")

        enter_handler = next(
            c.args[1] for c in widget.bind.call_args_list if c.args[0] == "<Enter>"
        )

        event = MagicMock()
        event.x_root = 50
        event.y_root = 100
        enter_handler(event)

        widget.after.assert_called_once()
        assert widget.after.call_args.args[0] == _DELAY_MS

    def test_leave_cancels_pending(self):
        from tooltip import attach_tooltip

        widget = MagicMock()
        widget.after.return_value = "after-id"
        attach_tooltip(widget, "Some text")

        enter_handler = next(
            c.args[1] for c in widget.bind.call_args_list if c.args[0] == "<Enter>"
        )
        leave_handler = next(
            c.args[1] for c in widget.bind.call_args_list if c.args[0] == "<Leave>"
        )

        event = MagicMock()
        event.x_root = 50
        event.y_root = 100
        enter_handler(event)
        leave_handler(MagicMock())

        widget.after_cancel.assert_called_once_with("after-id")
