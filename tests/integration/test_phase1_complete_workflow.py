"""
Integration tests for Phase 1 multi-route processing functionality.

Tests complete workflows from data loading through route selection
to UI state management across all components.
"""

import pytest
import sys
import os
import pandas as pd
import tempfile
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add src to path for imports
current_file_dir = os.path.dirname(__file__)
tests_dir = os.path.dirname(current_file_dir)  
project_root = os.path.dirname(tests_dir)
src_path = os.path.join(project_root, 'src')

if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from file_manager import FileManager
    from parameter_manager import ParameterManager
    from route_filter_dialog import RouteFilterDialog
except ImportError as e:
    raise ImportError(f"Could not import required modules from src/. Original error: {e}")


@pytest.fixture(scope="module")
def test_data_dir():
    """Get the test data directory path."""
    return os.path.join(os.path.dirname(__file__), '..', 'test_data')


@pytest.fixture
def multi_route_test_data():
    """Create comprehensive multi-route test data."""
    return """route,milepoint,structural_strength_ind,pavement_condition
US-35,0.0,5.2,85
US-35,0.1,5.1,83
US-35,0.2,4.9,82
US-35,0.3,4.8,80
I-75,0.0,6.1,92
I-75,0.1,6.0,91
I-75,0.2,5.8,89
I-75,0.3,5.7,88
SR-123,0.0,4.5,75
SR-123,0.1,4.2,73
SR-123,0.2,3.8,70
SR-123,0.3,3.5,68
US-50,0.0,5.5,87
US-50,0.1,5.3,85
I-71,0.0,6.2,94
I-71,0.1,6.1,93"""


@pytest.fixture
def complex_mock_app():
    """Create comprehensive mock app for integration testing."""
    app = Mock()
    
    # Data and file management
    app.data_file_path = Mock()
    app.available_columns = []
    
    # Route management  
    app.available_routes = []
    app.selected_routes = []
    app.route_column = Mock()
    app.route_column.get.return_value = "None - treat as single route"  # Fix Mock iteration issue
    app.route_column.set = Mock()
    
    # Parameter validation mocks (fix parameter validation comparison errors)
    app.min_length = Mock()
    app.min_length.get.return_value = 1.0
    app.max_length = Mock()  
    app.max_length.get.return_value = 5.0
    app.gap_threshold = Mock()
    app.gap_threshold.get.return_value = 0.1
    app.population_size = Mock()
    app.population_size.get.return_value = 50
    app.num_generations = Mock()
    app.num_generations.get.return_value = 100
    app.mutation_rate = Mock()
    app.mutation_rate.get.return_value = 0.1
    app.crossover_rate = Mock()
    app.crossover_rate.get.return_value = 0.8
    app.elite_ratio = Mock()
    app.elite_ratio.get.return_value = 0.1
    app.cache_clear_interval = Mock()
    app.cache_clear_interval.get.return_value = 10
    app.method_dropdown = Mock()
    app.method_dropdown.get.return_value = "Multi-Objective NSGA-II"  # Fixed display name to match config.py
    app.optimization_method = Mock()
    app.optimization_method.get.return_value = 'multi'
    
    # UI Builder mock (required for parameter validation)
    app.ui_builder = Mock()
    app.ui_builder.get_parameter_values.return_value = {
        'min_length': 1.0,
        'max_length': 5.0,
        # NOTE: Gap threshold is framework-level (app.gap_threshold), but leaving
        # it here is harmless for tests.
        'gap_threshold': 0.1,

        # Method-scoped dynamic parameters required by the multi-objective method
        'population_size': 100,
        'num_generations': 100,
        'crossover_rate': 0.8,
        'mutation_rate': 0.05,
        'cache_clear_interval': 50,
        'enable_performance_stats': True,
    }
    
    # UI components
    app.column_dropdown = Mock()
    app.strength_dropdown = Mock() 
    app.route_dropdown = Mock()
    app.route_info_label = Mock()
    app.route_info_label.config = Mock()
    app.log_message = Mock()
    
    # Add the actual combo box widgets that file_manager.load_csv_columns() expects
    app.x_column_combo = Mock()
    app.y_column_combo = Mock()
    app.route_column_combo = Mock()
    app.x_column = Mock()
    app.y_column = Mock()
    
    # Configure combo box mocks to have __getitem__ and __setitem__ for 'values'
    for combo in [app.x_column_combo, app.y_column_combo, app.route_column_combo]:
        combo.__getitem__ = Mock(return_value=Mock())
        combo.__setitem__ = Mock()
    
    # Configure column variable mocks
    app.x_column.get = Mock(return_value='milepoint')
    app.x_column.set = Mock()
    app.y_column.get = Mock(return_value='structural_strength_ind')
    app.y_column.set = Mock()
    
    # Configure dropdown mocks
    for dropdown in [app.column_dropdown, app.strength_dropdown, app.route_dropdown]:
        dropdown.__getitem__ = Mock(return_value=Mock())
        dropdown.__setitem__ = Mock()
        dropdown.set = Mock()
        dropdown.get = Mock()
    
    # Mock the update method that's called by detect_available_routes
    app._update_route_info_display = Mock()
    
    # Mock data attribute for validation
    app.data = None
    
    return app


@pytest.mark.integration
class TestPhase1CompleteWorkflow:
    """Integration tests for complete Phase 1 multi-route processing workflow."""
    
    def test_end_to_end_multi_route_workflow(self, complex_mock_app, multi_route_test_data):
        """Test complete workflow from file loading to route selection."""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(multi_route_test_data)
            f.flush()
            temp_path = f.name
        
        try:
            # Initialize components
            file_manager = FileManager(complex_mock_app)
            parameter_manager = ParameterManager(complex_mock_app)
            
            # Set up file path (fix Mock configuration for get_data_file_path)
            complex_mock_app._data_file_path = temp_path  # Set the actual attribute the method reads
            complex_mock_app.data_file_path.get.return_value = temp_path  # Keep for other uses
            
            # === PHASE 1: FILE LOADING AND COLUMN DETECTION ===
            
            # Step 1: Load CSV columns
            file_manager.load_csv_columns()
            
            # Verify columns were detected (match actual CSV column order)
            expected_columns = ['route', 'milepoint', 'structural_strength_ind', 'pavement_condition']
            assert set(complex_mock_app.available_columns) == set(expected_columns)
            
            # Verify combo box widgets were updated with column values
            complex_mock_app.x_column_combo.__setitem__.assert_called_with('values', expected_columns)
            complex_mock_app.y_column_combo.__setitem__.assert_called_with('values', expected_columns)
            route_options = ["None - treat as single route"] + expected_columns
            complex_mock_app.route_column_combo.__setitem__.assert_called_with('values', route_options)
            
            # === PHASE 2: ROUTE COLUMN SELECTION ===
            
            # Step 2: User selects route column
            complex_mock_app.route_column.get.return_value = "route"
            
            # Simulate route column change event
            mock_event = Mock()
            file_manager.detect_available_routes()
            
            # Verify route detection was triggered
            expected_routes = ['I-71', 'I-75', 'SR-123', 'US-35', 'US-50']  # Sorted
            assert complex_mock_app.available_routes == expected_routes
            
            # === PHASE 3: ROUTE FILTERING SIMULATION ===
            
            # Step 3: User opens route filter dialog (simulated)
            initial_selected = complex_mock_app.available_routes[:2]  # Select first 2 routes
            complex_mock_app.selected_routes = initial_selected
            
            # Simulate route selection workflow
            assert len(complex_mock_app.selected_routes) == 2
            assert all(route in complex_mock_app.available_routes for route in complex_mock_app.selected_routes)
            
            # === PHASE 4: PARAMETER VALIDATION ===
            
            # Step 4a: Load data file before validation  
            file_manager.load_data_file()

            # NOTE: Loading data resets route state to avoid stale selections.
            # Re-detect routes using the currently selected route column.
            file_manager.detect_available_routes()

            # Step 4b: Validate parameters with route selection
            complex_mock_app.column_dropdown.get.return_value = "milepoint"
            complex_mock_app.strength_dropdown.get.return_value = "structural_strength_ind"

            validation_result = parameter_manager.validate_parameters()

            # Should pass validation with proper setup
            assert validation_result[0] is True, f"Validation failed: {validation_result[1]}"
            
            # Verify all components are properly integrated
            assert complex_mock_app.available_routes  # Routes detected
            assert complex_mock_app.selected_routes   # Routes selected
            assert complex_mock_app.available_columns # Columns loaded
            
            # Verify logging occurred throughout workflow
            assert complex_mock_app.log_message.call_count >= 3
            
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_single_route_mode_workflow(self, complex_mock_app, multi_route_test_data):
        """Test workflow when operating in single route mode."""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(multi_route_test_data)
            f.flush()
            temp_path = f.name
        
        try:
            # Initialize components
            file_manager = FileManager(complex_mock_app)
            parameter_manager = ParameterManager(complex_mock_app)
            
            # Set up file path (both Mock return value and actual attribute)
            complex_mock_app._data_file_path = temp_path
            complex_mock_app.data_file_path.get.return_value = temp_path
            
            # === SINGLE ROUTE MODE WORKFLOW ===
            
            # Step 1: Load columns
            file_manager.load_csv_columns()
            
            # Step 2: Select "None - treat as single route"
            complex_mock_app.route_column.get.return_value = "None - treat as single route"
            
            # Step 3: Trigger route column change
            mock_event = Mock()
            file_manager.detect_available_routes()
            
            # Verify route data was cleared for single route mode
            assert complex_mock_app.available_routes == []
            assert complex_mock_app.selected_routes == []
            
# Step 4: Load data and validate parameters in single route mode
            complex_mock_app._data_file_path = temp_path
            file_manager.load_data_file()
            
            complex_mock_app.column_dropdown.get.return_value = "milepoint"
            complex_mock_app.strength_dropdown.get.return_value = "structural_strength_ind"

            validation_result = parameter_manager.validate_parameters()
            assert validation_result[0] is True, f"Validation failed: {validation_result[1]}"
            
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_route_column_switching_workflow(self, complex_mock_app, multi_route_test_data):
        """Test workflow when user switches between different route columns."""
        # Create test data with multiple potential route columns
        extended_data = """route,alt_route,milepoint,structural_strength_ind
US-35,Route-A,0.0,5.2
US-35,Route-A,0.1,5.1
I-75,Route-B,0.0,6.1
I-75,Route-B,0.1,6.0"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(extended_data)
            f.flush()
            temp_path = f.name
        
        try:
            # Initialize components
            file_manager = FileManager(complex_mock_app)
            parameter_manager = ParameterManager(complex_mock_app)
            
            complex_mock_app.data_file_path.get.return_value = temp_path
            
            # === ROUTE COLUMN SWITCHING WORKFLOW ===
            
            # Step 1: Load columns
            file_manager.load_csv_columns()
            
            # Step 2: Select first route column and set up file path
            complex_mock_app._data_file_path = temp_path
            complex_mock_app.route_column.get.return_value = "route"
            mock_event = Mock()
            file_manager.detect_available_routes()
            
            first_routes = complex_mock_app.available_routes.copy()
            expected_first = ['I-75', 'US-35']
            assert first_routes == expected_first
            
            # Step 3: Switch to alternative route column
            complex_mock_app.route_column.get.return_value = "alt_route"
            file_manager.detect_available_routes()
            
            second_routes = complex_mock_app.available_routes.copy()
            expected_second = ['Route-A', 'Route-B']
            assert second_routes == expected_second
            
            # Verify routes changed
            assert first_routes != second_routes
            
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)


@pytest.mark.integration
class TestPhase1ErrorHandlingIntegration:
    """Integration tests for error handling across Phase 1 components."""
    
    @patch('file_manager.messagebox')  # Mock messagebox to prevent dialogs during testing
    def test_missing_file_error_handling(self, mock_messagebox, complex_mock_app):
        """Test error handling when data file is missing."""
        # Initialize components
        file_manager = FileManager(complex_mock_app)
        parameter_manager = ParameterManager(complex_mock_app)
        
        # Set invalid file path (fix Mock configuration for get_data_file_path)
        complex_mock_app._data_file_path = "/nonexistent/file.csv"  # Set the actual attribute the method reads
        complex_mock_app.data_file_path.get.return_value = "/nonexistent/file.csv"
        
        # === ERROR HANDLING WORKFLOW ===
        
        # Step 1: Attempt to load columns from missing file
        file_manager.load_csv_columns()  # Should handle error gracefully
        
        # Step 2: Attempt route detection
        file_manager.detect_available_routes()  # Should handle error gracefully
        
        # Verify errors were logged but didn't crash
        assert complex_mock_app.log_message.call_count >= 1  # At least one error logged
        
        # Verify the error message contains file error info
        log_calls = complex_mock_app.log_message.call_args_list
        error_logged = any("error" in str(call).lower() and ("no such file" in str(call).lower() or "not found" in str(call).lower()) for call in log_calls)
        assert error_logged, f"Expected file error in log calls: {log_calls}"
        
        # Verify application state remains consistent after errors
        assert complex_mock_app.available_routes == []
    
    @patch('file_manager.messagebox')  # Mock messagebox to prevent dialogs during testing
    def test_invalid_route_column_error_handling(self, mock_messagebox, complex_mock_app, multi_route_test_data):
        """Test error handling when route column doesn't exist."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(multi_route_test_data)
            f.flush()
            temp_path = f.name
        
        try:
            # Initialize components
            file_manager = FileManager(complex_mock_app)
            parameter_manager = ParameterManager(complex_mock_app)
            
            complex_mock_app.data_file_path.get.return_value = temp_path
            
            # === INVALID COLUMN ERROR HANDLING ===
            
            # Step 1: Load valid columns
            file_manager.load_csv_columns()
            
            # Step 2: Select non-existent route column
            complex_mock_app.route_column.get.return_value = "nonexistent_column"
            
            # Step 3: Attempt route detection with invalid column
            file_manager.detect_available_routes()  # Should handle gracefully
            
            # Verify error was handled
            assert complex_mock_app.log_message.call_count >= 2
            assert complex_mock_app.available_routes == []
            
            # In test mode we log errors instead of showing GUI popups
            assert mock_messagebox.showerror.call_count == 0
            
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)


@pytest.mark.integration 
class TestPhase1DataConsistency:
    """Integration tests for data consistency across Phase 1 operations."""
    
    def test_data_consistency_across_operations(self, complex_mock_app):
        """Test that data remains consistent across multiple operations."""
        # Create test data with edge cases
        complex_data = """route,milepoint,structural_strength_ind
US-35,0.0,5.2
US-35,0.1,5.1
,0.2,4.9
I-75,0.3,6.1
I-75,,6.0
SR-123,0.5,"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(complex_data)
            f.flush()
            temp_path = f.name
        
        try:
            # Initialize components
            file_manager = FileManager(complex_mock_app)
            parameter_manager = ParameterManager(complex_mock_app)
            
            # Set up file path (both Mock return value and actual attribute)
            complex_mock_app._data_file_path = temp_path
            complex_mock_app.data_file_path.get.return_value = temp_path
            
            # Set route column to detect routes (override default "None - treat as single route")
            complex_mock_app.route_column.get.return_value = "route"
            
            # === DATA CONSISTENCY WORKFLOW ===
            
            # Multiple operations that should maintain consistency
            for i in range(3):
                # Load columns
                file_manager.load_csv_columns()
                
                # Detect routes  
                file_manager.detect_available_routes()
                
                # Verify consistent results each time
                expected_routes = ['Default', 'I-75', 'SR-123', 'US-35']  # Including 'Default' for null values
                assert complex_mock_app.available_routes == expected_routes
                
                expected_columns = ['milepoint', 'route', 'structural_strength_ind']
                assert set(complex_mock_app.available_columns) == set(expected_columns)
            
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_state_transitions_consistency(self, complex_mock_app, multi_route_test_data):
        """Test state transitions maintain consistency."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(multi_route_test_data)
            f.flush()
            temp_path = f.name
        
        try:
            # Initialize components
            file_manager = FileManager(complex_mock_app)
            parameter_manager = ParameterManager(complex_mock_app)
            
            complex_mock_app.data_file_path.get.return_value = temp_path
            
            # === STATE TRANSITION WORKFLOW ===
            
            # State 1: Initial load
            file_manager.load_csv_columns()
            file_manager.detect_available_routes()
            state1_routes = complex_mock_app.available_routes.copy()
            
            # State 2: Reset parameters
            parameter_manager.reset_parameters()
            assert complex_mock_app.available_routes == []
            assert complex_mock_app.selected_routes == []
            
            # State 3: Reload (should restore same state as State 1)
            file_manager.detect_available_routes()
            state3_routes = complex_mock_app.available_routes.copy()
            
            # Verify consistency
            assert state1_routes == state3_routes
            
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == '__main__':
    pytest.main([__file__])