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
from tkinter import ttk, messagebox, scrolledtext
import os
from datetime import datetime
import re
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
        
        # Create left scrollable pane for controls
        scrollable_frame = self.ui_builder.create_scrollable_left_pane(main_frame)
        
        # Create right pane for results
        right_pane = self.ui_builder.create_right_pane(main_frame)
        
        # Build all sections in the left pane
        current_row = 0
        current_row = self.ui_builder.create_file_operations_section(scrollable_frame, current_row)
        # parameters_section removed - now using dynamic parameters in method_section
        current_row = self.ui_builder.create_method_section(scrollable_frame, current_row)
        # performance_section removed - now handled by dynamic parameters
        # save_load_section removed - now integrated into file_operations_section
        # Note: start/stop buttons now moved to top of right pane
        
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
        if not hasattr(self, 'ui_builder'):
            return

        try:
            dynamic_values = self.ui_builder.get_parameter_values()
        except Exception as e:
            if hasattr(self, 'handle_error'):
                self.handle_error(
                    f"Could not read dynamic parameters for method '{method_key}'",
                    e,
                    severity="warning",
                    show_messagebox=False,
                )
            elif hasattr(self, 'log_message'):
                self.log_message(
                    f"Warning: Could not read dynamic parameters for method '{method_key}': {e}"
                )
            return

        opt = self.settings.setdefault('optimization', {})
        store = opt.setdefault('dynamic_parameters_by_method', {})
        store[method_key] = dynamic_values

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
            dialog = RouteFilterDialog(self.root, self.available_routes, self.selected_routes)
            result = dialog.show()
            
            if result:
                self.selected_routes = result
                self._update_route_info_display()
                self.log_message(f"Route selection updated: {len(self.selected_routes)} routes selected")
        except Exception as e:
            self.log_message(f"ERROR: Failed to open route filter dialog: {str(e)}")
            messagebox.showerror("Dialog Error", f"Error opening route filter dialog: {str(e)}")
    
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
        """Display the USER_GUIDE.md content with HTML rendering and TOC if markdown library available."""
        help_window = tk.Toplevel(self.root)
        help_window.title("Highway Segmentation Tool - User Guide")
        help_window.geometry("1000x750")
        help_window.grab_set()  # Make it modal
        
        # Create main frame with padding
        main_frame = ttk.Frame(help_window, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Highway Segmentation Tool - User Guide", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Load the user guide content
        try:
            user_guide_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "USER_GUIDE.md")
            with open(user_guide_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except FileNotFoundError:
            content = "USER_GUIDE.md file not found.\\n\\nPlease ensure the file is located in the project root directory."
        except Exception as e:
            content = f"Error loading user guide: {str(e)}"
        
        # Check if we can use HTML rendering
        if MARKDOWN_AVAILABLE and content.startswith("# "):
            self._create_html_help_view(main_frame, help_window, content)
        else:
            self._create_text_help_view(main_frame, help_window, content)
    
    def _create_html_help_view(self, parent, help_window, markdown_content):
        """Create HTML help view with table of contents using standard markdown library."""
        # Safety check - ensure markdown is available
        if not MARKDOWN_AVAILABLE:
            self._create_text_help_view(parent, help_window, markdown_content)
            return
            
        try:
            # Ensure markdown module is available before using it
            if 'markdown' not in globals():
                self._create_text_help_view(parent, help_window, markdown_content)
                return
                
            # Use standard markdown library with TOC extension
            md = markdown.Markdown(extensions=[
                'toc',           # Table of contents
                'extra',         # Extra features (tables, fenced code, etc.)
                'codehilite',    # Code syntax highlighting
                'nl2br'          # Newline to break
            ])
            
            # Convert markdown to HTML
            html_content = md.convert(markdown_content)
            
            # Get TOC if available (only exists if toc extension is loaded)
            toc_html = getattr(md, 'toc', '')  # Auto-generated table of contents
            
            # Create complete HTML document with styling
            full_html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>User Guide</title>
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
            
            # Create temporary HTML file and open in browser
            button_frame = ttk.Frame(parent)
            button_frame.pack(pady=(10, 0))
            
            def open_in_browser():
                try:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                        f.write(full_html)
                        temp_path = f.name
                    
                    webbrowser.open('file://' + os.path.abspath(temp_path))
                    help_window.destroy()
                    
                    # Clean up temp file after a delay
                    def cleanup():
                        try:
                            os.unlink(temp_path)
                        except OSError:
                            pass
                    help_window.after(5000, cleanup)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open browser: {e}")
            
            # Information and buttons
            info_label = ttk.Label(parent, 
                                  text="✨ Enhanced view available with Table of Contents and formatting!")
            info_label.pack(pady=(0, 10))
            
            ttk.Button(button_frame, text="🌐 Open in Browser (Recommended)", 
                      command=open_in_browser).pack(side="left", padx=(0, 10))
            
            # Fallback to text view
            ttk.Button(button_frame, text="📄 View as Text", 
                      command=lambda: self._create_text_help_view(parent, help_window, markdown_content, replace=True)).pack(side="left", padx=(0, 10))
            
            ttk.Button(button_frame, text="❌ Close", 
                      command=help_window.destroy).pack(side="right")
            
            # Show preview of TOC
            toc_frame = ttk.LabelFrame(parent, text="📋 Table of Contents Preview", padding=10)
            toc_frame.pack(fill="x", pady=(20, 0))
            
            toc_text = tk.Text(toc_frame, height=8, wrap="word", font=("Consolas", 9))
            toc_text.pack(fill="x")
            
            # Extract and display TOC from HTML
            import re
            toc_links = re.findall(r'<a href="#([^"]+)">([^<]+)</a>', toc_html)
            toc_preview = "\\n".join([f"• {title}" for _, title in toc_links[:15]])  # First 15 items
            if len(toc_links) > 15:
                toc_preview += f"\\n... and {len(toc_links) - 15} more sections"
            
            toc_text.insert("1.0", toc_preview)
            toc_text.config(state="disabled")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not create HTML view: {e}")
            self._create_text_help_view(parent, help_window, markdown_content)
        x = (help_window.winfo_screenwidth() // 2) - (help_window.winfo_width() // 2)
        y = (help_window.winfo_screenheight() // 2) - (help_window.winfo_height() // 2)
        help_window.geometry(f"+{x}+{y}")
    
    def _create_text_help_view(self, parent, help_window, content, replace=False):
        """Create fallback text view for help content."""
        if replace:
            # Clear existing widgets
            for widget in parent.winfo_children():
                if not isinstance(widget, ttk.Label) or "User Guide" not in widget.cget("text"):
                    widget.destroy()
        
        # Create scrolled text widget for content
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill="both", expand=True)
        
        text_widget = scrolledtext.ScrolledText(text_frame, 
                                               wrap="word", 
                                               font=("Consolas", 10),
                                               padx=10, pady=10)
        text_widget.pack(fill="both", expand=True)
        
        # Simple markdown formatting for better readability
        formatted_content = self._format_markdown_for_display(content)
        text_widget.insert("1.0", formatted_content)
        text_widget.config(state="disabled")  # Make read-only
        
        # Add navigation buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(pady=(10, 0))
        
        # Close button
        close_button = ttk.Button(button_frame, text="Close", 
                                 command=help_window.destroy)
        close_button.pack(side="right", padx=(10, 0))
        
        # Search functionality
        search_frame = ttk.Frame(button_frame)
        search_frame.pack(side="left")
        
        ttk.Label(search_frame, text="Search:").pack(side="left")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=20)
        search_entry.pack(side="left", padx=(5, 5))
        
        def search_text():
            query = search_var.get()
            if query:
                text_widget.config(state="normal")
                text_widget.tag_remove("highlight", "1.0", "end")
                
                start = "1.0"
                while True:
                    pos = text_widget.search(query, start, stopindex="end", nocase=True)
                    if not pos:
                        break
                    end = f"{pos}+{len(query)}c"
                    text_widget.tag_add("highlight", pos, end)
                    start = end
                
                text_widget.tag_config("highlight", background="yellow")
                text_widget.config(state="disabled")
                
                # Focus on first occurrence
                first_pos = text_widget.search(query, "1.0", stopindex="end", nocase=True)
                if first_pos:
                    text_widget.see(first_pos)
        
        search_button = ttk.Button(search_frame, text="Find", command=search_text)
        search_button.pack(side="left")
        
        # Bind Enter key to search
        search_entry.bind('<Return>', lambda e: search_text())
        
        # Center the help window if not already done
        if not replace:
            help_window.update_idletasks()
            x = (help_window.winfo_screenwidth() // 2) - (help_window.winfo_width() // 2)
            y = (help_window.winfo_screenheight() // 2) - (help_window.winfo_height() // 2)
            help_window.geometry(f"+{x}+{y}")
    
    def _format_markdown_for_display(self, content):
        """Apply basic markdown formatting for better text display."""
        lines = content.split('\\n')
        formatted_lines = []
        
        for line in lines:
            # Headers
            if line.startswith('# '):
                formatted_lines.append('\\n' + '='*60)
                formatted_lines.append(line[2:].upper())
                formatted_lines.append('='*60 + '\\n')
            elif line.startswith('## '):
                formatted_lines.append('\\n' + '-'*50)
                formatted_lines.append(line[3:])
                formatted_lines.append('-'*50 + '\\n')
            elif line.startswith('### '):
                formatted_lines.append('\\n' + line[4:].upper())
                formatted_lines.append('~'*len(line[4:]) + '\\n')
            elif line.startswith('#### '):
                formatted_lines.append('\\n' + line[5:])
                formatted_lines.append('*'*len(line[5:]) + '\\n')
            
            # Bold text (basic replacement)
            elif '**' in line:
                line = re.sub(r'\\*\\*(.*?)\\*\\*', r'\\1', line)
                formatted_lines.append(line)
            
            # Code blocks and bullets  
            elif line.startswith('```'):
                formatted_lines.append('\\n' + line)
            elif line.startswith('- '):
                formatted_lines.append('  • ' + line[2:])
                
            else:
                formatted_lines.append(line)
                
        return '\\n'.join(formatted_lines)
    
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
        self.log_message("GLOBAL PARAMETERS (shared by all methods):")
        self.log_message(f"  Population Size: {self.population_size.get()}")
        self.log_message(f"  Generations: {self.num_generations.get()}")
        self.log_message(f"  Mutation Rate: {self.mutation_rate.get()}")
        self.log_message(f"  Crossover Rate: {self.crossover_rate.get()}")
        self.log_message(f"  Cache Clear Interval: {self.cache_clear_interval.get()}")
        self.log_message(f"  Performance Stats: {self.get_enable_performance_stats()}")
        self.log_message(f"  Segment Caching: Always Enabled (Performance Optimization)")
        self.log_message(f"  Custom Save Name: {self.custom_save_name.get()}")
        
        if method in ["single", "constrained"]:
            self.log_message("")
            self.log_message("SINGLE-OBJECTIVE PARAMETERS:")
            self.log_message(f"  Elite Ratio: {self.elite_ratio.get()}")
        
        if method == "constrained":
            self.log_message("")
            self.log_message("CONSTRAINED OPTIMIZATION PARAMETERS:")
            self.log_message(f"  Target Avg Length: {self.target_avg_length.get()}")
            self.log_message(f"  Penalty Weight: {self.penalty_weight.get()}")
            self.log_message(f"  Length Tolerance: {self.length_tolerance.get()}")
        
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
            if method_key is None:
                legacy_method = opt_settings.get('method', 'multi')
                # Only treat legacy 'method' as optimization method if it looks like one.
                if legacy_method in ['single', 'multi', 'constrained', 'aashto_cda', 0, 1, 2, 3, '0', '1', '2', '3']:
                    method_key = legacy_method
                else:
                    method_key = 'multi'
            
            # BACKWARD COMPATIBILITY: Convert old numeric method IDs to new string keys
            method_key = self._migrate_method_key(method_key)
            
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
                    
                    # Create UI widgets for the selected method BEFORE loading parameters
                    # This ensures parameter_values dict is populated for the correct method
                    if hasattr(self, 'ui_builder') and hasattr(self.ui_builder, '_update_dynamic_parameters'):
                        self.ui_builder._update_dynamic_parameters()
                        
                except (ValueError, KeyError) as e:
                    # Fallback to default if method not found or invalid
                    self.log_message(f"Could not restore method '{method_key}': {e}. Using default.")
                    # Clear the invalid method from settings to prevent this error on next startup
                    # NOTE: do not overwrite AASHTO CDA's parameter name 'method'.
                    opt_settings['optimization_method'] = 'multi'  # Fix the bad optimization setting
                    self.method_dropdown.set("Multi-Objective NSGA-II")
                    self.optimization_method = 'multi'  # Ensure we have correct key even with fallback
                    
                    # Create UI widgets for the fallback method
                    if hasattr(self, 'ui_builder') and hasattr(self.ui_builder, '_update_dynamic_parameters'):
                        self.ui_builder._update_dynamic_parameters()
            
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
        Migrate old numeric method IDs to new string-based method keys for backward compatibility.
        
        Args:
            method_key: The method key from settings (could be old numeric or new string format)
            
        Returns:
            str: The standardized string-based method key
        """
        # If already a valid string method key, return as-is
        if method_key in ['single', 'multi', 'constrained', 'aashto_cda']:
            return method_key
            
        # Legacy numeric method ID mapping (based on old dropdown order)
        numeric_to_string = {
            '0': 'single',           # Single-Objective GA
            '1': 'multi',            # Multi-Objective NSGA-II  
            '2': 'aashto_cda',       # AASHTO CDA Statistical Analysis
            '3': 'constrained',      # Constrained Single-Objective
            # Handle both string and integer numeric IDs
            0: 'single',
            1: 'multi', 
            2: 'aashto_cda',
            3: 'constrained'
        }
        
        # Convert numeric ID to string key
        migrated_key = numeric_to_string.get(method_key, None)
        
        if migrated_key:
            self.log_message(f"Migrated old method ID '{method_key}' to '{migrated_key}'")
            return migrated_key
        else:
            # Unknown method key, use default and log warning
            self.log_message(f"Unknown method key '{method_key}', defaulting to 'multi'")
            return 'multi'
    
    def _setup_parameter_tracking(self):
        """Set up automatic saving when parameters change."""
        # List of all parameter variables to track (excluding dropdown which has its own callback)
        tracked_vars = [
            # min_length, max_length now handled by dynamic parameters
            # gap_threshold is framework parameter (tracked separately below)
            # enable_performance_stats handled by dynamic parameters, segment_cache always enabled
            self.population_size, self.num_generations, self.mutation_rate,
            self.crossover_rate, self.elite_ratio,
            self.target_avg_length, self.penalty_weight, self.length_tolerance,
            self.cache_clear_interval, self.custom_save_name
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

            # Update optimization parameters
            current_params = self.parameter_manager.get_current_parameters()
            self.settings['optimization'].update(current_params)
            
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
    root = tk.Tk()
    
    # Configure ttk style
    style = ttk.Style()
    if "winnative" in style.theme_names():
        style.theme_use("winnative")
    elif "clam" in style.theme_names():
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