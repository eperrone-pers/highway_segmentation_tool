"""
Settings Manager Module for Highway Segmentation GA

This module handles persistence of user settings and parameters between
application sessions, providing a seamless user experience.
"""

import json
import logging
import os
from tkinter import messagebox
from typing import Dict, Any

from config import get_optimization_method
from route_utils import normalize_route_column_selection

logger = logging.getLogger(__name__)


class SettingsManager:
    """
    Manages application settings persistence across sessions.
    
    Handles saving and loading of:
    - File paths (data file, save location)  
    - Optimization parameters (population size, generations, etc.)
    - Method selection and UI state
    - Column selections and advanced settings
    """
    
    def __init__(self):
        """Initialize settings manager with default settings file path."""
        self.settings_file = self._get_settings_file_path()
        self.default_settings = self._get_default_settings()
    
    def _get_settings_file_path(self) -> str:
        """Get the path to the settings file."""
        # Store settings in the same directory as the application
        app_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(app_dir, 'app_settings.json')
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings structure."""
        return {
            'files': {
                'data_file_path': '',
                'save_file_path': ''
            },
            'optimization': {
                # Store optimization method selection under a dedicated key to avoid
                # colliding with AASHTO CDA's parameter name 'method'.
                'optimization_method': 'multi',  # Values: single, multi, constrained, aashto_cda

                # Only true global optimization setting we keep.
                'custom_save_name': 'highway_segmentation',

                # Per-method dynamic parameter persistence. All GA/constrained/AASHTO
                # knobs live here (scoped by method) rather than being top-level globals.
                'dynamic_parameters_by_method': {}
            },
            'ui_state': {
                'selected_columns': [],
                'window_geometry': '',
                'last_data_directory': '',
                'last_save_directory': '',
                'x_column': '',
                'y_column': '',
                'route_column': '',
                'gap_threshold': 10000,
                # Multi-select list of input columns that force mandatory breakpoints
                # whenever their value changes (attribute-based must-break).
                'must_break_columns': [],
                'secondary_break_columns': []
            },
            'preprocessing': {
                # Preprocessing panel configurations: method selection + parameters
                # Each key stores {method: str, parameters: dict}
                'pregap_config': {'method': None, 'parameters': {}},
                'primary_config': {'method': None, 'parameters': {}},
                'secondary_config': {'method': None, 'parameters': {}}
            },
            'advanced': {
                'nsga2_settings': {
                    'diversity_metric': 'crowding_distance',
                    'selection_pressure': 2.0
                },
                'constraint_settings': {
                    'max_constraint_violations': 5,
                    'penalty_factor': 1.0
                }
            }
        }
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Load settings from file, returning defaults if file doesn't exist or is invalid.
        
        Returns:
            Dict containing all application settings
        """
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                
                # Merge with defaults to handle any missing keys
                settings = self._merge_with_defaults(loaded_settings)
                return settings
            else:
                # First run - use defaults
                return self.default_settings.copy()
                
        except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
            logger.warning("Could not load settings (%s). Using defaults.", e)
            return self.default_settings.copy()
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save settings to file.
        
        Args:
            settings: Dictionary containing all application settings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
                f.flush()  # Force buffer flush
                os.fsync(f.fileno())  # Force OS file system flush
            return True
            
        except (PermissionError, OSError) as e:
            logger.warning("Could not save settings (%s)", e)
            return False
    
    def _merge_with_defaults(self, loaded_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge loaded settings with defaults to handle missing keys.
        
        Args:
            loaded_settings: Settings loaded from file
            
        Returns:
            Complete settings dictionary with all required keys
        """
        def merge_dicts(default: Dict, loaded: Dict) -> Dict:
            """Recursively merge dictionaries."""
            result = default.copy()
            for key, value in loaded.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dicts(result[key], value)
                else:
                    result[key] = value
            return result
        
        return merge_dicts(self.default_settings, loaded_settings)
    
    def get_setting(self, settings: Dict[str, Any], path: str, default: Any = None) -> Any:
        """
        Get a setting value using dot notation path.
        
        Args:
            settings: Settings dictionary
            path: Dot-separated path (e.g., 'optimization.population_size')
            default: Default value if path not found
            
        Returns:
            Setting value or default
        """
        try:
            keys = path.split('.')
            value = settings
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_setting(self, settings: Dict[str, Any], path: str, value: Any) -> None:
        """
        Set a setting value using dot notation path.

        Args:
            settings: Settings dictionary to modify
            path: Dot-separated path (e.g., 'optimization.population_size')
            value: Value to set
        """
        keys = path.split('.')
        current = settings

        # Navigate to parent of target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

    # ===== APPLY SETTINGS TO APP =====

    def validate_method_key(self, method_key) -> str:
        """Validate a method key against the config registry.

        Raises:
            ValueError: If the key is not found in the registry.
        """
        if isinstance(method_key, str):
            try:
                get_optimization_method(method_key)
                return method_key
            except Exception:
                pass
        raise ValueError(f"Unknown optimization method key in settings: {method_key!r}")

    def apply_to_app(self, app) -> None:
        """Apply loaded settings to all UI elements of the app."""
        try:
            self._restore_file_paths(app)

            opt_settings = app.settings.get('optimization', {})
            method_key = self._resolve_method_key(app, opt_settings)
            app.optimization_method = method_key

            self._seed_dynamic_parameters(app, opt_settings, method_key)
            self._apply_method_selection(app, opt_settings, method_key)
            self._apply_method_parameters(app, opt_settings, method_key)
            self._restore_ui_state(app)

        except Exception as e:
            app.handle_error("Could not apply some loaded settings", e, "warning")

    def _restore_file_paths(self, app) -> None:
        """Apply stored file paths to the app (best-effort)."""
        data_path = app.settings.get('files', {}).get('data_file_path', '')
        if data_path and os.path.exists(data_path):
            app.file_manager.set_data_file_path(data_path)
            app.file_manager.load_csv_columns()

        save_path = app.settings.get('files', {}).get('save_file_path', '')
        if save_path:
            app.file_manager.set_save_file_path(save_path)

    def _resolve_method_key(self, app, opt_settings) -> str:
        """Resolve and validate the optimization method key from settings."""
        method_key = opt_settings.get('optimization_method', None)
        if method_key is None:
            method_key = opt_settings.get('method', None)

        try:
            method_key = self.validate_method_key(method_key)
        except Exception as e:
            try:
                app.log_message(
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
            method_key = getattr(app, 'optimization_method', None) or 'multi'

        return method_key

    def _seed_dynamic_parameters(self, app, opt_settings, method_key: str) -> None:
        """Seed per-method dynamic parameter store from legacy flat settings (best-effort)."""
        try:
            if isinstance(opt_settings, dict):
                store = opt_settings.setdefault('dynamic_parameters_by_method', {})
                if isinstance(store, dict) and method_key and method_key not in store:
                    legacy_candidate = {
                        k: v for k, v in opt_settings.items()
                        if k not in {'optimization_method', 'dynamic_parameters_by_method'}
                    }
                    store[method_key] = legacy_candidate
        except Exception as e:
            try:
                app.log_message(f"Warning: Could not seed per-method parameters for '{method_key}': {e}")
            except Exception:
                logger.warning("Could not seed per-method parameters for %r: %s", method_key, e)

    def _apply_method_selection(self, app, opt_settings, method_key: str) -> None:
        """Apply method selection to dropdown and refresh method-specific UI (best-effort)."""
        if app.method_dropdown is None:
            return
        try:
            method_config = get_optimization_method(method_key)
            app.method_dropdown.set(method_config.display_name)

            try:
                if hasattr(app, 'parameter_manager'):
                    app.parameter_manager.on_method_change()
                elif hasattr(app, 'ui_builder'):
                    app.ui_builder.set_method_description(method_key)
                    app.ui_builder.refresh_dynamic_params_grid(method_key)
            except Exception as e:
                app.log_message(f"Warning: Could not refresh dynamic parameters for '{method_key}': {e}")

        except (ValueError, KeyError) as e:
            app.log_message(f"Could not restore method '{method_key}': {e}. Using default.")
            opt_settings['optimization_method'] = 'multi'
            app.method_dropdown.set("Multi-Objective NSGA-II")
            app.optimization_method = 'multi'

            try:
                if hasattr(app, 'parameter_manager'):
                    app.parameter_manager.on_method_change()
                elif hasattr(app, 'ui_builder'):
                    app.ui_builder.set_method_description('multi')
                    app.ui_builder.refresh_dynamic_params_grid('multi')
            except Exception as e:
                app.log_message(f"Warning: Could not refresh dynamic parameters for fallback: {e}")

    def _apply_method_parameters(self, app, opt_settings, method_key: str) -> None:
        """Apply optimization parameters to the UI for the resolved method."""
        merged_settings = opt_settings.copy() if isinstance(opt_settings, dict) else {}
        per_method_store = merged_settings.get('dynamic_parameters_by_method', {}) if isinstance(merged_settings, dict) else {}
        per_method_params = per_method_store.get(method_key) if isinstance(per_method_store, dict) else None
        if isinstance(per_method_params, dict):
            merged_settings.update(per_method_params)

        app.parameter_manager.apply_settings(merged_settings)
        app._active_method_key = method_key

    def _restore_ui_state(self, app) -> None:
        """Restore UI state fields (columns, routes, preprocessing panels) from settings."""
        ui_state = app.settings.get('ui_state', {})
        if 'x_column' in ui_state and hasattr(app, 'x_column'):
            app.x_column.set(ui_state['x_column'])
        if 'y_column' in ui_state and hasattr(app, 'y_column'):
            app.y_column.set(ui_state['y_column'])
        if 'gap_threshold' in ui_state and hasattr(app, 'gap_threshold'):
            app.gap_threshold.set(ui_state['gap_threshold'])
        if 'route_column' in ui_state and hasattr(app, 'route_column'):
            route_col_value = ui_state['route_column']
            if route_col_value and isinstance(route_col_value, str):
                suspicious_patterns = ['Gap Threshold', 'X Column', 'Y Column', 'Route Column']
                if any(pattern in route_col_value for pattern in suspicious_patterns):
                    app.log_message(f"Rejecting corrupted route_column value from settings: '{route_col_value}'")
                    from route_utils import ROUTE_COLUMN_NONE_SENTINEL
                    app.route_column.set(ROUTE_COLUMN_NONE_SENTINEL)
                else:
                    app.route_column.set(route_col_value)
            else:
                app.route_column.set(route_col_value)

        try:
            raw = ui_state.get('must_break_columns', [])
            app.must_break_columns = [str(v).strip() for v in (raw or []) if str(v).strip()]
        except Exception:
            app.must_break_columns = []
        try:
            if hasattr(app, '_update_must_break_columns_display'):
                app._update_must_break_columns_display()
        except Exception:
            pass

        try:
            raw = ui_state.get('secondary_break_columns', [])
            app.secondary_break_columns = [str(v).strip() for v in (raw or []) if str(v).strip()]
        except Exception:
            app.secondary_break_columns = []
        try:
            if hasattr(app, '_update_secondary_break_columns_display'):
                app._update_secondary_break_columns_display()
        except Exception:
            pass

        preprocessing_settings = app.settings.get('preprocessing', {})

        if hasattr(app, 'pregap_preprocess_panel') and app.pregap_preprocess_panel:
            try:
                pregap_config = preprocessing_settings.get('pregap_config', {})
                method_key = pregap_config.get('method')
                if method_key:
                    app.pregap_preprocess_panel.set_method(method_key, pregap_config.get('parameters', {}), expand=True)
            except Exception as e:
                app.log_message(f"Warning: Could not restore pregap preprocessing config: {e}")

        if hasattr(app, 'primary_preprocess_panel') and app.primary_preprocess_panel:
            try:
                primary_config = preprocessing_settings.get('primary_config', {})
                method_key = primary_config.get('method')
                if method_key:
                    app.primary_preprocess_panel.set_method(method_key, primary_config.get('parameters', {}), expand=True)
            except Exception as e:
                app.log_message(f"Warning: Could not restore primary preprocessing config: {e}")

        if hasattr(app, 'secondary_preprocess_panel') and app.secondary_preprocess_panel:
            try:
                secondary_config = preprocessing_settings.get('secondary_config', {})
                method_key = secondary_config.get('method')
                if method_key:
                    app.secondary_preprocess_panel.set_method(method_key, secondary_config.get('parameters', {}), expand=True)
            except Exception as e:
                app.log_message(f"Warning: Could not restore secondary preprocessing config: {e}")

        if 'selected_routes' in ui_state:
            app.selected_routes = ui_state['selected_routes'].copy()

        if (
            hasattr(app, 'route_column')
            and normalize_route_column_selection(app.route_column.get()) is not None
            and app.file_manager.get_data_file_path()
        ):
            app.log_message("Detecting routes from restored settings...")
            app.on_route_column_change()