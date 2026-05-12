from settings_manager import SettingsManager


def test_default_settings_include_must_break_columns():
    sm = SettingsManager()
    defaults = sm._get_default_settings()

    assert "ui_state" in defaults
    assert "must_break_columns" in defaults["ui_state"]
    assert defaults["ui_state"]["must_break_columns"] == []


def test_merge_with_defaults_backfills_must_break_columns():
    sm = SettingsManager()

    loaded = {
        "ui_state": {
            "x_column": "X",
            "y_column": "Y",
        }
    }

    merged = sm._merge_with_defaults(loaded)
    assert merged["ui_state"]["must_break_columns"] == []
