"""
Unit tests for Phase 1 route processing functionality in FileManager.

Tests route detection, CSV column loading, and route data validation
for the multi-route processing enhancement.
"""

import pytest
import sys
import os
import pandas as pd
import tempfile
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
except ImportError as e:
    raise ImportError(f"Could not import FileManager from src/. Original error: {e}")


class TestFileManagerRouteProcessing:
    """Test suite for FileManager Phase 1 route processing functionality."""
    
    @pytest.fixture
    def mock_app_with_routes(self):
        """Create a mock app with route-related attributes."""
        app = Mock()
        app.available_routes = []
        app.selected_routes = []
        app.route_column = Mock()
        app.route_column.get.return_value = "route"
        app.log_message = Mock()
        return app
    
    @pytest.fixture
    def file_manager(self, mock_app_with_routes):
        """Create a FileManager instance with route-enabled mock app."""
        return FileManager(mock_app_with_routes)
    
    @pytest.fixture
    def temp_multi_route_csv(self):
        """Create temporary CSV file with multiple routes for testing."""
        content = """route,milepoint,structural_strength_ind
US-35,0.0,5.2
US-35,0.1,5.1
I-75,0.0,6.1
I-75,0.1,6.0
SR-123,0.0,4.5
SR-123,0.1,4.2"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture 
    def temp_single_route_csv(self):
        """Create temporary CSV file with single route for testing."""
        content = """milepoint,structural_strength_ind
0.0,5.2
0.1,5.1
0.2,4.9"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    # === ROUTE DETECTION TESTS ===
    
    @pytest.mark.unit
    def test_detect_available_routes_success(self, file_manager, temp_multi_route_csv):
        """Test successful route detection from multi-route CSV."""
        # Set up mock to return the temp file path
        file_manager.get_data_file_path = Mock(return_value=temp_multi_route_csv)
        
        # Execute
        file_manager.detect_available_routes()
        
        # Verify results
        expected_routes = ['I-75', 'SR-123', 'US-35']  # Sorted order
        assert file_manager.app.available_routes == expected_routes
        file_manager.app.log_message.assert_called()
    
    @pytest.mark.unit
    def test_detect_available_routes_no_data_file(self, file_manager):
        """Test route detection when no data file is selected."""
        # Set up mock to return None for data file path
        file_manager.get_data_file_path = Mock(return_value=None)
        
        # Execute
        file_manager.detect_available_routes()
        
        # Verify results - should clear routes
        assert file_manager.app.available_routes == []
        assert file_manager.app.selected_routes == []
    
    @pytest.mark.unit
    def test_detect_available_routes_no_route_column(self, file_manager, temp_multi_route_csv):
        """Test route detection when no route column is selected."""
        # Set up mocks
        file_manager.get_data_file_path = Mock(return_value=temp_multi_route_csv)
        file_manager.app.route_column.get.return_value = "None - treat as single route"
        
        # Execute
        file_manager.detect_available_routes()
        
        # Verify results - should clear routes
        assert file_manager.app.available_routes == []
        assert file_manager.app.selected_routes == []
    
    @pytest.mark.unit
    @patch('file_manager.messagebox')  # Mock messagebox to prevent dialogs during testing
    def test_detect_available_routes_missing_column(self, mock_messagebox, file_manager, temp_multi_route_csv):
        """Test route detection when route column doesn't exist in CSV."""
        # Set up mocks
        file_manager.get_data_file_path = Mock(return_value=temp_multi_route_csv)
        file_manager.app.route_column.get.return_value = "nonexistent_column"
        
        # Execute and expect exception to be handled
        file_manager.detect_available_routes()
        
        # Should handle error gracefully - check that log_message was called with error
        file_manager.app.log_message.assert_called()
        
        # Verify error was handled (no longer expect messagebox in test mode)
        log_calls = [str(call) for call in file_manager.app.log_message.call_args_list]
        assert any("ERROR:" in call for call in log_calls), "Expected error to be logged"
        
        # Verify routes were cleared on error
        assert file_manager.app.available_routes == []
        assert file_manager.app.selected_routes == []
    
    @pytest.mark.unit
    def test_detect_available_routes_with_nulls(self, file_manager):
        """Test route detection with null/missing values in route column."""
        # Create test data with missing values
        content = """route,milepoint,structural_strength_ind
US-35,0.0,5.2
,0.1,5.1
I-75,0.2,4.9
,0.3,4.8"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            temp_path = f.name
        
        try:
            # Set up mock
            file_manager.get_data_file_path = Mock(return_value=temp_path)
            
            # Execute
            file_manager.detect_available_routes()
            
            # Verify results - should handle nulls properly
            expected_routes = ['Default', 'I-75', 'US-35']  # Default for null values, sorted
            assert file_manager.app.available_routes == expected_routes
        
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.unit
    def test_detect_available_routes_duplicate_routes(self, file_manager):
        """Test route detection with duplicate route values."""
        # Create test data with duplicates
        content = """route,milepoint,structural_strength_ind
US-35,0.0,5.2
US-35,0.1,5.1
US-35,0.2,4.9
I-75,0.0,6.1
I-75,0.1,6.0"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            temp_path = f.name
        
        try:
            # Set up mock
            file_manager.get_data_file_path = Mock(return_value=temp_path)
            
            # Execute
            file_manager.detect_available_routes()
            
            # Verify results - should have unique routes only
            expected_routes = ['I-75', 'US-35']  # No duplicates, sorted
            assert file_manager.app.available_routes == expected_routes
        
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    # === CSV COLUMN LOADING TESTS ===
    
    @pytest.mark.unit 
    def test_load_csv_columns_with_route_support(self, file_manager, temp_multi_route_csv):
        """Test CSV column loading includes route column support."""
        # Set up mocks
        file_manager.get_data_file_path = Mock(return_value=temp_multi_route_csv)
        file_manager.app.available_columns = []
        
        # Create mocks for dropdown widgets - they need __setitem__ for ['values'] assignment
        mock_column_dropdown = Mock()
        mock_strength_dropdown = Mock()
        mock_route_dropdown = Mock()
        
        # Configure all mocks to support dictionary-style access  
        mock_column_dropdown.__setitem__ = Mock()
        mock_strength_dropdown.__setitem__ = Mock() 
        mock_route_dropdown.__setitem__ = Mock()
        
        file_manager.app.x_column_combo = mock_column_dropdown
        file_manager.app.y_column_combo = mock_strength_dropdown
        file_manager.app.route_column_combo = mock_route_dropdown
        
        # Mock route column to prevent route detection from being triggered
        file_manager.app.route_column = Mock()
        file_manager.app.route_column.get = Mock(return_value="None - treat as single route")
        
        # Execute
        file_manager.load_csv_columns()
        
        # Verify columns were loaded - order matches the test CSV header
        expected_columns = ['route', 'milepoint', 'structural_strength_ind']
        assert set(file_manager.app.available_columns) == set(expected_columns)
        
        # Verify dropdown values were set (the real implementation uses combo['values'] = columns)
        mock_column_dropdown.__setitem__.assert_called_with('values', expected_columns)
        mock_strength_dropdown.__setitem__.assert_called_with('values', expected_columns)
        
        file_manager.app.log_message.assert_any_call(
            f"Found {len(expected_columns)} columns: {expected_columns}"
        )
    
    @pytest.mark.unit
    def test_load_csv_columns_no_route_column(self, file_manager, temp_single_route_csv):
        """Test CSV column loading when no route column exists."""
        # Set up mocks
        file_manager.get_data_file_path = Mock(return_value=temp_single_route_csv)
        file_manager.app.available_columns = []
        
        # Create mocks (no route column case) - they need __setitem__ for ['values'] assignment
        mock_column_dropdown = Mock()
        mock_strength_dropdown = Mock()
        mock_route_dropdown = Mock()
        
        # Configure all mocks to support dictionary-style access  
        mock_column_dropdown.__setitem__ = Mock()
        mock_strength_dropdown.__setitem__ = Mock()
        mock_route_dropdown.__setitem__ = Mock()
        
        file_manager.app.x_column_combo = mock_column_dropdown
        file_manager.app.y_column_combo = mock_strength_dropdown
        file_manager.app.route_column_combo = mock_route_dropdown
        
        # Execute
        file_manager.load_csv_columns()
        
        # Verify route dropdown includes "None" option
        expected_columns = ['milepoint', 'structural_strength_ind']
        assert set(file_manager.app.available_columns) == set(expected_columns)
        
        # Verify route dropdown was configured with "None" option plus columns  
        expected_route_options = ["None - treat as single route"] + expected_columns
        mock_route_dropdown.__setitem__.assert_called_with('values', expected_route_options)
    
    @pytest.mark.unit
    def test_get_data_file_path_returns_valid_path(self, file_manager, temp_multi_route_csv):
        """Test get_data_file_path returns the current data file path."""
        # Set the actual attribute that get_data_file_path() accesses
        file_manager.app._data_file_path = temp_multi_route_csv
        
        # Execute the actual method being tested
        result = file_manager.get_data_file_path()
        
        # Verify - should return the _data_file_path attribute value
        assert result == temp_multi_route_csv
    
    # === ERROR HANDLING TESTS ===
    
    @pytest.mark.unit
    @patch('file_manager.messagebox')  # Mock messagebox to prevent dialogs during testing  
    def test_detect_routes_handles_file_read_error(self, mock_messagebox, file_manager):
        """Test route detection handles file read errors gracefully."""
        # Set up mock to return non-existent file path
        file_manager.get_data_file_path = Mock(return_value="/nonexistent/file.csv")
        
        # Execute - should not raise exception
        file_manager.detect_available_routes()
        
        # Verify error was logged
        file_manager.app.log_message.assert_called()
        
        # In test mode, verify error was logged instead of showing popup
        log_calls = [str(call) for call in file_manager.app.log_message.call_args_list]
        assert any("ERROR:" in call for call in log_calls), "Expected error to be logged during test"
        
        # Should clear routes on error
        assert file_manager.app.available_routes == []
    
    @pytest.mark.unit
    def test_load_csv_columns_handles_missing_file(self, file_manager):
        """Test CSV column loading handles missing file gracefully."""
        # Set up mock to return non-existent file
        file_manager.get_data_file_path = Mock(return_value="/nonexistent/file.csv")
        file_manager.app.available_columns = []
        
        # Execute - should not raise exception
        file_manager.load_csv_columns()
        
        # Should handle error gracefully
        file_manager.app.log_message.assert_called()


# === INTEGRATION TESTS ===

@pytest.mark.integration
class TestRouteProcessingIntegration:
    """Integration tests for route processing workflow."""
    
    @pytest.fixture
    def integration_app(self):
        """Create a more complete mock app for integration testing."""
        app = Mock()
        app.available_routes = []
        app.selected_routes = []
        app.available_columns = []
        app.route_column = Mock()
        app.route_column.get.return_value = "route"
        app.data_file_path = Mock()
        app.log_message = Mock()
        
        # Mock dropdown objects
        app.column_dropdown = Mock()
        app.strength_dropdown = Mock()
        app.route_dropdown = Mock()
        
        # Configure dropdown mocks to support __getitem__ method
        for dropdown in [app.column_dropdown, app.strength_dropdown, app.route_dropdown]:
            dropdown.__getitem__ = Mock(return_value=Mock())
        
        return app
    
    def test_complete_route_workflow(self, integration_app):
        """Test complete workflow from file loading to route detection."""
        # Create test data
        content = """route,milepoint,structural_strength_ind
US-35,0.0,5.2
US-35,0.1,5.1
I-75,0.0,6.1
I-75,0.1,6.0"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            f.flush()
            temp_path = f.name
        
        try:
            # Set up file manager
            file_manager = FileManager(integration_app)
            # Set the correct attribute that get_data_file_path() accesses
            integration_app._data_file_path = temp_path
            
            # Step 1: Load CSV columns
            file_manager.load_csv_columns()
            
            # Verify columns loaded - order matches the CSV header: route,milepoint,structural_strength_ind
            expected_columns = ['route', 'milepoint', 'structural_strength_ind']
            assert set(integration_app.available_columns) == set(expected_columns)
            
            # Step 2: Detect routes
            file_manager.detect_available_routes()
            
            # Verify routes detected
            expected_routes = ['I-75', 'US-35']
            assert integration_app.available_routes == expected_routes
            
            # Verify logging occurred
            assert integration_app.log_message.call_count >= 2  # At least 2 calls
        
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)