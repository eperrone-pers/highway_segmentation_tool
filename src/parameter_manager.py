"""
Parameter Manager Module for Highway Segmentation GA

This module handles parameter validation, state management, and UI updates
related to optimization parameters, separating this logic from the main GUI class.
"""

import os
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
            method_key = self._get_selected_method_key()
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
            target_length = self.app.target_avg_length.get()
            if target_length <= 0:
                errors.append("Target average length must be positive")
            
            tolerance = self.app.length_tolerance.get()
            if not (0.01 <= tolerance <= 1.0):
                errors.append("Length tolerance should be between 0.01 and 1.0")
            
            penalty_weight = self.app.penalty_weight.get()
            if penalty_weight < 0:
                errors.append("Penalty weight must be non-negative")
            elif penalty_weight > 100000:
                errors.append("Penalty weight should not exceed 100,000")
                
        except ValueError as e:
            errors.append(f"Invalid constrained parameter: {str(e)}")
    
    def reset_parameters(self):
        """Reset all parameters to their default values."""
        # GLOBAL PARAMETERS (shared across all optimization methods)
        # Dynamic parameters (min_length, max_length, gap_threshold) are now method-specific
        # and will be reset when method changes or by recreating the dynamic UI
        
        # Genetic algorithm parameters (shared across all methods)
        self.app.population_size.set(optimization_config.population_size_default)
        self.app.num_generations.set(optimization_config.multi_objective_generations)  # Use a reasonable default for all methods
        self.app.mutation_rate.set(optimization_config.mutation_rate_default)
        self.app.crossover_rate.set(optimization_config.crossover_rate_default)
        
        # Performance parameters (global)
        self.app.cache_clear_interval.set(optimization_config.cache_clear_interval)
        # enable_performance_stats is now handled by the dynamic parameter system.
        if hasattr(self.app, 'enable_performance_stats'):
            try:
                self.app.enable_performance_stats.set(True)
            except (AttributeError, TypeError, tk.TclError):
                pass
        # Segment caching always enabled for performance optimization
        
        # Save parameters (global)
        self.app.custom_save_name.set("highway_segmentation")
        
        # METHOD-SPECIFIC PARAMETERS
        # Single-objective only (used by single and constrained methods)
        self.app.elite_ratio.set(optimization_config.elite_ratio_default)
        
        # Constrained optimization only
        self.app.target_avg_length.set(constrained_config.target_avg_length_default)
        self.app.penalty_weight.set(constrained_config.penalty_weight_default)
        self.app.length_tolerance.set(constrained_config.length_tolerance_default)
        
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
            # Update the optimization_method attribute based on dropdown selection
            selected_method_key = self._get_selected_method_key()
            if selected_method_key:
                self.app.optimization_method = selected_method_key
                
            # Update parameter section visibility using UIBuilder's method
            if hasattr(self.app, 'ui_builder') and hasattr(self.app.ui_builder, '_update_dynamic_parameters'):
                self.app.ui_builder._update_dynamic_parameters()
        except Exception as e:
            print(f"Error updating method display: {e}")
    
    def _get_selected_method_key(self):
        """Get the currently selected method key from the dropdown."""
        try:
            selected_display_name = self.app.method_dropdown.get()
            return get_method_key_from_display_name(selected_display_name)
        except (ValueError, AttributeError):
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
        Combines dynamic method-specific parameters with global parameters.
        
        Returns:
            dict: Dictionary containing all optimization parameters
        """
        try:
            # Get dynamic parameters from UI
            dynamic_params = self.app.ui_builder.get_parameter_values()
        except Exception as e:
            self.app.log_message(f"Could not get dynamic parameters: {e}")
            dynamic_params = {}

        # Get global parameters
        values = {
            'population_size': self.app.population_size.get(),
            'num_generations': self.app.num_generations.get(),
            'mutation_rate': self.app.mutation_rate.get(),
            'crossover_rate': self.app.crossover_rate.get(),
            'elite_ratio': self.app.elite_ratio.get(),
            'optimization_method': self.app.optimization_method,
            'target_avg_length': self.app.target_avg_length.get(),
            'penalty_weight': self.app.penalty_weight.get(),
            'length_tolerance': self.app.length_tolerance.get(),
            'cache_clear_interval': self.app.cache_clear_interval.get(),
            'custom_save_name': self.app.custom_save_name.get(),
        }

        # Merge dynamic parameters
        values.update(dynamic_params)
        
        return values
    
    def load_method_dynamic_parameters(self, params):
        """
        Load method-specific dynamic parameters from saved settings.
        
        Args:
            params (dict): Dictionary containing all saved parameters
        """
        try:
            # Get current method to determine which parameters to load
            current_method = self.app.optimization_method if hasattr(self.app, 'optimization_method') else 'multi'
            
            # Check if dynamic parameter widgets are available
            if not hasattr(self.app, 'parameter_values'):
                self.app.log_message("Dynamic parameter widgets not yet initialized, skipping parameter loading")
                return
            
            # Get method configuration and its parameters
            method_config = get_optimization_method(current_method)
            loaded_count = 0
            
            # Load saved values for dynamic parameters
            for param_def in method_config.parameters:
                param_name = param_def.name
                if param_name in params:
                    try:
                        # Get the parameter widget info from app.parameter_values
                        widget_info = self.app.parameter_values.get(param_name)
                        if widget_info:
                            widget = widget_info['widget']
                            value = params[param_name]

                            # Normalize OptionalNumericParameter values coming from JSON/settings
                            # (saved settings can legitimately contain '', 'None', '(None)', etc.)
                            from config import OptionalNumericParameter
                            if isinstance(param_def, OptionalNumericParameter):
                                if value is None:
                                    normalized_value = None
                                elif isinstance(value, str) and value.strip().lower() in ("", "none", "(none)", "null"):
                                    normalized_value = None
                                else:
                                    normalized_value = value
                                value = normalized_value
                            
                            # Use the parameter definition's set_widget_value method
                            param_def.set_widget_value(widget, value)
                            loaded_count += 1
                            
                        else:
                            self.app.log_message(f"Widget for {param_name} not found in parameter_values")
                    except (ValueError, TypeError, AttributeError) as e:
                        self.app.log_message(f"Warning: Could not load parameter {param_name}: {e}")
                        
            # Parameters loaded successfully
            
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
        method = params['optimization_method']
        
        summary = []
        summary.append("Current Parameter Settings:")
        summary.append("=" * 40)
        summary.append(f"Method: {method.title()}")
        summary.append("")
        summary.append("GLOBAL PARAMETERS (shared across all methods):")
        summary.append(f"  Segment Length Range: {params['min_length']:.1f} - {params['max_length']:.1f} miles")
        summary.append(f"  Gap Threshold: {params['gap_threshold']:.1f} miles")
        summary.append(f"  Population Size: {params['population_size']}")
        summary.append(f"  Generations: {params['num_generations']}")
        summary.append(f"  Mutation Rate: {params['mutation_rate']:.3f}")
        summary.append(f"  Crossover Rate: {params['crossover_rate']:.2f}")
        summary.append(f"  Cache Clear Interval: {params['cache_clear_interval']} generations")
        summary.append(f"  Performance Stats: {'Enabled' if params['enable_performance_stats'] else 'Disabled'}")
        summary.append(f"  Segment Caching: Always Enabled (Performance Optimization)")
        
        # Method-specific parameters
        if method in ["single", "constrained"]:
            summary.append("")
            summary.append("SINGLE-OBJECTIVE PARAMETERS:")
            summary.append(f"  Elite Ratio: {params['elite_ratio']:.3f}")
        
        if method == "constrained":
            summary.append("")
            summary.append("CONSTRAINED OPTIMIZATION PARAMETERS:")
            summary.append(f"  Target Avg Length: {params['target_avg_length']:.2f} miles")
            summary.append(f"  Length Tolerance: ±{params['length_tolerance']:.2f}")
            summary.append(f"  Penalty Weight: {params['penalty_weight']:.0f}")
        
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
            # Set global parameters if they exist in settings
            if 'population_size' in settings_dict:
                self.app.population_size.set(settings_dict['population_size'])
            if 'num_generations' in settings_dict:
                self.app.num_generations.set(settings_dict['num_generations'])
            if 'mutation_rate' in settings_dict:
                self.app.mutation_rate.set(settings_dict['mutation_rate'])
            if 'crossover_rate' in settings_dict:
                self.app.crossover_rate.set(settings_dict['crossover_rate'])
            if 'elite_ratio' in settings_dict:
                self.app.elite_ratio.set(settings_dict['elite_ratio'])
            if 'target_avg_length' in settings_dict:
                self.app.target_avg_length.set(settings_dict['target_avg_length'])
            if 'penalty_weight' in settings_dict:
                self.app.penalty_weight.set(settings_dict['penalty_weight'])
            if 'length_tolerance' in settings_dict:
                self.app.length_tolerance.set(settings_dict['length_tolerance'])
            if 'cache_clear_interval' in settings_dict:
                self.app.cache_clear_interval.set(settings_dict['cache_clear_interval'])
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