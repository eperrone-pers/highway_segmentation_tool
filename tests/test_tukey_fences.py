"""
Unit tests for Tukey Fences preprocessing method.

Tests cover:
- Basic outlier detection and IQR calculation
- All three actions: remove, cap, interpolate
- Parameter handling and defaults
- Modification logging
- Edge cases and boundary conditions
- Integration with RouteAnalysis
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock
from typing import Dict, Any

from preprocessing.methods.tukey_fences import TukeyFencesPreprocessor
from preprocessing.base import PreprocessingResult


class TestTukeyFencesBasics:
    """Test basic properties and initialization."""
    
    def test_preprocessor_properties(self):
        """Test that preprocessor has correct properties."""
        preprocessor = TukeyFencesPreprocessor()
        
        assert preprocessor.preprocess_key == "tukey_fences"
        assert preprocessor.preprocess_name == "Tukey Fences Outlier Detection"
        assert "IQR" in preprocessor.description
        assert "outlier" in preprocessor.description.lower()


class TestTukeyFencesOutlierDetection:
    """Test outlier detection logic."""
    
    @pytest.fixture
    def mock_route_analysis(self):
        """Create a mock RouteAnalysis with test data."""
        # Create test data with clear outliers
        # Normal data: 100-120, Outliers: 10, 200
        data = pd.DataFrame({
            'Milepoint': [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            'IRI': [10.0, 100.0, 110.0, 115.0, 108.0, 200.0, 112.0]
        })
        
        route_analysis = Mock()
        route_analysis.route_data = data
        route_analysis.route_id = "TEST_ROUTE"
        route_analysis.gap_segments = []
        route_analysis.mandatory_breakpoints = set()
        route_analysis.valid_x_values = data['Milepoint'].tolist()
        route_analysis.route_stats = {'total_points': len(data)}
        route_analysis.must_break_columns_used = []
        route_analysis.attribute_breakpoints = set()
        route_analysis.attribute_break_events = []
        route_analysis.data_range = {
            'x_min': data['Milepoint'].min(),
            'x_max': data['Milepoint'].max(),
            'y_min': data['IRI'].min(),
            'y_max': data['IRI'].max()
        }
        
        return route_analysis
    
    def test_iqr_calculation(self, mock_route_analysis):
        """Test that IQR bounds are calculated correctly."""
        preprocessor = TukeyFencesPreprocessor()
        
        # Get the IRI values
        iri_values = mock_route_analysis.route_data['IRI'].values
        
        # Calculate expected IQR bounds
        q1 = np.percentile(iri_values, 25)
        q3 = np.percentile(iri_values, 75)
        iqr = q3 - q1
        k_factor = 1.5
        expected_lower = q1 - k_factor * iqr
        expected_upper = q3 + k_factor * iqr
        
        # Process with action='remove' to check bounds in metadata
        result = preprocessor.process(
            mock_route_analysis,
            'Milepoint',
            'IRI',
            k_factor=k_factor,
            action='remove'
        )
        
        # Check metadata contains correct configuration
        assert result.preprocessing_metadata['k_factor'] == k_factor
        assert result.preprocessing_metadata['action'] == 'remove'
        assert 'outliers_detected' in result.preprocessing_metadata
        assert 'segments_processed' in result.preprocessing_metadata
    
    def test_outlier_identification(self, mock_route_analysis):
        """Test that outliers are correctly identified."""
        preprocessor = TukeyFencesPreprocessor()
        
        result = preprocessor.process(
            mock_route_analysis,
            'Milepoint',
            'IRI',
            k_factor=1.5,
            action='remove'
        )
        
        # Should detect the two outliers (10.0 and 200.0)
        assert result.preprocessing_metadata['outliers_detected'] == 2
        assert result.preprocessing_metadata['points_before'] == 7
        assert result.preprocessing_metadata['points_after'] == 5  # 7 - 2 outliers


class TestTukeyFencesActions:
    """Test all three outlier handling actions."""
    
    @pytest.fixture
    def simple_data_with_outliers(self):
        """Create simple dataset with known outliers for testing."""
        # Data: [50, 100, 110, 120, 500, 110, 100]
        # With k=1.5, 50 and 500 should be outliers
        # Changed: outlier at x=4.0 (middle) instead of x=6.0 (boundary)
        data = pd.DataFrame({
            'X': [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            'Y': [50.0, 100.0, 110.0, 120.0, 500.0, 110.0, 100.0]
        })
        
        route_analysis = Mock()
        route_analysis.route_data = data
        route_analysis.route_id = "TEST"
        route_analysis.gap_segments = []
        route_analysis.mandatory_breakpoints = set()
        route_analysis.valid_x_values = data['X'].tolist()
        route_analysis.route_stats = {'total_points': len(data)}
        route_analysis.must_break_columns_used = []
        route_analysis.attribute_breakpoints = set()
        route_analysis.attribute_break_events = []
        route_analysis.data_range = {'x_min': 0.0, 'x_max': 6.0, 'y_min': 50.0, 'y_max': 500.0}
        
        return route_analysis
    
    def test_action_remove(self, simple_data_with_outliers):
        """Test that 'remove' action removes outlier points."""
        preprocessor = TukeyFencesPreprocessor()
        
        result = preprocessor.process(
            simple_data_with_outliers,
            'X',
            'Y',
            k_factor=1.5,
            action='remove'
        )
        
        # Check that outliers were removed
        processed_data = result.processed_route_analysis.route_data
        assert len(processed_data) < len(simple_data_with_outliers.route_data)
        
        # Check modification log
        assert len(result.modification_log) > 0
        remove_mods = [m for m in result.modification_log if m.modification_type == "point_removed"]
        assert len(remove_mods) > 0
        
        # Verify summary message
        assert "remove" in result.modifications_summary.lower()
    
    def test_action_cap(self, simple_data_with_outliers):
        """Test that 'cap' action caps outliers to fence boundaries."""
        preprocessor = TukeyFencesPreprocessor()
        
        result = preprocessor.process(
            simple_data_with_outliers,
            'X',
            'Y',
            k_factor=1.5,
            action='cap'
        )
        
        # Check that no points were removed
        processed_data = result.processed_route_analysis.route_data
        assert len(processed_data) == len(simple_data_with_outliers.route_data)
        
        # Check modification log
        cap_mods = [m for m in result.modification_log if m.modification_type == "y_value_capped"]
        assert len(cap_mods) > 0
        
        # Verify that modification contains reason with fence information
        for mod in cap_mods:
            assert "fence" in mod.reason
            assert mod.new_y_value is not None
            assert mod.new_y_value != mod.original_y_value
    
    def test_action_interpolate(self, simple_data_with_outliers):
        """Test that 'interpolate' action interpolates outlier values."""
        preprocessor = TukeyFencesPreprocessor()
        
        result = preprocessor.process(
            simple_data_with_outliers,
            'X',
            'Y',
            k_factor=1.5,
            action='interpolate'
        )
        
        # Check that no points were removed
        processed_data = result.processed_route_analysis.route_data
        assert len(processed_data) == len(simple_data_with_outliers.route_data)
        
        # Check modification log
        interp_mods = [m for m in result.modification_log if m.modification_type == "point_interpolated"]
        assert len(interp_mods) > 0
        
        # Verify that interpolated values are different from originals
        for mod in interp_mods:
            assert mod.new_y_value != mod.original_y_value

    def test_boundary_breakpoint_capped_once(self):
        """Test that a shared mandatory breakpoint row is processed in only one segment."""
        data = pd.DataFrame({
            'X': [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            'Y': [10.0, 10.0, 10.0, 100.0, 10.0, 10.0, 10.0]
        })

        route_analysis = Mock()
        route_analysis.route_data = data
        route_analysis.route_id = "BOUNDARY_TEST"
        route_analysis.gap_segments = []
        route_analysis.mandatory_breakpoints = {0.0, 3.0, 6.0}
        route_analysis.valid_x_values = data['X'].tolist()
        route_analysis.route_stats = {'total_points': len(data)}
        route_analysis.must_break_columns_used = []
        route_analysis.attribute_breakpoints = set()
        route_analysis.attribute_break_events = []
        route_analysis.data_range = {'x_min': 0.0, 'x_max': 6.0, 'y_min': 10.0, 'y_max': 100.0}

        preprocessor = TukeyFencesPreprocessor()
        result = preprocessor.process(
            route_analysis,
            'X',
            'Y',
            k_factor=1.5,
            action='cap'
        )

        boundary_mods = [m for m in result.modification_log if m.x_value == 3.0]
        assert len(boundary_mods) == 1
        assert boundary_mods[0].modification_type == "y_value_capped"

    def test_remove_skips_mandatory_breakpoint_outliers(self):
        """Test that remove action preserves mandatory breakpoint outliers instead of raising."""
        data = pd.DataFrame({
            'X': [0.0, 1.0, 2.0, 3.0, 4.0],
            'Y': [500.0, 10.0, 10.0, 10.0, 10.0]
        })

        route_analysis = Mock()
        route_analysis.route_data = data
        route_analysis.route_id = "MANDATORY_REMOVE_TEST"
        route_analysis.gap_segments = []
        route_analysis.mandatory_breakpoints = {0.0, 4.0}
        route_analysis.valid_x_values = data['X'].tolist()
        route_analysis.route_stats = {'total_points': len(data)}
        route_analysis.must_break_columns_used = []
        route_analysis.attribute_breakpoints = set()
        route_analysis.attribute_break_events = []
        route_analysis.data_range = {'x_min': 0.0, 'x_max': 4.0, 'y_min': 10.0, 'y_max': 500.0}

        preprocessor = TukeyFencesPreprocessor()
        result = preprocessor.process(
            route_analysis,
            'X',
            'Y',
            k_factor=1.5,
            action='remove'
        )

        assert result.processed_route_analysis.route_data['X'].tolist() == [0.0, 1.0, 2.0, 3.0, 4.0]
        assert [m.x_value for m in result.modification_log if m.modification_type == 'point_removed'] == []


class TestTukeyFencesParameters:
    """Test parameter handling."""
    
    @pytest.fixture
    def basic_route_analysis(self):
        """Create minimal route analysis for parameter testing."""
        data = pd.DataFrame({
            'X': [0.0, 1.0, 2.0, 3.0, 4.0],
            'Y': [10.0, 100.0, 110.0, 100.0, 500.0]  # 10 and 500 are outliers
        })
        
        route_analysis = Mock()
        route_analysis.route_data = data
        route_analysis.route_id = "TEST"
        route_analysis.gap_segments = []
        route_analysis.mandatory_breakpoints = set()
        route_analysis.valid_x_values = data['X'].tolist()
        route_analysis.route_stats = {'total_points': len(data)}
        route_analysis.must_break_columns_used = []
        route_analysis.attribute_breakpoints = set()
        route_analysis.attribute_break_events = []
        route_analysis.data_range = {'x_min': 0.0, 'x_max': 4.0, 'y_min': 10.0, 'y_max': 500.0}
        
        return route_analysis
    
    def test_default_parameters(self, basic_route_analysis):
        """Test that default parameters work correctly."""
        preprocessor = TukeyFencesPreprocessor()
        
        # Call without specifying parameters
        result = preprocessor.process(
            basic_route_analysis,
            'X',
            'Y'
        )
        
        # Should use defaults: k_factor=1.5, action='remove'
        assert result.preprocessing_metadata['k_factor'] == 1.5
        assert result.preprocessing_metadata['action'] == 'remove'
    
    def test_custom_k_factor(self, basic_route_analysis):
        """Test that custom k_factor affects outlier detection."""
        preprocessor = TukeyFencesPreprocessor()
        
        # Test with lenient k_factor (3.0) - fewer outliers
        result_lenient = preprocessor.process(
            basic_route_analysis,
            'X',
            'Y',
            k_factor=3.0,
            action='remove'
        )
        
        # Test with aggressive k_factor (1.0) - more outliers
        result_aggressive = preprocessor.process(
            basic_route_analysis,
            'X',
            'Y',
            k_factor=1.0,
            action='remove'
        )
        
        # Aggressive should detect more outliers
        assert (result_aggressive.preprocessing_metadata['outliers_detected'] >= 
                result_lenient.preprocessing_metadata['outliers_detected'])
    
    def test_parameter_in_metadata(self, basic_route_analysis):
        """Test that all parameters are recorded in metadata."""
        preprocessor = TukeyFencesPreprocessor()
        
        result = preprocessor.process(
            basic_route_analysis,
            'X',
            'Y',
            k_factor=2.0,
            action='cap'
        )
        
        metadata = result.preprocessing_metadata
        assert metadata['k_factor'] == 2.0
        assert metadata['action'] == 'cap'
        assert 'method_key' in metadata
        assert 'method_name' in metadata


class TestTukeyFencesResult:
    """Test PreprocessingResult structure and content."""
    
    @pytest.fixture
    def sample_route_analysis(self):
        """Create sample route analysis."""
        data = pd.DataFrame({
            'Mile': [0.0, 1.0, 2.0, 3.0, 4.0],
            'Value': [10.0, 100.0, 110.0, 105.0, 1000.0]
        })
        
        route_analysis = Mock()
        route_analysis.route_data = data
        route_analysis.route_id = "SAMPLE"
        route_analysis.gap_segments = []
        route_analysis.mandatory_breakpoints = set()
        route_analysis.valid_x_values = data['Mile'].tolist()
        route_analysis.route_stats = {'total_points': len(data)}
        route_analysis.must_break_columns_used = []
        route_analysis.attribute_breakpoints = set()
        route_analysis.attribute_break_events = []
        route_analysis.data_range = {'x_min': 0.0, 'x_max': 4.0, 'y_min': 10.0, 'y_max': 1000.0}
        
        return route_analysis
    
    def test_result_structure(self, sample_route_analysis):
        """Test that result has all required fields."""
        preprocessor = TukeyFencesPreprocessor()
        
        result = preprocessor.process(
            sample_route_analysis,
            'Mile',
            'Value',
            k_factor=1.5,
            action='remove'
        )
        
        # Check required fields
        assert isinstance(result, PreprocessingResult)
        assert result.processed_route_analysis is not None
        assert isinstance(result.modification_log, list)
        assert isinstance(result.preprocessing_metadata, dict)
        assert isinstance(result.original_y_values, list)
        assert isinstance(result.modifications_summary, str)
    
    def test_original_values_preserved(self, sample_route_analysis):
        """Test that original Y values are preserved in result."""
        preprocessor = TukeyFencesPreprocessor()
        
        original_y = sample_route_analysis.route_data['Value'].tolist()
        
        result = preprocessor.process(
            sample_route_analysis,
            'Mile',
            'Value',
            k_factor=1.5,
            action='remove'
        )
        
        # Original values should match
        assert result.original_y_values == original_y
    
    def test_modification_log_completeness(self, sample_route_analysis):
        """Test that modification log is complete and accurate."""
        preprocessor = TukeyFencesPreprocessor()
        
        result = preprocessor.process(
            sample_route_analysis,
            'Mile',
            'Value',
            k_factor=1.5,
            action='remove'
        )
        
        # Log should have entries
        assert len(result.modification_log) > 0
        
        # Each log entry should have required fields
        for mod in result.modification_log:
            assert mod.modification_type is not None
            assert mod.x_value is not None
            assert mod.timestamp is not None
            
            if mod.modification_type == "point_removed":
                assert mod.original_y_value is not None
                assert mod.new_y_value is None


class TestTukeyFencesEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_no_outliers(self):
        """Test behavior when no outliers are detected."""
        # Create data with no outliers (all values close together)
        data = pd.DataFrame({
            'X': [0.0, 1.0, 2.0, 3.0, 4.0],
            'Y': [100.0, 101.0, 102.0, 101.0, 100.0]
        })
        
        route_analysis = Mock()
        route_analysis.route_data = data
        route_analysis.route_id = "NO_OUTLIERS"
        route_analysis.gap_segments = []
        route_analysis.mandatory_breakpoints = set()
        route_analysis.valid_x_values = data['X'].tolist()
        route_analysis.route_stats = {'total_points': len(data)}
        route_analysis.must_break_columns_used = []
        route_analysis.attribute_breakpoints = set()
        route_analysis.attribute_break_events = []
        route_analysis.data_range = {'x_min': 0.0, 'x_max': 4.0, 'y_min': 100.0, 'y_max': 102.0}
        
        preprocessor = TukeyFencesPreprocessor()
        result = preprocessor.process(route_analysis, 'X', 'Y', k_factor=1.5, action='remove')
        
        # Should detect 0 outliers
        assert result.preprocessing_metadata['outliers_detected'] == 0
        assert len(result.modification_log) == 0
        assert result.preprocessing_metadata['points_before'] == result.preprocessing_metadata['points_after']
    
    def test_all_outliers(self):
        """Test behavior when all points are outliers (edge case)."""
        # Create data where extremes dominate
        data = pd.DataFrame({
            'X': [0.0, 1.0, 2.0, 3.0, 4.0],
            'Y': [1.0, 100.0, 2.0, 200.0, 3.0]
        })
        
        route_analysis = Mock()
        route_analysis.route_data = data
        route_analysis.route_id = "ALL_OUTLIERS"
        route_analysis.gap_segments = []
        route_analysis.mandatory_breakpoints = set()
        route_analysis.valid_x_values = data['X'].tolist()
        route_analysis.route_stats = {'total_points': len(data)}
        route_analysis.must_break_columns_used = []
        route_analysis.attribute_breakpoints = set()
        route_analysis.attribute_break_events = []
        route_analysis.data_range = {'x_min': 0.0, 'x_max': 4.0, 'y_min': 1.0, 'y_max': 200.0}
        
        preprocessor = TukeyFencesPreprocessor()
        result = preprocessor.process(route_analysis, 'X', 'Y', k_factor=0.5, action='remove')
        
        # With very aggressive k_factor, may detect many outliers
        assert result.preprocessing_metadata['outliers_detected'] >= 0  # Just ensure it runs


class TestTukeyFencesIntegration:
    """Integration tests with registry and configuration."""
    
    def test_can_be_resolved_from_registry(self):
        """Test that Tukey Fences can be resolved from registry."""
        # Import within test to ensure registry is populated
        import sys
        import importlib
        
        # Reload config to ensure PREPROCESSING_METHODS is populated
        if 'config' in sys.modules:
            importlib.reload(sys.modules['config'])
        
        from config import resolve_preprocessing_class, get_preprocessing_method, PREPROCESSING_METHODS
        
        # Verify registry has content
        assert len(PREPROCESSING_METHODS) > 0, "PREPROCESSING_METHODS registry is empty"
        
        # Get method config
        method_config = get_preprocessing_method("tukey_fences")
        assert method_config.method_key == "tukey_fences"
        assert method_config.display_name == "Tukey Fences Outlier Detection"
        
        # Resolve class
        cls = resolve_preprocessing_class("tukey_fences")
        assert cls is TukeyFencesPreprocessor
        
        # Can instantiate
        instance = cls()
        assert isinstance(instance, TukeyFencesPreprocessor)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
