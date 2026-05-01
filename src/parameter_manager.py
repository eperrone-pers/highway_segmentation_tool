"""
Parameter Manager Module for Highway Segmentation GA

This module handles parameter validation, state management, and UI updates
related to optimization parameters, separating this logic from the main GUI class.
"""

import os
import tkinter as tk
from tkinter import messagebox
from config import AlgorithmConstants, ConstrainedOptimizationConfig, get_method_key_from_display_name, get_optimization_method

# Create config instances
optimization_config = AlgorithmConstants()
constrained_config = ConstrainedOptimizationConfig()


class ParameterManager:
    """
    Handles parameter validation, state management, and UI updates.
    
    This class manages all aspects of parameter handling including validation,
    default value management, method-specific parameter visibility, and
    constraint checking.
    """
    
    def __init__(self, main_app):
        """
        Initialize the parameter manager with a reference to the main application.
        
        Args:
            main_app: Reference to the main HighwaySegmentationGUI instance
        """
        self.app = main_app
    
    def validate_parameters(self):
        """
        Validate all optimization parameters and return validation results.
        
        Returns:
            tuple: (is_valid, error_messages) where is_valid is bool and error_messages is list
        """
        errors = []
        
        try:
            # Determine selected method key
            try:
                method_key = self._get_selected_method_key(strict=True)
            except (AttributeError, ValueError, tk.TclError):
                errors.append("Optimization method selection is missing or invalid")
                return False, errors

            method_config = get_optimization_method(method_key)

            # Use the same merged parameter source as the controller/methods (method-specific + globals)
            params = self.get_optimization_parameters()

            # Validate framework-level gap_threshold (single source of truth: app.gap_threshold)
            try:
                gap_threshold = float(self.app.gap_threshold.get())
            except (AttributeError, TypeError, ValueError, tk.TclError):
                gap_threshold = None

            if gap_threshold is None:
                errors.append("Gap threshold is missing or invalid")
            else:
                # Per our explicit gap-handling contract, this must be provided and > 0
                if gap_threshold <= 0:
                    errors.append(f"Gap threshold must be > 0 (got {gap_threshold})")
                elif gap_threshold > 5.0:
                    errors.append("Gap threshold should not exceed 5.0")

            # Validate method-specific parameters using declarative config definitions
            for param_def in method_config.parameters:
                if param_def.name not in params:
                    if getattr(param_def, 'required', True):
                        errors.append(f"Missing required parameter: {param_def.display_name}")
                    continue

                ok, msg = param_def.validate_value(params.get(param_def.name))
                if not ok and msg:
                    errors.append(msg)

                # Column selector parameters: if we know the loaded headers, ensure the selection exists.
                try:
                    from config import ColumnSelectParameter

                    if isinstance(param_def, ColumnSelectParameter):
                        selected = params.get(param_def.name)
                        selected = "" if selected is None else str(selected).strip()

                        available = getattr(self.app, 'available_columns', None)
                        if selected and isinstance(available, list) and available and selected not in available:
                            errors.append(
                                f"{param_def.display_name} must be a column from the loaded data file"
                            )
                except Exception:
                    # Non-fatal: fall back to method-level validation.
                    pass

            # Cross-field validation for segment length constraints when both exist
            if 'min_length' in params and 'max_length' in params:
                try:
                    min_length = float(params['min_length'])
                    max_length = float(params['max_length'])
                    if min_length >= max_length:
                        errors.append("Maximum segment length must be greater than minimum")
                except Exception:
                    # Type errors already handled by per-parameter validation
                    pass
            
            # Data validation
            if not hasattr(self.app, 'data') or self.app.data is None:
                errors.append("No data loaded. Please load a data file first.")
            elif len(self.app.data.route_data) < 3:
                errors.append("Need at least 3 data points for segmentation")
            
        except ValueError as e:
            errors.append(f"Invalid parameter value: {str(e)}")
        except Exception as e:
            errors.append(f"Parameter validation error: {str(e)}")
        
        return len(errors) == 0, errors
    
    def _validate_constrained_parameters(self, errors):
        """
        Validate constrained optimization specific parameters.
        
        Args:
            errors (list): List to append error messages to
        """
        try:
            params = self.get_optimization_parameters()

            target_length = params.get('target_avg_length')
            if target_length is not None and float(target_length) <= 0:
                errors.append("Target average length must be positive")

            tolerance = params.get('length_tolerance')
            if tolerance is not None:
                tolerance_val = float(tolerance)
                if not (0.01 <= tolerance_val <= 1.0):
                    errors.append("Length tolerance should be between 0.01 and 1.0")

            penalty_weight = params.get('penalty_weight')
            if penalty_weight is not None:
                penalty_val = float(penalty_weight)
                if penalty_val < 0:
                    errors.append("Penalty weight must be non-negative")
                elif penalty_val > 100000:
                    errors.append("Penalty weight should not exceed 100,000")
        except ValueError as e:
            errors.append(f"Invalid constrained parameter: {str(e)}")
    
    def reset_parameters(self):
        """Reset all parameters to their default values."""
        # Reset framework-level UI state
        if hasattr(self.app, 'custom_save_name'):
            self.app.custom_save_name.set("highway_segmentation")

        if hasattr(self.app, 'gap_threshold'):
            try:
                # Framework-level default (keep consistent with GUI initialization)
                self.app.gap_threshold.set(0.5)
            except Exception:
                pass

        # Clear per-method dynamic parameter overrides so defaults apply again
        try:
            if hasattr(self.app, 'settings') and isinstance(getattr(self.app, 'settings', None), dict):
                opt = self.app.settings.setdefault('optimization', {})
                opt['dynamic_parameters_by_method'] = {}
        except Exception:
            pass
        
        # Method settings - reset to default method
        from config import get_optimization_method_names
        method_names = get_optimization_method_names()
        if hasattr(self.app, 'method_dropdown') and method_names and hasattr(self.app.method_dropdown, 'set'):
            self.app.method_dropdown.set(method_names[1])  # Default to Multi-Objective (2nd in list)
        
        # Initialize method-dependent UI states
        self.app.root.after(100, self.app.on_method_change)  # Defer to ensure widgets are created
    
    def on_method_change(self, event=None):
        """Handle optimization method selection changes using new dropdown architecture."""
        try:
            # Commit any in-progress inline edit before switching.
            try:
                if hasattr(self.app, 'ui_builder') and hasattr(self.app.ui_builder, '_commit_dynamic_param_cell_edit'):
                    self.app.ui_builder._commit_dynamic_param_cell_edit()
            except Exception:
                pass

            # Update the optimization_method attribute based on dropdown selection
            selected_method_key = self._get_selected_method_key()
            if selected_method_key:
                self.app.optimization_method = selected_method_key

            # Update method description + refresh dynamic parameter grid
            if hasattr(self.app, 'ui_builder'):
                if hasattr(self.app.ui_builder, 'set_method_description'):
                    self.app.ui_builder.set_method_description(self.app.optimization_method)
                if hasattr(self.app.ui_builder, 'refresh_dynamic_params_grid'):
                    self.app.ui_builder.refresh_dynamic_params_grid(self.app.optimization_method)
        except Exception as e:
            print(f"Error updating method display: {e}")
    
    def _get_selected_method_key(self, strict: bool = False):
        """Get the currently selected method key from the dropdown.

        Args:
            strict: If True, raise when the dropdown is missing/invalid instead of
                returning a default method.
        """
        try:
            selected_display_name = self.app.method_dropdown.get()
            method_key = get_method_key_from_display_name(selected_display_name)
            if not method_key:
                raise ValueError(f"Unrecognized optimization method: {selected_display_name}")
            return method_key
        except (ValueError, AttributeError, tk.TclError):
            if strict:
                raise
            # Fallback to default if dropdown not ready
            from config import get_default_method_key
            return get_default_method_key()
    
    def on_column_change(self, event=None):
        """Handle column selection changes in data loading."""
        x_col = self.app.x_column.get()
        y_col = self.app.y_column.get()
        
        if x_col and y_col and hasattr(self.app, 'log_message'):
            # Don't log if this is initial setup
            if hasattr(self.app, 'data') and self.app.data is not None:
                self.app.log_message(f"Column selection changed: X='{x_col}', Y='{y_col}'")
                
                # CRITICAL FIX: Reload data when columns change to ensure data matches UI
                # This handles the case where user browses new file but data isn't refreshed
                self.app.log_message("Reloading data with new column selection...")
                try:
                    self.app.load_data_file()
                    self.app.log_message("Data reloaded successfully")
                except Exception as e:
                    self.app.log_message(f"Data reload failed: {e}")
    
    def on_save_option_change(self):
        """Handle save option changes - now simplified since save location is always required."""
        # Save name entry is always enabled now
        if hasattr(self.app, 'save_name_entry'):
            self.app.save_name_entry.config(state="normal")
    
    def get_optimization_parameters(self):
        """
        Get all current optimization parameters as a dictionary.
        Combines method-specific dynamic parameters with the small set of
        framework-level/global settings.

        Global (framework) parameters are intentionally minimal:
        - data file selection (managed by FileManager)
        - route column / route filter selection (UI state)
        - x/y column selection (UI state)
        - gap_threshold (framework parameter)

        All other optimization knobs (GA, constrained, AASHTO-specific, etc.)
        are method-scoped and come from the dynamic parameter system.
        
        Returns:
            dict: Dictionary containing all optimization parameters
        """
        # Determine selected method key from the dropdown (single source of truth).
        # Fall back to app.optimization_method only if the dropdown isn't ready.
        try:
            method_key = self._get_selected_method_key(strict=True)
        except (AttributeError, ValueError, tk.TclError):
            method_key = getattr(self.app, 'optimization_method', None)
            if not method_key:
                raise RuntimeError(
                    "Optimization method is not initialized (method dropdown unavailable and app.optimization_method is unset)"
                )
            if hasattr(self.app, 'log_message'):
                self.app.log_message(
                    "Warning: method dropdown unavailable; using app.optimization_method for parameter retrieval"
                )

        # Start from config defaults for this method so required parameters are always present.
        method_config = get_optimization_method(method_key)
        method_defaults = {}
        if method_config and getattr(method_config, 'parameters', None):
            method_defaults = {param.name: param.default_value for param in method_config.parameters}

        # Get dynamic overrides from UI (may be partial)
        try:
            dynamic_params = self.app.ui_builder.get_parameter_values()
            if dynamic_params is None:
                dynamic_params = {}
        except Exception as e:
            # Keep this non-fatal; callers (including validation) can still proceed using defaults.
            if hasattr(self.app, 'log_message'):
                self.app.log_message(f"Could not get dynamic parameters: {e}")
            dynamic_params = {}

        # Framework/global parameters (keep minimal)
        try:
            custom_save_name = self.app.custom_save_name.get()
        except Exception:
            custom_save_name = "highway_segmentation"

        values = {
            'optimization_method': method_key,
            'custom_save_name': custom_save_name,
        }

        # Merge order: defaults -> dynamic overrides
        values.update(method_defaults)
        values.update(dynamic_params)

        return values
    
    def load_method_dynamic_parameters(self, params):
        """
        Load method-specific dynamic parameters from saved settings.
        
        Args:
            params (dict): Dictionary containing all saved parameters
        """
        try:
            current_method = self.app.optimization_method if hasattr(self.app, 'optimization_method') else 'multi'
            method_config = get_optimization_method(current_method)
            allowed_names = {p.name for p in method_config.parameters}

            if not hasattr(self.app, 'settings') or not isinstance(getattr(self.app, 'settings', None), dict):
                return

            store = self.app.settings.setdefault('optimization', {}).setdefault('dynamic_parameters_by_method', {})
            if not isinstance(store, dict):
                return

            per_method = store.setdefault(current_method, {})
            if not isinstance(per_method, dict):
                per_method = {}
                store[current_method] = per_method

            from config import OptionalNumericParameter
            for param_def in method_config.parameters:
                name = param_def.name
                if name not in params:
                    continue

                value = params.get(name)
                if isinstance(param_def, OptionalNumericParameter):
                    if value is None:
                        value = None
                    elif isinstance(value, str) and value.strip().lower() in ("", "none", "(none)", "null"):
                        value = None

                per_method[name] = value

            # Drop any keys that are no longer valid for this method
            for k in list(per_method.keys()):
                if k not in allowed_names:
                    per_method.pop(k, None)

            # Refresh the Treeview grid if present
            if hasattr(self.app.ui_builder, 'refresh_dynamic_params_grid'):
                self.app.ui_builder.refresh_dynamic_params_grid(current_method)

        except Exception as e:
            if hasattr(self.app, 'handle_error'):
                self.app.handle_error("Could not load dynamic parameters", e, severity="warning", show_messagebox=False)
            else:
                self.app.log_message(f"Warning: Could not load dynamic parameters: {e}")
    
    def validate_and_show_errors(self):
        """
        Validate parameters and show error dialog if validation fails.
        
        Returns:
            bool: True if validation passed, False otherwise
        """
        is_valid, errors = self.validate_parameters()
        
        if not is_valid:
            error_message = "Parameter validation failed:\n\n" + "\n".join([f"• {error}" for error in errors])
            messagebox.showerror("Parameter Validation Error", error_message)
            return False
        
        return True
    
    def get_parameter_summary(self):
        """
        Get a formatted summary of current parameters.
        
        Returns:
            str: Formatted parameter summary
        """
        params = self.get_optimization_parameters()
        method = params.get('optimization_method', 'multi')

        summary = []
        summary.append("Current Parameter Settings:")
        summary.append("=" * 40)
        summary.append(f"Method: {str(method).title()}")
        summary.append("")
        summary.append("FRAMEWORK PARAMETERS:")
        try:
            summary.append(f"  Gap Threshold: {float(self.app.gap_threshold.get()):.3f} miles")
        except Exception:
            summary.append("  Gap Threshold: (invalid)")
        summary.append(f"  Custom Save Name: {params.get('custom_save_name', '')}")
        summary.append("")
        summary.append("METHOD-SPECIFIC PARAMETERS:")

        # Prefer the UIBuilder dynamic parameter source (single source of truth)
        try:
            dyn = self.app.ui_builder.get_parameter_values()
            for name, value in dyn.items():
                summary.append(f"  {name}: {value}")
        except Exception:
            for name, value in params.items():
                if name in ('optimization_method', 'custom_save_name'):
                    continue
                summary.append(f"  {name}: {value}")

        return "\n".join(summary)
    
    def get_current_parameters(self):
        """
        Get current parameters for settings persistence.
        Alias for get_optimization_parameters() for cleaner settings integration.
        
        Returns:
            dict: Dictionary containing all current optimization parameters
        """
        return self.get_optimization_parameters()
    
    def set_optimization_parameters(self, settings_dict):
        """
        Set optimization parameters from settings dictionary.
        
        Args:
            settings_dict (dict): Dictionary containing parameter settings
        """
        try:
            # Keep non-method settings minimal; do not set GA/constrained knobs globally.
            if 'custom_save_name' in settings_dict:
                self.app.custom_save_name.set(settings_dict['custom_save_name'])
            
            # Load method-specific dynamic parameters
            self.load_method_dynamic_parameters(settings_dict)
            
        except Exception as e:
            self.app.log_message(f"Warning: Could not apply some parameters: {e}")
    
    def apply_settings(self, settings_dict):
        """
        Apply settings loaded from file to UI parameters.
        Alias for set_optimization_parameters() for cleaner settings integration.
        
        Args:
            settings_dict (dict): Dictionary containing parameter settings
        """
        return self.set_optimization_parameters(settings_dict)