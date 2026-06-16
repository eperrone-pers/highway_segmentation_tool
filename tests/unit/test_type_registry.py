"""Unit tests for data_sources.type_registry."""

import pytest

from data_sources.type_registry import (
    DATA_SOURCE_TYPES,
    TYPE_BY_KEY,
    get_source_type,
    get_display_names,
    get_type_by_display_name,
)


class TestDataSourceTypeConfig:
    @pytest.mark.unit
    def test_required_fields_present(self):
        for t in DATA_SOURCE_TYPES:
            assert t.type_key, f"type_key must not be empty (entry: {t})"
            assert t.display_name, f"display_name must not be empty (entry: {t})"
            assert t.dialog_type in ("file_browser", "connection_form"), (
                f"'{t.type_key}' has unknown dialog_type '{t.dialog_type}'"
            )

    @pytest.mark.unit
    def test_type_keys_are_unique(self):
        keys = [t.type_key for t in DATA_SOURCE_TYPES]
        assert len(keys) == len(set(keys)), "Duplicate type_key values found"

    @pytest.mark.unit
    def test_display_names_are_unique(self):
        names = [t.display_name for t in DATA_SOURCE_TYPES]
        assert len(names) == len(set(names)), "Duplicate display_name values found"

    @pytest.mark.unit
    def test_file_browser_types_have_file_types(self):
        for t in DATA_SOURCE_TYPES:
            if t.dialog_type == "file_browser":
                assert t.file_types, (
                    f"file_browser type '{t.type_key}' must declare file_types"
                )

    @pytest.mark.unit
    def test_connection_form_types_have_no_file_types(self):
        for t in DATA_SOURCE_TYPES:
            if t.dialog_type == "connection_form":
                assert t.file_types == [], (
                    f"connection_form type '{t.type_key}' should have empty file_types"
                )


class TestTypeByKey:
    @pytest.mark.unit
    def test_lookup_dict_matches_list(self):
        assert set(TYPE_BY_KEY.keys()) == {t.type_key for t in DATA_SOURCE_TYPES}

    @pytest.mark.unit
    def test_csv_present(self):
        assert "csv" in TYPE_BY_KEY

    @pytest.mark.unit
    def test_database_present(self):
        assert "database" in TYPE_BY_KEY


class TestGetSourceType:
    @pytest.mark.unit
    def test_returns_correct_entry(self):
        t = get_source_type("csv")
        assert t.type_key == "csv"
        assert t.dialog_type == "file_browser"

    @pytest.mark.unit
    def test_database_is_connection_form(self):
        t = get_source_type("database")
        assert t.dialog_type == "connection_form"

    @pytest.mark.unit
    def test_raises_for_unknown_key(self):
        with pytest.raises(KeyError, match="Unknown data source type key"):
            get_source_type("nonexistent")


class TestGetDisplayNames:
    @pytest.mark.unit
    def test_returns_list_of_strings(self):
        names = get_display_names()
        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)

    @pytest.mark.unit
    def test_length_matches_registry(self):
        assert len(get_display_names()) == len(DATA_SOURCE_TYPES)

    @pytest.mark.unit
    def test_order_matches_registry(self):
        expected = [t.display_name for t in DATA_SOURCE_TYPES]
        assert get_display_names() == expected

    @pytest.mark.unit
    def test_csv_and_database_present(self):
        names = get_display_names()
        assert "CSV File" in names
        assert "Database (SQL)" in names


class TestGetTypeByDisplayName:
    @pytest.mark.unit
    def test_returns_correct_config(self):
        t = get_type_by_display_name("CSV File")
        assert t is not None
        assert t.type_key == "csv"

    @pytest.mark.unit
    def test_returns_none_for_unknown_name(self):
        assert get_type_by_display_name("Nonexistent Source") is None

    @pytest.mark.unit
    def test_roundtrip_display_name_to_type_key(self):
        for source_type in DATA_SOURCE_TYPES:
            result = get_type_by_display_name(source_type.display_name)
            assert result is not None
            assert result.type_key == source_type.type_key
