import pytest

import route_filter_dialog


pytestmark = pytest.mark.ui


def test_route_filter_dialog_returns_selected_routes(monkeypatch):
    expected = ["R1", "R2"]

    def fake_ask(parent, *, title, items, selected=None, prompt=None, width=0, height=0):
        assert title == "Filter Routes"
        assert "R1" in list(items)
        return expected

    monkeypatch.setattr(route_filter_dialog.MultiSelectDialog, "ask", staticmethod(fake_ask))

    dlg = route_filter_dialog.RouteFilterDialog(object(), ["R1", "R2", "R3"], ["R3"])
    assert dlg.show() == expected


def test_route_filter_dialog_cancel_returns_none(monkeypatch):
    def fake_ask(*_args, **_kwargs):
        return None

    monkeypatch.setattr(route_filter_dialog.MultiSelectDialog, "ask", staticmethod(fake_ask))

    dlg = route_filter_dialog.RouteFilterDialog(object(), ["R1"], ["R1"])
    assert dlg.show() is None
