import pytest

from config import MultiColumnSelectParameter


def test_multi_column_select_parameter_valid_list():
    p = MultiColumnSelectParameter(
        name="cols",
        display_name="Cols",
        description="",
        group="g",
        order=0,
        default_value=[],
        required=False,
    )

    ok, msg = p.validate_value(["A", "B"])
    assert ok, msg


def test_multi_column_select_parameter_empty_allowed_when_not_required():
    p = MultiColumnSelectParameter(
        name="cols",
        display_name="Cols",
        description="",
        group="g",
        order=0,
        default_value=[],
        required=False,
    )

    ok, msg = p.validate_value([])
    assert ok, msg

    ok, msg = p.validate_value(None)
    assert ok, msg


def test_multi_column_select_parameter_empty_rejected_when_required():
    p = MultiColumnSelectParameter(
        name="cols",
        display_name="Cols",
        description="",
        group="g",
        order=0,
        default_value=[],
        required=True,
    )

    ok, msg = p.validate_value([])
    assert not ok
    assert "required" in msg.lower()


@pytest.mark.parametrize("value", ["A", 123, [""], ["  "]])
def test_multi_column_select_parameter_rejects_invalid_values(value):
    p = MultiColumnSelectParameter(
        name="cols",
        display_name="Cols",
        description="",
        group="g",
        order=0,
        default_value=[],
        required=False,
    )

    ok, _msg = p.validate_value(value)
    assert not ok


def test_multi_column_select_parameter_none_rejected_when_required():
    p = MultiColumnSelectParameter(
        name="cols",
        display_name="Cols",
        description="",
        group="g",
        order=0,
        default_value=[],
        required=True,
    )

    ok, msg = p.validate_value(None)
    assert not ok
    assert "required" in msg.lower()
