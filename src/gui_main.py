"""Main GUI class for the Highway Segmentation application.

Coordinates between six specialized managers — UIBuilder, FileManager,
ParameterManager, OptimizationController, SettingsManager, and HelpManager —
rather than implementing all concerns directly.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import logging
import json
from datetime import datetime
from typing import List, Optional

from ui_builder import UIBuilder
from file_manager import FileManager
from help_manager import HelpManager
from parameter_manager import ParameterManager
from optimization_controller import OptimizationController
from settings_manager import SettingsManager
from config import UIConfig, AlgorithmConstants, ConstrainedOptimizationConfig
from route_utils import ROUTE_COLUMN_NONE_SENTINEL, normalize_route_column_selection
from cli_export_dialog import CLIExportDialog
from run_spec import (
    build_command_for_run_spec,
    build_run_spec,
    default_run_spec_path_for_output,
)


def _json_safe(value):
    """Recursively coerce a value to a JSON-serialisable type."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    try:
        if hasattr(value, 'item'):
            return _json_safe(value.item())
    except Exception:
        pass
    return str(value)

ui_config = UIConfig()
optimization_config = AlgorithmConstants()
constrained_config = ConstrainedOptimizationConfig()


class GUILogHandler(logging.Handler):
    """Routes stdlib WARNING+ log records into the GUI right panel via log_message().

    Attached to the root logger after results_text is ready so that any library
    or framework code that calls logging.warning() / logging.error() appears in
    the right panel alongside other run messages, without requiring callers to
    know about the GUI.
    """

    def __init__(self, log_message_fn):
        super().__init__(level=logging.WARNING)
        self._log_message = log_message_fn

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._log_message(self.format(record))
        except Exception:
            self.handleError(record)


class HighwaySegmentationGUI:
    """Main application window for the Highway Segmentation GA tool."""
    
    def _get_parameter_defaults(self):
        """Extract default values from parameter definitions across all methods."""
        from config import OPTIMIZATION_METHODS
        defaults = {}
        
        # Collect defaults from all methods (in case user switches methods)
        for method_config in OPTIMIZATION_METHODS:
            for param in method_config.parameters:
                if param.name not in defaults:  # Use first occurrence as default
                    defaults[param.name] = param.default_value
        
        return defaults
    
    def __init__(self, root):
        """Initialize the main application with specialized managers."""
        self.root = root
        self.root.title("Highway Segmentation")
        self.root.geometry(f"{ui_config.window_width}x{ui_config.window_height}")
        
        # Working directory is set to the application directory for consistent relative paths.
        app_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(app_dir)

        self._initialize_variables()

        # results_text must exist before managers are constructed so they can log.
        self._create_early_log_widget()

        # Dependency check: exits early with a user-friendly message if packages are missing.
        self._log_dependency_status()

        self.ui_builder = UIBuilder(self)
        self.file_manager = FileManager(self)
        self.help_manager = HelpManager(self)
        self.parameter_manager = ParameterManager(self)
        self.optimization_controller = OptimizationController(self)
        self.settings_manager = SettingsManager()

        self.settings = self.settings_manager.load_settings()

        self._create_interface()

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _log_dependency_status(self) -> None:
        """Validate required libraries.

        Goal: make missing dependencies discoverable at runtime (especially when
        users are running the GUI with a different interpreter than they used to
        install packages).

        If dependencies are missing, the app logs clear messages, shows one
        consolidated popup with install guidance, then exits startup.
        """

        from dependency_check import (
            missing_dependencies,
            install_cmd,
            format_missing_dependencies_message,
        )

        missing = missing_dependencies()

        # If everything is present, stay silent by default.
        if not missing:
            return

        # Only log when there are missing libraries (keeps startup logs clean).
        self.log_message("=== Dependency Check (Missing Libraries) ===")
        self.log_message(f"Python interpreter: {sys.executable}")

        for dep in missing:
            self.handle_error(
                f"Missing required dependency: {dep.module} ({dep.label}). {install_cmd(dep.pip_package)}",
                severity="critical",
                show_messagebox=False,
                silence_console=True,
            )

        messagebox.showerror(
            "Missing Dependencies",
            format_missing_dependencies_message(missing),
        )

        self.log_message("===========================================")

        # Exit startup: these are required for correct operation.
        try:
            self.root.destroy()
        except Exception:
            pass
        raise SystemExit(1)
    
    def _initialize_variables(self):
        """Initialize all Tkinter variables and application state."""
        # Widgets are created by UIBuilder and attached dynamically to this
        # instance (e.g., self.method_dropdown). Predeclare key ones so static
        # type checkers can reason about them.
        self.dynamic_params_parent: Optional[ttk.Frame] = None
        self.analysis_method_panel = None  # Will be set by UIBuilder
        self.primary_preprocess_panel = None  # Will be set by UIBuilder
        self.pregap_preprocess_panel = None  # Will be set by UIBuilder
        self.secondary_preprocess_panel = None  # Will be set by UIBuilder
        self.route_info_label: Optional[ttk.Label] = None
        self.filter_routes_button: Optional[ttk.Button] = None

        self.data = None
        self._data_file_path = ""
        self.data_file = tk.StringVar(value="No file selected")
        self._save_file_path = ""
        
        # Column mapping - initialized empty, UI builder sets display text
        self.x_column = tk.StringVar(value="")
        self.y_column = tk.StringVar(value="")
        self.route_column = tk.StringVar(value=ROUTE_COLUMN_NONE_SENTINEL)  # New route column selection
        
        # Framework parameters (like x/y columns)
        self.gap_threshold = tk.DoubleVar(value=0.5)

        # Must-break columns are stored as a plain list and persisted under settings.ui_state.must_break_columns.
        self.must_break_columns: List[str] = []
        self.secondary_break_columns: List[str] = []

        self.available_columns = []
        self.available_routes = []
        self.selected_routes = []

        defaults = self._get_parameter_defaults()

        self.population_size = tk.IntVar(value=defaults.get('population_size', 100))
        self.num_generations = tk.IntVar(value=100)  # Universal default for all methods
        self.mutation_rate = tk.DoubleVar(value=defaults.get('mutation_rate', 0.05)) 
        self.crossover_rate = tk.DoubleVar(value=defaults.get('crossover_rate', 0.8))
        self.elite_ratio = tk.DoubleVar(value=defaults.get('elite_ratio', 0.05))
        
        self.optimization_method = 'multi'

        self.target_avg_length = tk.DoubleVar(value=defaults.get('target_avg_length', 2.0))
        self.penalty_weight = tk.DoubleVar(value=defaults.get('penalty_weight', 1000.0))
        self.length_tolerance = tk.DoubleVar(value=defaults.get('length_tolerance', 0.2))
        
        self.cache_clear_interval = tk.IntVar(value=defaults.get('cache_clear_interval', 50))
        self.custom_save_name = tk.StringVar(value="highway_segmentation.json")
        self.is_running = False
        self.stop_requested = False
    
    @property
    def method_dropdown(self):
        """Backward compatibility: access dropdown through analysis_method_panel."""
        if self.analysis_method_panel:
            return self.analysis_method_panel.method_dropdown
        return None
    
    def _create_early_log_widget(self):
        """Create a minimal results_text widget early for logging during initialization."""
        self.results_text = tk.Text(self.root, height=1, width=1)
        # Placed off-screen; the full UI replaces it once _create_interface() runs.
        self.results_text.place(x=-1000, y=-1000)

        # Route stdlib WARNING+ into the right panel for framework/library messages.
        self._gui_log_handler = GUILogHandler(self.log_message)
        self._gui_log_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        logging.getLogger().addHandler(self._gui_log_handler)
    
    def _create_interface(self):
        """Create the complete user interface using the UI builder."""
        main_frame = self.ui_builder.create_main_layout()
        required_frame = self.ui_builder.create_scrollable_left_pane(main_frame)
        right_pane = self.ui_builder.create_right_pane(main_frame)

        current_row = 0
        current_row = self.ui_builder.create_basic_setup_section(required_frame, current_row)
        current_row = self.ui_builder.create_pregap_preprocessing_section(required_frame, current_row)
        current_row = self.ui_builder.create_gap_analysis_section(required_frame, current_row)
        current_row = self.ui_builder.create_primary_attribute_breaks_section(required_frame, current_row)
        current_row = self.ui_builder.create_primary_preprocessing_section(required_frame, current_row)
        current_row = self.ui_builder.create_secondary_attribute_breaks_section(required_frame, current_row)
        current_row = self.ui_builder.create_secondary_preprocessing_section(required_frame, current_row)
        current_row = self.ui_builder.create_analysis_method_section(required_frame, current_row)

        # Old dynamic params section - now each panel has its own Treeview
        # if self.dynamic_params_parent is not None:
        #     self.ui_builder.create_dynamic_params_section(self.dynamic_params_parent)

        self.ui_builder.create_right_pane_actions(right_pane)
        self.ui_builder.create_results_section(right_pane)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._apply_loaded_settings()
        self._setup_parameter_tracking()
    
    # ===== DELEGATED METHODS =====

    def set_data_file_path(self, full_path):
        """Set the path of the loaded data file."""
        return self.file_manager.set_data_file_path(full_path)

    def get_data_file_path(self):
        """Return the path of the loaded data file."""
        return self.file_manager.get_data_file_path()

    def set_save_file_path(self, full_path):
        """Set the path where results will be saved."""
        return self.file_manager.set_save_file_path(full_path)

    def get_save_file_path(self):
        """Return the path where results will be saved."""
        return self.file_manager.get_save_file_path()
    
    def browse_data_file(self):
        """Browse for data file and save the selection."""
        result = self.file_manager.browse_data_file()
        if result:  # File was selected
            self.on_parameter_change()  # Save the new file path
        return result
    
    def browse_save_location(self):
        """Browse for save location and save the selection."""
        result = self.file_manager.browse_save_location()
        if result:  # Location was selected
            self.on_parameter_change()  # Save the new save path
        return result
    def load_csv_columns(self):
        """Load column headers from the selected CSV file."""
        return self.file_manager.load_csv_columns()

    def load_data_file(self):
        """Load the data file into memory."""
        return self.file_manager.load_data_file()

    def load_and_plot_results(self):
        """Load a results JSON file and open its visualization."""
        return self.file_manager.load_and_plot_results()

    def save_parameters(self):
        """Save the current parameter set to a file."""
        return self.file_manager.save_parameters()

    def load_parameters(self):
        """Load a previously saved parameter set from a file."""
        return self.file_manager.load_parameters()

    def validate_parameters(self):
        """Validate all current parameter values."""
        return self.parameter_manager.validate_parameters()
    
    def reset_parameters(self):
        """Reset parameters - delegates to ParameterManager for method-specific, resets framework parameters."""
        # Reset framework parameters to defaults
        if hasattr(self, 'gap_threshold'):
            self.gap_threshold.set(0.5)  # Framework default
        
        # Delegate method-specific parameter reset to parameter manager
        return self.parameter_manager.reset_parameters()
    
    def on_method_change(self, event=None):
        """Handle method change.

        Persist the outgoing method's dynamic parameters, then switch UI and
        restore the incoming method's saved dynamic parameters (if any).
        """
        # Commit any in-progress inline table edit before switching methods.
        # Without this, the Treeview refresh can cancel the editor and lose the edit.
        try:
            if hasattr(self, 'ui_builder') and hasattr(self.ui_builder, '_commit_dynamic_param_cell_edit'):
                self.ui_builder._commit_dynamic_param_cell_edit()
        except Exception:
            pass

        try:
            old_method_key = getattr(self, '_active_method_key', None) or getattr(self, 'optimization_method', None)
            if old_method_key:
                self._persist_dynamic_parameters_for_method(old_method_key)
        except Exception as e:
            if hasattr(self, 'handle_error'):
                self.handle_error(
                    "Could not persist method parameters before switch",
                    e,
                    severity="warning",
                    show_messagebox=False,
                )
            elif hasattr(self, 'log_message'):
                self.log_message(f"Warning: Could not persist method parameters before switch: {e}")

        result = self.parameter_manager.on_method_change(event)

        try:
            new_method_key = self._get_selected_method_key_safe()
            if new_method_key:
                self._active_method_key = new_method_key
                self._restore_dynamic_parameters_for_method(new_method_key)
        except Exception as e:
            if hasattr(self, 'handle_error'):
                self.handle_error(
                    "Could not restore method parameters after switch",
                    e,
                    severity="warning",
                    show_messagebox=False,
                )
            elif hasattr(self, 'log_message'):
                self.log_message(f"Warning: Could not restore method parameters after switch: {e}")

        return result

    def _get_selected_method_key_safe(self):
        """Return currently selected method key, best-effort."""
        try:
            from config import get_method_key_from_display_name
            if self.method_dropdown is not None:
                return get_method_key_from_display_name(self.method_dropdown.get())
        except (ImportError, AttributeError, ValueError, KeyError, TypeError):
            pass

        try:
            if hasattr(self, 'optimization_method'):
                return self.settings_manager.validate_method_key(self.optimization_method)
        except (AttributeError, ValueError, KeyError, TypeError):
            pass
        return None

    def _persist_dynamic_parameters_for_method(self, method_key: str) -> None:
        """Snapshot current dynamic parameter widget values for a specific method."""
        if not hasattr(self, 'settings') or not self.settings:
            return
        # Dynamic parameter edits are persisted immediately into
        # settings['optimization']['dynamic_parameters_by_method'][method_key]
        # by the inline editor. Do not overwrite here (especially during method
        # switching, when the dropdown selection may already reflect the new method).
        opt = self.settings.setdefault('optimization', {})
        store = opt.setdefault('dynamic_parameters_by_method', {})
        store.setdefault(method_key, {})

    def _restore_dynamic_parameters_for_method(self, method_key: str) -> None:
        """Apply saved dynamic parameters for a method to the current widgets."""
        if not hasattr(self, 'settings') or not self.settings:
            return

        opt = self.settings.get('optimization', {})
        store = opt.get('dynamic_parameters_by_method', {}) if isinstance(opt, dict) else {}
        per_method = store.get(method_key)
        if not per_method:
            return

        # Dynamic widgets must exist for this method at this point.
        try:
            if hasattr(self, 'parameter_manager'):
                self.parameter_manager.load_method_dynamic_parameters(per_method)
        except Exception as e:
            if hasattr(self, 'handle_error'):
                self.handle_error(
                    f"Could not restore dynamic parameters for method '{method_key}'",
                    e,
                    severity="warning",
                    show_messagebox=False,
                )
            elif hasattr(self, 'log_message'):
                self.log_message(
                    f"Warning: Could not restore dynamic parameters for method '{method_key}': {e}"
                )
    
    def on_column_change(self, event=None):
        """Handle column change - delegates to ParameterManager."""
        return self.parameter_manager.on_column_change(event)
    
    def on_column_keyrelease(self, event, combobox):
        """Handle type-ahead filtering for column selection comboboxes."""
        if not hasattr(self, 'available_columns') or not self.available_columns:
            return
            
        typed_text = combobox.get().lower()

        if typed_text == "load data first...":
            return

        matching_columns = [col for col in self.available_columns
                            if typed_text in col.lower()]
        combobox['values'] = matching_columns

        # Keep the dropdown open while the user is typing.
        if matching_columns and len(typed_text) > 0:
            combobox.event_generate('<Down>')
    
    def on_save_option_change(self):
        """Handle save option change."""
        return self.parameter_manager.on_save_option_change()

    def _reset_route_ui_state(self, *, reset_route_column: bool) -> None:
        """Clear route lists, route label, and disable the filter button."""
        if reset_route_column:
            self.route_column.set(ROUTE_COLUMN_NONE_SENTINEL)

        self.available_routes = []
        self.selected_routes = []
        if self.route_info_label is not None:
            self.route_info_label.config(text="")
        if self.filter_routes_button is not None:
            self.filter_routes_button.config(state="disabled")

    def _route_column_exists_in_file(self, data_path: str, route_col: str) -> bool:
        """Return True if the given route column exists in the CSV header.

        Raises on I/O/parse errors so the caller can handle and reset UI state
        consistently.
        """
        import pandas as pd

        df_headers = pd.read_csv(data_path, nrows=0)
        return route_col in df_headers.columns
    
    def on_route_column_change(self, event=None):
        """Handle route column selection change."""
        route_col_raw = self.route_column.get()
        route_col = normalize_route_column_selection(route_col_raw)

        if route_col is not None:
            # Route column selected - validate it exists before trying to detect routes
            data_path = self.file_manager.get_data_file_path()
            if data_path:
                try:
                    # Quick check if the column exists to prevent error popups
                    if self._route_column_exists_in_file(data_path, route_col):
                        # Treat route identifiers as categorical strings in-memory
                        try:
                            self.file_manager.ensure_route_column_is_string(route_col)
                        except Exception as e:
                            self.log_message(f"Warning: Could not normalize route column to string: {e}")
                        # Column exists - safe to detect routes
                        self.file_manager.detect_available_routes()
                        if self.filter_routes_button is not None:
                            self.filter_routes_button.config(state="normal")
                    else:
                        # Column doesn't exist - reset quietly without popup
                        self.log_message(f"Route column '{route_col}' not found - resetting selection")
                        self._reset_route_ui_state(reset_route_column=True)
                except Exception as e:
                    # Error reading file - reset to safe state
                    self.log_message(f"Error validating route column: {str(e)}")
                    self._reset_route_ui_state(reset_route_column=True)
            else:
                # No data file - can't detect routes
                self._reset_route_ui_state(reset_route_column=False)
        else:
            self._reset_route_ui_state(reset_route_column=False)
    
    def open_route_filter_dialog(self):
        """Open the route filter dialog to select which routes to process."""
        
        if not self.available_routes:
            # Try to automatically detect routes using current settings
            data_path = self.file_manager.get_data_file_path()
            route_col = normalize_route_column_selection(
                self.route_column.get() if hasattr(self, 'route_column') else None
            )
            
            if not data_path:
                messagebox.showwarning("No Data File", "Please select a data file first before filtering routes.")
                return
            elif route_col is None:
                messagebox.showwarning("No Route Column", "Please select a route column first before filtering routes.")
                return
            else:
                # Try to detect routes automatically
                self.log_message("No routes loaded. Attempting to detect routes from current settings...")
                try:
                    self.file_manager.detect_available_routes()
                    if not self.available_routes:
                        messagebox.showerror("Route Detection Failed", 
                                           f"Could not find any routes in column '{route_col}' of the selected data file. "
                                           f"Please verify the route column selection and data file content.")
                        return
                except Exception as e:
                    messagebox.showerror("Route Detection Error", 
                                       f"Error detecting routes: {str(e)}")
                    return
            
        # Import and create route filter dialog
        try:
            from route_filter_dialog import RouteFilterDialog
            self.log_message("Opening route filter dialog...")
            
            dialog = RouteFilterDialog(self.root, self.available_routes, self.selected_routes)
            result = dialog.show()
            
            if result is not None:
                self.selected_routes = result
                self._update_route_info_display()
                self.log_message(f"Route selection updated: {len(self.selected_routes)} routes selected")
            else:
                self.log_message("Route filter dialog cancelled or failed")
                
        except Exception as e:
            error_msg = f"Failed to open route filter dialog: {str(e)}"
            self.log_message(f"ERROR: {error_msg}")
            # Use simpler error dialog for better macOS compatibility
            try:
                messagebox.showerror("Dialog Error", error_msg)
            except Exception:
                # Fallback if messagebox also fails
                self.log_message(f"Critical error: {error_msg}")

    def _update_must_break_columns_display(self) -> None:
        label = getattr(self, 'must_break_columns_summary', None)
        if label is None:
            return

        cols = getattr(self, 'must_break_columns', None)
        if not isinstance(cols, list):
            cols = []

        cleaned = [str(v).strip() for v in cols if str(v).strip()]
        label.config(text="None" if len(cleaned) == 0 else f"{len(cleaned)} selected")

    def open_must_break_columns_dialog(self) -> None:
        """Open multi-select dialog to choose attribute columns that force mandatory breakpoints."""

        available = getattr(self, 'available_columns', None)
        if not isinstance(available, list) or not available:
            messagebox.showwarning(
                "Load Data First",
                "Please select a data file first so column headers are available.",
            )
            return

        try:
            from multi_select_dialog import MultiSelectDialog

            preselected = getattr(self, 'must_break_columns', [])
            if not isinstance(preselected, list):
                preselected = []

            selected = MultiSelectDialog.ask(
                self.root,
                title="Must Break Column List",
                items=available,
                selected=preselected,
                prompt="Select columns that force a mandatory breakpoint when their value changes:",
            )

            if selected is None:
                return

            self.must_break_columns = [str(v).strip() for v in selected if str(v).strip()]
            self._update_must_break_columns_display()
            self.on_parameter_change()
        except Exception as e:
            self.handle_error("Failed to open must-break column selector", e, severity="error", show_messagebox=True)
    
    def open_secondary_break_columns_dialog(self) -> None:
        """Open multi-select dialog to choose secondary attribute columns that force mandatory breakpoints."""

        available = getattr(self, 'available_columns', None)
        if not isinstance(available, list) or not available:
            messagebox.showwarning(
                "Load Data First",
                "Please select a data file first so column headers are available.",
            )
            return

        try:
            from multi_select_dialog import MultiSelectDialog

            preselected = getattr(self, 'secondary_break_columns', [])
            if not isinstance(preselected, list):
                preselected = []

            selected = MultiSelectDialog.ask(
                self.root,
                title="Secondary Break Column List",
                items=available,
                selected=preselected,
                prompt="Select columns that force a mandatory breakpoint when their value changes:",
            )

            if selected is None:
                return

            self.secondary_break_columns = [str(v).strip() for v in selected if str(v).strip()]
            self._update_secondary_break_columns_display()
            self.on_parameter_change()
        except Exception as e:
            self.handle_error("Failed to open secondary-break column selector", e, severity="error", show_messagebox=True)
    
    def _update_secondary_break_columns_display(self) -> None:
        label = getattr(self, 'secondary_break_columns_summary', None)
        if label is None:
            return

        cols = getattr(self, 'secondary_break_columns', None)
        if not isinstance(cols, list):
            cols = []

        cleaned = [str(v).strip() for v in cols if str(v).strip()]
        label.config(text="None" if len(cleaned) == 0 else f"{len(cleaned)} selected")
    
    def _update_route_info_display(self):
        """Update the route info label to show selected route count."""
        if self.route_info_label is None:
            return

        if self.available_routes:
            total_routes = len(self.available_routes)
            selected_count = len(self.selected_routes)
            self.route_info_label.config(text=f"{selected_count} of {total_routes} selected")
        else:
            self.route_info_label.config(text="")
    
    # Dynamic Parameter Helper Methods
    def _get_dynamic_parameter(self, param_name, default_value):
        """Get a dynamic parameter value, falling back to default if not available."""
        try:
            dynamic_params = self.ui_builder.get_parameter_values()
            return dynamic_params.get(param_name, default_value)
        except (AttributeError, KeyError, TypeError, ValueError, tk.TclError):
            return default_value
    
    def get_enable_performance_stats(self):
        """Get enable_performance_stats value from dynamic parameter system."""
        return self._get_dynamic_parameter('enable_performance_stats', True)

    
    # Optimization Control Methods (delegate to OptimizationController)
    def start_optimization(self):
        """Auto-save current parameters then launch the optimization."""
        self._save_current_settings()
        
        return self.optimization_controller.start_optimization()
    
    def stop_optimization(self):
        """Request the running optimization to stop."""
        return self.optimization_controller.stop_optimization()

    def _collect_current_analysis_export_state(self) -> Optional[dict]:
        """Validate the current GUI state and return a plain dict of export fields.

        Shows an error messagebox and returns None if any required field is missing
        or invalid. Returns a dict on success — no file I/O or clipboard interaction.
        """
        data_file_path = self.file_manager.get_data_file_path() if hasattr(self, 'file_manager') else ''
        if not data_file_path:
            messagebox.showerror("Data Required", "Please select a data file before exporting a command line.")
            return None

        x_column = self.x_column.get() if hasattr(self, 'x_column') else ''
        y_column = self.y_column.get() if hasattr(self, 'y_column') else ''
        if not x_column or not y_column:
            messagebox.showerror("Columns Required", "Please select both X and Y columns before exporting a command line.")
            return None

        try:
            gap_threshold = float(self.gap_threshold.get())
        except Exception:
            messagebox.showerror("Gap Threshold Required", "Gap threshold is missing or invalid.")
            return None

        params = self.parameter_manager.get_optimization_parameters()
        method_key = params.get('optimization_method')
        if not method_key:
            messagebox.showerror("Method Required", "Optimization method is missing or invalid.")
            return None

        method_parameters = {
            k: v
            for k, v in params.items()
            if k not in ('optimization_method', 'custom_save_name')
        }

        route_column_raw = self.route_column.get() if hasattr(self, 'route_column') else None
        route_column = normalize_route_column_selection(route_column_raw)

        selected_routes = None
        if route_column is not None:
            sr = getattr(self, 'selected_routes', None)
            if isinstance(sr, (list, tuple)) and sr:
                selected_routes = [str(r) for r in sr]

        save_file_path = self.file_manager.get_save_file_path() if hasattr(self, 'file_manager') else ''
        if save_file_path:
            output_json_path = save_file_path
        else:
            project_root = os.path.dirname(os.path.dirname(__file__))
            name = (self.custom_save_name.get() if hasattr(self, 'custom_save_name') else 'highway_segmentation')
            name = str(name).strip() or 'highway_segmentation'
            if not name.lower().endswith('.json'):
                name = name + '.json'
            output_json_path = os.path.join(project_root, 'Results', name)

        must_break_raw = getattr(self, 'must_break_columns', None)
        must_break_columns = None
        if isinstance(must_break_raw, (list, tuple)):
            cleaned = [str(c).strip() for c in must_break_raw if str(c).strip()]
            must_break_columns = cleaned or None

        secondary_break_raw = getattr(self, 'secondary_break_columns', None)
        secondary_break_columns = None
        if isinstance(secondary_break_raw, (list, tuple)):
            cleaned = [str(c).strip() for c in secondary_break_raw if str(c).strip()]
            secondary_break_columns = cleaned or None

        return {
            'data_file_path': str(data_file_path),
            'x_column': str(x_column),
            'y_column': str(y_column),
            'gap_threshold': gap_threshold,
            'method_key': str(method_key),
            'method_parameters': {str(k): _json_safe(v) for k, v in method_parameters.items()},
            'route_column': route_column,
            'selected_routes': [str(r) for r in selected_routes] if selected_routes is not None else None,
            'must_break_columns': must_break_columns,
            'secondary_break_columns': secondary_break_columns,
            'output_json_path': str(output_json_path),
            'app_version': str(getattr(self, 'app_version', 'dev')),
        }

    def _write_single_run_export_artifacts(self, state: dict):
        """Build and persist the run-spec JSON for a single-file export.

        Takes the validated state dict from _collect_current_analysis_export_state,
        writes the run-spec file, and returns (spec_path, cli_command).
        No GUI interaction — safe to call from a dialog or test.
        """
        output_json_path = state['output_json_path']
        spec_path = default_run_spec_path_for_output(output_json_path)

        spec = build_run_spec(
            data_file_path=state['data_file_path'],
            x_column=state['x_column'],
            y_column=state['y_column'],
            gap_threshold=state['gap_threshold'],
            must_break_columns=state['must_break_columns'],
            secondary_break_columns=state['secondary_break_columns'],
            route_column=state['route_column'],
            selected_routes=state['selected_routes'],
            method_key=state['method_key'],
            method_parameters=state['method_parameters'],
            output_json_path=output_json_path,
            overwrite=True,
            application_version=state['app_version'],
        )

        os.makedirs(os.path.dirname(str(spec_path)), exist_ok=True)
        with open(spec_path, 'w', encoding='utf-8') as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)

        cmd = build_command_for_run_spec(str(spec_path))
        return spec_path, cmd

    def copy_command_line_for_analysis(self) -> None:
        """Open the Export CLI Run dialog for the current UI state."""
        state = self._collect_current_analysis_export_state()
        if state is None:
            return
        CLIExportDialog.open(
            self.root,
            state=state,
            log_callback=self.log_message,
        )
    
    def show_help(self):
        """Open the documentation browser dialog."""
        self.help_manager.show_help()

    # ===== REMAINING DIRECT METHODS =====
    # These methods remain in the main class as they coordinate between managers
    
    def log_message(self, message):
        """Append a timestamped message to the GUI log.

        Args:
            message (str): Message to log.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        # Strip \r so progress-update lines don't overwrite previous output.
        clean_message = message.replace('\r', '')
        formatted_message = f"[{timestamp}] {clean_message}"
        # results_text exists from early widget creation — safe to write here.
        self.results_text.insert(tk.END, formatted_message + '\n')
        self.results_text.see(tk.END)
    
    def handle_error(self, error_message: str, exception: Optional[Exception] = None,
                    severity: str = "error", show_messagebox: bool = False,
                    silence_console: bool = True) -> None:
        """Log an error to the GUI and optionally show a dialog.

        Args:
            error_message: Human-readable error description.
            exception: Original exception object (if any).
            severity: One of 'info', 'warning', 'error', 'critical'.
            show_messagebox: Whether to show a popup dialog.
            silence_console: When True, suppress console output.
        """
        severity_prefix = {
            'info': 'ℹ️ INFO',
            'warning': '⚠️ WARNING',
            'error': '❌ ERROR',
            'critical': '🚨 CRITICAL'
        }.get(severity, '❌ ERROR')

        formatted_message = f"{severity_prefix}: {error_message}"
        if exception:
            formatted_message += f"\n   Details: {str(exception)}"

        self.log_message(formatted_message)

        if show_messagebox:
            if severity == 'critical':
                messagebox.showerror("Critical Error", error_message)
            elif severity == 'error':
                messagebox.showerror("Error", error_message)
            elif severity == 'warning':
                messagebox.showwarning("Warning", error_message)
            else:
                messagebox.showinfo("Information", error_message)

        if not silence_console:
            print(f"[{severity.upper()}] {error_message}")
            if exception:
                print(f"   Exception: {exception}")

    def show_current_parameters(self):
        """Display all current parameter values in the log for user review."""
        method = self.method_dropdown.get() if self.method_dropdown is not None else ""
        self.log_message("=== CURRENT PARAMETER VALUES ===")
        self.log_message(f"Optimization Method: {method}")
        self.log_message("")
        try:
            current_params = self.ui_builder.get_parameter_values()
            self.log_message("METHOD-SPECIFIC PARAMETERS:")
            for param_name, value in current_params.items():
                self.log_message(f"  {param_name}: {value}")
        except Exception as e:
            self.log_message(f"  Error getting dynamic parameters: {e}")
            
        self.log_message("")
        self.log_message("FRAMEWORK PARAMETERS:")
        if hasattr(self, 'gap_threshold'):
            self.log_message(f"  Gap Threshold: {self.gap_threshold.get()}")
        if hasattr(self, 'x_column'):
            self.log_message(f"  X Column: {self.x_column.get()}")
        if hasattr(self, 'y_column'):
            self.log_message(f"  Y Column: {self.y_column.get()}")
        if hasattr(self, 'route_column'):
            self.log_message(f"  Route Column: {self.route_column.get()}")
        if hasattr(self, 'custom_save_name'):
            self.log_message(f"  Custom Save Name: {self.custom_save_name.get()}")
        
        self.log_message("=================================")
    
    def _refresh_ui_widgets(self):
        """Refresh UI widgets to ensure they show current variable values."""
        # Force UI refresh to ensure widgets show correct values
        self._refresh_ui_values()
    
    def _refresh_ui_values(self):
        """Force refresh all UI widgets to show current variable values."""
        try:
            # Force update all entry widgets by temporarily setting their values
            vars_and_widgets = [
                (self.population_size, 'pop_size_entry'),
                (self.num_generations, 'generations_entry'),
                # min_length, max_length now handled by dynamic parameters
                (self.mutation_rate, 'mutation_rate_entry'),
                (self.crossover_rate, 'crossover_rate_entry'),
                (self.elite_ratio, 'elite_ratio_entry'),
                (self.target_avg_length, 'target_entry'),
                (self.penalty_weight, 'penalty_entry'),
                (self.length_tolerance, 'tolerance_entry'),
                (self.cache_clear_interval, 'cache_interval_entry'),
                (self.custom_save_name, 'save_name_entry')
            ]
            
            for var, widget_name in vars_and_widgets:
                if hasattr(self, widget_name):
                    widget = getattr(self, widget_name)
                    if hasattr(widget, 'delete') and hasattr(widget, 'insert'):
                        current_val = str(var.get())
                        widget.delete(0, 'end')
                        widget.insert(0, current_val)
                        
        except Exception as e:
            # Avoid hard-failing on refresh, but don't hide unexpected errors.
            if hasattr(self, 'handle_error'):
                self.handle_error("UI refresh failed (non-fatal)", e, severity="warning", show_messagebox=False)
    
    def _apply_loaded_settings(self):
        """Apply loaded settings to all UI elements."""
        self.settings_manager.apply_to_app(self)
    
    def _setup_parameter_tracking(self):
        """Set up automatic saving when parameters change."""
        # Track only framework/global UI state here; method-specific parameters
        # are persisted via the per-method dynamic parameter store.
        tracked_vars: List[tk.Variable] = [self.custom_save_name]

        if hasattr(self, 'x_column'):
            tracked_vars.append(self.x_column)
        if hasattr(self, 'y_column'):
            tracked_vars.append(self.y_column)
        if hasattr(self, 'gap_threshold'):
            tracked_vars.append(self.gap_threshold)
        if hasattr(self, 'route_column'):
            tracked_vars.append(self.route_column)

        for var in tracked_vars:
            try:
                var.trace_add("write", lambda *_: self.on_parameter_change())
            except Exception as e:
                self.handle_error(f"Could not add auto-save to variable {var}", e, "warning")
    
    def _save_current_settings(self):
        """Save current UI state to settings."""
        try:
            self.settings['files']['data_file_path'] = self.file_manager.get_data_file_path() or ''
            self.settings['files']['save_file_path'] = self.file_manager.get_save_file_path() or ''

            # Persist dynamic params for the active method so they survive restart.
            try:
                active_key = getattr(self, '_active_method_key', None) or self._get_selected_method_key_safe()
                if active_key:
                    # Save parameters from the analysis_method_panel
                    if hasattr(self, 'analysis_method_panel') and self.analysis_method_panel:
                        params = self.analysis_method_panel.get_parameters()
                        if params:
                            # Store in the dynamic_parameters_by_method for persistence
                            opt = self.settings.setdefault('optimization', {})
                            store = opt.setdefault('dynamic_parameters_by_method', {})
                            store[active_key] = params
                    else:
                        # Fallback for legacy path
                        self._persist_dynamic_parameters_for_method(active_key)
            except (AttributeError, ValueError, KeyError, TypeError):
                pass

            # Persist only minimal non-method optimization settings here.
            # (All method parameters are stored per-method under dynamic_parameters_by_method.)
            if 'optimization' not in self.settings or not isinstance(self.settings.get('optimization'), dict):
                self.settings['optimization'] = {}
            if hasattr(self, 'custom_save_name'):
                self.settings['optimization']['custom_save_name'] = self.custom_save_name.get()

            # Enforce minimal-globals contract: strip any legacy optimization
            # keys that used to be stored as globals.
            legacy_optimization_keys = [
                'population_size', 'num_generations', 'mutation_rate', 'crossover_rate',
                'elite_ratio', 'target_avg_length', 'penalty_weight', 'length_tolerance',
                'cache_clear_interval', 'enable_performance_stats',
                # Older builds stored segment constraints and framework values here
                'min_length', 'max_length', 'gap_threshold',
                # AASHTO CDA params were previously stored globally
                'alpha', 'method', 'use_segment_length', 'min_segment_datapoints',
                'max_segments', 'min_section_difference',
            ]
            for k in legacy_optimization_keys:
                self.settings['optimization'].pop(k, None)
            
            method_dropdown = getattr(self, "method_dropdown", None)
            if method_dropdown is None:
                ui_builder = getattr(self, "ui_builder", None)
                method_dropdown = getattr(ui_builder, "method_dropdown", None)

            if method_dropdown is not None:
                from config import get_method_key_from_display_name
                display_name = method_dropdown.get()
                try:
                    method_key = get_method_key_from_display_name(display_name)
                except ValueError:
                    from config import get_optimization_method
                    try:
                        get_optimization_method(display_name)
                        method_key = display_name
                    except (ValueError, KeyError):
                        method_key = 'multi'

                method_key = self.settings_manager.validate_method_key(method_key)
                self.settings['optimization']['optimization_method'] = method_key
            elif hasattr(self, 'optimization_method'):
                method_key = self.settings_manager.validate_method_key(self.optimization_method)
                self.settings['optimization']['optimization_method'] = method_key
            else:
                self.settings['optimization']['optimization_method'] = 'multi'

            self.settings['ui_state']['window_geometry'] = self.root.geometry()

            if hasattr(self, 'x_column'):
                self.settings['ui_state']['x_column'] = self.x_column.get()
            if hasattr(self, 'y_column'):
                self.settings['ui_state']['y_column'] = self.y_column.get()
            if hasattr(self, 'gap_threshold'):
                self.settings['ui_state']['gap_threshold'] = self.gap_threshold.get()
            if hasattr(self, 'route_column'):
                self.settings['ui_state']['route_column'] = self.route_column.get()

            try:
                cols = getattr(self, 'must_break_columns', [])
                if cols is None:
                    cols = []
                if isinstance(cols, list):
                    self.settings['ui_state']['must_break_columns'] = [str(v).strip() for v in cols if str(v).strip()]
                else:
                    self.settings['ui_state']['must_break_columns'] = []
            except Exception:
                self.settings['ui_state']['must_break_columns'] = []
            
            try:
                sec_cols = getattr(self, 'secondary_break_columns', [])
                if sec_cols is None:
                    sec_cols = []
                if isinstance(sec_cols, list):
                    self.settings['ui_state']['secondary_break_columns'] = [str(v).strip() for v in sec_cols if str(v).strip()]
                else:
                    self.settings['ui_state']['secondary_break_columns'] = []
            except Exception:
                self.settings['ui_state']['secondary_break_columns'] = []
            
            if hasattr(self, 'selected_routes'):
                self.settings['ui_state']['selected_routes'] = self.selected_routes.copy()
            
            # Save preprocessing panel configurations
            if 'preprocessing' not in self.settings:
                self.settings['preprocessing'] = {}
            
            # Save pregap preprocessing panel
            if hasattr(self, 'pregap_preprocess_panel') and self.pregap_preprocess_panel:
                try:
                    method_key = self.pregap_preprocess_panel.get_method_key()
                    parameters = self.pregap_preprocess_panel.get_parameters() if method_key else {}
                    self.settings['preprocessing']['pregap_config'] = {
                        'method': method_key,
                        'parameters': parameters
                    }
                except Exception as e:
                    self.log_message(f"Warning: Could not save pregap preprocessing config: {e}")
            
            # Save primary preprocessing panel
            if hasattr(self, 'primary_preprocess_panel') and self.primary_preprocess_panel:
                try:
                    method_key = self.primary_preprocess_panel.get_method_key()
                    parameters = self.primary_preprocess_panel.get_parameters() if method_key else {}
                    self.settings['preprocessing']['primary_config'] = {
                        'method': method_key,
                        'parameters': parameters
                    }
                except Exception as e:
                    self.log_message(f"Warning: Could not save primary preprocessing config: {e}")
            
            # Save secondary preprocessing (postprocessing) panel
            if hasattr(self, 'secondary_preprocess_panel') and self.secondary_preprocess_panel:
                try:
                    method_key = self.secondary_preprocess_panel.get_method_key()
                    parameters = self.secondary_preprocess_panel.get_parameters() if method_key else {}
                    self.settings['preprocessing']['secondary_config'] = {
                        'method': method_key,
                        'parameters': parameters
                    }
                except Exception as e:
                    self.log_message(f"Warning: Could not save secondary preprocessing config: {e}")

            self.settings_manager.save_settings(self.settings)
            
        except Exception as e:
            self.log_message(f"Could not save settings: {e}")
    
    def _on_closing(self):
        """Handle application closing — save settings, stop optimization, and destroy window."""
        if hasattr(self, '_save_timer'):
            try:
                self.root.after_cancel(self._save_timer)
            except tk.TclError:
                pass

        try:
            self._save_current_settings()
        except Exception as e:
            self.handle_error("Could not save settings on shutdown", e, "warning")

        if hasattr(self, 'optimization_controller') and self.is_running:
            self.stop_requested = True
            self.optimization_controller.stop_optimization()

        try:
            import matplotlib.pyplot as plt
            if plt.get_fignums():
                plt.close('all')
            plt.ioff()
        except Exception as e:
            self.handle_error("Failed to cleanup matplotlib resources", e,
                             severity="warning", silence_console=True)

        self.is_running = False

        # Brief pause to let any in-flight file operations complete.
        import time
        time.sleep(0.1)

        try:
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            self.handle_error("Error occurred during application shutdown", e,
                             severity="error", silence_console=True)
    
    def on_parameter_change(self):
        """Debounce settings saves so rapid edits don't thrash the file system."""
        # Cancel any existing timer to avoid excessive saves.
        if hasattr(self, '_save_timer'):
            try:
                self.root.after_cancel(self._save_timer)
            except tk.TclError:
                pass
        self._save_timer = self.root.after(500, self._save_current_settings)
    
    def on_closing(self):
        """Handle application closing."""
        self._on_closing()


def main():
    """Main entry point for the application."""
    # Optional stdlib logging setup (opt-in).
    # If you want module logs (e.g., from data_loader), set HIGHWAY_SEG_LOG_LEVEL
    # to DEBUG/INFO/WARNING/ERROR before launching the GUI.
    log_level_raw = os.environ.get("HIGHWAY_SEG_LOG_LEVEL")
    if log_level_raw:
        log_level_name = str(log_level_raw).upper()
        log_level = getattr(logging, log_level_name, logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

    root = tk.Tk()
    style = ttk.Style()
    # Prefer platform-native ttk themes for visual consistency.
    # Forcing non-native themes (e.g. "clam" on macOS) can lead to odd
    # backgrounds (including black) and mismatched widget styling.
    import sys
    theme_names = set(style.theme_names())
    if sys.platform.startswith("win") and "winnative" in theme_names:
        style.theme_use("winnative")
    elif sys.platform == "darwin" and "aqua" in theme_names:
        style.theme_use("aqua")
    elif "clam" in theme_names:
        style.theme_use("clam")
    
    # Validate method registry early so misconfigurations fail fast with clear messaging
    try:
        from config import validate_optimization_method_registry
        validate_optimization_method_registry()
    except Exception as e:
        messagebox.showerror(
            "Configuration Error",
            f"Optimization method registry validation failed.\n\n{e}"
        )
        try:
            root.destroy()
        except Exception:
            pass
        return

    HighwaySegmentationGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Application interrupted by user")
        root.destroy()


if __name__ == "__main__":
    main()