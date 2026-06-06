"""Two-stage database connection dialog.

Stage 1 — Connection form: driver selection, credentials, connection naming.
Stage 2 — Table / view picker: schema dropdown and scrollable table list.

On "Use This Table" the dialog:
  - Activates a live ``DatabaseDataSource`` on ``app._active_data_source``.
  - Populates column combo-boxes via ``file_manager.populate_columns_from_list``.
  - Saves connection metadata (no password) to ``app.settings``.
  - Stores the password in the system keyring if a connection name is given.
"""

from __future__ import annotations

import dataclasses
import logging
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional, Tuple

from data_sources.base import DataSourceConfig, DataSourceError
from data_sources.database_source import DatabaseDataSource
from data_sources.driver_registry import DATABASE_DRIVERS, DatabaseDriverConfig, get_driver

_logger = logging.getLogger(__name__)

_KEYRING_SERVICE = "highway_segmentation_tool"
_NEW_CONNECTION_SENTINEL = "— New connection —"

# Maps field keys (from DatabaseDriverConfig.fields) to GUI labels.
_FIELD_LABELS: Dict[str, str] = {
    "host": "Host:",
    "port": "Port:",
    "database": "Database:",
    "schema": "Schema (optional):",
    "username": "Username:",
    "account": "Account:",
    "project": "Project:",
    "dataset": "Dataset:",
    "file_path": "File path:",
    "connection_url": "Connection URL:",
}

_PAD: Dict[str, Any] = {"padx": 6, "pady": 3}
_LABEL_PAD: Dict[str, Any] = {"padx": (6, 3), "pady": 3}


class DatabaseConnectionDialog(tk.Toplevel):
    """Modal two-stage dialog for selecting a database table or view.

    Stage 1 presents the connection form; "Browse Tables & Views" tests the
    connection and advances to Stage 2 where the user selects a table.
    "Use This Table" closes the dialog and activates the chosen source.

    Args:
        parent_app: The main ``HighwaySegmentationGUI`` application instance.
    """

    def __init__(self, parent_app: Any) -> None:
        super().__init__(parent_app)
        self.app = parent_app
        self.title("Database Connection")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # ── Stage-1 state ────────────────────────────────────────────────
        self._driver_var = tk.StringVar()
        self._conn_name_var = tk.StringVar()
        self._password_var = tk.StringVar()
        self._saved_conn_var = tk.StringVar(value=_NEW_CONNECTION_SENTINEL)
        self._field_vars: Dict[str, tk.StringVar] = {}
        self._driver_fields_frame: Optional[ttk.Frame] = None

        # ── Stage-2 state ────────────────────────────────────────────────
        self._schema_var = tk.StringVar()
        self._table_items: List[Tuple[str, str]] = []   # (name, "TABLE"|"VIEW")
        self._connected_source: Optional[DatabaseDataSource] = None

        # ── Build UI ─────────────────────────────────────────────────────
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._stage1_outer = ttk.Frame(self, padding=4)
        self._stage2_outer = ttk.Frame(self, padding=4)

        self._build_stage1()
        self._build_stage2()
        self._show_stage1()

        # Centre over parent window.
        self.update_idletasks()
        px = parent_app.winfo_rootx() + parent_app.winfo_width() // 2
        py = parent_app.winfo_rooty() + parent_app.winfo_height() // 2
        self.geometry(
            f"+{px - self.winfo_width() // 2}+{py - self.winfo_height() // 2}"
        )

        self.grab_set()
        self.wait_window(self)

    # ──────────────────────────────────────────────────────────────────── #
    # Stage 1 — connection form                                            #
    # ──────────────────────────────────────────────────────────────────── #

    def _build_stage1(self) -> None:
        outer = self._stage1_outer
        outer.columnconfigure(1, weight=1)

        # ── Saved connections ─────────────────────────────────────────── #
        saved_frame = ttk.LabelFrame(outer, text="Saved connections", padding=6)
        saved_frame.grid(row=0, column=0, columnspan=3, sticky="ew", **_PAD)
        saved_frame.columnconfigure(0, weight=1)

        self._saved_conn_combo = ttk.Combobox(
            saved_frame, textvariable=self._saved_conn_var,
            state="readonly", width=36,
        )
        self._saved_conn_combo.grid(row=0, column=0, sticky="w", padx=(0, 4))
        self._saved_conn_combo.bind("<<ComboboxSelected>>", self._on_saved_selected)

        ttk.Button(saved_frame, text="Load",
                   command=self._load_saved_connection).grid(row=0, column=1, padx=(0, 2))
        ttk.Button(saved_frame, text="Delete",
                   command=self._delete_saved_connection).grid(row=0, column=2)
        self._refresh_saved_combo()

        # ── Connection name ───────────────────────────────────────────── #
        ttk.Label(outer, text="Connection name:").grid(
            row=1, column=0, sticky="w", **_LABEL_PAD,
        )
        ttk.Entry(outer, textvariable=self._conn_name_var, width=38).grid(
            row=1, column=1, columnspan=2, sticky="ew", **_PAD,
        )

        ttk.Separator(outer, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=(4, 2), padx=6,
        )

        # ── Driver dropdown ───────────────────────────────────────────── #
        ttk.Label(outer, text="Driver:").grid(row=3, column=0, sticky="w", **_LABEL_PAD)
        driver_names = [d.display_name for d in DATABASE_DRIVERS]
        self._driver_combo = ttk.Combobox(
            outer, textvariable=self._driver_var,
            values=driver_names, state="readonly", width=30,
        )
        self._driver_combo.set(driver_names[0])
        self._driver_var.set(driver_names[0])
        self._driver_combo.grid(row=3, column=1, sticky="w", **_PAD)
        self._driver_combo.bind("<<ComboboxSelected>>", self._on_driver_changed)

        # ── Dynamic credential fields (rebuilt on driver change) ──────── #
        self._driver_fields_frame = ttk.Frame(outer)
        self._driver_fields_frame.grid(row=4, column=0, columnspan=3, sticky="ew")
        self._driver_fields_frame.columnconfigure(1, weight=1)
        self._rebuild_driver_fields()

        # ── Notes / install hint ─────────────────────────────────────── #
        self._notes_label = ttk.Label(
            outer, text="", foreground="gray",
            font=("Arial", 8), wraplength=430, justify="left",
        )
        self._notes_label.grid(
            row=5, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4),
        )
        self._update_notes_label()

        ttk.Separator(outer, orient="horizontal").grid(
            row=6, column=0, columnspan=3, sticky="ew", pady=(2, 4), padx=6,
        )

        # ── Action buttons ────────────────────────────────────────────── #
        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=7, column=0, columnspan=3, sticky="e", padx=6, pady=(0, 6))
        ttk.Button(btn_frame, text="Cancel",
                   command=self._on_cancel).pack(side="left", padx=(0, 6))
        ttk.Button(btn_frame, text="Browse Tables & Views…",
                   command=self._browse_tables).pack(side="left")

    def _rebuild_driver_fields(self) -> None:
        """Destroy and recreate the credential widgets for the active driver."""
        frame = self._driver_fields_frame
        for widget in frame.winfo_children():
            widget.destroy()
        frame.columnconfigure(1, weight=1)

        driver = self._current_driver()
        self._field_vars = {}

        for i, field_name in enumerate(driver.fields):
            label_text = _FIELD_LABELS.get(
                field_name, f"{field_name.replace('_', ' ').title()}:"
            )
            ttk.Label(frame, text=label_text).grid(
                row=i, column=0, sticky="w", **_LABEL_PAD,
            )

            var = tk.StringVar()
            self._field_vars[field_name] = var

            if field_name == "port" and driver.default_port:
                var.set(str(driver.default_port))
                ttk.Entry(frame, textvariable=var, width=10).grid(
                    row=i, column=1, sticky="w", **_PAD,
                )
            elif field_name == "file_path":
                row_frame = ttk.Frame(frame)
                row_frame.grid(row=i, column=1, columnspan=2, sticky="ew", **_PAD)
                row_frame.columnconfigure(0, weight=1)
                ttk.Entry(row_frame, textvariable=var, width=32).grid(
                    row=0, column=0, sticky="ew",
                )
                ttk.Button(
                    row_frame, text="Browse…",
                    command=lambda v=var: self._browse_sqlite_file(v),
                ).grid(row=0, column=1, padx=(4, 0))
            elif field_name == "connection_url":
                ttk.Entry(frame, textvariable=var, width=50).grid(
                    row=i, column=1, columnspan=2, sticky="ew", **_PAD,
                )
            else:
                ttk.Entry(frame, textvariable=var, width=30).grid(
                    row=i, column=1, sticky="ew", **_PAD,
                )

        # Password field — omitted for SQLite (file-based) and custom URL.
        if driver.driver_key not in ("sqlite", "custom"):
            pw_row = len(driver.fields)
            ttk.Label(frame, text="Password:").grid(
                row=pw_row, column=0, sticky="w", **_LABEL_PAD,
            )
            ttk.Entry(
                frame, textvariable=self._password_var, show="*", width=30,
            ).grid(row=pw_row, column=1, sticky="w", **_PAD)
            ttk.Label(
                frame, text="(never saved)", foreground="gray", font=("Arial", 8),
            ).grid(row=pw_row, column=2, sticky="w")

    def _on_driver_changed(self, _event: Any = None) -> None:
        self._rebuild_driver_fields()
        self._update_notes_label()

    def _update_notes_label(self) -> None:
        driver = self._current_driver()
        parts: List[str] = []
        if driver.notes:
            parts.append(driver.notes)
        if driver.required_packages:
            pkgs = " ".join(driver.required_packages)
            parts.append(f"Required: pip install {pkgs}")
        self._notes_label.config(text="   ".join(parts))

    def _current_driver(self) -> DatabaseDriverConfig:
        display = self._driver_var.get()
        for d in DATABASE_DRIVERS:
            if d.display_name == display:
                return d
        return DATABASE_DRIVERS[0]

    # ── Saved connections ─────────────────────────────────────────────── #

    def _saved_connections(self) -> List[Dict[str, Any]]:
        return self.app.settings.get("data_sources", {}).get("saved_connections", [])

    def _refresh_saved_combo(self) -> None:
        names = [_NEW_CONNECTION_SENTINEL] + [
            c["name"] for c in self._saved_connections()
        ]
        self._saved_conn_combo["values"] = names
        if self._saved_conn_var.get() not in names:
            self._saved_conn_var.set(_NEW_CONNECTION_SENTINEL)

    def _on_saved_selected(self, _event: Any = None) -> None:
        if self._saved_conn_var.get() != _NEW_CONNECTION_SENTINEL:
            self._load_saved_connection()

    def _load_saved_connection(self) -> None:
        selected = self._saved_conn_var.get()
        if selected == _NEW_CONNECTION_SENTINEL:
            return
        conn = next(
            (c for c in self._saved_connections() if c["name"] == selected), None,
        )
        if conn is None:
            return

        self._conn_name_var.set(conn.get("name", ""))
        driver_key = conn.get("driver_key", "postgresql")
        try:
            driver = get_driver(driver_key)
            self._driver_var.set(driver.display_name)
        except KeyError:
            pass
        self._rebuild_driver_fields()
        self._update_notes_label()

        for field_name, var in self._field_vars.items():
            value = conn.get(field_name, "")
            if field_name == "port" and isinstance(value, int):
                value = str(value)
            var.set(str(value) if value is not None else "")

        # Pre-fill password from keyring so the user doesn't have to retype it.
        try:
            import keyring
            stored = keyring.get_password(_KEYRING_SERVICE, conn["name"])
            if stored:
                self._password_var.set(stored)
        except Exception:
            pass

    def _delete_saved_connection(self) -> None:
        selected = self._saved_conn_var.get()
        if selected == _NEW_CONNECTION_SENTINEL:
            return
        conns = [c for c in self._saved_connections() if c["name"] != selected]
        self.app.settings.setdefault("data_sources", {})["saved_connections"] = conns
        self._saved_conn_var.set(_NEW_CONNECTION_SENTINEL)
        self._refresh_saved_combo()

    # ── Connection test + stage advance ──────────────────────────────── #

    def _browse_tables(self) -> None:
        """Test the connection and advance to Stage 2 on success."""
        try:
            config = self._build_config(table_or_view="")
        except ValueError as exc:
            messagebox.showerror("Missing fields", str(exc), parent=self)
            return

        try:
            source = DatabaseDataSource(config)
            source.get_available_schemas()   # lightweight connectivity test
            self._connected_source = source
        except DataSourceError as exc:
            messagebox.showerror("Connection failed", str(exc), parent=self)
            return
        except Exception as exc:
            messagebox.showerror(
                "Connection failed", f"Unexpected error: {exc}", parent=self,
            )
            return

        self._show_stage2()
        self._populate_schemas()

    def _build_config(self, table_or_view: str) -> DataSourceConfig:
        """Assemble a ``DataSourceConfig`` from the Stage-1 form.

        Args:
            table_or_view: Table or view name to embed in the config.

        Returns:
            A ``DataSourceConfig`` populated from the current form state.

        Raises:
            ValueError: If required fields are blank.
        """
        driver = self._current_driver()
        extra: Dict[str, Any] = {}

        for field_name, var in self._field_vars.items():
            raw = var.get().strip()
            if field_name == "port":
                extra[field_name] = int(raw) if raw else driver.default_port
            elif raw:
                extra[field_name] = raw
            else:
                extra[field_name] = None

        password = self._password_var.get()
        if password:
            extra["password"] = password

        # Validate required fields (schema is always optional).
        if driver.driver_key not in ("sqlite", "custom"):
            required = [f for f in driver.fields if f != "schema"]
            missing = [
                _FIELD_LABELS.get(f, f) for f in required if not extra.get(f)
            ]
            if missing:
                raise ValueError(
                    f"Required fields are empty: {', '.join(missing)}"
                )

        schema = extra.pop("schema", None) or None
        host = extra.pop("host", None)
        port = extra.pop("port", None)
        database = extra.pop("database", None)
        username = extra.pop("username", None)

        return DataSourceConfig(
            source_type="database",
            driver_key=driver.driver_key,
            host=host,
            port=port,
            database=database,
            schema=schema,
            table_or_view=table_or_view,
            username=username,
            connection_name=self._conn_name_var.get().strip() or None,
            extra=extra,
        )

    def _browse_sqlite_file(self, var: tk.StringVar) -> None:
        path = filedialog.askopenfilename(
            title="Select SQLite database file",
            filetypes=[
                ("SQLite databases", "*.db *.sqlite *.sqlite3"),
                ("All files", "*.*"),
            ],
            parent=self,
        )
        if path:
            var.set(path)

    # ──────────────────────────────────────────────────────────────────── #
    # Stage 2 — table / view picker                                        #
    # ──────────────────────────────────────────────────────────────────── #

    def _build_stage2(self) -> None:
        outer = self._stage2_outer
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        # Status line
        self._conn_status_label = ttk.Label(outer, text="", foreground="blue")
        self._conn_status_label.grid(
            row=0, column=0, columnspan=2, sticky="w", **_PAD,
        )

        # Schema selector
        schema_frame = ttk.Frame(outer)
        schema_frame.grid(row=1, column=0, columnspan=2, sticky="w", **_PAD)
        ttk.Label(schema_frame, text="Schema:").pack(side="left", padx=(0, 6))
        self._schema_combo = ttk.Combobox(
            schema_frame, textvariable=self._schema_var, state="readonly", width=26,
        )
        self._schema_combo.pack(side="left")
        self._schema_combo.bind("<<ComboboxSelected>>", self._on_schema_changed)

        # Table / view list
        list_frame = ttk.LabelFrame(outer, text="Tables and views", padding=4)
        list_frame.grid(
            row=2, column=0, columnspan=2, sticky="nsew", padx=6, pady=(0, 4),
        )
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self._table_listbox = tk.Listbox(
            list_frame, width=54, height=12,
            selectmode=tk.SINGLE, exportselection=False,
            font=("Courier", 10),
        )
        self._table_listbox.grid(row=0, column=0, sticky="nsew")
        self._table_listbox.bind("<<ListboxSelect>>", self._on_table_selected)

        sb = ttk.Scrollbar(
            list_frame, orient="vertical", command=self._table_listbox.yview,
        )
        sb.grid(row=0, column=1, sticky="ns")
        self._table_listbox.config(yscrollcommand=sb.set)

        ttk.Separator(outer, orient="horizontal").grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(2, 4), padx=6,
        )

        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=4, column=0, columnspan=2, sticky="e", padx=6, pady=(0, 6))
        ttk.Button(btn_frame, text="Back",
                   command=self._show_stage1).pack(side="left", padx=(0, 6))
        self._use_table_btn = ttk.Button(
            btn_frame, text="Use This Table", state="disabled",
            command=self._use_selected_table,
        )
        self._use_table_btn.pack(side="left")

    def _show_stage1(self) -> None:
        self._stage2_outer.grid_remove()
        self._stage1_outer.grid(row=0, column=0, sticky="nsew")
        self.title("Database Connection")

    def _show_stage2(self) -> None:
        self._stage1_outer.grid_remove()
        self._stage2_outer.grid(row=0, column=0, sticky="nsew")
        self.title("Database Connection — Select Table or View")

        cfg = self._connected_source._config  # type: ignore[union-attr]
        driver = self._current_driver()
        host_part = (
            cfg.host
            or (cfg.extra or {}).get("account")
            or (cfg.extra or {}).get("project")
            or ""
        )
        db_part = (
            cfg.database
            or (cfg.extra or {}).get("dataset")
            or (cfg.extra or {}).get("file_path")
            or ""
        )
        parts = [db_part or "N/A"]
        if host_part:
            parts.append(f"@ {host_part}")
        parts.append(f"({driver.display_name})")
        self._conn_status_label.config(text="Connected: " + "  ".join(parts))

    def _populate_schemas(self) -> None:
        try:
            schemas = self._connected_source.get_available_schemas()  # type: ignore[union-attr]
        except DataSourceError as exc:
            messagebox.showerror("Schema list failed", str(exc), parent=self)
            return

        display_schemas = schemas if schemas else ["(default)"]
        self._schema_combo["values"] = display_schemas
        self._schema_var.set(display_schemas[0])
        self._load_tables_for_schema(display_schemas[0])

    def _on_schema_changed(self, _event: Any = None) -> None:
        schema = self._schema_var.get()
        self._load_tables_for_schema(schema)

    def _load_tables_for_schema(self, schema: str) -> None:
        resolved = None if schema in ("", "(default)") else schema
        try:
            items = self._connected_source.get_available_tables_and_views(  # type: ignore[union-attr]
                schema=resolved,
            )
        except DataSourceError as exc:
            messagebox.showerror("Table list failed", str(exc), parent=self)
            return

        self._table_items = items
        self._table_listbox.delete(0, tk.END)
        for name, kind in items:
            # Monospace font keeps columns aligned: "TABLE  name" / "VIEW   name"
            badge = "TABLE " if kind == "TABLE" else "VIEW  "
            self._table_listbox.insert(tk.END, f"{badge}  {name}")
        self._use_table_btn.config(state="disabled")

    def _on_table_selected(self, _event: Any = None) -> None:
        has_selection = bool(self._table_listbox.curselection())
        self._use_table_btn.config(state="normal" if has_selection else "disabled")

    # ── Confirm selection ─────────────────────────────────────────────── #

    def _use_selected_table(self) -> None:
        """Activate the selected table/view and close the dialog."""
        selection = self._table_listbox.curselection()
        if not selection:
            return

        table_name, _kind = self._table_items[selection[0]]
        schema = self._schema_var.get()
        resolved_schema = None if schema in ("", "(default)") else schema

        # Build config with the chosen table and schema from Stage 2.
        try:
            config = self._build_config(table_or_view=table_name)
        except ValueError as exc:
            messagebox.showerror("Configuration error", str(exc), parent=self)
            return

        if resolved_schema:
            config = dataclasses.replace(config, schema=resolved_schema)

        # Fetch column list to populate the GUI combos.
        try:
            source = DatabaseDataSource(config)
            columns = source.get_available_columns()
        except DataSourceError as exc:
            messagebox.showerror("Column read failed", str(exc), parent=self)
            return

        # Assemble display string for the "Connected to:" entry.
        driver = self._current_driver()
        cfg = config
        host_part = (
            cfg.host
            or (cfg.extra or {}).get("account")
            or (cfg.extra or {}).get("project")
            or ""
        )
        db_part = (
            cfg.database
            or (cfg.extra or {}).get("dataset")
            or (cfg.extra or {}).get("file_path")
            or ""
        )
        display = f"{db_part or driver.display_name}"
        if host_part:
            display += f" @ {host_part}"
        display += f" / {table_name}"

        # Activate on the application.
        self.app._active_data_source = source
        self.app._data_file_path = ""
        self.app.data_file.set(display)

        # Populate column combos — same logic as file_manager.load_csv_columns.
        self.app.file_manager.populate_columns_from_list(columns)

        # Keep the type dropdown in sync with the connected source type.
        if hasattr(self.app, 'data_source_type_var'):
            self.app.data_source_type_var.set("Database (SQL)")
        if hasattr(self.app, 'data_source_type_combo'):
            self.app.data_source_type_combo.set("Database (SQL)")

        # Persist connection metadata (no password) and save password to keyring.
        self._persist_connection(config, table_name)

        _logger.info(
            "Database source activated: driver=%s  table=%s",
            driver.driver_key, table_name,
        )
        self.destroy()

    def _persist_connection(self, config: DataSourceConfig, table_name: str) -> None:
        """Write connection metadata to app settings and password to keyring.

        Args:
            config: The ``DataSourceConfig`` for the chosen connection.
            table_name: The selected table or view name.
        """
        conn_name = (
            config.connection_name
            or f"{config.database or 'db'}/{table_name}"
        )
        driver = self._current_driver()

        record: Dict[str, Any] = {
            "name": conn_name,
            "driver_key": driver.driver_key,
            "table_or_view": table_name,
        }
        for attr in ("host", "port", "database", "schema", "username"):
            val = getattr(config, attr, None)
            if val is not None:
                record[attr] = val
        # Copy non-password extra fields (e.g. Snowflake account, BigQuery project).
        for k, v in (config.extra or {}).items():
            if k != "password" and v is not None:
                record[k] = v

        ds = self.app.settings.setdefault("data_sources", {})
        conns: List[Dict[str, Any]] = ds.setdefault("saved_connections", [])
        idx = next(
            (i for i, c in enumerate(conns) if c["name"] == conn_name), None,
        )
        if idx is not None:
            conns[idx] = record
        else:
            conns.append(record)

        # Password into keyring — never written to disk.
        password = self._password_var.get()
        if password:
            try:
                import keyring
                keyring.set_password(_KEYRING_SERVICE, conn_name, password)
            except Exception as exc:
                _logger.warning("Could not store password in keyring: %s", exc)

    # ── Cancel ───────────────────────────────────────────────────────── #

    def _on_cancel(self) -> None:
        self.destroy()
