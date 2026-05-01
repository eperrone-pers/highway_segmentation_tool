"""
UI Builder Module for Highway Segmentation GA

This module handles the creation and configuration of all GUI widgets,
separating UI construction logic from the main application class to improve
organization and maintainability.
"""

import tkinter as tk
from tkinter import ttk
import sys
from tkinter import messagebox
from config import UIConfig, get_optimization_method_names, get_method_key_from_display_name

# Create UI config instance
ui_config = UIConfig()


class UIBuilder:
    """
    Handles the creation and configuration of GUI widgets for the Highway Segmentation application.
    
    This class separates widget creation logic from the main application class,
    following the Builder pattern to improve code organization and maintainability.
    """
    
    def __init__(self, main_app):
        """
        Initialize the UI builder with a reference to the main application.
        
        Args:
            main_app: Reference to the main HighwaySegmentationGUI instance
        """
        self.app = main_app
    
    def create_main_layout(self):
        """Create the main application layout structure."""
        # Configure root window
        self.app.root.grid_rowconfigure(0, weight=1)
        self.app.root.columnconfigure(0, weight=1)
        
        # Create main frame
        main_frame = ttk.Frame(self.app.root, padding=ui_config.main_padding)
        main_frame.grid(row=0, column=0, sticky="nsew")
        # Configure grid weights for responsive layout
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=0)  # Left pane: auto-size to fit content
        main_frame.grid_columnconfigure(1, weight=0)  # Scrollbar column (fixed width when visible)  
        main_frame.grid_columnconfigure(2, weight=1)  # Right pane gets all remaining horizontal space
        
        # Create title
        title_label = ttk.Label(main_frame, text="Highway Segmentation Tool", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=ui_config.title_columnspan, 
                        pady=ui_config.standard_padding_y)
        
        return main_frame
    
    def create_scrollable_left_pane(self, parent):
        """Create the left pane with fixed required controls and a dynamic parameter area.

        The required controls stay visible. The dynamic parameters area below will
        host a native-scrollable grid (Treeview) to avoid cross-platform mousewheel
        quirks with scrollable frames on macOS.
        """

        left_container = ttk.Frame(parent)
        left_container.grid(row=1, column=0, sticky="nsew", padx=ui_config.standard_padding_x)
        left_container.grid_rowconfigure(0, weight=0)
        left_container.grid_rowconfigure(1, weight=1)
        left_container.grid_columnconfigure(0, weight=1)

        required_frame = ttk.Frame(left_container)
        required_frame.grid(row=0, column=0, sticky="ew")
        required_frame.grid_columnconfigure(0, weight=1)

        dynamic_frame = ttk.LabelFrame(left_container, text="Method Parameters (double click on parameter value to edit)", padding="6")
        dynamic_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        dynamic_frame.grid_rowconfigure(0, weight=1)
        dynamic_frame.grid_columnconfigure(0, weight=1)

        # Expose the dynamic params parent so gui_main can populate it.
        self.app.dynamic_params_parent = dynamic_frame

        return required_frame
    
    def create_right_pane(self, parent):
        """Create the right pane for results and status."""
        right_pane = ttk.Frame(parent)
        right_pane.grid(row=1, column=2, sticky="nsew", padx=(10, 0))
        right_pane.grid_rowconfigure(1, weight=1)
        right_pane.grid_columnconfigure(0, weight=1)
        
        return right_pane
    
    def create_file_operations_section(self, parent, row):
        """Create the unified file operations section (data loading, column selection, and results saving)."""
        file_ops_frame = ttk.LabelFrame(parent, text="📁 File Operations", padding="6")  # Reduced from 10
        file_ops_frame.grid(row=row, column=0, sticky="ew", pady=3)  # Reduced from 5
        # Configure columns for proper widget spacing
        file_ops_frame.columnconfigure(1, weight=1)  # Entry fields expand
        file_ops_frame.columnconfigure(2, weight=0)  # Buttons maintain natural size
        file_ops_frame.columnconfigure(0, weight=0)  # Labels maintain natural size
        
        # === DATA LOADING SECTION ===
        # File selection
        ttk.Label(file_ops_frame, text="Data File:").grid(row=0, column=0, sticky="w")
        self.app.data_entry = ttk.Entry(file_ops_frame, textvariable=self.app.data_file, 
                                       width=ui_config.entry_field_width_large)
        self.app.data_entry.grid(row=0, column=1, sticky="ew", padx=ui_config.standard_padding_x)
        
        ttk.Button(file_ops_frame, text="Browse...", 
                  command=self.app.browse_data_file).grid(row=0, column=2, padx=ui_config.standard_padding_x, sticky="w")
        
        # Route column selection (for multi-route data files)
        ttk.Label(file_ops_frame, text="Route Column (Optional):").grid(row=1, column=0, sticky="w", pady=(5, 0))  # Reduced from (10, 0)
        
        # Create a frame to hold combobox and filter button together
        route_controls_frame = ttk.Frame(file_ops_frame)
        route_controls_frame.grid(row=1, column=1, sticky="w", pady=(5, 0), padx=ui_config.standard_padding_x)
        
        self.app.route_column_combo = ttk.Combobox(route_controls_frame, textvariable=self.app.route_column,
                                                  width=20)
        self.app.route_column_combo.set("None - treat as single route")
        self.app.route_column_combo.grid(row=0, column=0, sticky="w")
        self.app.route_column_combo.bind('<<ComboboxSelected>>', self.app.on_route_column_change)
        
        # Filter button - compact text, positioned right next to dropdown
        self.app.filter_routes_button = ttk.Button(route_controls_frame, text="Filter", 
                                                  command=self.app.open_route_filter_dialog,
                                                  state="disabled")  # Start disabled
        self.app.filter_routes_button.grid(row=0, column=1, padx=(3, 0))
        
        # Route selection status display - more compact text
        self.app.route_info_label = ttk.Label(file_ops_frame, text="", foreground="blue")
        self.app.route_info_label.grid(row=1, column=2, pady=(5, 0), padx=(5, 0), sticky="ew")
        
        # Column selection
        ttk.Label(file_ops_frame, text="X Column (Distance):").grid(row=2, column=0, sticky="w")
        self.app.x_column_combo = ttk.Combobox(file_ops_frame, textvariable=self.app.x_column, 
                                              width=20)
        self.app.x_column_combo.set("Load data first...")
        self.app.x_column_combo.grid(row=2, column=1, sticky="w", padx=ui_config.standard_padding_x)
        self.app.x_column_combo.bind('<<ComboboxSelected>>', self.app.on_column_change)
        self.app.x_column_combo.bind('<KeyRelease>', lambda e: self.app.on_column_keyrelease(e, self.app.x_column_combo))
        
        ttk.Label(file_ops_frame, text="Y Column (Data Values):").grid(row=3, column=0, sticky="w")
        self.app.y_column_combo = ttk.Combobox(file_ops_frame, textvariable=self.app.y_column, 
                                              width=20)
        self.app.y_column_combo.set("Load data first...")
        self.app.y_column_combo.grid(row=3, column=1, sticky="w", padx=ui_config.standard_padding_x)
        self.app.y_column_combo.bind('<<ComboboxSelected>>', self.app.on_column_change)
        self.app.y_column_combo.bind('<KeyRelease>', lambda e: self.app.on_column_keyrelease(e, self.app.y_column_combo))
        
        # Framework Parameters (shared across all methods)
        ttk.Label(file_ops_frame, text="Gap Threshold (miles):").grid(row=4, column=0, sticky="w")
        self.app.gap_threshold_entry = ttk.Entry(file_ops_frame, textvariable=self.app.gap_threshold, 
                                                width=10)
        self.app.gap_threshold_entry.grid(row=4, column=1, sticky="w", padx=ui_config.standard_padding_x)
        
        # === SEPARATOR ===
        separator = ttk.Separator(file_ops_frame, orient='horizontal')
        separator.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 5))  # Reduced from (15, 10)
        
        # === RESULTS SAVING SECTION ===
        # Info about auto-save
        info_label = ttk.Label(file_ops_frame, text="Parameters auto-save when optimization starts and on exit.", 
                              font=("Arial", 8), foreground="gray")
        info_label.grid(row=6, column=0, columnspan=3, sticky="w", pady=(0, 3))  # Reduced from (0, 5)
        
        # Reset button
        ttk.Button(file_ops_frame, text="Reset to Defaults", 
                  command=self.app.reset_parameters).grid(row=7, column=0, sticky="w", pady=(0, 5))  # Reduced from (0, 10)
        
        # Results save location
        ttk.Label(file_ops_frame, text="Results File (Required):").grid(row=8, column=0, sticky="w", pady=(3, 0))  # Reduced from (5, 0)
        
        # Save location selection frame
        save_frame = ttk.Frame(file_ops_frame)
        save_frame.grid(row=9, column=0, columnspan=3, sticky="ew", pady=(3, 0))  # Reduced from (5, 0)
        save_frame.columnconfigure(0, weight=1)
        
        self.app.save_name_entry = ttk.Entry(save_frame, textvariable=self.app.custom_save_name, 
                                            width=ui_config.entry_field_width_medium)
        self.app.save_name_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        ttk.Button(save_frame, text="Browse...", 
                  command=self.app.browse_save_location).grid(row=0, column=1)
        
        return row + 1
    
    # create_parameters_section method removed - now using dynamic parameter generation
    
    def create_method_section(self, parent, row):
        """Create the extensible optimization method selection section using dropdown."""
        method_frame = ttk.LabelFrame(parent, text="🔬 Optimization Method", padding="6")  # Reduced from 10
        method_frame.grid(row=row, column=0, sticky="ew", pady=3)  # Reduced from 5
        method_frame.columnconfigure(1, weight=1)
        method_frame.columnconfigure(0, weight=0)  # Labels should not expand
        
        # Method selection dropdown (replaces radio buttons for extensibility)
        ttk.Label(method_frame, text="Optimization Method:").grid(row=0, column=0, sticky="w")
        
        # Get method names from configuration for dynamic population
        method_names = get_optimization_method_names()
        
        self.app.method_dropdown = ttk.Combobox(method_frame, values=method_names, 
                                               state="readonly", width=35)
        self.app.method_dropdown.set(method_names[0] if method_names else "No methods available")
        self.app.method_dropdown.grid(row=0, column=1, sticky="ew", padx=ui_config.standard_padding_x)
        self.app.method_dropdown.bind('<<ComboboxSelected>>', self.app.on_method_change)
        
        # Method description (dynamic based on selection)
        self.app.method_description = ttk.Label(method_frame, text="", foreground="gray", wraplength=500)
        self.app.method_description.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))  # Reduced from (10, 0)

        # Initialize description for the current selection
        try:
            method_key = get_method_key_from_display_name(self.app.method_dropdown.get())
            from config import get_optimization_method
            self.app.method_description.config(text=get_optimization_method(method_key).description)
        except Exception:
            # Non-fatal; description will be updated on method change.
            pass
        
        return row + 1

    # ===== DYNAMIC PARAMETER GRID (TREEVIEW) =====

    def create_dynamic_params_section(self, parent):
        """Create the dynamic parameter grid with inline editing.

        Double-click a value cell to edit in-place. This avoids a separate editor
        pane while keeping native scrolling behavior (especially important on macOS).
        """
        container = ttk.Frame(parent)
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=0)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=0)

        columns = ("parameter", "value")
        tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse", height=10)
        tree.heading("parameter", text="Parameter")
        tree.heading("value", text="Value")
        tree.column("parameter", width=260, anchor="w")
        tree.column("value", width=180, anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        button_row = ttk.Frame(container)
        button_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        # Store references on the app for access from event handlers
        self.app.dynamic_params_tree = tree
        self.app.dynamic_params_defs = {}       # param_name -> ParameterDefinition
        self.app.dynamic_params_cell_editor = {
            "widget": None,
            "param_name": None,
            "method_key": None,
        }

        reset_btn = ttk.Button(button_row, text="Reset Selected to Default", command=self._reset_selected_dynamic_param)
        reset_btn.pack(side="left")

        tree.bind("<Double-1>", self._on_dynamic_param_double_click)
        tree.bind("<Button-1>", self._on_dynamic_param_single_click)

        # Initial population based on the currently selected method (if available)
        try:
            method_key = self._get_selected_method_key_safe()
            if method_key:
                self.refresh_dynamic_params_grid(method_key)
        except Exception:
            pass

        return container

    def refresh_dynamic_params_grid(self, method_key: str) -> None:
        """Rebuild the Treeview rows for the specified method."""
        if not hasattr(self.app, "dynamic_params_tree"):
            return

        from config import get_optimization_method
        method_config = get_optimization_method(method_key)

        tree = self.app.dynamic_params_tree
        self._cancel_dynamic_param_cell_edit()
        tree.delete(*tree.get_children())
        self.app.dynamic_params_defs = {param.name: param for param in method_config.parameters}

        values = self._get_dynamic_params_for_method(method_key)

        # Sort by group then order for stable presentation
        params_sorted = sorted(method_config.parameters, key=lambda p: (p.group, p.order))
        for param_def in params_sorted:
            value = values.get(param_def.name, param_def.default_value)
            # Use param name as the Treeview iid for stable lookup
            tree.insert("", "end", iid=param_def.name, values=(param_def.display_name, self._format_param_value(param_def, value)))

    def set_method_description(self, method_key: str) -> None:
        """Update the method description label based on config."""
        try:
            from config import get_optimization_method
            if hasattr(self.app, "method_description"):
                self.app.method_description.config(text=get_optimization_method(method_key).description)
        except Exception:
            return

    def get_parameter_values(self):
        """Return current dynamic parameter values for the selected method.

        This is used by controller/parameter save/load paths; it must remain stable.
        """
        method_key = self._get_selected_method_key_safe()
        if not method_key:
            return {}
        return self._get_dynamic_params_for_method(method_key)

    def _get_selected_method_key_safe(self):
        try:
            if hasattr(self.app, "method_dropdown"):
                display_name = self.app.method_dropdown.get()
                return get_method_key_from_display_name(display_name)
        except Exception:
            pass

        try:
            if hasattr(self.app, "optimization_method") and isinstance(self.app.optimization_method, str):
                return self.app.optimization_method
        except Exception:
            pass
        return None

    def _get_dynamic_store(self) -> dict:
        """Return settings-backed dynamic parameter store, creating it if needed."""
        settings = getattr(self.app, "settings", None)
        if not isinstance(settings, dict):
            self.app.settings = {}
            settings = self.app.settings
        opt = settings.setdefault("optimization", {})
        store = opt.setdefault("dynamic_parameters_by_method", {})
        return store

    def _get_dynamic_params_for_method(self, method_key: str) -> dict:
        """Return merged dynamic params (stored overrides + defaults) for a method."""
        from config import get_optimization_method

        method_config = get_optimization_method(method_key)
        store = self._get_dynamic_store()
        overrides = store.get(method_key, {}) if isinstance(store.get(method_key, {}), dict) else {}

        merged = {param.name: param.default_value for param in method_config.parameters}
        merged.update(overrides)
        return merged

    def _set_dynamic_param_value(self, method_key: str, param_name: str, value):
        store = self._get_dynamic_store()
        per_method = store.setdefault(method_key, {})
        per_method[param_name] = value

    def _format_param_value(self, param_def, value) -> str:
        from config import NumericParameter, OptionalNumericParameter, SelectParameter, BoolParameter, ColumnSelectParameter

        if isinstance(param_def, OptionalNumericParameter) and value is None:
            return param_def.none_text
        if isinstance(param_def, BoolParameter):
            return "True" if bool(value) else "False"
        if isinstance(param_def, SelectParameter):
            for display, v in param_def.options:
                if v == value:
                    return str(display)
            return str(value)
        if isinstance(param_def, ColumnSelectParameter):
            return "" if value is None else str(value)
        if isinstance(param_def, NumericParameter):
            try:
                if param_def.decimal_places == 0:
                    return str(int(value))
                return f"{float(value):.{param_def.decimal_places}f}"
            except Exception:
                return str(value)
        return str(value)

    def _reset_selected_dynamic_param(self) -> None:
        tree = getattr(self.app, "dynamic_params_tree", None)
        if tree is None:
            return

        method_key = self._get_selected_method_key_safe()
        if not method_key:
            return

        selection = tree.selection()
        if not selection:
            return

        param_name = selection[0]
        param_def = self.app.dynamic_params_defs.get(param_name)
        if not param_def:
            return

        self._set_dynamic_param_value(method_key, param_name, param_def.default_value)
        tree.item(param_name, values=(param_def.display_name, self._format_param_value(param_def, param_def.default_value)))

        try:
            if hasattr(self.app, 'on_parameter_change'):
                self.app.on_parameter_change()
        except Exception:
            pass

    def _on_dynamic_param_single_click(self, event=None):
        # Clicking elsewhere should commit/cancel the in-place editor.
        self._commit_dynamic_param_cell_edit()

    def _on_dynamic_param_double_click(self, event) -> None:
        tree = getattr(self.app, "dynamic_params_tree", None)
        if tree is None:
            return

        region = tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        col = tree.identify_column(event.x)
        if col != "#2":
            return

        row_iid = tree.identify_row(event.y)
        if not row_iid:
            return

        method_key = self._get_selected_method_key_safe()
        if not method_key:
            return

        param_name = row_iid
        param_def = self.app.dynamic_params_defs.get(param_name)
        if not param_def:
            return

        # Bool: toggle immediately
        from config import BoolParameter, SelectParameter, OptionalNumericParameter, ColumnSelectParameter
        current_value = self._get_dynamic_params_for_method(method_key).get(param_name, param_def.default_value)
        if isinstance(param_def, BoolParameter):
            new_value = not bool(current_value)
            ok, msg = param_def.validate_value(new_value)
            if not ok:
                messagebox.showerror("Parameter Validation Error", msg or "Invalid value")
                return
            self._set_dynamic_param_value(method_key, param_name, new_value)
            tree.item(param_name, values=(param_def.display_name, self._format_param_value(param_def, new_value)))
            try:
                if hasattr(self.app, 'on_parameter_change'):
                    self.app.on_parameter_change()
            except Exception:
                pass
            return

        # Start an in-place editor
        self._cancel_dynamic_param_cell_edit()
        bbox = tree.bbox(row_iid, "value")
        if not bbox:
            return
        x, y, width, height = bbox

        if isinstance(param_def, SelectParameter):
            display_values = [display for display, _ in param_def.options]
            editor = ttk.Combobox(tree, values=display_values, state="readonly")
            current_display = next((d for d, v in param_def.options if v == current_value), display_values[0] if display_values else "")
            editor.set(str(current_display))
            editor.place(x=x, y=y, width=width, height=height)
            editor.focus_set()
            editor.bind("<<ComboboxSelected>>", lambda _e: self._commit_dynamic_param_cell_edit())
        elif isinstance(param_def, ColumnSelectParameter):
            # Prefer dropdown from currently loaded CSV headers.
            # If headers aren't available yet, fall back to a free-text entry.
            available_columns = getattr(self.app, 'available_columns', None)
            if isinstance(available_columns, list) and available_columns:
                editor = ttk.Combobox(tree, values=available_columns, state="readonly")
                if current_value is not None and str(current_value) in available_columns:
                    editor.set(str(current_value))
                else:
                    editor.set("")
                editor.place(x=x, y=y, width=width, height=height)
                editor.focus_set()
                editor.bind("<<ComboboxSelected>>", lambda _e: self._commit_dynamic_param_cell_edit())
            else:
                editor = ttk.Entry(tree)
                editor.insert(0, "" if current_value is None else str(current_value))
                editor.place(x=x, y=y, width=width, height=height)
                editor.focus_set()
                editor.selection_range(0, tk.END)
                editor.bind("<Return>", lambda _e: self._commit_dynamic_param_cell_edit())
        else:
            editor = ttk.Entry(tree)
            if isinstance(param_def, OptionalNumericParameter) and current_value is None:
                editor.insert(0, "")
            else:
                editor.insert(0, str(current_value))
            editor.place(x=x, y=y, width=width, height=height)
            editor.focus_set()
            editor.selection_range(0, tk.END)
            editor.bind("<Return>", lambda _e: self._commit_dynamic_param_cell_edit())

        editor.bind("<Escape>", lambda _e: self._cancel_dynamic_param_cell_edit())
        editor.bind("<FocusOut>", lambda _e: self._commit_dynamic_param_cell_edit())

        self.app.dynamic_params_cell_editor = {
            "widget": editor,
            "param_name": param_name,
            "method_key": method_key,
        }

    def _cancel_dynamic_param_cell_edit(self) -> None:
        editor_state = getattr(self.app, "dynamic_params_cell_editor", None)
        if not editor_state or not editor_state.get("widget"):
            return
        try:
            editor_state["widget"].destroy()
        except Exception:
            pass
        self.app.dynamic_params_cell_editor = {"widget": None, "param_name": None, "method_key": None}

    def _commit_dynamic_param_cell_edit(self) -> None:
        editor_state = getattr(self.app, "dynamic_params_cell_editor", None)
        tree = getattr(self.app, "dynamic_params_tree", None)
        if not editor_state or tree is None:
            return
        widget = editor_state.get("widget")
        if widget is None:
            return

        method_key = editor_state.get("method_key")
        param_name = editor_state.get("param_name")
        if not method_key or not param_name:
            self._cancel_dynamic_param_cell_edit()
            return

        param_def = self.app.dynamic_params_defs.get(param_name)
        if not param_def:
            self._cancel_dynamic_param_cell_edit()
            return

        try:
            value = self._read_inline_editor_value(param_def, widget)
        except Exception as e:
            messagebox.showerror("Invalid Value", str(e))
            try:
                widget.focus_set()
            except Exception:
                pass
            return

        ok, msg = param_def.validate_value(value)
        if not ok:
            messagebox.showerror("Parameter Validation Error", msg or "Invalid value")
            try:
                widget.focus_set()
            except Exception:
                pass
            return

        # If this is a column selector and headers are available, enforce membership.
        try:
            from config import ColumnSelectParameter
            if isinstance(param_def, ColumnSelectParameter):
                available_columns = getattr(self.app, 'available_columns', None)
                if isinstance(available_columns, list) and available_columns:
                    col_name = ("" if value is None else str(value)).strip()
                    if col_name and col_name not in available_columns:
                        messagebox.showerror(
                            "Parameter Validation Error",
                            f"{param_def.display_name} must be a column from the loaded data file",
                        )
                        try:
                            widget.focus_set()
                        except Exception:
                            pass
                        return
        except Exception:
            # Non-fatal; fall back to method-level validation.
            pass

        self._set_dynamic_param_value(method_key, param_name, value)
        tree.item(param_name, values=(param_def.display_name, self._format_param_value(param_def, value)))

        self._cancel_dynamic_param_cell_edit()

        try:
            if hasattr(self.app, 'on_parameter_change'):
                self.app.on_parameter_change()
        except Exception:
            pass

    def _read_inline_editor_value(self, param_def, widget):
        from config import NumericParameter, OptionalNumericParameter, SelectParameter, ColumnSelectParameter

        if isinstance(param_def, SelectParameter):
            display = widget.get()
            for d, v in param_def.options:
                if str(d) == str(display):
                    return v
            raise ValueError(f"Invalid selection for {param_def.display_name}")

        if isinstance(param_def, ColumnSelectParameter):
            return widget.get().strip()

        text = widget.get().strip()

        if isinstance(param_def, OptionalNumericParameter):
            if not text or text.lower() in ("none", "(none)", "null"):
                return None
            try:
                num = float(text)
            except Exception:
                raise ValueError(f"{param_def.display_name} must be a valid number or None")
            if param_def.decimal_places == 0:
                if not float(num).is_integer():
                    raise ValueError(f"{param_def.display_name} must be an integer or None")
                return int(num)
            return round(num, param_def.decimal_places)

        if isinstance(param_def, NumericParameter):
            try:
                num = float(text)
            except Exception:
                raise ValueError(f"{param_def.display_name} must be a valid number")
            if param_def.decimal_places == 0:
                if not float(num).is_integer():
                    raise ValueError(f"{param_def.display_name} must be an integer")
                return int(num)
            return round(num, param_def.decimal_places)

        # TextParameter and other string-like values
        return text
    
    def _create_basic_ga_section(self, parent, row):
        """Create basic genetic algorithm parameters section."""
        ga_frame = ttk.LabelFrame(parent, text="Genetic Algorithm Parameters", padding="5")
        ga_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        # Global parameters shared across all optimization methods
        basic_params = [
            ("Population Size:", self.app.population_size, "pop_size_entry"),
            ("Generations:", self.app.num_generations, "generations_entry"), 
            ("Crossover Rate (0-1):", self.app.crossover_rate, "crossover_rate_entry"),
            ("Mutation Rate (0-1):", self.app.mutation_rate, "mutation_rate_entry")
        ]
        
        for i, (label, var, attr_name) in enumerate(basic_params):
            ttk.Label(ga_frame, text=label).grid(row=i, column=0, sticky="w")
            entry = ttk.Entry(ga_frame, textvariable=var, width=ui_config.entry_field_width_small)
            entry.grid(row=i, column=1, sticky="w", padx=ui_config.standard_padding_x)
            setattr(self.app, attr_name, entry)
        
        return ga_frame
    
    def _create_single_objective_section(self, parent, row):
        """Create single-objective specific parameters section."""  
        single_frame = ttk.LabelFrame(parent, text="Single-Objective Parameters", padding="5")
        single_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        # Elite ratio parameter (only for single-objective methods)
        ttk.Label(single_frame, text="Elite Ratio (0-1):").grid(row=0, column=0, sticky="w")
        elite_entry = ttk.Entry(single_frame, textvariable=self.app.elite_ratio, 
                               width=ui_config.entry_field_width_small)
        elite_entry.grid(row=0, column=1, sticky="w", padx=ui_config.standard_padding_x)
        self.app.elite_ratio_entry = elite_entry
        
        return single_frame
    
    def _create_constraint_params_section(self, parent, row):
        """Create constraint-specific parameters section."""
        constraint_frame = ttk.LabelFrame(parent, text="Constraint Parameters", padding="5")
        constraint_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        # Constraint parameters
        constraint_params = [
            ("Target Avg Length (miles):", self.app.target_avg_length, "target_length_entry"),
            ("Length Tolerance:", self.app.length_tolerance, "tolerance_entry"),
            ("Penalty Weight:", self.app.penalty_weight, "penalty_entry")
        ]
        
        for i, (label, var, attr_name) in enumerate(constraint_params):
            ttk.Label(constraint_frame, text=label).grid(row=i, column=0, sticky="w")
            entry = ttk.Entry(constraint_frame, textvariable=var, width=ui_config.entry_field_width_small)
            entry.grid(row=i, column=1, sticky="w", padx=ui_config.standard_padding_x)
            setattr(self.app, attr_name, entry)
        
        return constraint_frame
    
    def _update_dynamic_parameters(self):
        """Update parameter widgets dynamically based on selected method."""
        try:
            # Save current parameter values BEFORE clearing widgets
            current_values = {}
            if hasattr(self.app, 'parameter_values'):
                for param_name, widget_info in self.app.parameter_values.items():
                    try:
                        widget = widget_info['widget']
                        param_def = widget_info['param_def']
                        current_values[param_name] = self._extract_widget_value(widget, param_def)
                    except Exception:
                        # Skip parameters that can't be extracted
                        pass
            
            # Get selected method configuration
            selected_display_name = self.app.method_dropdown.get()
            method_key = get_method_key_from_display_name(selected_display_name)
            
            from config import get_optimization_method
            method_config = get_optimization_method(method_key)
            
            # Update method description
            self.app.method_description.config(text=method_config.description)
            
            # Generate dynamic parameter widgets
            self.create_dynamic_parameter_widgets(self.app.params_container, method_key)
            
            # Restore parameter values AFTER widgets are created
            if current_values and hasattr(self.app, 'parameter_values'):
                for param_name, value in current_values.items():
                    if param_name in self.app.parameter_values:
                        try:
                            widget_info = self.app.parameter_values[param_name]
                            widget = widget_info['widget']
                            param_def = widget_info['param_def']
                            param_def.set_widget_value(widget, value)
                        except Exception as e:
                            # Skip parameters that can't be restored
                            if hasattr(self.app, 'handle_error'):
                                self.app.handle_error(f"Could not restore parameter '{param_name}'", e, severity="warning", show_messagebox=False)
                            elif hasattr(self.app, 'log_message'):
                                self.app.log_message(f"Warning: Could not restore parameter '{param_name}': {e}")
                            else:
                                print(f"Warning: Could not restore {param_name}: {e}")
            
        except (ValueError, AttributeError) as e:
            # Handle case where method is not found or dropdown not ready
            if hasattr(self.app, 'handle_error'):
                self.app.handle_error("Error updating dynamic parameters", e, severity="warning", show_messagebox=False)
            else:
                print(f"Error updating dynamic parameters: {e}")
            # Fallback to first method if current selection fails
            if hasattr(self.app, 'method_dropdown') and self.app.method_dropdown.get():
                try:
                    method_names = self.get_method_display_names()
                    if method_names:
                        self.app.method_dropdown.set(method_names[0])
                        self._update_dynamic_parameters()
                except Exception as e:
                    # Non-fatal fallback failure; keep UI responsive.
                    if hasattr(self.app, 'handle_error'):
                        self.app.handle_error(
                            "Could not fall back to first method",
                            e,
                            severity="warning",
                            show_messagebox=False,
                        )
                    elif hasattr(self.app, 'log_message'):
                        self.app.log_message(f"Warning: Could not fall back to first method: {e}")
                    else:
                        print(f"Warning: Could not fall back to first method: {e}")
    
    def _toggle_parameter_sections(self, required_sections):
        """Show/hide parameter sections based on required sections list."""
        # Basic GA parameters are always shown
        if hasattr(self.app, 'basic_ga_frame'):
            self.app.basic_ga_frame.grid()
        
        # Single-objective parameters (for single and constrained methods)
        if hasattr(self.app, 'single_objective_frame'):
            if "single_objective" in required_sections:
                self.app.single_objective_frame.grid()
            else:
                self.app.single_objective_frame.grid_remove()
        
        # Constraint parameters (only for constrained method)
        if hasattr(self.app, 'constraint_params_frame'):
            if "constraint_params" in required_sections:
                self.app.constraint_params_frame.grid()
            else:
                self.app.constraint_params_frame.grid_remove()
    
    def create_performance_section(self, parent, row):
        """Create the performance and caching controls section."""
        perf_frame = ttk.LabelFrame(parent, text="⚡ Performance & Caching", padding="6")  # Reduced from 10
        perf_frame.grid(row=row, column=0, sticky="ew", pady=3)  # Reduced from 5
        
        # Cache management (other performance settings now handled by dynamic parameters)
        cache_frame = ttk.Frame(perf_frame)
        cache_frame.grid(row=0, column=0, sticky="ew", pady=(5, 0))  # Reduced from (10, 0)
        
        ttk.Label(cache_frame, text="Cache clear interval (generations):").grid(row=0, column=0, sticky="w")
        ttk.Entry(cache_frame, textvariable=self.app.cache_clear_interval, 
                 width=ui_config.entry_field_width_small).grid(row=0, column=1, sticky="w", 
                                                              padx=ui_config.standard_padding_x)
        
        return row + 1
    
    # create_save_load_section method removed - now integrated into create_file_operations_section
    
    def create_action_buttons(self, parent, row):
        """Create the main action buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, sticky="ew", pady=10)  # Reduced from 20
        
        # Main action buttons
        self.app.start_button = ttk.Button(button_frame, text="🚀 Start Optimization", 
                                          command=self.app.start_optimization, 
                                          style="Accent.TButton")
        self.app.start_button.grid(row=0, column=0, padx=(0, 10))
        
        self.app.stop_button = ttk.Button(button_frame, text="⏹ Stop", 
                                         command=self.app.stop_optimization, state="disabled")
        self.app.stop_button.grid(row=0, column=1)
        
        return row + 1
    
    def create_right_pane_actions(self, parent):
        """Create action buttons for the right pane."""
        top_right_frame = ttk.Frame(parent)
        top_right_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))  # Reduced from (0, 10)
        top_right_frame.columnconfigure(0, weight=1)
        
        # Action button frame
        actions_frame = ttk.Frame(top_right_frame)
        actions_frame.grid(row=0, column=0)
        
        # Main optimization control buttons
        self.app.start_button = ttk.Button(actions_frame, text="🚀 Start Optimization", 
                                          command=self.app.start_optimization, 
                                          style="Accent.TButton")
        self.app.start_button.grid(row=0, column=0, padx=(0, 5))
        
        self.app.stop_button = ttk.Button(actions_frame, text="⏹ Stop", 
                                         command=self.app.stop_optimization, state="disabled")
        self.app.stop_button.grid(row=0, column=1, padx=(0, 10))
        
        # Results button
        ttk.Button(actions_frame, text="📊 Load & Plot Results", 
                  command=self.app.load_and_plot_results).grid(row=0, column=2, padx=(0, 5))
        
        # Help button
        ttk.Button(actions_frame, text="❓ Help", 
                  command=self.app.show_help).grid(row=0, column=3, padx=(0, 5))
        
        # Exit button
        def exit_clicked():
            self.app._on_closing()
        
        ttk.Button(actions_frame, text="❌ Exit", 
                  command=exit_clicked).grid(row=0, column=4, padx=(0, 5))
        
        return top_right_frame
    
    def create_results_section(self, parent):
        """Create the results display section with tabbed interface."""
        results_container = ttk.Frame(parent)
        results_container.grid(row=1, column=0, sticky="nsew")
        results_container.columnconfigure(0, weight=1)
        results_container.rowconfigure(0, weight=1)
        
        # Notebook for tabs
        self.app.results_notebook = ttk.Notebook(results_container)
        self.app.results_notebook.grid(row=0, column=0, sticky="nsew")
        
        # Tab 1: Optimization Log
        log_frame = ttk.Frame(self.app.results_notebook)
        self.app.results_notebook.add(log_frame, text="Optimization Log")
        
        # Text widget with scrollbar for optimization log
        # Check if results_text already exists from early initialization
        existing_content = ""
        if hasattr(self.app, 'results_text') and self.app.results_text is not None:
            # Save existing content and destroy the temporary widget
            try:
                existing_content = self.app.results_text.get(1.0, tk.END)
                self.app.results_text.destroy()
            except (tk.TclError, AttributeError):
                pass  # Ignore errors if widget is already destroyed
        
        # Create the proper results_text widget in the correct location
        self.app.results_text = tk.Text(log_frame, wrap=tk.WORD)
        
        # Restore any existing content
        if existing_content.strip():
            self.app.results_text.insert(1.0, existing_content)
        
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.app.results_text.yview)
        self.app.results_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.app.results_text.grid(row=0, column=0, sticky="nsew")
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        # Tab 2: Results Files
        results_file_frame = ttk.Frame(self.app.results_notebook)
        self.app.results_notebook.add(results_file_frame, text="Results Files")
        
        # Text widget for results files
        self.app.results_file_text = tk.Text(results_file_frame, wrap=tk.WORD, state=tk.DISABLED)
        file_scrollbar = ttk.Scrollbar(results_file_frame, orient="vertical", command=self.app.results_file_text.yview)
        self.app.results_file_text.configure(yscrollcommand=file_scrollbar.set)
        
        self.app.results_file_text.grid(row=0, column=0, sticky="nsew")
        file_scrollbar.grid(row=0, column=1, sticky="ns")
        
        results_file_frame.grid_rowconfigure(0, weight=1)
        results_file_frame.grid_columnconfigure(0, weight=1)
        
        return results_container
    
    def create_tooltip(self, widget, text):
        """Create a tooltip for the given widget."""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = tk.Label(tooltip, text=text, justify='left',
                           background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                           font=("Arial", 9))
            label.pack(ipadx=1)
            
            widget._tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, '_tooltip'):
                widget._tooltip.destroy()
                del widget._tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)


    # ===== DYNAMIC PARAMETER UI GENERATION =====
    # These functions create UI widgets dynamically from parameter definitions
    
    def get_method_display_names(self):
        """Get list of method display names for dropdown."""
        from config import OPTIMIZATION_METHODS
        return [method.display_name for method in OPTIMIZATION_METHODS]
    
    def get_parameter_groups_for_method(self, method_key: str):
        """Get parameters organized by group for a specific method."""
        from config import get_optimization_method
        try:
            method_config = get_optimization_method(method_key)
            groups = {}
            
            # Group parameters by their group field
            for param in method_config.parameters:
                group_name = param.group
                if group_name not in groups:
                    groups[group_name] = []
                groups[group_name].append(param)
            
            # Sort parameters within each group by order field
            for group_name in groups:
                groups[group_name].sort(key=lambda p: p.order)
                
            return groups
            
        except (ValueError, AttributeError) as e:
            print(f"Error getting parameter groups for method {method_key}: {e}")
            return {}
    
    def create_dynamic_parameter_widgets(self, parent, method_key: str):
        """Create parameter widgets dynamically for the specified method."""
        from config import BoolParameter
        
        # Clear any existing parameter widgets
        if hasattr(self.app, 'dynamic_param_widgets'):
            for widget in self.app.dynamic_param_widgets:
                widget.destroy()
        
        self.app.dynamic_param_widgets = []
        self.app.parameter_values = {}  # Store parameter widgets for value retrieval
        
        # Get grouped parameters
        parameter_groups = self.get_parameter_groups_for_method(method_key)
        
        current_row = 0
        for group_name, parameters in parameter_groups.items():
            # Create group frame
            group_frame = ttk.LabelFrame(parent, text=self._format_group_name(group_name), padding="6")  # Reduced from 10
            group_frame.grid(row=current_row, column=0, columnspan=2, sticky="ew", pady=(5, 0))  # Reduced from (10, 0)
            group_frame.columnconfigure(1, weight=1)
            
            self.app.dynamic_param_widgets.append(group_frame)
            
            # Create widgets for each parameter in the group  
            param_row = 0
            for param in parameters:
                # Create label
                label = ttk.Label(group_frame, text=param.display_name + ":")
                label.grid(row=param_row, column=0, sticky="w", pady=2)
                
                # Create widget based on parameter type
                widget = self._create_parameter_widget(group_frame, param)
                widget.grid(row=param_row, column=1, sticky="w", padx=(10, 0), pady=2)
                
                # Store widget for value retrieval
                # For BoolParameter, store the BooleanVar rather than the Checkbutton
                if isinstance(param, BoolParameter):
                    stored_widget = widget._var  # Store the BooleanVar for consistent set/get operations
                else:
                    stored_widget = widget
                    
                self.app.parameter_values[param.name] = {
                    'widget': stored_widget,
                    'param_def': param
                }
                
                # Create tooltip for the parameter
                self.create_tooltip(widget, param.description)
                
                param_row += 1
            
            current_row += 1
        
        return current_row
    
    def _create_parameter_widget(self, parent, param_def):
        """Create appropriate widget based on parameter definition type."""
        from config import NumericParameter, OptionalNumericParameter, SelectParameter, BoolParameter, TextParameter
        
        if isinstance(param_def, NumericParameter):
            # Create entry widget for numeric parameters
            widget = ttk.Entry(parent, width=param_def.widget_width)
            # Set default value
            if param_def.decimal_places == 0:
                widget.insert(0, str(int(param_def.default_value)))
            else:
                widget.insert(0, f"{param_def.default_value:.{param_def.decimal_places}f}")
            return widget

        elif isinstance(param_def, OptionalNumericParameter):
            # Create entry widget for optional numeric parameters (can be None)
            widget = ttk.Entry(parent, width=param_def.widget_width)
            try:
                param_def.set_widget_value(widget, param_def.default_value)
            except Exception:
                widget.insert(0, str(param_def.default_value))
            return widget
            
        elif isinstance(param_def, SelectParameter):
            # Create combobox for selection parameters
            values = [display for display, value in param_def.options]
            widget = ttk.Combobox(parent, values=values, state="readonly", width=25)
            # Set default display value
            default_display = next((display for display, val in param_def.options 
                                  if val == param_def.default_value), 
                                 param_def.options[0][0] if param_def.options else "")
            widget.set(default_display)
            return widget
            
        elif isinstance(param_def, BoolParameter):
            # Create checkbutton for boolean parameters
            var = tk.BooleanVar(value=param_def.default_value)
            widget = ttk.Checkbutton(parent, variable=var)
            widget._var = var  # Store variable reference for retrieval
            return widget
            
        elif isinstance(param_def, TextParameter):
            # Create entry widget for text parameters
            if param_def.multiline:
                widget = tk.Text(parent, width=param_def.widget_width, height=3)
                widget.insert("1.0", str(param_def.default_value))
            else:
                widget = ttk.Entry(parent, width=param_def.widget_width)
                widget.insert(0, str(param_def.default_value))
            return widget
            
        else:
            # Fallback to simple entry
            widget = ttk.Entry(parent, width=20)
            widget.insert(0, str(param_def.default_value))
            return widget
    
    def _format_group_name(self, group_name: str) -> str:
        """Convert group name to user-friendly display format."""
        # Convert snake_case to Title Case
        formatted = group_name.replace('_', ' ').title()
        
        # Add icons for visual appeal
        icons = {
            'Segment Constraints': '📏 Segment Constraints',
            'Genetic Algorithm': '🧬 Genetic Algorithm', 
            'Performance': '⚡ Performance',
            'Constraints': '🎯 Constraints',
            'Algorithm': '🔬 Algorithm'
        }
        
        return icons.get(formatted, formatted)
    
    def get_parameter_values(self):
        """Return current dynamic parameter values for the selected method.

        NOTE: This method is used by controller/validation/save-load paths.
        The source of truth is the settings-backed store populated by the
        Treeview/editor UI.
        """
        method_key = self._get_selected_method_key_safe()
        if not method_key:
            return {}
        return self._get_dynamic_params_for_method(method_key)
    
    def _extract_widget_value(self, widget, param_def):
        """Extract value from widget based on parameter definition type."""
        from config import NumericParameter, OptionalNumericParameter, SelectParameter, BoolParameter, TextParameter
        
        if isinstance(param_def, NumericParameter):
            value = float(widget.get())
            return int(value) if param_def.decimal_places == 0 else value

        elif isinstance(param_def, OptionalNumericParameter):
            # Delegate parsing so blank / 'None' / '(None)' become None
            return param_def.get_widget_value(widget)
            
        elif isinstance(param_def, SelectParameter):
            display_text = widget.get()
            # Find corresponding value
            for display, value in param_def.options:
                if display == display_text:
                    return value
            return param_def.default_value
            
        elif isinstance(param_def, BoolParameter):
            # Widget is now the BooleanVar directly
            return widget.get()
            
        elif isinstance(param_def, TextParameter):
            if hasattr(widget, 'get'):
                if callable(getattr(widget, 'get')):
                    # Entry widget
                    return widget.get()
                else:
                    # Text widget
                    return widget.get("1.0", tk.END).strip()
            return str(param_def.default_value)
            
        else:
            return widget.get()
    
    def validate_parameter_values(self, method_key: str):
        """Validate all parameter values for the given method."""
        from config import get_optimization_method
        
        try:
            method_config = get_optimization_method(method_key)
            values = self.get_parameter_values()
            validation_errors = []
            
            for param in method_config.parameters:
                if param.name in values:
                    is_valid, error_msg = param.validate_value(values[param.name])
                    if not is_valid:
                        validation_errors.append(error_msg)
                        
            return validation_errors
            
        except Exception as e:
            return [f"Validation error: {e}"]