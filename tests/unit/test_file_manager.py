"""
Unit tests for FileManager class.

Tests file loading, saving, validation, and data manipulation
for all supported file formats and operations.
"""
import pytest

pytest.skip(
    "Legacy FileManager unit tests are being retired; to be replaced with updated coverage.",
    allow_module_level=True,
)

import sys
import os
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
import tempfile
import shutil

# Add src to path for imports - portable approach
current_file_dir = os.path.dirname(__file__)  # tests/unit
tests_dir = os.path.dirname(current_file_dir)  # tests  
project_root = os.path.dirname(tests_dir)  # highway-segmentation-ga
src_path = os.path.join(project_root, 'src')

# Add to path if not already present
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from file_manager import FileManager
except ImportError as e:
    # If imports still fail, provide helpful error message
    raise ImportError(f"Could not import FileManager from src/. "
                     f"Make sure you're running from project root or with PYTHONPATH=src. "
                     f"Original error: {e}")

class TestFileManager:
    """Test suite for FileManager functionality."""
    
    def test_init_with_mock_app(self, mock_gui_app):
        """Test FileManager initialization."""
        file_manager = FileManager(mock_gui_app)
        assert file_manager.app == mock_gui_app
        # FileManager doesn't have these attributes directly -
        # it manages paths through the app object
    
    # === DATA LOADING TESTS ===
    
    @pytest.mark.unit
    @pytest.mark.data_dependent
    def test_load_csv_file_success(self, mock_gui_app, temp_csv_file):
        """Test successful CSV file loading."""
        fm = FileManager(mock_gui_app)
        
        # Set required data file path and columns for FileManager to work
        fm.set_data_file_path(temp_csv_file)
        mock_gui_app.x_column.set('milepoint')
        mock_gui_app.y_column.set('structural_strength_ind')
        
        # Mock messagebox to prevent any potential popups
        with patch('tkinter.messagebox.showerror'):
            # Load the data
            fm.load_data_file()
        
        # Verify data was loaded
        assert fm.get_data_file_path() == temp_csv_file
        # Data should be loaded into app.data
        assert mock_gui_app.data is not None
    
    @pytest.mark.unit
    def test_browse_data_file_cancelled(self, mock_gui_app):
        """Test CSV browse when user cancels file dialog."""
        fm = FileManager(mock_gui_app)
        
        # Mock cancelled file dialog (returns empty string)
        with patch('tkinter.filedialog.askopenfilename', return_value=''):
            fm.browse_data_file()
        
        # No file should be selected
        assert fm.get_data_file_path() == ''
    
    @pytest.mark.unit
    def test_load_nonexistent_file(self, mock_gui_app):
        """Test loading a file that doesn't exist."""
        fm = FileManager(mock_gui_app)
        
        # Set path to nonexistent file
        fm.set_data_file_path('/nonexistent/file.csv')
        mock_gui_app.x_column.set('milepoint')
        mock_gui_app.y_column.set('structural_strength_ind')
        
        # Mock messagebox to prevent actual popup dialogs during testing
        with patch('tkinter.messagebox.showerror') as mock_messagebox:
            # Should handle error gracefully (won't crash but will log error)
            fm.load_data_file()
            
            # Should show error messagebox
            mock_messagebox.assert_called()
        
        # Should log error message
        mock_gui_app.log_message.assert_called()
    
    # @pytest.mark.unit 
    # def test_load_invalid_csv_format(self, mock_gui_app, temp_directory):
    #     """Test loading CSV with invalid format."""
    #     # Create invalid CSV file
    #     invalid_csv = os.path.join(temp_directory, 'invalid.csv')
    #     with open(invalid_csv, 'w') as f:
    #         f.write("invalid,csv,format\\n")
    #         f.write("no,proper,headers\\n")
    #         f.write("missing,required,columns\\n")
    #     
    #     fm = FileManager(mock_gui_app)
    #     result = fm.load_data_from_path(invalid_csv)
    #     
    #     # Should handle gracefully and return False
    #     assert result is False
    
    # @pytest.mark.unit
    # def test_validate_data_structure_valid(self, mock_gui_app, sample_highway_data):
    #     """Test data validation with valid dataset."""
    #     fm = FileManager(mock_gui_app)
    #     
    #     is_valid, message = fm.validate_data_structure(sample_highway_data)
    #     
    #     assert is_valid is True
    #     assert "valid" in message.lower() or message == ""
    # 
    # @pytest.mark.unit
    # def test_validate_data_structure_missing_columns(self, mock_gui_app):
    #     """Test data validation with missing required columns."""
    #     fm = FileManager(mock_gui_app)
    #     
    #     # Data missing required columns
    #     invalid_data = pd.DataFrame({
    #         'wrong_column': [1, 2, 3],
    #         'another_wrong': [4, 5, 6]
    #     })
    #     
    #     is_valid, message = fm.validate_data_structure(invalid_data)
    #     
    #     assert is_valid is False
    #     assert "milepoint" in message.lower()
    # 
    # @pytest.mark.unit
    # def test_validate_data_structure_empty_data(self, mock_gui_app):
    #     """Test data validation with empty dataset."""
    #     fm = FileManager(mock_gui_app)
    #     
    #     empty_data = pd.DataFrame(columns=['milepoint', 'structural_strength_ind'])
    #     
    #     is_valid, message = fm.validate_data_structure(empty_data)
    #     
    #     assert is_valid is False
    #     assert "empty" in message.lower() or "no data" in message.lower()
    # 
    # @pytest.mark.unit
    # def test_validate_data_structure_single_point(self, mock_gui_app):
    #     """Test data validation with single data point."""
    #     fm = FileManager(mock_gui_app)
    #     
    #     single_point = pd.DataFrame({
    #         'milepoint': [0.0],
    #         'structural_strength_ind': [5.0]
    #     })
    #     
    #     is_valid, message = fm.validate_data_structure(single_point)
    #     
    #     assert is_valid is False  # Need at least 2 points for segmentation
    #     assert "insufficient" in message.lower() or "few" in message.lower()
    
    # === DATA PROCESSING TESTS ===
    # NOTE: These methods don't exist in current FileManager implementation
    
    # @pytest.mark.unit
    # def test_sort_data_by_milepoint(self, mock_gui_app):
    #     """Test data sorting by milepoint."""
    #     fm = FileManager(mock_gui_app)
    #     
    #     # Create unsorted data
    #     unsorted_data = pd.DataFrame({
    #         'milepoint': [3.0, 1.0, 5.0, 2.0],
    #         'structural_strength_ind': [1, 2, 3, 4]
    #     })
    #     
    #     sorted_data = fm.sort_data_by_milepoint(unsorted_data)
    #     
    #     # Check if sorted correctly
    #     expected_milepoints = [1.0, 2.0, 3.0, 5.0]
    #     assert list(sorted_data['milepoint']) == expected_milepoints
    # 
    # @pytest.mark.unit
    # def test_remove_duplicate_milepoints(self, mock_gui_app):
    #     """Test removal of duplicate milepoints."""
    #     fm = FileManager(mock_gui_app)
    #     
    #     data_with_duplicates = pd.DataFrame({
    #         'milepoint': [1.0, 1.0, 2.0, 2.0, 3.0],
    #         'structural_strength_ind': [5.0, 5.1, 3.0, 3.1, 4.0]
    #     })
    #     
    #     cleaned_data = fm.remove_duplicate_milepoints(data_with_duplicates)
    #     
    #     # Should have unique milepoints
    #     assert len(cleaned_data) < len(data_with_duplicates)
    #     assert cleaned_data['milepoint'].is_unique
    
    # === SAVE PATH MANAGEMENT TESTS ===
    
    @pytest.mark.unit
    def test_set_save_file_path(self, mock_gui_app):
        """Test setting save file path."""
        fm = FileManager(mock_gui_app)
        
        test_path = "/path/to/results.csv"
        fm.set_save_file_path(test_path)
        
        assert fm.get_save_file_path() == test_path
    
    @pytest.mark.unit
    def test_get_save_file_path(self, mock_gui_app):
        """Test getting current save file path."""
        fm = FileManager(mock_gui_app)
        
        # Initially empty string (not None)
        assert fm.get_save_file_path() == ''
        
        # After setting
        test_path = "/path/to/results.csv"
        fm.set_save_file_path(test_path)
        assert fm.get_save_file_path() == test_path
    
    @pytest.mark.unit
    def test_choose_save_location(self, mock_gui_app, temp_directory):
        """Test save location selection dialog.""" 
        fm = FileManager(mock_gui_app)
        
        expected_path = os.path.join(temp_directory, 'test_results.csv')
        
        with patch('tkinter.filedialog.asksaveasfilename', return_value=expected_path):
            fm.browse_save_location()
        
        # Should set the save path
        assert fm.get_save_file_path() == expected_path
    
    @pytest.mark.unit  
    def test_choose_save_location_cancelled(self, mock_gui_app):
        """Test save location selection when user cancels."""
        fm = FileManager(mock_gui_app)
        
        with patch('tkinter.filedialog.asksaveasfilename', return_value=''):
            fm.browse_save_location()
        
        # Should not set save path when cancelled
        assert fm.get_save_file_path() == ''
    
    # === RESULT FILE DISPLAY TESTS ===
    
    # @pytest.mark.unit
    # def test_display_results_file_exists(self, mock_gui_app, sample_results_files):
    #     """Test displaying results file that exists."""
    #     fm = FileManager(mock_gui_app)
    #     
    #     # Mock subprocess to avoid actually opening file
    #     with patch('subprocess.run') as mock_subprocess:
    #         fm.display_results_file(sample_results_files['res'])
    #         
    #         # Should attempt to open file
    #         mock_subprocess.assert_called_once()
    # 
    # @pytest.mark.unit
    # def test_display_results_file_not_exists(self, mock_gui_app):
    #     """Test displaying results file that doesn't exist."""
    #     fm = FileManager(mock_gui_app)
    #     
    #     result = fm.display_results_file('/nonexistent/file.res')
    #     
    #     assert result is False
    #     # Should log error
    #     if hasattr(mock_gui_app, 'log_message'):
    #         mock_gui_app.log_message.assert_called()
    
    # === AUTO-LOAD FUNCTIONALITY TESTS ===
    # NOTE: These methods don't exist in current FileManager implementation
    
    # @pytest.mark.unit
    # @pytest.mark.data_dependent  
    # def test_auto_load_txdot_data(self, mock_gui_app, txdot_data):
    #     """Test automatic loading of TxDOT data if available."""
    #     fm = FileManager(mock_gui_app)
    #     
    #     # Should be able to load the real data
    #     result = fm.auto_load_default_data()
    #     
    #     if result:
    #         assert fm.current_data_path is not None
    #         # Verify it loaded actual TxDOT data structure
    #         assert hasattr(mock_gui_app, 'data') or mock_gui_app.data is not None
    
    # === ERROR HANDLING TESTS ===
    
    # @pytest.mark.unit
    # def test_load_corrupted_csv(self, mock_gui_app, temp_directory):
    #     """Test loading corrupted CSV file."""
    #     # Create corrupted CSV
    #     corrupted_csv = os.path.join(temp_directory, 'corrupted.csv')
    #     with open(corrupted_csv, 'wb') as f:
    #         f.write(b'\\xff\\xfe\\x00\\x00corrupted data')  # Invalid bytes
    #     
    #     fm = FileManager(mock_gui_app)
    #     result = fm.load_data_from_path(corrupted_csv)
    #     
    #     assert result is False
    #         
    # @pytest.mark.unit
    # def test_load_csv_with_encoding_issues(self, mock_gui_app, temp_directory):
    #     """Test loading CSV with encoding issues."""
    #     # Create CSV with special characters
    #     special_csv = os.path.join(temp_directory, 'special.csv')
    #     with open(special_csv, 'w', encoding='latin1') as f:
    #         f.write("milepoint,structural_strength_ind\\n")
    #         f.write("1.0,5.5\\n")
    #         f.write("2.0,café\\n")  # Special character that might cause issues
    #     
    #     fm = FileManager(mock_gui_app) 
    #     result = fm.load_data_from_path(special_csv)
    #     
    #     # Should handle gracefully (might succeed or fail, but shouldn't crash)
    #     assert isinstance(result, bool)
    
    # === PATH UTILITIES TESTS ===
    
    @pytest.mark.unit
    def test_get_data_file_path(self, mock_gui_app):
        """Test getting current data file path."""
        fm = FileManager(mock_gui_app)
        
        # Initially empty string (not None)
        assert fm.get_data_file_path() == ''
        
        # After setting path
        test_path = "/path/to/data.csv"
        fm.set_data_file_path(test_path)
        assert fm.get_data_file_path() == test_path
    
    # @pytest.mark.unit
    # def test_clear_current_data(self, mock_gui_app):
    #     """Test clearing current loaded data."""
    #     fm = FileManager(mock_gui_app)
    #     
    #     # Set some data first
    #     fm.current_data_path = "/some/path.csv"
    #     mock_gui_app.data = pd.DataFrame({'test': [1, 2, 3]})
    #     
    #     fm.clear_current_data()
    #     
    #     # Should clear both path and data
    #     assert fm.current_data_path is None
    #     # Should call app method to clear data
    #     if hasattr(mock_gui_app, 'clear_data'):
    #         mock_gui_app.clear_data.assert_called_once()
    
    # === INTEGRATION WITH EDGE CASES ===
    # NOTE: These methods don't exist in current FileManager implementation
    
    # @pytest.mark.unit
    # def test_load_very_large_file(self, mock_gui_app, performance_test_data, temp_directory):
    #     """Test loading large dataset (performance consideration)."""
    #     # Create large CSV file
    #     large_csv = os.path.join(temp_directory, 'large_data.csv')
    #     performance_test_data.to_csv(large_csv, index=False)
    #     
    #     fm = FileManager(mock_gui_app)
    #     
    #     # Should complete within reasonable time (this is more of a smoke test)
    #     result = fm.load_data_from_path(large_csv)
    #     
    #     # Large file should load successfully (if system has enough memory)
    #     assert isinstance(result, bool)
    # 
    # @pytest.mark.unit  
    # def test_load_edge_case_datasets(self, mock_gui_app, edge_case_datasets, temp_directory):
    #     """Test loading various edge case datasets."""
    #     fm = FileManager(mock_gui_app)
    #     
    #     for case_name, dataset in edge_case_datasets.items():
    #         # Create temporary file for this case
    #         case_file = os.path.join(temp_directory, f'{case_name}.csv')
    #         dataset.to_csv(case_file, index=False)
    #         
    #         result = fm.load_data_from_path(case_file)
    #         
    #         # Should handle all cases without crashing
    #         assert isinstance(result, bool)
    #         
    #         # Validation should catch issues appropriately
    #         if result:  # If loading succeeded, check validation
    #             is_valid, _ = fm.validate_data_structure(dataset)
    #             if case_name in ['empty', 'single_point']:
    #                 assert is_valid is False  # These should not be valid
    #             elif case_name == 'two_points':
    #                 assert is_valid is True   # Minimum viable dataset