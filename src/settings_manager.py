"""
Settings Manager Module for Highway Segmentation GA

This module handles persistence of user settings and parameters between
application sessions, providing a seamless user experience.
"""

import json
import os
from typing import Dict, Any

from logger import create_logger


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
                'y_column': ''
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
            create_logger().log(f"Warning: Could not load settings ({e}). Using defaults.")
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
            create_logger().log(f"Warning: Could not save settings ({e})")
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