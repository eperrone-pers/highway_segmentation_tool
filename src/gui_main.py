"""
Refactored GUI Main Module for Highway Segmentation

This module demonstrates the refactored architecture where the original god object
(44 methods, 1,901 lines) has been broken down into focused, single-responsibility
classes. The main GUI class now coordinates between specialized managers rather
than handling everything directly.

REFACTORING DEMONSTRATION:
- Original: 1 class with 44 methods handling all concerns
- Refactored: 5 focused classes with clear separation of concerns
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import logging
from datetime import datetime
import webbrowser
import tempfile
try:
    import markdown
    from markdown.extensions import toc
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

# Import the specialized manager classes
from ui_builder import UIBuilder
from file_manager import FileManager  
from parameter_manager import ParameterManager
from optimization_controller import OptimizationController
from settings_manager import SettingsManager
from config import UIConfig, AlgorithmConstants, ConstrainedOptimizationConfig

# Create config instances
ui_config = UIConfig()
optimization_config = AlgorithmConstants()
constrained_config = ConstrainedOptimizationConfig()


class HighwaySegmentationGUI:
    """
    REFACTORED Main GUI class for Highway Segmentation Genetic Algorithm.
    
    This class now coordinates between specialized managers instead of handling
    all concerns directly. This demonstrates proper separation of concerns and
    elimination of the god object anti-pattern.
    
    ARCHITECTURE:
    - UIBuilder: Handles all widget creation and layout
    - FileManager: Handles file I/O and data loading  
    - ParameterManager: Handles parameter validation and state
    - OptimizationController: Handles optimization execution
    - HighwaySegmentationGUI: Coordinates and provides unified interface
    """
    
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
        self.root.title("Highway Segmentation - REFACTORED ARCHITECTURE")
        self.root.geometry(f"{ui_config.window_width}x{ui_config.window_height}")
        
        # Set working directory to application directory for consistent file operations
        app_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(app_dir)
        
        # Initialize data and state variables
        self._initialize_variables()
        
        # Create results_text widget immediately to enable logging during initialization
        self._create_early_log_widget()
        
        # Initialize specialized manager classes (now safe to log during initialization)
        self.ui_builder = UIBuilder(self)
        self.file_manager = FileManager(self)
        self.parameter_manager = ParameterManager(self)
        self.optimization_controller = OptimizationController(self)
        self.settings_manager = SettingsManager()
        
        # Load saved settings
        self.settings = self.settings_manager.load_settings()
        
        # Create the user interface (will integrate the early log widget)
        self._create_interface()
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _initialize_variables(self):
        """Initialize all Tkinter variables and application state."""
        # Data management
        self.data = None
        self._data_file_path = ""
        self.data_file = tk.StringVar(value="No file selected")
        self._save_file_path = ""
        
        # Column mapping - initialized empty, UI builder sets display text
        self.x_column = tk.StringVar(value="")
        self.y_column = tk.StringVar(value="")
        self.route_column = tk.StringVar(value="None - treat as single route")  # New route column selection
        
        # Framework parameters (like x/y columns)
        self.gap_threshold = tk.DoubleVar(value=0.5)  # Framework-level parameter
        
        self.available_columns = []
        
        # Route processing state
        self.available_routes = []  # List of all routes in the data
        self.selected_routes = []   # List of routes selected for processing
        
        # Get default values from parameter definitions
        defaults = self._get_parameter_defaults()
        
        # Optimization parameters: Basic parameters (min_length, max_length, gap_threshold) 
        # are now handled by the dynamic parameter system for better method-specific control
        
        # Genetic algorithm parameters
        self.population_size = tk.IntVar(value=defaults.get('population_size', 100))
        self.num_generations = tk.IntVar(value=100)  # Universal default for all methods
        self.mutation_rate = tk.DoubleVar(value=defaults.get('mutation_rate', 0.05)) 
        self.crossover_rate = tk.DoubleVar(value=defaults.get('crossover_rate', 0.8))
        self.elite_ratio = tk.DoubleVar(value=defaults.get('elite_ratio', 0.05))
        
        # Method selection: Using dropdown UI (method_dropdown) instead of radio buttons,
        # but maintaining compatibility attribute for existing code
        self.optimization_method = 'multi'  # Default method
        
        # Constrained optimization parameters
        self.target_avg_length = tk.DoubleVar(value=defaults.get('target_avg_length', 2.0))
        self.penalty_weight = tk.DoubleVar(value=defaults.get('penalty_weight', 1000.0))
        self.length_tolerance = tk.DoubleVar(value=defaults.get('length_tolerance', 0.2))
        
        # Performance and caching controls
        self.cache_clear_interval = tk.IntVar(value=defaults.get('cache_clear_interval', 50))
        
        # Save/load options - always require manual save location selection
        self.custom_save_name = tk.StringVar(value="highway_segmentation.json")
        
        # Application state
        self.is_running = False
        self.stop_requested = False
    
    def _create_early_log_widget(self):
        """Create a minimal results_text widget early for logging during initialization."""
        # Create a temporary hidden text widget for early logging
        self.results_text = tk.Text(self.root, height=1, width=1)
        # Hide it off-screen - the proper UI will replace this
        self.results_text.place(x=-1000, y=-1000)
    
    def _create_interface(self):
        """Create the complete user interface using the UI builder."""
        # Create main layout
        main_frame = self.ui_builder.create_main_layout()
        
        # Create left pane: fixed required controls + dynamic parameters area
        required_frame = self.ui_builder.create_scrollable_left_pane(main_frame)
        
        # Create right pane for results
        right_pane = self.ui_builder.create_right_pane(main_frame)
        
        # Build required sections in the fixed (non-scrollable) left pane
        current_row = 0
        current_row = self.ui_builder.create_file_operations_section(required_frame, current_row)
        # parameters_section removed - now using dynamic parameters in method_section
        current_row = self.ui_builder.create_method_section(required_frame, current_row)
        # performance_section removed - now handled by dynamic parameters
        # save_load_section removed - now integrated into file_operations_section
        # Note: start/stop buttons now moved to top of right pane

        # Dynamic parameters UI: Treeview grid + editor panel
        if hasattr(self, "dynamic_params_parent"):
            self.ui_builder.create_dynamic_params_section(self.dynamic_params_parent)
        
        # Build right pane (now includes start/stop buttons at top)
        self.ui_builder.create_right_pane_actions(right_pane)
        self.ui_builder.create_results_section(right_pane)
        
        # Configure root window grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Apply loaded settings to UI
        self._apply_loaded_settings()
        
        # Set up parameter change tracking for auto-save
        self._setup_parameter_tracking()
        
        # Save settings on window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    # ===== DELEGATED METHODS =====
    # These methods delegate to the appropriate specialized managers
    
    # File Management Methods (delegate to FileManager)
    def set_data_file_path(self, full_path):
        """Set data file path - delegates to FileManager."""
        return self.file_manager.set_data_file_path(full_path)
    
    def get_data_file_path(self):
        """Get data file path - delegates to FileManager."""
        return self.file_manager.get_data_file_path()
    
    def set_save_file_path(self, full_path):
        """Set save file path - delegates to FileManager."""
        return self.file_manager.set_save_file_path(full_path)
    
    def get_save_file_path(self):
        """Get save file path - delegates to FileManager."""
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
        """Load CSV columns - delegates to FileManager."""
        return self.file_manager.load_csv_columns()
    
    def load_data_file(self):
        """Load data file - delegates to FileManager."""
        return self.file_manager.load_data_file()
    
    def load_and_plot_results(self):
        """Load and plot results - delegates to FileManager."""
        return self.file_manager.load_and_plot_results()
    
    def save_parameters(self):
        """Save parameters - delegates to FileManager.""" 
        return self.file_manager.save_parameters()
    
    def load_parameters(self):
        """Load parameters - delegates to FileManager."""
        return self.file_manager.load_parameters()
    
    # Parameter Management Methods (delegate to ParameterManager)
    def validate_parameters(self):
        """Validate parameters - delegates to ParameterManager."""
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
            if hasattr(self, 'method_dropdown') and hasattr(self.method_dropdown, 'get'):
                return get_method_key_from_display_name(self.method_dropdown.get())
        except (ImportError, AttributeError, ValueError, KeyError, TypeError):
            pass

        try:
            if hasattr(self, 'optimization_method'):
                return self._migrate_method_key(self.optimization_method)
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
        
        # Don't filter if it's the placeholder text
        if typed_text == "load data first...":
            return
            
        # Filter columns based on what user typed
        matching_columns = [col for col in self.available_columns 
                           if typed_text in col.lower()]
        
        # Update the combobox values with filtered results
        combobox['values'] = matching_columns
        
        # Keep the dropdown open to show filtered results
        if matching_columns and len(typed_text) > 0:
            combobox.event_generate('<Down>')
    
    def on_save_option_change(self):
        """Handle save option change - delegates to ParameterManager."""
        return self.parameter_manager.on_save_option_change()
    
    def on_route_column_change(self, event=None):
        """Handle route column selection change."""
        route_col = self.route_column.get()
        
        if route_col and route_col != "None - treat as single route":
            # Route column selected - validate it exists before trying to detect routes
            data_path = self.file_manager.get_data_file_path()
            if data_path:
                try:
                    # Quick check if the column exists to prevent error popups
                    import pandas as pd
                    df_headers = pd.read_csv(data_path, nrows=0)
                    if route_col in df_headers.columns:
                        # Treat route identifiers as categorical strings in-memory
                        try:
                            self.file_manager.ensure_route_column_is_string(route_col)
                        except Exception as e:
                            self.log_message(f"Warning: Could not normalize route column to string: {e}")
                        # Column exists - safe to detect routes
                        self.file_manager.detect_available_routes()
                        if hasattr(self, 'filter_routes_button'):
                            self.filter_routes_button.config(state="normal")
                    else:
                        # Column doesn't exist - reset quietly without popup
                        self.log_message(f"Route column '{route_col}' not found - resetting selection")
                        self.route_column.set("None - treat as single route")
                        self.available_routes = []
                        self.selected_routes = []
                        self.route_info_label.config(text="")
                        if hasattr(self, 'filter_routes_button'):
                            self.filter_routes_button.config(state="disabled")
                except Exception as e:
                    # Error reading file - reset to safe state
                    self.log_message(f"Error validating route column: {str(e)}")
                    self.route_column.set("None - treat as single route")
                    self.available_routes = []
                    self.selected_routes = []
                    self.route_info_label.config(text="")
                    if hasattr(self, 'filter_routes_button'):
                        self.filter_routes_button.config(state="disabled")
            else:
                # No data file - can't detect routes
                self.available_routes = []
                self.selected_routes = []
                self.route_info_label.config(text="")
                if hasattr(self, 'filter_routes_button'):
                    self.filter_routes_button.config(state="disabled")
        else:
            # No route column - clear route data and disable filter button
            self.available_routes = []
            self.selected_routes = []
            self.route_info_label.config(text="")
            if hasattr(self, 'filter_routes_button'):
                self.filter_routes_button.config(state="disabled")
            
        # Log the change (removed problematic parameter_manager call)
    
    def open_route_filter_dialog(self):
        """Open the route filter dialog to select which routes to process."""
        
        if not self.available_routes:
            # Try to automatically detect routes using current settings
            data_path = self.file_manager.get_data_file_path()
            route_col = self.route_column.get() if hasattr(self, 'route_column') else None
            
            if not data_path:
                messagebox.showwarning("No Data File", "Please select a data file first before filtering routes.")
                return
            elif not route_col or route_col == "None - treat as single route":
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
            except:
                # Fallback if messagebox also fails
                print(f"Critical error: {error_msg}")
    
    def _update_route_info_display(self):
        """Update the route info label to show selected route count."""
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
        """Start optimization - auto-save parameters then delegate to OptimizationController."""
        # Auto-save current parameters before starting optimization
        self._save_current_settings()
        
        return self.optimization_controller.start_optimization()
    
    def stop_optimization(self):
        """Stop optimization - delegates to OptimizationController."""
        return self.optimization_controller.stop_optimization()
    
    def show_help(self):
        """Open documentation in the user's browser (preferred UX).

        This dialog intentionally does not render markdown inline. It provides
        config-driven shortcuts to open:
        - USER_GUIDE.md
        - Method-specific README.md files under src/analysis/methods/docs/{method_key}/README.md
        """
        help_window = tk.Toplevel(self.root)
        help_window.title("Documentation")
        help_window.geometry("620x280")
        help_window.resizable(False, False)
        help_window.grab_set()  # Make it modal

        main_frame = ttk.Frame(help_window, padding=12)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(
            main_frame,
            text="Documentation",
            font=("Arial", 14, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            main_frame,
            text="Open the User Guide or method documentation in your browser.",
        ).pack(anchor="w", pady=(4, 12))

        project_root = os.path.dirname(os.path.dirname(__file__))
        user_guide_path = os.path.join(project_root, "USER_GUIDE.md")

        user_guide_frame = ttk.LabelFrame(main_frame, text="User Guide", padding=10)
        user_guide_frame.pack(fill="x")

        ttk.Button(
            user_guide_frame,
            text="🌐 Open User Guide in Browser",
            command=lambda: self._open_markdown_path_in_browser(user_guide_path, title="User Guide"),
        ).pack(anchor="w")

        method_frame = ttk.LabelFrame(main_frame, text="Method Documentation", padding=10)
        method_frame.pack(fill="x", pady=(12, 0))

        available_docs = self._get_available_method_docs(project_root)
        if not available_docs:
            ttk.Label(
                method_frame,
                text="No method README files found under src/analysis/methods/docs/.",
            ).pack(anchor="w")
        else:
            ttk.Label(method_frame, text="Method:").pack(side="left")

            method_display_names = [item[0] for item in available_docs]
            selected_method = tk.StringVar(value=method_display_names[0])

            method_combo = ttk.Combobox(
                method_frame,
                textvariable=selected_method,
                values=method_display_names,
                state="readonly",
                width=36,
            )
            method_combo.pack(side="left", padx=(6, 10))

            def open_selected_method_doc():
                display_name = selected_method.get()
                for name, _, readme_path in available_docs:
                    if name == display_name:
                        self._open_markdown_path_in_browser(readme_path, title=f"Method Doc - {name}")
                        return
                messagebox.showerror("Error", f"Could not resolve README for '{display_name}'")

            ttk.Button(
                method_frame,
                text="🌐 Open in Browser",
                command=open_selected_method_doc,
            ).pack(side="left")

        button_row = ttk.Frame(main_frame)
        button_row.pack(fill="x", pady=(14, 0))

        ttk.Button(button_row, text="Close", command=help_window.destroy).pack(side="right")

        help_window.update_idletasks()
        x = (help_window.winfo_screenwidth() // 2) - (help_window.winfo_width() // 2)
        y = (help_window.winfo_screenheight() // 2) - (help_window.winfo_height() // 2)
        help_window.geometry(f"+{x}+{y}")

    def _get_available_method_docs(self, project_root: str):
        """Return list of (display_name, method_key, readme_path) for methods with docs."""
        try:
            from config import OPTIMIZATION_METHODS
        except Exception:
            return []

        docs_root = os.path.join(project_root, "src", "analysis", "methods", "docs")
        available = []
        for method in OPTIMIZATION_METHODS:
            readme_path = os.path.join(docs_root, method.method_key, "README.md")
            if os.path.exists(readme_path):
                available.append((method.display_name, method.method_key, readme_path))
        return available

    def _open_markdown_path_in_browser(self, markdown_path: str, title: str):
        """Render a markdown file to HTML and open it in the browser."""
        if not os.path.exists(markdown_path):
            messagebox.showerror("Not Found", f"File not found:\n{markdown_path}")
            return

        if not MARKDOWN_AVAILABLE or 'markdown' not in globals():
            messagebox.showerror(
                "Markdown Not Available",
                "HTML documentation view requires the 'markdown' package. "
                "Install it (pip install markdown) or use the packaged environment.",
            )
            return

        try:
            with open(markdown_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()

            html = self._render_markdown_to_html(markdown_content, title=title)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp:
                tmp.write(html)
                temp_path = tmp.name

            webbrowser.open('file://' + os.path.abspath(temp_path))

            # Best-effort cleanup after a delay (keep file long enough for browser to load).
            def cleanup():
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

            self.root.after(5000, cleanup)

        except Exception as e:
            messagebox.showerror("Error", f"Could not open browser: {e}")

    def _render_markdown_to_html(self, markdown_content: str, title: str) -> str:
        """Convert markdown to a styled HTML document with TOC."""
        md = markdown.Markdown(extensions=[
            'toc',
            'extra',
            'codehilite',
            'nl2br',
        ])

        html_content = md.convert(markdown_content)
        toc_html = getattr(md, 'toc', '')

        return f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
    <script>
        // Render LaTeX math in docs using MathJax.
        // Supports inline: $...$ or \\(...\\) and display: $$...$$ or \\[...\\].
        window.MathJax = {{
            tex: {{
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
            }},
            options: {{
                skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
            }},
        }};
    </script>
    <script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; line-height: 1.6; }}
    .toc {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
    .toc h2 {{ margin-top: 0; color: #333; }}
    .toc ul {{ margin: 0; padding-left: 20px; }}
    .toc a {{ color: #0066cc; text-decoration: none; }}
    .toc a:hover {{ text-decoration: underline; }}
    h1, h2, h3, h4 {{ color: #2c3e50; }}
    h1 {{ border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
    h2 {{ border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }}
    pre {{ background: #f8f8f8; padding: 10px; border-radius: 5px; overflow-x: auto; }}
    code {{ background: #f0f0f0; padding: 2px 4px; border-radius: 3px; }}
    blockquote {{ border-left: 4px solid #3498db; padding-left: 15px; margin: 15px 0; color: #555; }}
    table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #f2f2f2; }}
  </style>
</head>
<body>
  <div class="toc">
    <h2>📋 Table of Contents</h2>
    {toc_html}
  </div>
  <hr>
  {html_content}
</body>
</html>
'''
    
    # ===== REMAINING DIRECT METHODS =====
    # These methods remain in the main class as they coordinate between managers
    
    def log_message(self, message):
        """
        Log a message to the GUI with timestamp.
        
        Args:
            message (str): Message to log
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Clean up \r characters from progress updates but don't do any replacement logic
        clean_message = message.replace('\r', '')
        formatted_message = f"[{timestamp}] {clean_message}"
        
        # results_text is now guaranteed to exist from early widget creation
        self.results_text.insert(tk.END, formatted_message + '\n')
        
        # Auto-scroll to the bottom
        self.results_text.see(tk.END)
    
    def handle_error(self, error_message: str, exception: Exception = None, 
                    severity: str = "error", show_messagebox: bool = False, 
                    silence_console: bool = True) -> None:
        """
        Centralized error handling that logs to GUI and optionally shows user dialogs.
        
        Replaces scattered print statements with structured error handling that:
        - Logs to GUI with consistent formatting and timestamps
        - Optionally shows user-friendly message boxes for critical errors
        - Maintains exception context for debugging
        - Provides severity levels for different error types
        
        Args:
            error_message: Human-readable error description
            exception: Original exception object (if any) 
            severity: 'info', 'warning', 'error', 'critical'
            show_messagebox: Whether to show a popup message to user
            silence_console: If True, don't print to console (use GUI logging instead)
        """
        # Format error message with severity prefix
        severity_prefix = {
            'info': 'ℹ️ INFO',
            'warning': '⚠️ WARNING', 
            'error': '❌ ERROR',
            'critical': '🚨 CRITICAL'
        }.get(severity, '❌ ERROR')
        
        formatted_message = f"{severity_prefix}: {error_message}"
        
        # Add exception details if provided
        if exception:
            formatted_message += f"\n   Details: {str(exception)}"
        
        # Log to GUI (this already includes timestamp)
        self.log_message(formatted_message)
        
        # Optionally show user dialog for critical errors
        if show_messagebox:
            if severity == 'critical':
                messagebox.showerror("Critical Error", error_message)
            elif severity == 'error':
                messagebox.showerror("Error", error_message)
            elif severity == 'warning':
                messagebox.showwarning("Warning", error_message)
            else:
                messagebox.showinfo("Information", error_message)
        
        # For debugging - optionally still print to console
        if not silence_console:
            print(f"[{severity.upper()}] {error_message}")
            if exception:
                print(f"   Exception: {exception}")

    def show_current_parameters(self):
        """Display all current parameter values in the log for user review."""
        method = self.ui_builder.method_dropdown.get()
        self.log_message("=== CURRENT PARAMETER VALUES ===")
        self.log_message(f"Optimization Method: {method}")
        self.log_message("")
        
        # Get current parameter values from dynamic system
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
        try:
            # Apply file paths
            data_path = self.settings.get('files', {}).get('data_file_path', '')
            if data_path and os.path.exists(data_path):
                self.file_manager.set_data_file_path(data_path)
                # Load CSV columns to populate dropdowns when restoring settings
                self.file_manager.load_csv_columns()
            
            save_path = self.settings.get('files', {}).get('save_file_path', '')
            if save_path:
                self.file_manager.set_save_file_path(save_path)
            
            # Apply optimization parameters
            opt_settings = self.settings.get('optimization', {})
            
            # Load optimization method FIRST before applying parameters
            # NOTE: We store the optimization method selection under 'optimization_method'
            # to avoid colliding with AASHTO CDA's parameter name 'method'.
            method_key = opt_settings.get('optimization_method', None)

            # If older settings stored the optimization method under a generic 'method' key,
            # accept it only if it is a valid registry method key.
            if method_key is None:
                legacy_candidate = opt_settings.get('method', None)
                method_key = legacy_candidate

            # Validate against registry (no numeric-ID migration; keep it simple).
            # If invalid, treat as an incompatibility error and require user selection.
            try:
                method_key = self._migrate_method_key(method_key)
            except Exception as e:
                try:
                    self.log_message(
                        f"ERROR: Settings contain an unknown optimization method ({method_key}). "
                        f"Please select a valid method from the dropdown. Details: {e}"
                    )
                except Exception:
                    pass
                try:
                    messagebox.showerror(
                        "Incompatible Settings",
                        "Saved settings refer to an unknown optimization method.\n\n"
                        "Please choose a valid method from the dropdown and re-save your settings.",
                    )
                except Exception:
                    pass
                # Keep the currently initialized GUI default method.
                method_key = getattr(self, 'optimization_method', None) or 'multi'
            
            # Store the optimization method as an attribute
            self.optimization_method = method_key

            # Migration: if per-method store is empty/missing for this method, seed it from
            # the legacy flat optimization dict (min_length/max_length/etc were historically shared).
            try:
                if isinstance(opt_settings, dict):
                    store = opt_settings.setdefault('dynamic_parameters_by_method', {})
                    if isinstance(store, dict) and method_key and method_key not in store:
                        # Only include keys that are likely to be dynamic method parameters.
                        # We avoid copying 'optimization_method' and other meta keys.
                        legacy_candidate = {
                            k: v for k, v in opt_settings.items()
                            if k not in {
                                'optimization_method',
                                'dynamic_parameters_by_method'
                            }
                        }
                        store[method_key] = legacy_candidate
            except Exception as e:
                # Non-fatal migration failure; do not block startup.
                if hasattr(self, 'log_message'):
                    self.log_message(f"Warning: Could not seed per-method parameters for '{method_key}': {e}")
                else:
                    print(f"Warning: Could not seed per-method parameters for '{method_key}': {e}")
            
            # Apply method selection to dropdown BEFORE loading parameters
            if hasattr(self, 'method_dropdown') and hasattr(self.method_dropdown, 'set'):
                try:
                    # Convert method key to display name
                    from config import get_optimization_method
                    method_config = get_optimization_method(method_key)
                    self.method_dropdown.set(method_config.display_name)

                    # Refresh dynamic parameter UI for the selected method
                    try:
                        if hasattr(self, 'parameter_manager'):
                            self.parameter_manager.on_method_change()
                        elif hasattr(self, 'ui_builder'):
                            self.ui_builder.set_method_description(method_key)
                            self.ui_builder.refresh_dynamic_params_grid(method_key)
                    except Exception as e:
                        self.log_message(f"Warning: Could not refresh dynamic parameters for '{method_key}': {e}")
                        
                except (ValueError, KeyError) as e:
                    # Fallback to default if method not found or invalid
                    self.log_message(f"Could not restore method '{method_key}': {e}. Using default.")
                    # Clear the invalid method from settings to prevent this error on next startup
                    # NOTE: do not overwrite AASHTO CDA's parameter name 'method'.
                    opt_settings['optimization_method'] = 'multi'  # Fix the bad optimization setting
                    self.method_dropdown.set("Multi-Objective NSGA-II")
                    self.optimization_method = 'multi'  # Ensure we have correct key even with fallback

                    # Refresh dynamic parameter UI for the fallback method
                    try:
                        if hasattr(self, 'parameter_manager'):
                            self.parameter_manager.on_method_change()
                        elif hasattr(self, 'ui_builder'):
                            self.ui_builder.set_method_description('multi')
                            self.ui_builder.refresh_dynamic_params_grid('multi')
                    except Exception as e:
                        self.log_message(f"Warning: Could not refresh dynamic parameters for fallback: {e}")
            
            # NOW apply parameters to the correct method's UI
            # If we have per-method saved dynamic parameters, merge those for the
            # selected method so min/max/etc don't get overwritten by another method.
            merged_settings = opt_settings.copy() if isinstance(opt_settings, dict) else {}
            per_method_store = merged_settings.get('dynamic_parameters_by_method', {}) if isinstance(merged_settings, dict) else {}
            per_method_params = per_method_store.get(method_key) if isinstance(per_method_store, dict) else None
            if isinstance(per_method_params, dict):
                merged_settings.update(per_method_params)

            self.parameter_manager.apply_settings(merged_settings)

            # Track active method for later switch persistence
            self._active_method_key = method_key
            
            # Apply column selections  
            ui_state = self.settings.get('ui_state', {})
            if 'x_column' in ui_state and hasattr(self, 'x_column'):
                self.x_column.set(ui_state['x_column'])
            if 'y_column' in ui_state and hasattr(self, 'y_column'):
                self.y_column.set(ui_state['y_column'])
            if 'gap_threshold' in ui_state and hasattr(self, 'gap_threshold'):
                self.gap_threshold.set(ui_state['gap_threshold'])
            if 'route_column' in ui_state and hasattr(self, 'route_column'):
                self.route_column.set(ui_state['route_column'])
            
            # Restore route selection
            if 'selected_routes' in ui_state:
                self.selected_routes = ui_state['selected_routes'].copy()
            
            # If route column is set and data file exists, trigger full route processing
            if (hasattr(self, 'route_column') and 
                self.route_column.get() and 
                self.route_column.get() != "None - treat as single route" and
                self.file_manager.get_data_file_path()):
                self.log_message("Detecting routes from restored settings...")
                # Call the full route column change handler to enable button and update display
                self.on_route_column_change()
            
            # Update UI visibility based on loaded method
            # BUT skip if we just loaded parameters to avoid widget rebuild
            # Parameter loading already handles method-specific UI setup
            # self.parameter_manager.on_method_change()  # DISABLED - causes widget rebuild after parameter loading
        
        except Exception as e:
            self.handle_error("Could not apply some loaded settings", e, "warning")
    
    def _migrate_method_key(self, method_key):
        """
        Normalize/validate method keys loaded from settings.

        This project uses config-driven method registration. We accept a method key
        only if it exists in the config registry; otherwise we fall back to the GUI
        default.
        
        Args:
            method_key: The method key from settings (could be old numeric or new string format)
            
        Returns:
            str: The standardized string-based method key
        """
        if isinstance(method_key, str):
            try:
                from config import get_optimization_method
                get_optimization_method(method_key)
                return method_key
            except Exception:
                pass

        raise ValueError(f"Unknown optimization method key in settings: {method_key!r}")
    
    def _setup_parameter_tracking(self):
        """Set up automatic saving when parameters change."""
        # Track only framework/global UI state here.
        # Method-specific optimization parameters are persisted via the dynamic
        # parameter store and the Apply/Reset buttons in the editor.
        tracked_vars = [
            self.custom_save_name,
        ]
        
        # Add column selection variables if they exist
        if hasattr(self, 'x_column'):
            tracked_vars.append(self.x_column)
        if hasattr(self, 'y_column'):
            tracked_vars.append(self.y_column)
        if hasattr(self, 'gap_threshold'):
            tracked_vars.append(self.gap_threshold)
        if hasattr(self, 'route_column'):
            tracked_vars.append(self.route_column)
        
        # Add trace callbacks to automatically save when values change
        for var in tracked_vars:
            try:
                var.trace_add("write", lambda *_: self.on_parameter_change())
            except Exception as e:
                self.handle_error(f"Could not add auto-save to variable {var}", e, "warning")
    
    def _save_current_settings(self):
        """Save current UI state to settings."""
        try:
            # Update file paths
            self.settings['files']['data_file_path'] = self.file_manager.get_data_file_path() or ''
            self.settings['files']['save_file_path'] = self.file_manager.get_save_file_path() or ''
            
            # Persist dynamic params for the active method (so they survive restart)
            try:
                active_key = getattr(self, '_active_method_key', None) or self._get_selected_method_key_safe()
                if active_key:
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
            
            # Update method selection from dropdown - convert display name to key for settings
            if hasattr(self.ui_builder, 'method_dropdown'):
                from config import get_method_key_from_display_name
                display_name = self.ui_builder.method_dropdown.get()
                try:
                    method_key = get_method_key_from_display_name(display_name)
                except ValueError:
                    # If display_name lookup fails, check if it's already a method key
                    from config import get_optimization_method
                    try:
                        get_optimization_method(display_name)  # Test if it's a valid method key
                        method_key = display_name  # Use as-is if it's a valid method key
                    except (ValueError, KeyError):
                        method_key = 'multi'  # Final fallback
                        
                # Ensure we always save the migrated string-based method key
                method_key = self._migrate_method_key(method_key)
                self.settings['optimization']['optimization_method'] = method_key
            elif hasattr(self, 'optimization_method'):
                # Fallback: use the optimization_method attribute with migration
                method_key = self._migrate_method_key(self.optimization_method)
                self.settings['optimization']['optimization_method'] = method_key
            else:
                # Final fallback
                self.settings['optimization']['optimization_method'] = 'multi'
            
            # Save window geometry
            self.settings['ui_state']['window_geometry'] = self.root.geometry()
            
            # Save column selections
            if hasattr(self, 'x_column'):
                self.settings['ui_state']['x_column'] = self.x_column.get()
            if hasattr(self, 'y_column'):
                self.settings['ui_state']['y_column'] = self.y_column.get()
            if hasattr(self, 'gap_threshold'):
                self.settings['ui_state']['gap_threshold'] = self.gap_threshold.get()
            if hasattr(self, 'route_column'):
                self.settings['ui_state']['route_column'] = self.route_column.get()
            
            # Save route selection
            if hasattr(self, 'selected_routes'):
                self.settings['ui_state']['selected_routes'] = self.selected_routes.copy()
            
            # Save to file
            self.settings_manager.save_settings(self.settings)
            
        except Exception as e:
            self.log_message(f"Could not save settings: {e}")
    
    def _on_closing(self):
        """Handle application closing - save settings and clean up."""
        
        # Cancel any pending save timers first
        if hasattr(self, '_save_timer'):
            try:
                self.root.after_cancel(self._save_timer)
            except tk.TclError:
                pass  # Timer may have already executed
                
        # Save current settings before closing
        try:
            self._save_current_settings()
        except Exception as e:
            self.handle_error("Could not save settings on shutdown", e, "warning")
        
        # Stop any running optimization immediately and wait for it to finish
        if hasattr(self, 'optimization_controller') and self.is_running:
            self.stop_requested = True
            self.optimization_controller.stop_optimization()
            
        # Proper matplotlib cleanup
        try:
            import matplotlib.pyplot as plt
            
            # Close any remaining matplotlib figures
            open_figures = plt.get_fignums()
            if open_figures:
                plt.close('all')
                
            # Turn off interactive mode
            plt.ioff()
        except Exception as e:
            self.handle_error("Failed to cleanup matplotlib resources", e, 
                             severity="warning", silence_console=True)
            
        # Clean up application state
        self.is_running = False
        
        # Small delay to ensure all file operations complete
        import time
        time.sleep(0.1)
        
        # Normal, proper shutdown
        try:
            self.root.quit()  # Stop the main loop but keep window
            self.root.destroy()  # Now destroy the window
        except Exception as e:
            self.handle_error("Error occurred during application shutdown", e,
                             severity="error", silence_console=True)
    
    def on_parameter_change(self):
        """Called when any parameter changes - save settings with minimal delay."""
        # Cancel any existing timer to avoid excessive saves
        if hasattr(self, '_save_timer'):
            try:
                self.root.after_cancel(self._save_timer)
            except tk.TclError:
                pass
        # Reduced delay from 1000ms to 500ms for faster response        
        self._save_timer = self.root.after(500, self._save_current_settings)
    
    def on_closing(self):
        """Handle application closing - redirect to main close handler."""
        # Redirect to the main close handler - no artificial delays
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
    
    # Configure ttk style
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

    # Create and run application
    app = HighwaySegmentationGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Application interrupted by user")
        root.destroy()


if __name__ == "__main__":
    main()