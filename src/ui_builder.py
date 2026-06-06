"""GUI widget construction for the Highway Segmentation application.

Separates widget creation logic from the main application class.
"""

import logging
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from config import (
    UIConfig,
    get_optimization_method_names,
    get_method_key_from_display_name,
    get_preprocessing_method_names,
    get_preprocessing_method_key_from_display_name,
    get_optimization_method
)
from data_sources.type_registry import get_display_names as get_source_type_display_names
from value_parsing import parse_optional_float, parse_optional_int
from route_utils import ROUTE_COLUMN_NONE_SENTINEL
from parameter_tree_view import ParameterTreeView, DEFAULT_TREEVIEW_HEIGHT
from tooltip import ParameterTreeTooltip, attach_tooltip

logger = logging.getLogger(__name__)

ui_config = UIConfig()


class MethodConfigurationPanel(ttk.Frame):
    """
    Reusable collapsible panel for configuring a preprocessing or optimization method.
    
    Features:
    - Method dropdown at top with collapsible arrow
    - Parameters displayed in Treeview with inline editing (double-click to edit)
    - Collapsible sections (▶/▼) to reduce clutter
    - Auto-expands when method is selected
    - Consistent look and feel across all configurations
    """
    
    def __init__(self, parent, panel_title, app, method_registry_type="preprocessing", **kwargs):
        """
        Initialize a method configuration panel.
        
        Args:
            parent: Parent widget
            panel_title: Display title for the panel (e.g., "Primary Preprocessing")
            app: Main application instance
            method_registry_type: "preprocessing" or "optimization" (determines which methods to list)
            **kwargs: Additional arguments passed to ttk.Frame
        """
        super().__init__(parent, **kwargs)
        
        self.panel_title = panel_title
        self.app = app
        self.method_registry_type = method_registry_type
        self.is_expanded = False  # Start collapsed
        self.method_var = tk.StringVar(value="None")
        self._saved_parameters = {}  # {method_key: {param_name: value}} - persist params when switching
        self._current_method_key = None
        
        # Will be created in _create_ui
        self.param_tree_view = None
        
        self._create_ui()
    
    def _create_ui(self):
        """Create the panel UI elements."""
        self.columnconfigure(0, weight=1)
        
        # Header frame with arrow and method dropdown
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        header_frame.columnconfigure(2, weight=1)  # Dropdown column expands
        
        # Collapsible arrow (clickable label)
        self.arrow_label = ttk.Label(header_frame, text="▶", cursor="hand2", width=2)
        self.arrow_label.grid(row=0, column=0, sticky="w")
        self.arrow_label.bind("<Button-1>", lambda e: self.toggle_collapse())
        
        # Panel title and method selection dropdown
        title_method_label = ttk.Label(header_frame, text=f"{self.panel_title}")
        title_method_label.grid(row=0, column=1, sticky="w", padx=(5, 5))
        
        # Get method names from registry
        if self.method_registry_type == "preprocessing":
            method_names = ["None"] + get_preprocessing_method_names()
        else:  # optimization
            method_names = get_optimization_method_names()
        
        self.method_dropdown = ttk.Combobox(header_frame, textvariable=self.method_var,
                                            values=method_names, state="readonly", width=30)
        self.method_dropdown.grid(row=0, column=2, sticky="ew", padx=(0, 5))
        self.method_dropdown.bind('<<ComboboxSelected>>', self._on_method_changed)
        
        # Method description (dynamic based on selection)
        self.description_label = ttk.Label(header_frame, text="", foreground="gray", 
                                          wraplength=400, justify="left")
        self.description_label.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(3, 0))
        # Start hidden - will show when method is selected
        self.description_label.grid_remove()
        
        # Parameters container (collapsible)
        self.params_container = ttk.Frame(self)
        self.params_container.grid(row=1, column=0, sticky="nsew", padx=(20, 0))
        self.params_container.grid_columnconfigure(0, weight=1)
        self.params_container.grid_rowconfigure(1, weight=1)
        
        # Start collapsed - hide the content
        self.params_container.grid_remove()
        
        # Parameters label
        params_label = ttk.Label(self.params_container, text="Parameters (double-click value to edit):", 
                                font=("TkDefaultFont", 9))
        params_label.grid(row=0, column=0, sticky="w", pady=(0, 2))
        
        # Create Parameter TreeView
        self.param_tree_view = ParameterTreeView(
            self.params_container, 
            self.app,
            height=DEFAULT_TREEVIEW_HEIGHT,
            on_change_callback=self._on_parameter_change
        )
        self.param_tree_view.frame.grid(row=1, column=0, sticky="nsew")
        
        # Reset button
        button_frame = ttk.Frame(self.params_container)
        button_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        ttk.Button(button_frame, text="Reset Selected to Default", 
                  command=self.param_tree_view.reset_selected_to_default).pack(side="left")
    
    def _on_method_changed(self, event=None, auto_expand=True):
        """Handle method selection change.
        
        Args:
            event: Event object from Combobox selection (optional)
            auto_expand: Whether to auto-expand the panel when method is selected (default True)
        """
        method_name = self.method_var.get()
        
        # Step 1: Persist current method's parameters before switching.
        # Write to both _saved_parameters (in-memory) and app.settings (persistent store)
        # so that changes are not lost if the debounced save fires after the method switch.
        if self._current_method_key and self.param_tree_view:
            outgoing_params = self.param_tree_view.get_values()
            self._saved_parameters[self._current_method_key] = outgoing_params
            # For analysis methods: flush directly into the settings dict so the
            # outgoing params are captured regardless of debounce timing.
            if self.method_registry_type == 'optimization' and outgoing_params:
                try:
                    if hasattr(self.app, 'settings'):
                        opt = self.app.settings.setdefault('optimization', {})
                        store = opt.setdefault('dynamic_parameters_by_method', {})
                        store[self._current_method_key] = outgoing_params
                except Exception:
                    pass
        
        # Step 2: Handle "None" selection
        if method_name == "None":
            self._current_method_key = None
            self.description_label.config(text="")
            self.description_label.grid_remove()  # Hide description
            if self.param_tree_view:
                self.param_tree_view.tree.delete(*self.param_tree_view.tree.get_children())
            if self.is_expanded:
                self.toggle_collapse()
            return
        
        # Step 3: Auto-expand when method is selected (if enabled)
        if auto_expand and not self.is_expanded:
            self.toggle_collapse()
        
        # Step 4: Get method config and update description
        try:
            if self.method_registry_type == "preprocessing":
                method_key = get_preprocessing_method_key_from_display_name(method_name)
                from config import get_preprocessing_method
                method_config = get_preprocessing_method(method_key)
            else:  # optimization
                method_key = get_method_key_from_display_name(method_name)
                method_config = get_optimization_method(method_key)
            
            self._current_method_key = method_key
            
            # Update description and show it if there's content (visible even when collapsed)
            if hasattr(method_config, 'description') and method_config.description:
                self.description_label.config(text=method_config.description)
                self.description_label.grid()  # Show description even when collapsed
            else:
                self.description_label.config(text="")
                self.description_label.grid_remove()
                
        except Exception as e:
            if hasattr(self.app, 'log_message'):
                self.app.log_message(f"Warning: Could not load method config for {method_name}: {e}")
            return
        
        # Step 5: Refresh parameter tree view
        try:
            # Use saved parameters if available, otherwise defaults
            param_values = self._saved_parameters.get(method_key, None)
            self.param_tree_view.refresh(method_key, self.method_registry_type, param_values)
        except Exception as e:
            if hasattr(self.app, 'log_message'):
                self.app.log_message(f"Warning: Could not load parameters for {method_name}: {e}")
    
    def _on_parameter_change(self):
        """Trigger debounced settings save whenever any parameter value changes."""
        if hasattr(self.app, 'on_parameter_change'):
            self.app.on_parameter_change()
    
    def toggle_collapse(self):
        """Toggle the collapsed/expanded state."""
        if self.is_expanded:
            # Collapse: hide parameters only (keep description visible)
            self.params_container.grid_remove()
            self.arrow_label.config(text="▶")
            self.is_expanded = False
        else:
            # Expand: show parameters
            self.params_container.grid()
            self.arrow_label.config(text="▼")
            self.is_expanded = True
    
    def get_method_key(self):
        """Get the selected method key (or None)."""
        method_name = self.method_var.get()
        if method_name == "None":
            return None
        
        try:
            if self.method_registry_type == "preprocessing":
                return get_preprocessing_method_key_from_display_name(method_name)
            else:
                return get_method_key_from_display_name(method_name)
        except Exception:
            return None
    
    def get_parameters(self):
        """Get the current parameter values as a dictionary."""
        if not self.param_tree_view or not self._current_method_key:
            return {}
        return self.param_tree_view.get_values()
    
    def set_method(self, method_key, parameters=None, expand=False):
        """
        Set the method and parameters programmatically.
        
        Args:
            method_key: Method key to select (or None for "None")
            parameters: Optional dict of parameter values
            expand: Whether to auto-expand the panel (default False for programmatic calls)
        """
        if not method_key:
            self.method_var.set("None")
            self._on_method_changed(auto_expand=False)
            return
        
        try:
            if self.method_registry_type == "preprocessing":
                from config import get_preprocessing_method
                method_config = get_preprocessing_method(method_key)
                self.method_var.set(method_config.display_name)
            else:  # optimization
                method_config = get_optimization_method(method_key)
                self.method_var.set(method_config.display_name)
            
            # Store parameters if provided
            if parameters:
                self._saved_parameters[method_key] = parameters
            
            self._on_method_changed(auto_expand=expand)
                        
        except Exception as e:
            if hasattr(self.app, 'log_message'):
                self.app.log_message(f"Warning: Could not set method configuration: {e}")
    
    def clear_saved_parameters(self):
        """Clear all saved parameter values (useful for reset functionality)."""
        self._saved_parameters.clear()
    
    def get_saved_parameters(self, method_key):
        """Get saved parameters for a specific method key."""
        return self._saved_parameters.get(method_key, {})


class UIBuilder:
    """Builds and configures all Tkinter widgets for the main application window."""

    def __init__(self, main_app):
        """Initialize the UI builder.

        Args:
            main_app: Reference to the main HighwaySegmentationGUI instance.
        """
        self.app = main_app
    
    def create_main_layout(self):
        """Create the main application layout structure."""
        self.app.root.grid_rowconfigure(0, weight=1)
        self.app.root.columnconfigure(0, weight=1)

        main_frame = ttk.Frame(self.app.root, padding=ui_config.main_padding)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=0, minsize=550)  # Left pane: wider for better layout
        main_frame.grid_columnconfigure(1, weight=0)  # Scrollbar column (fixed width when visible)
        main_frame.grid_columnconfigure(2, weight=1)  # Right pane gets all remaining space

        title_label = ttk.Label(main_frame, text="Highway Segmentation Tool",
                                font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=ui_config.title_columnspan,
                         pady=ui_config.standard_padding_y)

        return main_frame
    
    def create_scrollable_left_pane(self, parent):
        """Create the left pane with scrollable content area.

        Uses a Canvas with a Scrollbar to allow all panels to be visible even when expanded.
        """

        left_container = ttk.Frame(parent)
        left_container.grid(row=1, column=0, sticky="nsew", padx=ui_config.standard_padding_x)
        left_container.grid_rowconfigure(0, weight=1)
        left_container.grid_columnconfigure(0, weight=1)

        # Create canvas for scrolling
        canvas = tk.Canvas(left_container, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        
        # Create scrollbar
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create frame inside canvas
        required_frame = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=required_frame, anchor="nw")
        
        # Configure canvas scrolling
        def on_frame_configure(event=None):
            """Update scroll region when frame size changes."""
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)
                # Only show scrollbar if content exceeds canvas height
                canvas_height = canvas.winfo_height()
                content_height = bbox[3] - bbox[1]
                if content_height > canvas_height and canvas_height > 1:
                    scrollbar.grid()
                else:
                    scrollbar.grid_remove()
        
        def on_canvas_configure(event):
            """Update frame width when canvas size changes."""
            canvas.itemconfig(canvas_window, width=event.width)
            # Re-check if scrollbar is needed when canvas resizes
            on_frame_configure()
        
        required_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        
        # Enable mousewheel scrolling only when content exceeds canvas height
        def on_mousewheel(event):
            # Check if scrolling is actually needed
            bbox = canvas.bbox("all")
            if bbox:
                canvas_height = canvas.winfo_height()
                content_height = bbox[3] - bbox[1]
                if content_height > canvas_height:
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        def unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind("<Enter>", bind_mousewheel)
        canvas.bind("<Leave>", unbind_mousewheel)
        
        required_frame.grid_columnconfigure(0, weight=1)
        
        # Store canvas reference for potential future use
        self.app.left_pane_canvas = canvas

        return required_frame
    
    def create_right_pane(self, parent):
        """Create the right pane for results and status."""
        right_pane = ttk.Frame(parent)
        right_pane.grid(row=1, column=2, sticky="nsew", padx=(10, 0))
        right_pane.grid_rowconfigure(1, weight=1)
        right_pane.grid_columnconfigure(0, weight=1)
        
        return right_pane
    
    def create_basic_setup_section(self, parent, row):
        """Create the Basic Setup section with file operations and column selections."""
        setup_frame = ttk.LabelFrame(parent, text="📋 Basic Setup", padding="6")
        setup_frame.grid(row=row, column=0, sticky="ew", pady=3)
        setup_frame.columnconfigure(1, weight=1)
        
        # Row 0: Data source type selector + Connect / Open button
        ttk.Label(setup_frame, text="Data Source:").grid(row=0, column=0, sticky="w")
        source_names = get_source_type_display_names()
        self.app.data_source_type_combo = ttk.Combobox(
            setup_frame, textvariable=self.app.data_source_type_var,
            values=source_names, state="readonly", width=20,
        )
        self.app.data_source_type_combo.set(source_names[0])
        self.app.data_source_type_var.set(source_names[0])
        self.app.data_source_type_combo.grid(
            row=0, column=1, sticky="w", padx=ui_config.standard_padding_x,
        )
        ttk.Button(
            setup_frame, text="Connect / Open",
            command=self.app.connect_or_open,
        ).grid(row=0, column=2, padx=ui_config.standard_padding_x, sticky="w")

        # Row 1: Read-only status showing what is currently connected
        ttk.Label(setup_frame, text="Connected to:").grid(
            row=1, column=0, sticky="w", pady=(3, 0),
        )
        self.app.data_entry = ttk.Entry(
            setup_frame, textvariable=self.app.data_file,
            width=ui_config.entry_field_width_large, state="readonly",
        )
        self.app.data_entry.grid(
            row=1, column=1, columnspan=2, sticky="ew",
            padx=ui_config.standard_padding_x, pady=(3, 0),
        )

        # Row 2: Route column selection (for multi-route data)
        ttk.Label(setup_frame, text="Route Column (Optional):").grid(row=2, column=0, sticky="w", pady=(5, 0))
        route_controls_frame = ttk.Frame(setup_frame)
        route_controls_frame.grid(row=2, column=1, columnspan=2, sticky="w", pady=(5, 0), padx=ui_config.standard_padding_x)

        self.app.route_column_combo = ttk.Combobox(route_controls_frame, textvariable=self.app.route_column,
                                                  width=20, state="readonly")
        self.app.route_column_combo.set(ROUTE_COLUMN_NONE_SENTINEL)
        self.app.route_column_combo.grid(row=0, column=0, sticky="w")
        self.app.route_column_combo.bind('<<ComboboxSelected>>', self.app.on_route_column_change)

        self.app.filter_routes_button = ttk.Button(route_controls_frame, text="Filter",
                                                  command=self.app.open_route_filter_dialog,
                                                  state="disabled")
        self.app.filter_routes_button.grid(row=0, column=1, padx=(3, 0))

        self.app.route_info_label = ttk.Label(route_controls_frame, text="", foreground="blue")
        self.app.route_info_label.grid(row=0, column=2, padx=(5, 0), sticky="w")

        # Row 3: X Column (Distance)
        ttk.Label(setup_frame, text="X Column (Distance):").grid(row=3, column=0, sticky="w", pady=(5, 0))
        self.app.x_column_combo = ttk.Combobox(setup_frame, textvariable=self.app.x_column,
                                              width=20, state="readonly")
        self.app.x_column_combo.set("Load data first...")
        self.app.x_column_combo.grid(row=3, column=1, sticky="w", padx=ui_config.standard_padding_x, pady=(5, 0))
        self.app.x_column_combo.bind('<<ComboboxSelected>>', self.app.on_column_change)

        # Row 4: Y Column (Data Values)
        ttk.Label(setup_frame, text="Y Column (Data Values):").grid(row=4, column=0, sticky="w", pady=(5, 0))
        self.app.y_column_combo = ttk.Combobox(setup_frame, textvariable=self.app.y_column,
                                              width=20, state="readonly")
        self.app.y_column_combo.set("Load data first...")
        self.app.y_column_combo.grid(row=4, column=1, sticky="w", padx=ui_config.standard_padding_x, pady=(5, 0))
        self.app.y_column_combo.bind('<<ComboboxSelected>>', self.app.on_column_change)

        # Row 5: Output Data File (Results)
        ttk.Label(setup_frame, text="Output Data File:").grid(row=5, column=0, sticky="w", pady=(10, 0))
        self.app.save_name_entry = ttk.Entry(setup_frame, textvariable=self.app.custom_save_name,
                                       width=ui_config.entry_field_width_large)
        self.app.save_name_entry.grid(row=5, column=1, sticky="ew", padx=ui_config.standard_padding_x, pady=(10, 0))
        ttk.Button(setup_frame, text="Browse...",
                  command=self.app.browse_save_location).grid(row=5, column=2, padx=ui_config.standard_padding_x, pady=(10, 0), sticky="w")

        # Row 6: Reset button + auto-save info
        ttk.Button(setup_frame, text="Reset to Defaults",
                  command=self.app.reset_parameters).grid(row=6, column=0, sticky="w", pady=(10, 0))

        info_label = ttk.Label(setup_frame, text="Parameters auto-save when optimization starts and on exit.",
                              font=("Arial", 8), foreground="gray")
        info_label.grid(row=6, column=1, columnspan=2, sticky="w", pady=(10, 0))
        
        return row + 1
    
    # create_parameters_section method removed - now using dynamic parameter generation
    
    def create_pregap_preprocessing_section(self, parent, row):
        """Create the Pre-Gap Preprocessing configuration panel (Step 1)."""
        self.app.pregap_preprocess_panel = MethodConfigurationPanel(
            parent,
            panel_title="1. Pre-Gap Preprocessing (optional)",
            app=self.app,
            method_registry_type="preprocessing"
        )
        self.app.pregap_preprocess_panel.grid(row=row, column=0, sticky="ew", pady=3)
        return row + 1
    
    def create_gap_analysis_section(self, parent, row):
        """Create the Gap Analysis Settings section (Step 2)."""
        gap_frame = ttk.Frame(parent)
        gap_frame.grid(row=row, column=0, sticky="ew", pady=3)
        gap_frame.columnconfigure(1, weight=1)
        
        ttk.Label(gap_frame, text=" 2. Gap Analysis - Gap Threshold (in x units):").grid(row=0, column=0, sticky="w")
        self.app.gap_threshold_entry = ttk.Entry(gap_frame, textvariable=self.app.gap_threshold, width=20)
        self.app.gap_threshold_entry.grid(row=0, column=1, sticky="w", padx=ui_config.standard_padding_x)
        attach_tooltip(
            self.app.gap_threshold_entry,
            "Minimum gap between consecutive x-axis measurements that forces a segment boundary.\n"
            "Default (10000) effectively disables gap detection. Lower values (e.g. 1.0) split\n"
            "segments wherever the data has a physical gap larger than that distance.",
        )

        return row + 1
    
    def create_primary_attribute_breaks_section(self, parent, row):
        """Create the Primary Attribute Breaks section (Step 3)."""
        attr_frame = ttk.Frame(parent)
        attr_frame.grid(row=row, column=0, sticky="ew", pady=3)
        attr_frame.columnconfigure(1, weight=1)
        
        ttk.Label(attr_frame, text=" 3. Early Attribute Break Columns (optional):").grid(row=0, column=0, sticky="w")
        
        columns_frame = ttk.Frame(attr_frame)
        columns_frame.grid(row=0, column=1, sticky="w", padx=ui_config.standard_padding_x)
        
        self.app.must_break_columns_summary = ttk.Label(columns_frame, text="None selected", foreground="blue")
        self.app.must_break_columns_summary.grid(row=0, column=0, sticky="w")
        
        ttk.Button(columns_frame, text="Select...",
                  command=self.app.open_must_break_columns_dialog).grid(row=0, column=1, padx=(8, 0))
        
        return row + 1
    
    def create_primary_preprocessing_section(self, parent, row):
        """Create the Primary Preprocessing configuration panel (Step 4)."""
        self.app.primary_preprocess_panel = MethodConfigurationPanel(
            parent,
            panel_title="4. Primary Preprocessing (optional)",
            app=self.app,
            method_registry_type="preprocessing"
        )
        self.app.primary_preprocess_panel.grid(row=row, column=0, sticky="ew", pady=3)
        return row + 1
    
    def create_secondary_attribute_breaks_section(self, parent, row):
        """Create the Secondary Attribute Breaks section (Step 5)."""
        attr_frame = ttk.Frame(parent)
        attr_frame.grid(row=row, column=0, sticky="ew", pady=3)
        attr_frame.columnconfigure(1, weight=1)
        
        ttk.Label(attr_frame, text=" 5. Late Attribute Break Columns (optional):").grid(row=0, column=0, sticky="w")
        
        columns_frame = ttk.Frame(attr_frame)
        columns_frame.grid(row=0, column=1, sticky="w", padx=ui_config.standard_padding_x)
        
        # Secondary attribute breaks selection
        self.app.secondary_break_columns_summary = ttk.Label(columns_frame, text="None", foreground="blue")
        self.app.secondary_break_columns_summary.grid(row=0, column=0, sticky="w")
        
        ttk.Button(columns_frame, text="Select...",
                  command=self.app.open_secondary_break_columns_dialog).grid(row=0, column=1, padx=(8, 0))
        
        return row + 1
    
    def create_secondary_preprocessing_section(self, parent, row):
        """Create the Postprocessing configuration panel (Step 6)."""
        self.app.secondary_preprocess_panel = MethodConfigurationPanel(
            parent,
            panel_title="6. Postprocessing (optional)",
            app=self.app,
            method_registry_type="preprocessing"
        )
        self.app.secondary_preprocess_panel.grid(row=row, column=0, sticky="ew", pady=3)
        return row + 1
    
    def create_analysis_method_section(self, parent, row):
        """Create the Analysis Method configuration panel (Step 7)."""
        self.app.analysis_method_panel = MethodConfigurationPanel(
            parent,
            panel_title="7. Analysis Method",
            app=self.app,
            method_registry_type="optimization"
        )
        self.app.analysis_method_panel.grid(row=row, column=0, sticky="ew", pady=3)
        
        # Set default method (first in list) and expand by default
        method_names = get_optimization_method_names()
        if method_names:
            method_key = get_method_key_from_display_name(method_names[0])
            self.app.analysis_method_panel.set_method(method_key, expand=True)
        
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
        ParameterTreeTooltip(tree, lambda: self.app.dynamic_params_defs)
        
        # Fix mousewheel scrolling to work within treeview instead of parent
        def on_mousewheel(event):
            if event.num == 4 or event.delta > 0:  # Scroll up
                tree.yview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0:  # Scroll down
                tree.yview_scroll(1, "units")
            return "break"
        
        tree.bind("<MouseWheel>", on_mousewheel)
        tree.bind("<Button-4>", on_mousewheel)  # Linux scroll up
        tree.bind("<Button-5>", on_mousewheel)  # Linux scroll down

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
        # Use the new MethodConfigurationPanel if available
        if hasattr(self.app, 'analysis_method_panel'):
            return self.app.analysis_method_panel.get_parameters()
        
        # Fallback to old dynamic params system (legacy)
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
        from config import (
            NumericParameter,
            OptionalNumericParameter,
            SelectParameter,
            BoolParameter,
            ColumnSelectParameter,
            MultiColumnSelectParameter,
        )

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
        if isinstance(param_def, MultiColumnSelectParameter):
            if not isinstance(value, list):
                return "None"
            cleaned = [str(v).strip() for v in value if str(v).strip()]
            return "None" if len(cleaned) == 0 else f"{len(cleaned)} selected"
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
        from config import BoolParameter, SelectParameter, OptionalNumericParameter, ColumnSelectParameter, MultiColumnSelectParameter
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

        # Multi-column selector: open a modal dialog (no inline editor).
        if isinstance(param_def, MultiColumnSelectParameter):
            try:
                from multi_select_dialog import MultiSelectDialog

                available_columns = getattr(self.app, 'available_columns', None)
                items = available_columns if isinstance(available_columns, list) else []

                preselected = current_value if isinstance(current_value, list) else []
                selected = MultiSelectDialog.ask(
                    self.app.root if hasattr(self.app, 'root') else tree,
                    title=f"Select {param_def.display_name}",
                    items=items,
                    selected=preselected,
                    prompt="Select one or more columns:",
                )

                if selected is None:
                    return

                ok, msg = param_def.validate_value(selected)
                if not ok:
                    messagebox.showerror("Parameter Validation Error", msg or "Invalid value")
                    return

                # Enforce membership when headers are known.
                if isinstance(items, list) and items:
                    for col_name in selected:
                        if col_name not in items:
                            messagebox.showerror(
                                "Parameter Validation Error",
                                f"{param_def.display_name} must contain columns from the loaded data file",
                            )
                            return

                self._set_dynamic_param_value(method_key, param_name, selected)
                tree.item(param_name, values=(param_def.display_name, self._format_param_value(param_def, selected)))
                try:
                    if hasattr(self.app, 'on_parameter_change'):
                        self.app.on_parameter_change()
                except Exception:
                    pass
                return
            except Exception as e:
                messagebox.showerror("Parameter Editor Error", str(e))
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

        if isinstance(param_def, OptionalNumericParameter):
            try:
                if param_def.decimal_places == 0:
                    return parse_optional_int(widget.get())

                num = parse_optional_float(widget.get())
                if num is None:
                    return None
            except ValueError:
                raise ValueError(f"{param_def.display_name} must be a valid number or None")
            return round(num, param_def.decimal_places)

        text = widget.get().strip()

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
                                logger.warning("Could not restore %s: %s", param_name, e)
            
        except (ValueError, AttributeError) as e:
            # Handle case where method is not found or dropdown not ready
            if hasattr(self.app, 'handle_error'):
                self.app.handle_error("Error updating dynamic parameters", e, severity="warning", show_messagebox=False)
            else:
                logger.warning("Error updating dynamic parameters: %s", e)
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
                        logger.warning("Could not fall back to first method: %s", e)
    
    def create_right_pane_actions(self, parent):
        """Create action buttons for the right pane."""
        top_right_frame = ttk.Frame(parent)
        top_right_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))  # Reduced from (0, 10)
        top_right_frame.columnconfigure(0, weight=1)
        
        # Action button frame
        actions_frame = ttk.Frame(top_right_frame)
        actions_frame.grid(row=0, column=0, sticky="w")  # Left-align buttons
        
        # Row 0: primary run controls + results
        self.app.start_button = ttk.Button(actions_frame, text="🚀 Start",
                                          command=self.app.start_optimization,
                                          style="Accent.TButton")
        self.app.start_button.grid(row=0, column=0, padx=(0, 5))

        self.app.stop_button = ttk.Button(actions_frame, text="⏹ Stop",
                                         command=self.app.stop_optimization, state="disabled")
        self.app.stop_button.grid(row=0, column=1, padx=(0, 5))

        ttk.Button(actions_frame, text="📊 Load & Plot Results",
                  command=self.app.load_and_plot_results).grid(row=0, column=2, padx=(0, 5))

        # Row 1: secondary actions — kept narrow so row 0 is never clipped
        def exit_clicked():
            self.app._on_closing()

        ttk.Button(actions_frame, text="❓ Help",
                  command=self.app.show_help).grid(row=1, column=0, padx=(0, 5), pady=(5, 0))

        ttk.Button(actions_frame, text="📋 Create Batch Command",
                  command=self.app.copy_command_line_for_analysis).grid(row=1, column=1, padx=(0, 5), pady=(5, 0))

        ttk.Button(actions_frame, text="❌ Exit",
                  command=exit_clicked).grid(row=1, column=2, padx=(0, 5), pady=(5, 0), sticky="ew")
        
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
            if hasattr(self.app, 'handle_error'):
                self.app.handle_error(
                    f"Error getting parameter groups for method '{method_key}'",
                    e,
                    severity="warning",
                    show_messagebox=False,
                )
            elif hasattr(self.app, 'log_message'):
                self.app.log_message(f"Warning: Error getting parameter groups for method {method_key}: {e}")
            else:
                logger.warning("Error getting parameter groups for method %s: %s", method_key, e)
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