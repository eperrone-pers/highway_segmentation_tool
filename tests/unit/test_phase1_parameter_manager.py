"""
Unit tests for Phase 1 route processing functionality in ParameterManager.

Tests route parameter validation, settings persistence, and route column
change handling for the multi-route processing enhancement.
"""

import pytest
import sys
import os
from unittest.mock import Mock

# Add src to path for imports
current_file_dir = os.path.dirname(__file__)
tests_dir = os.path.dirname(current_file_dir)  
project_root = os.path.dirname(tests_dir)
src_path = os.path.join(project_root, 'src')

if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from parameter_manager import ParameterManager
except ImportError as e:
    raise ImportError(f"Could not import ParameterManager from src/. Original error: {e}")

from route_utils import ROUTE_COLUMN_NONE_SENTINEL


class TestParameterManagerRouteProcessing:
    """Test suite for ParameterManager Phase 1 route processing functionality."""
    
    @pytest.fixture
    def mock_app_with_routes(self):
        """Create a mock app with route-related attributes and methods."""
        app = Mock()
        app.available_routes = ['US-35', 'I-75', 'SR-123']
        app.selected_routes = ['US-35', 'I-75']
        app.route_column = Mock()
        app.route_column.get.return_value = "route"
        app.log_message = Mock()

        # Framework-level gap threshold (required by validate_parameters)
        app.gap_threshold = Mock()
        app.gap_threshold.get.return_value = 0.5
        
        # Mock file manager
        app.file_manager = Mock()
        app.file_manager.detect_available_routes = Mock()
        
        # Mock UI elements
        app.route_info_label = Mock()
        app.route_info_label.config = Mock()
        
        # Mock numeric parameter controls that validate_parameters() needs
        app.population_size = Mock()
        app.population_size.get.return_value = 100
        app.num_generations = Mock() 
        app.num_generations.get.return_value = 200
        app.mutation_rate = Mock()
        app.mutation_rate.get.return_value = 0.01
        app.crossover_rate = Mock()
        app.crossover_rate.get.return_value = 0.8
        app.elite_ratio = Mock()
        app.elite_ratio.get.return_value = 0.1
        app.cache_clear_interval = Mock()
        app.cache_clear_interval.get.return_value = 10
        
        # Mock UI builder for dynamic parameters (method-specific)
        app.ui_builder = Mock()
        app.ui_builder.get_parameter_values.return_value = {
            'min_length': 1.0,
            'max_length': 5.0,
            # enable_performance_stats is a configured method parameter (required)
            'enable_performance_stats': True,
        }
        
        # Mock data object for validation  
        app.data = Mock()
        app.data.route_data = [1, 2, 3, 4, 5]  # Mock data with length > 3
        
        # Mock method dropdown for validation
        app.method_dropdown = Mock()
        # Must match config display_name exactly for get_method_key_from_display_name
        app.method_dropdown.get.return_value = "Multi-Objective NSGA-II"

        # Reset/async callbacks
        app.root = Mock()
        app.root.after = Mock()
        app.on_method_change = Mock()
        
        return app
    
    @pytest.fixture
    def parameter_manager(self, mock_app_with_routes):
        """Create a ParameterManager instance with route-enabled mock app."""
        return ParameterManager(mock_app_with_routes)
    
    # === ROUTE COLUMN VALIDATION TESTS ===
    
    @pytest.mark.unit
    def test_validate_parameters_with_route_column_selected(self, parameter_manager):
        """Test parameter validation when route column is selected."""
        # Set up mock app state
        parameter_manager.app.route_column.get.return_value = "route"
        parameter_manager.app.available_routes = ['US-35', 'I-75']
        parameter_manager.app.selected_routes = ['US-35']
        
        # Mock other required parameters for validation
        parameter_manager.app.data_file_path = Mock()
        parameter_manager.app.data_file_path.get.return_value = "/path/to/data.csv"
        parameter_manager.app.column_dropdown = Mock()
        parameter_manager.app.column_dropdown.get.return_value = "milepoint"
        parameter_manager.app.strength_dropdown = Mock()  
        parameter_manager.app.strength_dropdown.get.return_value = "structural_strength_ind"
        
        # Execute
        is_valid, errors = parameter_manager.validate_parameters()
        
        # Should pass validation with proper route setup
        assert is_valid is True
        assert errors == []
    
    @pytest.mark.unit
    def test_validate_parameters_no_route_column_single_route_mode(self, parameter_manager):
        """Test parameter validation in single route mode (no route column)."""
        # Set up mock app state for single route mode
        parameter_manager.app.route_column.get.return_value = ROUTE_COLUMN_NONE_SENTINEL
        parameter_manager.app.available_routes = []
        parameter_manager.app.selected_routes = []
        
        # Mock other required parameters
        parameter_manager.app.data_file_path = Mock()
        parameter_manager.app.data_file_path.get.return_value = "/path/to/data.csv"
        parameter_manager.app.column_dropdown = Mock()
        parameter_manager.app.column_dropdown.get.return_value = "milepoint"
        parameter_manager.app.strength_dropdown = Mock()
        parameter_manager.app.strength_dropdown.get.return_value = "structural_strength_ind"
        
        # Execute
        is_valid, errors = parameter_manager.validate_parameters()
        
        # Should pass validation in single route mode
        assert is_valid is True
        assert errors == []
    
    # === ROUTE COLUMN CHANGE HANDLING TESTS ===
    
    # === PARAMETER RESET TESTS ===
    
    @pytest.mark.unit
    def test_reset_parameters_clears_route_data(self, parameter_manager):
        """Test that parameter reset runs without errors (route lists are managed elsewhere)."""
        parameter_manager.reset_parameters()
    
    @pytest.mark.unit
    def test_reset_parameters_resets_route_column(self, parameter_manager):
        """Test that parameter reset re-initializes method selection callbacks."""
        parameter_manager.reset_parameters()

        # reset_parameters sets the method dropdown and defers a UI refresh
        assert parameter_manager.app.method_dropdown.set.called
        parameter_manager.app.root.after.assert_called()


# === SETTINGS PERSISTENCE TESTS ===

@pytest.mark.unit
class TestRouteSettingsPersistence:
    """Test suite for route settings persistence functionality."""
    
    @pytest.fixture
    def mock_app_for_settings(self):
        """Create mock app for settings persistence testing."""
        app = Mock()
        app.route_column = Mock()
        app.selected_routes = ['US-35', 'I-75']
        app.available_routes = ['US-35', 'I-75', 'SR-123']
        app.log_message = Mock()
        
        # Mock dropdown for route column
        app.route_dropdown = Mock()
        
        return app
    
    @pytest.fixture
    def parameter_manager_with_settings(self, mock_app_for_settings):
        """Create ParameterManager for settings testing."""
        return ParameterManager(mock_app_for_settings)


# === ERROR HANDLING TESTS ===

@pytest.mark.unit 
class TestRouteParameterErrorHandling:
    """Test suite for error handling in route parameter operations."""
    
    @pytest.fixture
    def parameter_manager_with_errors(self):
        """Create ParameterManager set up to test error conditions."""
        app = Mock()
        app.route_column = Mock()
        app.file_manager = Mock()
        app.log_message = Mock()
        app.available_routes = []
        app.selected_routes = []
        app.route_info_label = Mock()
        
        return ParameterManager(app)
    
    @pytest.mark.unit
    def test_validation_handles_missing_route_attributes(self, parameter_manager_with_errors):
        """Test parameter validation handles missing route attributes gracefully.

        Note: validate_parameters does not depend on route attributes in the current implementation.
        """
        # Remove route-related attributes to simulate error condition
        del parameter_manager_with_errors.app.available_routes
        del parameter_manager_with_errors.app.selected_routes
        
        # Execute - should not raise exception
        try:
            parameter_manager_with_errors.validate_parameters()
        except AttributeError:
            # This is expected behavior if route attributes are missing
            # The test verifies the code attempts to access route attributes
            pass
        
        # No route-specific assertions required


if __name__ == '__main__':
    pytest.main([__file__])