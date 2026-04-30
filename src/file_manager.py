"""
File Manager Module for Highway Segmentation GA

This module handles all file operations including data loading, CSV processing,
parameter saving/loading, and result file management, separating these concerns 
from the main GUI class.
"""

import os
import sys
import json
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from config import UIConfig

# Create UI config instance
ui_config = UIConfig()


def is_test_environment():
    """Detect if we're running in a test environment to avoid GUI popups."""
    return (
        'pytest' in sys.modules or
        'unittest' in sys.modules or
        any('test' in arg.lower() for arg in sys.argv) or
        os.environ.get('PYTEST_CURRENT_TEST') is not None
    )


def show_error_message(title, message, log_callback=None):
    """Show error message - popup in GUI mode, log in test mode."""
    if is_test_environment():
        # In test mode: just log the error, don't show popup
        error_msg = f"[{title}] {message}"
        if log_callback:
            log_callback(error_msg)
        else:
            print(f"TEST MODE ERROR: {error_msg}")
    else:
        # In GUI mode: show popup as normal
        messagebox.showerror(title, message)


class FileManager:
    """
    Handles all file operations for the Highway Segmentation application.
    
    This class manages data loading, CSV processing, parameter persistence,
    and result file handling, providing a clean separation of file I/O logic
    from the main application class.
    """
    
    def __init__(self, main_app):
        """
        Initialize the file manager with a reference to the main application.
        
        Args:
            main_app: Reference to the main HighwaySegmentationGUI instance
        """
        self.app = main_app
    
    def set_data_file_path(self, full_path):
        """
        Set the full data file path and update display with filename only.
        
        Args:
            full_path (str): Complete path to the data file
        """
        if full_path:
            self.app._data_file_path = full_path
            # Extract and display just the filename
            filename = os.path.basename(full_path)
            
            # Create tooltip helper for the entry widget
            class ToolTip:
                def __init__(self, widget, text=''):
                    self.widget = widget
                    self.text = text
                    self.widget.bind("<Enter>", self.enter)
                    self.widget.bind("<Leave>", self.leave)
                    self.tooltip = None
                
                def enter(self, event=None):
                    x = y = 0
                    x, y, _, _ = self.widget.bbox("insert")
                    x += self.widget.winfo_rootx() + 25
                    y += self.widget.winfo_rooty() + 25
                    
                    self.tooltip = tw = tk.Toplevel(self.widget)
                    tw.wm_overrideredirect(True)
                    tw.wm_geometry("+%d+%d" % (x, y))
                    
                    label = tk.Label(tw, text=self.text, justify='left',
                                   background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                                   font=("Arial", 9))
                    label.pack(ipadx=1)
                
                def leave(self, event=None):
                    if self.tooltip:
                        self.tooltip.destroy()
                        self.tooltip = None
                
                def update_text(self, new_text):
                    self.text = new_text
            
            # Update display with filename only
            self.app.data_file.set(filename)
            
            # Add tooltip showing full path
            if hasattr(self.app, 'data_entry'):
                if not hasattr(self.app, '_data_tooltip'):
                    self.app._data_tooltip = ToolTip(self.app.data_entry, full_path)
                else:
                    self.app._data_tooltip.update_text(full_path)
    
    def get_data_file_path(self):
        """Get the full path to the currently selected data file."""
        return getattr(self.app, '_data_file_path', '')
    
    def set_save_file_path(self, full_path):
        """
        Set the full save file path and update display with filename only.
        
        Args:
            full_path (str): Complete path to the save location
        """
        if full_path:
            self.app._save_file_path = full_path
            # Extract and display just the filename without extension
            filename = os.path.splitext(os.path.basename(full_path))[0]
            self.app.custom_save_name.set(filename)
    
    def get_save_file_path(self):
        """Get the full path to the currently selected save location."""
        return getattr(self.app, '_save_file_path', '')
    
    def browse_data_file(self):
        """Open file dialog to select a CSV data file."""
        try:
            # Start in current directory by default
            initial_dir = os.getcwd()
            
            filename = filedialog.askopenfilename(
                title="Select Highway Data CSV File",
                filetypes=ui_config.csv_file_types,
                initialdir=initial_dir
            )
            
            if filename:
                self.set_data_file_path(filename)
                self.load_csv_columns()
        except Exception as e:
            show_error_message("File Selection Error", f"Error selecting file: {str(e)}", self.app.log_message)
    
    def browse_save_location(self):
        """Open file dialog to select save location for results."""
        try:
            # Determine initial directory - default to Results/ folder with fallback to last directory
            initial_dir = "Results"
            if hasattr(self.app, '_last_file_directory') and self.app._last_file_directory:
                initial_dir = self.app._last_file_directory
            elif self.get_save_file_path():
                initial_dir = os.path.dirname(self.get_save_file_path())
            elif not os.path.exists("Results"):
                initial_dir = "."
            
            filename = filedialog.asksaveasfilename(
                title="Select Save Location for Results", 
                filetypes=ui_config.results_file_types,
                defaultextension=".json",
                initialdir=initial_dir
            )
            
            if filename:
                # Store selected directory for future use
                self.app._last_file_directory = os.path.dirname(filename)
                self.set_save_file_path(filename)
        except Exception as e:
            show_error_message("Save Location Error", f"Error selecting save location: {str(e)}", self.app.log_message)
    
    def load_csv_columns(self):
        """Load and populate column names from the selected CSV file."""
        data_path = self.get_data_file_path()
        if not data_path:
            return
        
        try:
            # Read just the first row to get column names
            df = pd.read_csv(data_path, nrows=0)
            columns = df.columns.tolist()
            self.app.available_columns = columns
            
            self.app.log_message(f"Found {len(columns)} columns: {columns}")
            
            # Reset route state when loading new file
            self.app.available_routes = []
            self.app.selected_routes = []
            if hasattr(self.app, 'route_info_label'):
                self.app.route_info_label.config(text="")
            if hasattr(self.app, 'filter_routes_button'):
                self.app.filter_routes_button.config(state="disabled")
            
            # Reset route column selection to default when loading new file
            if hasattr(self.app, 'route_column'):
                self.app.route_column.set("None - treat as single route")
            
            # Reset optimization controller state to prevent stale data issues
            if hasattr(self.app, 'optimization_controller'):
                self.app.optimization_controller.reset_state()
            
            # Update combobox values
            if hasattr(self.app, 'x_column_combo'):
                self.app.x_column_combo['values'] = columns
                # CRITICAL FIX: Always clear X column selection when loading new file
                # This prevents old column names from persisting when switching files
                current_x = self.app.x_column.get()
                if current_x == "Load data first..." or current_x not in columns:
                    self.app.x_column.set("")
                    self.app.log_message(f"Cleared X column selection (was '{current_x}', not in new file)")
            if hasattr(self.app, 'y_column_combo'):
                self.app.y_column_combo['values'] = columns
                # CRITICAL FIX: Always clear Y column selection when loading new file
                # This prevents old column names from persisting when switching files
                current_y = self.app.y_column.get()
                if current_y == "Load data first..." or current_y not in columns:
                    self.app.y_column.set("")
                    self.app.log_message(f"Cleared Y column selection (was '{current_y}', not in new file)")
            if hasattr(self.app, 'route_column_combo'):
                # Add "None" option at the beginning for route column
                route_options = ["None - treat as single route"] + columns
                self.app.route_column_combo['values'] = route_options
                self.app.log_message(f"Updated route column combo with {len(route_options)} options: {route_options}")
                
                # Check if current route column selection is still valid
                current_route_col = self.app.route_column.get()
                if current_route_col and current_route_col not in route_options:
                    # Current selection is no longer valid - reset to "None"
                    self.app.route_column.set("None - treat as single route")
                    self.app.log_message(f"Reset route column selection: '{current_route_col}' not found in new file")
                elif not current_route_col or "None" not in current_route_col:
                    # Reset to "None" if currently showing placeholder or empty
                    self.app.route_column.set("None - treat as single route")
            else:
                self.app.log_message("Warning: route_column_combo widget not found!")
            
            # INTENTIONALLY LEAVE COLUMNS EMPTY - Force explicit user selection
            # This prevents auto-selection mistakes when switching between files
            # User must consciously choose the correct X and Y columns
            self.app.log_message("Column selections cleared - please select X and Y columns manually")
                    
            # After loading columns, if a route column was previously selected, detect routes
            if (hasattr(self.app, 'route_column') and 
                self.app.route_column.get() and 
                self.app.route_column.get() != "None - treat as single route"):
                self.app.log_message("Re-detecting routes after column reload...")
                self.detect_available_routes()
                    
        except Exception as e:
            self.app.log_message(f"Error loading CSV columns: {str(e)}")
    
    def load_data_file(self):
        """Load and process the selected data file."""
        data_path = self.get_data_file_path()
        if not data_path:
            show_error_message("No File Selected", "Please select a data file first.", self.app.log_message)
            return
        
        x_col = self.app.x_column.get()
        y_col = self.app.y_column.get()
        
        if not x_col or not y_col:
            show_error_message("Column Selection Required", "Please select both X and Y columns.", self.app.log_message)
            return
        
        try:
            # Load the data.
            # IMPORTANT: Read as strings first to preserve leading zeros (IDs/categorical fields).
            # We then convert numeric columns (at minimum X/Y) after validation.
            data = pd.read_csv(data_path, dtype=str)
            
            # Validate columns exist
            if x_col not in data.columns:
                show_error_message("Column Error", f"Column '{x_col}' not found in the data file.", self.app.log_message)
                return
            if y_col not in data.columns:
                show_error_message("Column Error", f"Column '{y_col}' not found in the data file.", self.app.log_message)
                return
            
            # UNIFIED ROUTE ARCHITECTURE: Always include a route column
            # Either use user-selected route column or create one from filename
            route_col = getattr(self.app, 'route_column', None)
            route_col_name = route_col.get() if route_col else None
            
            if (route_col_name and 
                route_col_name != "None - treat as single route" and
                route_col_name in data.columns):
                # User selected a route column - use it
                actual_route_column = route_col_name
                self.app.log_message(f"Using user-selected route column: '{route_col_name}'")
            else:
                # Create route column from filename - unified processing
                actual_route_column = 'route'
                filename = os.path.splitext(os.path.basename(data_path))[0]
                data[actual_route_column] = filename
                self.app.log_message(f"Created route column from filename: '{filename}'")

            # Treat the route column as categorical (string) regardless of CSV type inference.
            # This keeps route matching consistent across UI selection, optimization, export, etc.
            try:
                data[actual_route_column] = data[actual_route_column].astype("string").str.strip()
            except Exception as e:
                self.app.log_message(f"Warning: Could not normalize route column '{actual_route_column}' to string: {e}")

            # Convert X/Y to numeric for downstream calculations.
            # Also attempt to convert other columns to numeric when it is lossless,
            # but NEVER convert the active route column.
            def _has_leading_zero_integers(series: pd.Series) -> bool:
                try:
                    s = series.astype("string")
                    s = s.dropna().str.strip()
                    if s.empty:
                        return False
                    # Leading-zero integers like "00123" should remain strings.
                    return bool(s.str.match(r"^0\d+$").any())
                except Exception:
                    return False

            def _safe_to_numeric(series: pd.Series) -> pd.Series:
                numeric = pd.to_numeric(series, errors="coerce")
                invalid_mask = series.notna() & numeric.isna()
                if invalid_mask.any():
                    return series
                return numeric

            for col in list(data.columns):
                if col == actual_route_column:
                    continue
                if col == x_col or col == y_col:
                    data[col] = pd.to_numeric(data[col], errors="coerce")
                    continue
                if _has_leading_zero_integers(data[col]):
                    continue
                data[col] = _safe_to_numeric(data[col])
            
            # Keep the full dataset in memory.
            # Rationale: users may change the selected route column after loading the file.
            # If we trim to only [X, Y, route] here, later selecting a real route column
            # (e.g., 'RDB') can cause KeyErrors during route processing / saving.
            required_columns = [x_col, y_col, actual_route_column]
            
            # Validate that X and Y columns contain numeric data
            try:
                # Check X column for numeric values
                non_numeric_x = data[x_col].isna() | (~pd.to_numeric(data[x_col], errors='coerce').notna())
                if non_numeric_x.any():
                    sample_invalid = data.loc[non_numeric_x, x_col].iloc[0]
                    messagebox.showerror("Invalid X Column", 
                                       f"X column '{x_col}' contains non-numeric values.\n"
                                       f"Example invalid value: '{sample_invalid}'\n"
                                       f"Please select a column with numeric distance/position data.")
                    return
                
                # Check Y column for numeric values  
                non_numeric_y = data[y_col].isna() | (~pd.to_numeric(data[y_col], errors='coerce').notna())
                if non_numeric_y.any():
                    sample_invalid = data.loc[non_numeric_y, y_col].iloc[0]
                    messagebox.showerror("Invalid Y Column", 
                                       f"Y column '{y_col}' contains non-numeric values.\n"
                                       f"Example invalid value: '{sample_invalid}'\n"
                                       f"Please select a column with numeric measurement data.")
                    return
                    
            except Exception as e:
                show_error_message("Data Validation Error", f"Error validating numeric columns: {str(e)}", self.app.log_message)
                return
            
            # Clean the data - remove rows with missing values in required columns only.
            # (If we keep all columns, a full dropna() could remove many valid rows due
            #  to unrelated columns containing NaNs.)
            initial_count = len(data)
            data = data.dropna(subset=required_columns)
            final_count = len(data)
            
            if final_count < initial_count:
                self.app.log_message(f"Removed {initial_count - final_count} rows with missing values")
            
            # Sort by X column (position/distance)
            data = data.sort_values(x_col).reset_index(drop=True)
            
            # Validate we have enough data
            if len(data) < 3:
                show_error_message("Insufficient Data", "Need at least 3 data points for segmentation.", self.app.log_message)
                return
            
            # Perform gap analysis on the cleaned data (combined analysis for route detection)
            from data_loader import RouteAnalysis, analyze_route_gaps
            effective_gap_threshold = float(self.app.gap_threshold.get())
            if effective_gap_threshold <= 0:
                raise ValueError(f"gap_threshold must be > 0 (got {effective_gap_threshold})")

            route_analysis = analyze_route_gaps(
                data,
                x_col,
                y_col,
                route_id="_COMBINED_DATA_",
                gap_threshold=effective_gap_threshold,
            )
            self.app.log_message(f"Gap analysis: {len(route_analysis.gap_segments)} gaps detected, {len(route_analysis.mandatory_breakpoints)} mandatory breakpoints")
            
            # Store the RouteAnalysis object (contains both data and gap info)
            self.app.data = route_analysis

            # Reset optimization controller state to prevent stale thread/progress state,
            # but preserve route selection (it is owned by the GUI/user).
            if hasattr(self.app, 'optimization_controller'):
                self.app.optimization_controller.reset_state()

            # Re-detect routes after load so available_routes stays in sync with the file.
            # This also preserves any existing user selection by intersecting it with
            # the newly detected distinct routes.
            try:
                if (hasattr(self.app, 'route_column') and
                    self.app.route_column.get() and
                    self.app.route_column.get() != "None - treat as single route"):
                    self.detect_available_routes()
            except Exception as e:
                self.app.log_message(f"Warning: Could not re-detect routes after load: {e}")
                
            filepath = self.get_data_file_path()
            self.app.log_message(f"Data loaded: {len(route_analysis.route_data)} points from {os.path.basename(filepath)} (X: {x_col}, Y: {y_col})")
            self.app.log_message(f"Data columns available: {list(route_analysis.route_data.columns)}")
            
            # Enable optimization controls
            if hasattr(self.app, 'start_button'):
                self.app.start_button.config(state="normal")
            
        except Exception as e:
            self.app.log_message(f"Error loading data: {str(e)}")    
            show_error_message("Data Loading Error", f"Error loading data: {str(e)}", self.app.log_message)
    
    def detect_available_routes(self):
        """Detect and populate available routes based on selected route column."""
        data_path = self.get_data_file_path()
        route_col = self.app.route_column.get()
        
        if not data_path or not route_col or route_col == "None - treat as single route":
            self.app.available_routes = []
            self.app.selected_routes = []
            return
            
        try:
            # First, read the CSV headers to verify the column exists
            df_headers = pd.read_csv(data_path, nrows=0)
            if route_col not in df_headers.columns:
                available_columns = list(df_headers.columns)
                self.app.log_message(f"ERROR: Column '{route_col}' not found in CSV file")
                self.app.log_message(f"Available columns: {available_columns}")
                
                # Auto-reset to "None" to prevent repeated errors
                self.app.route_column.set("None - treat as single route")
                
                show_error_message(
                    "Column Not Found", 
                    f"Route column '{route_col}' not found in the selected data file.\n\n" +
                    f"This may happen when switching between different CSV files.\n\n" +
                    f"Available columns:\n" + "\n".join(f"• {col}" for col in available_columns) +
                    f"\n\nThe route column has been reset to 'None'. " +
                    f"Please select a valid route column if you need multi-route processing.",
                    self.app.log_message
                )
                self.app.available_routes = []
                self.app.selected_routes = []
                return
            
            # Load just the route column to get distinct values
            df = pd.read_csv(data_path, usecols=[route_col], dtype={route_col: str})
            
            # Get distinct routes, handle missing values
            distinct_routes = df[route_col].fillna('Default').astype("string").str.strip().unique()
            distinct_routes = sorted([str(route) for route in distinct_routes if str(route).strip()])
            
            self.app.available_routes = distinct_routes
            
            # Default: select all routes
            if not self.app.selected_routes:
                self.app.selected_routes = distinct_routes.copy()
            else:
                # Remove any previously selected routes that no longer exist
                self.app.selected_routes = [r for r in self.app.selected_routes if r in distinct_routes]
                # If no valid routes remain, select all
                if not self.app.selected_routes:
                    self.app.selected_routes = distinct_routes.copy()
            
            self.app._update_route_info_display()
            self.app.log_message(f"Found {len(distinct_routes)} routes in column '{route_col}': {distinct_routes}")
            
        except FileNotFoundError:
            self.app.log_message(f"ERROR: Data file not found: {data_path}")
            show_error_message("File Not Found", f"The selected data file could not be found:\n{data_path}", self.app.log_message)
            self.app.available_routes = []
            self.app.selected_routes = []
        except pd.errors.EmptyDataError:
            self.app.log_message(f"ERROR: Data file is empty: {data_path}")
            show_error_message("Empty File", "The selected data file is empty or contains no data.", self.app.log_message)
            self.app.available_routes = []
            self.app.selected_routes = []
        except Exception as e:
            self.app.log_message(f"ERROR: Unexpected error detecting routes: {str(e)}")
            show_error_message("Route Detection Error", f"An unexpected error occurred while reading routes:\n\n{str(e)}", self.app.log_message)
            self.app.available_routes = []
            self.app.selected_routes = []

    def ensure_route_column_is_string(self, route_col: str):
        """Ensure the in-memory dataset treats the given route column as string.

        This supports workflows where a user loads a file, then changes the selected
        route column. Route identifiers are treated as categorical keys, not numeric.
        """
        if not route_col or route_col == "None - treat as single route":
            return
        if not hasattr(self.app, "data") or self.app.data is None:
            return
        if not hasattr(self.app.data, "route_data") or self.app.data.route_data is None:
            return
        df = self.app.data.route_data
        if route_col not in df.columns:
            return
        try:
            df[route_col] = df[route_col].astype("string").str.strip()
        except Exception as e:
            self.app.log_message(
                f"Warning: Could not normalize route column '{route_col}' to string in-memory: {e}"
            )
    
    def load_and_plot_results(self):
        """Load and plot results from a JSON file."""
        try:
            # Determine initial directory - default to Results/ folder with fallback to last directory
            initial_dir = "Results"
            if hasattr(self.app, '_last_file_directory') and self.app._last_file_directory:
                initial_dir = self.app._last_file_directory
            elif not os.path.exists("Results"):
                initial_dir = "."

            filename = filedialog.askopenfilename(
                title="Select JSON Results File",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialdir=initial_dir
            )
            
            if not filename:
                return
                
            # Store selected directory for future use  
            self.app._last_file_directory = os.path.dirname(filename)

            # Load and validate JSON data
            with open(filename, 'r') as f:
                json_data = json.load(f)

            if not json_data:
                messagebox.showwarning("Empty File", "The selected file contains no data.")
                return

            self.app.log_message(f"Loading JSON results from: {os.path.basename(filename)}")

            # Validate JSON against schema
            validation_result = self._validate_json_schema(json_data)
            if validation_result['valid']:
                self.app.log_message("✅ JSON schema validation passed")
            else:
                self.app.log_message("⚠️ JSON schema validation warnings:")
                for warning in validation_result['warnings']:
                    self.app.log_message(f"  - {warning}")

            # Apply run parameters from the results JSON back into the GUI so the
            # Method Parameters table reflects the loaded run.
            try:
                self._apply_results_json_to_ui(json_data)
            except Exception as e:
                # Fatal: if we cannot determine/validate the method, this results file is incompatible.
                error_msg = (
                    "Results file is missing a valid optimization method key or references an unknown method. "
                    "This results file may be incompatible with this version of the tool.\n\n"
                    f"Details: {e}"
                )
                messagebox.showerror("Incompatible Results File", error_msg)
                if hasattr(self.app, 'log_message'):
                    self.app.log_message(f"❌ {error_msg}")
                return

            # Launch enhanced visualization with JSON data
            try:
                from enhanced_visualization import show_enhanced_visualization
                
                # Launch visualization - it will handle column extraction internally
                show_enhanced_visualization(
                    parent_app=self.app,
                    json_results_data=json_data
                )
                
                # Get method type for logging
                method_key = json_data.get('analysis_metadata', {}).get('analysis_method', 'unknown')
                self.app.log_message(f"✅ Enhanced visualization opened for {method_key} results")
                
            except Exception as e:
                error_msg = f"Failed to open visualization: {str(e)}"
                messagebox.showerror("Visualization Error", error_msg)
                self.app.log_message(f"❌ {error_msg}")
        
        except FileNotFoundError:
            messagebox.showerror("File Error", "The selected JSON file could not be found.")
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Error", f"Invalid JSON file format: {str(e)}")
        except Exception as e:
            error_msg = f"Error loading results: {str(e)}"
            messagebox.showerror("Load Error", error_msg)
            if hasattr(self.app, 'log_message'):
                self.app.log_message(error_msg)

    def _apply_results_json_to_ui(self, json_data: dict) -> None:
        """Best-effort restoration of method + parameters from a results JSON.

        This is intentionally UI-focused: it updates the method dropdown/description,
        restores the method-scoped parameter store, and applies a few framework-level
        globals (gap threshold, x/y/route selections) when present.
        """

        meta = json_data.get('analysis_metadata', {}) or {}
        input_params = json_data.get('input_parameters', {}) or {}

        method_cfg = input_params.get('optimization_method_config', {}) or {}
        method_key = meta.get('analysis_method') or method_cfg.get('method_key')
        display_name = method_cfg.get('display_name')

        # Method key is required for correct interpretation of the results.
        if not method_key:
            raise ValueError("Missing analysis_metadata.analysis_method in results JSON")

        # Validate method key against registry.
        from config import get_optimization_method
        get_optimization_method(str(method_key))
        method_key = str(method_key)

        # Restore method selection
        if display_name and hasattr(self.app, 'method_dropdown') and hasattr(self.app.method_dropdown, 'set'):
            try:
                self.app.method_dropdown.set(display_name)
            except Exception:
                pass

        # If display name not present, attempt to set from registry.
        if (not display_name) and hasattr(self.app, 'method_dropdown') and hasattr(self.app.method_dropdown, 'set'):
            try:
                method_config = get_optimization_method(method_key)
                self.app.method_dropdown.set(method_config.display_name)
            except Exception:
                pass

        if method_key:
            try:
                self.app.optimization_method = method_key
                setattr(self.app, '_active_method_key', method_key)
            except Exception:
                pass

            # Ensure settings structure exists
            try:
                if not hasattr(self.app, 'settings') or not isinstance(self.app.settings, dict):
                    self.app.settings = {}
                opt = self.app.settings.setdefault('optimization', {})
                opt['optimization_method'] = method_key
                opt.setdefault('dynamic_parameters_by_method', {})
            except Exception:
                pass

        # Restore framework/global UI state
        route_processing = input_params.get('route_processing', {}) or {}
        col_info = (meta.get('input_file_info', {}) or {}).get('column_info', {}) or {}

        x_col = route_processing.get('x_column') or col_info.get('x_column')
        y_col = route_processing.get('y_column') or col_info.get('y_column')
        route_col = route_processing.get('route_column') or col_info.get('route_column')

        if x_col and hasattr(self.app, 'x_column') and hasattr(self.app.x_column, 'set'):
            self.app.x_column.set(x_col)
        if y_col and hasattr(self.app, 'y_column') and hasattr(self.app.y_column, 'set'):
            self.app.y_column.set(y_col)
        if route_col and hasattr(self.app, 'route_column') and hasattr(self.app.route_column, 'set'):
            self.app.route_column.set(route_col)

        if 'selected_routes' in route_processing:
            try:
                self.app.selected_routes = list(route_processing.get('selected_routes') or [])
            except Exception:
                pass

        if 'custom_save_name' in route_processing and hasattr(self.app, 'custom_save_name') and hasattr(self.app.custom_save_name, 'set'):
            try:
                self.app.custom_save_name.set(route_processing.get('custom_save_name') or '')
            except Exception:
                pass

        method_params = input_params.get('method_parameters', {}) or {}
        if hasattr(self.app, 'gap_threshold') and hasattr(self.app.gap_threshold, 'set'):
            if 'gap_threshold' in method_params:
                try:
                    self.app.gap_threshold.set(method_params.get('gap_threshold'))
                except Exception:
                    pass

        # Restore method-scoped parameters into the settings-backed store
        if method_key and isinstance(method_params, dict) and method_params:
            try:
                if hasattr(self.app, 'parameter_manager'):
                    self.app.parameter_manager.load_method_dynamic_parameters(method_params)
                else:
                    opt = self.app.settings.setdefault('optimization', {})
                    store = opt.setdefault('dynamic_parameters_by_method', {})
                    store[method_key] = dict(method_params)
            except Exception:
                # Fall back to raw store write
                try:
                    opt = self.app.settings.setdefault('optimization', {})
                    store = opt.setdefault('dynamic_parameters_by_method', {})
                    store[method_key] = dict(method_params)
                except Exception:
                    pass

        # Refresh method description/grid (best-effort)
        try:
            if hasattr(self.app, 'ui_builder'):
                if method_key and hasattr(self.app.ui_builder, 'set_method_description'):
                    self.app.ui_builder.set_method_description(method_key)
                if method_key and hasattr(self.app.ui_builder, 'refresh_dynamic_params_grid'):
                    self.app.ui_builder.refresh_dynamic_params_grid(method_key)
        except Exception:
            pass
    
    def _validate_json_schema(self, json_data):
        """Validate JSON against schema with graceful error handling."""
        try:
            from pathlib import Path
            schema_path = Path(__file__).parent / "highway_segmentation_results_schema.json"
            
            if not schema_path.exists():
                return {'valid': False, 'warnings': ['Schema file not found in src/ directory']}
            
            # Import jsonschema if available
            try:
                import jsonschema
                from jsonschema import validate, ValidationError
            except ImportError:
                return {'valid': True, 'warnings': ['jsonschema package not installed - validation skipped']}
            
            # Load schema
            with open(schema_path, 'r') as f:
                schema = json.load(f)
            
            # Validate
            jsonschema.validate(json_data, schema)
            return {'valid': True, 'warnings': []}
            
        except jsonschema.ValidationError as e:
            return {'valid': False, 'warnings': [f'Schema validation failed: {e.message}']}
        except Exception as e:
            return {'valid': False, 'warnings': [f'Validation error: {str(e)}']}
    
    def display_json_summary(self, json_path: str) -> None:
        """Render a human-readable summary from a schema-compliant results JSON.

        This populates the "Results Files" tab with standard analysis metadata plus
        any available method-specific/custom summary sections.

        Args:
            json_path: Path to results JSON file
        """
        if not json_path:
            return

        if not hasattr(self.app, 'results_file_text'):
            return

        try:
            if not os.path.exists(json_path):
                raise FileNotFoundError(json_path)

            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            summary_text = self._format_results_json_summary(json_data, json_path)

            self.app.results_file_text.config(state=tk.NORMAL)
            self.app.results_file_text.delete(1.0, tk.END)
            self.app.results_file_text.insert(1.0, summary_text)
            self.app.results_file_text.config(state=tk.DISABLED)

            # Switch to Results Files tab
            if hasattr(self.app, 'results_notebook'):
                self.app.results_notebook.select(1)

        except Exception as e:
            # Keep this non-fatal; show what we can in the tab
            fallback = f"Could not load JSON summary from: {json_path}\n\nError: {e}\n"
            try:
                self.app.results_file_text.config(state=tk.NORMAL)
                self.app.results_file_text.delete(1.0, tk.END)
                self.app.results_file_text.insert(1.0, fallback)
                self.app.results_file_text.config(state=tk.DISABLED)
                if hasattr(self.app, 'results_notebook'):
                    self.app.results_notebook.select(1)
            except (tk.TclError, AttributeError):
                pass

            if hasattr(self.app, 'handle_error'):
                self.app.handle_error("Could not render JSON summary", e, severity="warning", show_messagebox=False)
            elif hasattr(self.app, 'log_message'):
                self.app.log_message(f"Warning: Could not render JSON summary: {e}")

    def _format_results_json_summary(self, json_data: dict, json_path: str) -> str:
        """Format a concise, readable summary from a results JSON dict."""

        def _fmt(v):
            if v is None:
                return "(none)"
            return str(v)

        def _fmt_num(v, digits=3):
            try:
                return f"{float(v):.{digits}f}"
            except (TypeError, ValueError):
                return _fmt(v)

        lines: list[str] = []
        lines.append("HIGHWAY SEGMENTATION RESULTS SUMMARY")
        lines.append("=" * 44)
        lines.append(f"Source JSON: {os.path.basename(json_path)}")
        lines.append("")

        meta = json_data.get('analysis_metadata', {}) or {}
        summary = meta.get('analysis_summary', {}) or {}
        input_info = meta.get('input_file_info', {}) or {}
        col_info = input_info.get('column_info', {}) or {}

        method_key = meta.get('analysis_method')
        status = meta.get('analysis_status')
        timestamp = meta.get('timestamp')
        sw = meta.get('software_version', {}) or {}

        lines.append("STANDARD SUMMARY")
        lines.append("-" * 15)
        lines.append(f"Timestamp: {_fmt(timestamp)}")
        lines.append(f"Status: {_fmt(status)}")
        lines.append(f"Method key: {_fmt(method_key)}")
        lines.append(f"Software: {_fmt(sw.get('application'))} {_fmt(sw.get('version'))}")
        lines.append("")

        lines.append("INPUT")
        lines.append("-" * 5)
        lines.append(f"Data file: {_fmt(input_info.get('data_file_name'))}")
        lines.append(f"Rows: {_fmt(input_info.get('total_data_rows'))}")
        lines.append(f"Routes available: {_fmt(input_info.get('total_routes_available'))}")
        lines.append(f"Columns: x={_fmt(col_info.get('x_column'))}, y={_fmt(col_info.get('y_column'))}, route={_fmt(col_info.get('route_column'))}")
        lines.append("")

        lines.append("ANALYSIS")
        lines.append("-" * 8)
        lines.append(f"Total processing time (s): {_fmt_num(summary.get('total_processing_time'), digits=3)}")
        lines.append(f"Routes processed: {_fmt(summary.get('total_routes_processed'))}")
        lines.append(f"Total length processed: {_fmt_num(summary.get('total_length_processed'), digits=3)}")
        if 'total_segments_generated' in summary:
            lines.append(f"Total segments generated: {_fmt(summary.get('total_segments_generated'))}")
        if 'total_breakpoints_generated' in summary:
            lines.append(f"Total breakpoints generated: {_fmt(summary.get('total_breakpoints_generated'))}")
        if 'total_gaps_identified' in summary:
            lines.append(f"Total gaps identified: {_fmt(summary.get('total_gaps_identified'))}")
        lines.append("")

        # Method identification/config if present
        input_params = json_data.get('input_parameters', {}) or {}
        method_cfg = input_params.get('optimization_method_config', {}) or {}
        if method_cfg:
            lines.append("METHOD CONFIG")
            lines.append("-" * 13)
            lines.append(f"Display name: {_fmt(method_cfg.get('display_name'))}")
            if method_cfg.get('description'):
                lines.append(f"Description: {_fmt(method_cfg.get('description'))}")
            lines.append("")

        # Method-specific analysis-level stats
        method_stats = json_data.get('method_specific_analysis_stats')
        if isinstance(method_stats, dict) and method_stats:
            lines.append("METHOD-SPECIFIC SUMMARY")
            lines.append("-" * 23)
            for k in sorted(method_stats.keys()):
                v = method_stats.get(k)
                if isinstance(v, (dict, list)):
                    lines.append(f"{k}: {json.dumps(v, indent=2, ensure_ascii=False)}")
                else:
                    lines.append(f"{k}: {_fmt(v)}")
            lines.append("")

        # Per-route highlights
        routes = json_data.get('route_results', []) or []
        if isinstance(routes, list) and routes:
            lines.append("ROUTE HIGHLIGHTS")
            lines.append("-" * 16)
            for rr in routes:
                route_id = (rr.get('route_info', {}) or {}).get('route_id', 'unknown')

                gap_total = ((rr.get('input_data_analysis', {}) or {}).get('gap_analysis', {}) or {}).get('total_gaps', None)
                mandatory = ((rr.get('input_data_analysis', {}) or {}).get('mandatory_segments', {}) or {}).get('mandatory_breakpoints', None)
                mandatory_count = len(mandatory) if isinstance(mandatory, list) else None

                pareto_points = ((rr.get('processing_results', {}) or {}).get('pareto_points', []) or [])
                pareto_count = len(pareto_points) if isinstance(pareto_points, list) else 0

                # Best/selected point: use point_id 0 if present else first
                best_point = None
                if pareto_points:
                    best_point = pareto_points[0]
                seg = (best_point or {}).get('segmentation', {}) or {}
                seg_count = seg.get('segment_count', None)
                avg_len = seg.get('average_segment_length', None)

                lines.append(f"Route: {route_id}")
                if gap_total is not None:
                    lines.append(f"  Gaps: {gap_total}")
                if mandatory_count is not None:
                    lines.append(f"  Mandatory breakpoints: {mandatory_count}")
                if pareto_count:
                    lines.append(f"  Pareto points: {pareto_count}")
                if seg_count is not None:
                    lines.append(f"  Segment count (best): {_fmt(seg_count)}")
                if avg_len is not None:
                    lines.append(f"  Avg segment length (best): {_fmt_num(avg_len, digits=3)}")

                # Route-level method custom stats if present
                for key in ("method_specific_route_stats", "method_specific_stats", "custom_statistics"):
                    custom = rr.get(key)
                    if isinstance(custom, dict) and custom:
                        lines.append(f"  {key}:")
                        for ck in sorted(custom.keys()):
                            cv = custom.get(ck)
                            if isinstance(cv, (dict, list)):
                                lines.append(f"    {ck}: {json.dumps(cv, ensure_ascii=False)}")
                            else:
                                lines.append(f"    {ck}: {_fmt(cv)}")

                lines.append("")

        return "\n".join(lines).rstrip() + "\n"
    
    def save_parameters(self):
        """Save current parameter settings to a JSON file."""
        try:
            # Determine initial directory - default to Results/ folder with fallback to last directory
            initial_dir = "Results"
            if hasattr(self.app, '_last_file_directory') and self.app._last_file_directory:
                initial_dir = self.app._last_file_directory
            elif not os.path.exists("Results"):
                initial_dir = "."
                
            filename = filedialog.asksaveasfilename(
                title="Save Parameters",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialdir=initial_dir
            )
            
            if filename:
                # Store selected directory for future use
                self.app._last_file_directory = os.path.dirname(filename)
                
                # Persist minimal framework UI state + per-method dynamic parameters.
                # Avoid writing GA/constrained knobs as global parameters.
                try:
                    from config import get_method_key_from_display_name

                    method_key = None
                    try:
                        if hasattr(self.app, 'method_dropdown'):
                            method_key = get_method_key_from_display_name(self.app.method_dropdown.get())
                    except Exception:
                        method_key = getattr(self.app, 'optimization_method', None)

                    # Persist active method's latest params into the store
                    try:
                        if hasattr(self.app, '_persist_dynamic_parameters_for_method') and method_key:
                            self.app._persist_dynamic_parameters_for_method(method_key)
                    except Exception:
                        pass

                    dynamic_store = {}
                    try:
                        opt = getattr(self.app, 'settings', {}).get('optimization', {})
                        if isinstance(opt, dict):
                            dynamic_store = opt.get('dynamic_parameters_by_method', {}) or {}
                    except Exception:
                        dynamic_store = {}

                    config = {
                        'files': {
                            'data_file_path': self.get_data_file_path(),
                            'save_file_path': self.get_save_file_path(),
                        },
                        'ui_state': {
                            'x_column': self.app.x_column.get() if hasattr(self.app, 'x_column') else '',
                            'y_column': self.app.y_column.get() if hasattr(self.app, 'y_column') else '',
                            'gap_threshold': self.app.gap_threshold.get() if hasattr(self.app, 'gap_threshold') else 0.5,
                            'route_column': self.app.route_column.get() if hasattr(self.app, 'route_column') else '',
                            'selected_routes': getattr(self.app, 'selected_routes', None),
                            'window_geometry': self.app.root.geometry(),
                        },
                        'optimization': {
                            'optimization_method': method_key or getattr(self.app, 'optimization_method', 'multi'),
                            'custom_save_name': self.app.custom_save_name.get() if hasattr(self.app, 'custom_save_name') else 'highway_segmentation',
                            'dynamic_parameters_by_method': dynamic_store,
                        }
                    }
                except Exception as e:
                    messagebox.showerror("Save Error", f"Error collecting parameters: {str(e)}")
                    return
                
                # Save to JSON file
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                
                messagebox.showinfo("Parameters Saved", f"Parameters saved to {os.path.basename(filename)}")
                
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving parameters: {str(e)}")
    
    def load_parameters(self):
        """Load parameter settings from a JSON file."""
        try:
            filename = filedialog.askopenfilename(
                title="Load Parameters",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'r') as f:
                    config = json.load(f)

                # Require the structured parameters format.
                if isinstance(config, dict) and 'optimization' in config and isinstance(config.get('optimization'), dict):
                    opt = config.get('optimization', {})
                    files = config.get('files', {}) if isinstance(config.get('files'), dict) else {}
                    ui_state = config.get('ui_state', {}) if isinstance(config.get('ui_state'), dict) else {}

                    method_key = opt.get('optimization_method') or getattr(self.app, 'optimization_method', 'multi')
                    # Require method key to be valid; do not guess defaults.
                    try:
                        if hasattr(self.app, '_migrate_method_key'):
                            method_key = self.app._migrate_method_key(method_key)
                    except Exception as e:
                        messagebox.showerror(
                            "Incompatible Parameters File",
                            "This parameters file refers to an unknown optimization method.\n\n"
                            f"Details: {e}",
                        )
                        return

                    # Restore file paths
                    data_file_path = files.get('data_file_path')
                    if data_file_path:
                        self.set_data_file_path(data_file_path)
                        self.load_csv_columns()
                    save_file_path = files.get('save_file_path')
                    if save_file_path:
                        self.set_save_file_path(save_file_path)

                    # Restore UI globals
                    if 'x_column' in ui_state and hasattr(self.app, 'x_column'):
                        self.app.x_column.set(ui_state.get('x_column') or '')
                    if 'y_column' in ui_state and hasattr(self.app, 'y_column'):
                        self.app.y_column.set(ui_state.get('y_column') or '')
                    if 'gap_threshold' in ui_state and hasattr(self.app, 'gap_threshold'):
                        self.app.gap_threshold.set(ui_state.get('gap_threshold'))
                    if 'route_column' in ui_state and hasattr(self.app, 'route_column'):
                        self.app.route_column.set(ui_state.get('route_column') or '')
                    if 'selected_routes' in ui_state:
                        self.app.selected_routes = ui_state.get('selected_routes') or []
                    if 'window_geometry' in ui_state and ui_state.get('window_geometry'):
                        try:
                            self.app.root.geometry(ui_state.get('window_geometry'))
                        except tk.TclError:
                            pass

                    # Restore optimization method + dynamic store
                    self.app.optimization_method = method_key
                    if hasattr(self.app, 'custom_save_name') and 'custom_save_name' in opt:
                        self.app.custom_save_name.set(opt.get('custom_save_name') or '')

                    try:
                        if not hasattr(self.app, 'settings') or not isinstance(self.app.settings, dict):
                            self.app.settings = {}
                        app_opt = self.app.settings.setdefault('optimization', {})
                        app_opt['optimization_method'] = method_key
                        store = opt.get('dynamic_parameters_by_method', {})
                        if isinstance(store, dict):
                            app_opt['dynamic_parameters_by_method'] = store
                    except Exception:
                        pass

                    # Update UI based on method
                    try:
                        if hasattr(self.app, 'on_method_change'):
                            self.app.on_method_change()
                    except Exception:
                        pass

                else:
                    messagebox.showerror(
                        "Incompatible Parameters File",
                        "This parameters file is not in the supported structured format.\n\n"
                        "Please re-save parameters using this version of the application.",
                    )
                    return

                messagebox.showinfo("Parameters Loaded", f"Parameters loaded from {os.path.basename(filename)}")
                
        except Exception as e:
            messagebox.showerror("Load Error", f"Error loading parameters: {str(e)}")
    
