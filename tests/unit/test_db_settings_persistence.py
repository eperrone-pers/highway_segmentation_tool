"""Unit tests for saved-connection settings persistence helpers.

Tests the pure module-level functions extracted from DatabaseConnectionDialog:

- ``build_connection_record`` — builds a settings dict from a DataSourceConfig
- ``upsert_connection_record`` — inserts or updates in the saved list
- ``get_saved_connections`` — reads back the list from app.settings
- ``delete_connection_by_name`` — removes an entry by name

No Tkinter dependency — these functions operate on plain dicts only.
"""
from __future__ import annotations

from data_sources.base import DataSourceConfig
from database_connection_dialog import (
    build_connection_record,
    delete_connection_by_name,
    get_saved_connections,
    upsert_connection_record,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config(
    connection_name: str = "Test DB",
    driver_key: str = "postgresql",
    host: str = "db.example.com",
    port: int = 5432,
    database: str = "pavement",
    schema: str | None = None,
    username: str = "analyst",
    extra: dict | None = None,
) -> DataSourceConfig:
    return DataSourceConfig(
        source_type="database",
        driver_key=driver_key,
        host=host,
        port=port,
        database=database,
        schema=schema,
        username=username,
        connection_name=connection_name,
        extra=extra or {},
    )


# ---------------------------------------------------------------------------
# build_connection_record
# ---------------------------------------------------------------------------

class TestBuildConnectionRecord:

    def test_name_comes_from_connection_name(self):
        record = build_connection_record(_config(connection_name="DOT DB"), "postgresql", "roads")
        assert record["name"] == "DOT DB"

    def test_falls_back_to_database_slash_table_when_no_name(self):
        record = build_connection_record(_config(connection_name="", database="mydb"), "postgresql", "iri")
        assert record["name"] == "mydb/iri"

    def test_falls_back_to_db_slash_table_when_database_also_missing(self):
        cfg = _config(connection_name="", database=None)
        record = build_connection_record(cfg, "sqlite", "tbl")
        assert record["name"] == "db/tbl"

    def test_driver_key_is_written(self):
        record = build_connection_record(_config(), "oracle", "roads")
        assert record["driver_key"] == "oracle"

    def test_table_or_view_is_written(self):
        record = build_connection_record(_config(), "postgresql", "iri_survey")
        assert record["table_or_view"] == "iri_survey"

    def test_standard_fields_are_included(self):
        cfg = _config(host="myhost", port=5433, database="mydb", schema="public", username="bob")
        record = build_connection_record(cfg, "postgresql", "t")
        assert record["host"] == "myhost"
        assert record["port"] == 5433
        assert record["database"] == "mydb"
        assert record["schema"] == "public"
        assert record["username"] == "bob"

    def test_none_fields_are_omitted(self):
        cfg = _config(schema=None)
        record = build_connection_record(cfg, "postgresql", "t")
        assert "schema" not in record

    def test_password_never_included(self):
        cfg = _config(extra={"password": "s3cr3t", "project": "my-gcp"})
        record = build_connection_record(cfg, "bigquery", "t")
        assert "password" not in record
        assert "s3cr3t" not in str(record.values())

    def test_non_password_extra_fields_are_included(self):
        cfg = _config(extra={"project": "my-gcp", "dataset": "roads"})
        record = build_connection_record(cfg, "bigquery", "iri")
        assert record["project"] == "my-gcp"
        assert record["dataset"] == "roads"

    def test_none_extra_values_are_omitted(self):
        cfg = _config(extra={"project": None, "account": "xy12345"})
        record = build_connection_record(cfg, "snowflake", "t")
        assert "project" not in record
        assert record["account"] == "xy12345"


# ---------------------------------------------------------------------------
# upsert_connection_record
# ---------------------------------------------------------------------------

class TestUpsertConnectionRecord:

    def test_appends_to_empty_settings(self):
        settings: dict = {}
        upsert_connection_record(settings, {"name": "A", "driver_key": "sqlite"})
        assert len(settings["data_sources"]["saved_connections"]) == 1

    def test_appends_new_entry(self):
        settings: dict = {"data_sources": {"saved_connections": [
            {"name": "A", "driver_key": "sqlite"},
        ]}}
        upsert_connection_record(settings, {"name": "B", "driver_key": "postgresql"})
        conns = settings["data_sources"]["saved_connections"]
        assert len(conns) == 2
        assert conns[1]["name"] == "B"

    def test_updates_in_place_when_name_matches(self):
        settings: dict = {"data_sources": {"saved_connections": [
            {"name": "Existing", "driver_key": "postgresql", "table_or_view": "old"},
        ]}}
        upsert_connection_record(settings, {"name": "Existing", "driver_key": "postgresql", "table_or_view": "new"})
        conns = settings["data_sources"]["saved_connections"]
        assert len(conns) == 1, "should update in place, not append"
        assert conns[0]["table_or_view"] == "new"

    def test_preserves_order_of_other_entries_on_update(self):
        settings: dict = {"data_sources": {"saved_connections": [
            {"name": "A"},
            {"name": "B", "table_or_view": "old"},
            {"name": "C"},
        ]}}
        upsert_connection_record(settings, {"name": "B", "table_or_view": "new"})
        names = [c["name"] for c in settings["data_sources"]["saved_connections"]]
        assert names == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# get_saved_connections
# ---------------------------------------------------------------------------

class TestGetSavedConnections:

    def test_returns_empty_list_when_settings_empty(self):
        assert get_saved_connections({}) == []

    def test_returns_empty_list_when_data_sources_key_missing(self):
        assert get_saved_connections({"other": "value"}) == []

    def test_returns_stored_connections(self):
        settings = {"data_sources": {"saved_connections": [
            {"name": "A"},
            {"name": "B"},
        ]}}
        result = get_saved_connections(settings)
        assert [c["name"] for c in result] == ["A", "B"]

    def test_round_trip_upsert_then_read(self):
        settings: dict = {}
        upsert_connection_record(settings, {"name": "RT", "table_or_view": "tbl"})
        result = get_saved_connections(settings)
        assert len(result) == 1
        assert result[0]["name"] == "RT"
        assert result[0]["table_or_view"] == "tbl"


# ---------------------------------------------------------------------------
# delete_connection_by_name
# ---------------------------------------------------------------------------

class TestDeleteConnectionByName:

    def test_removes_named_connection(self):
        settings: dict = {"data_sources": {"saved_connections": [
            {"name": "Keep"},
            {"name": "Remove"},
        ]}}
        delete_connection_by_name(settings, "Remove")
        assert [c["name"] for c in get_saved_connections(settings)] == ["Keep"]

    def test_no_op_when_name_not_found(self):
        settings: dict = {"data_sources": {"saved_connections": [{"name": "Real"}]}}
        delete_connection_by_name(settings, "Ghost")
        assert len(get_saved_connections(settings)) == 1

    def test_no_op_on_empty_settings(self):
        settings: dict = {}
        delete_connection_by_name(settings, "anything")
        assert get_saved_connections(settings) == []

    def test_preserves_other_connections(self):
        settings: dict = {"data_sources": {"saved_connections": [
            {"name": "A"},
            {"name": "B"},
            {"name": "C"},
        ]}}
        delete_connection_by_name(settings, "B")
        assert [c["name"] for c in get_saved_connections(settings)] == ["A", "C"]

    def test_full_round_trip_upsert_then_delete(self):
        settings: dict = {}
        upsert_connection_record(settings, {"name": "Temp", "table_or_view": "tbl"})
        assert len(get_saved_connections(settings)) == 1

        delete_connection_by_name(settings, "Temp")
        assert get_saved_connections(settings) == []


# ---------------------------------------------------------------------------
# build_connection_record + upsert — integration
# ---------------------------------------------------------------------------

class TestBuildAndUpsertIntegration:

    def test_build_then_upsert_writes_correct_record(self):
        cfg = _config(connection_name="DOT", host="h", port=5432, database="d", username="u")
        settings: dict = {}
        upsert_connection_record(settings, build_connection_record(cfg, "postgresql", "iri"))
        record = get_saved_connections(settings)[0]
        assert record["name"] == "DOT"
        assert record["host"] == "h"
        assert record["port"] == 5432
        assert record["database"] == "d"
        assert record["username"] == "u"
        assert "password" not in record

    def test_multiple_connections_persist_independently(self):
        settings: dict = {}
        upsert_connection_record(settings, build_connection_record(_config(connection_name="A"), "postgresql", "t1"))
        upsert_connection_record(settings, build_connection_record(_config(connection_name="B"), "sqlite", "t2"))
        upsert_connection_record(settings, build_connection_record(_config(connection_name="C"), "oracle", "t3"))
        conns = get_saved_connections(settings)
        assert len(conns) == 3
        assert {c["name"] for c in conns} == {"A", "B", "C"}
