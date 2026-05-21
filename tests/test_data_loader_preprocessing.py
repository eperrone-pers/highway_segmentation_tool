"""
Unit tests for data_loader preprocessing integration functions.

Tests cover:
- apply_preprocessing_phase() helper function
- process_route_with_preprocessing() orchestration function
- Integration with preprocessing framework
- Parameter validation and error handling
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, call
from typing import List

from data_loader import (
    apply_preprocessing_phase,
    process_route_with_preprocessing,
    RouteAnalysis
)
from config import PreprocessingRunConfig
from preprocessing.base import PreprocessingResult


class TestApplyPreprocessingPhase:
    """Test the apply_preprocessing_phase helper function."""
    
    @pytest.fixture
    def mock_route_analysis(self):
        """Create a mock RouteAnalysis for testing."""
        data = pd.DataFrame({
            'Milepoint': [0.0, 1.0, 2.0, 3.0, 4.0],
            'IRI': [100.0, 110.0, 115.0, 108.0, 112.0]
        })
        
        route_analysis = RouteAnalysis(
            route_id="TEST_ROUTE",
            route_data=data,
            gap_segments=[],
            mandatory_breakpoints=set(),
            valid_x_values=data['Milepoint'].tolist(),
            data_range={
                'x_min': 0.0, 'x_max': 4.0,
                'y_min': 100.0, 'y_max': 115.0
            },
            route_stats={'total_points': 5},
            must_break_columns_used=[],
            attribute_breakpoints=set(),
            attribute_break_events=[]
        )
        
        return route_analysis
    
    def test_no_preprocessing_returns_unchanged(self, mock_route_analysis):
        """Test that None method_key returns original route analysis."""
        result_analysis, result = apply_preprocessing_phase(
            mock_route_analysis,
            method_key=None,
            parameters={},
            x_column='Milepoint',
            y_column='IRI'
        )
        
        # Should return original unchanged
        assert result_analysis is mock_route_analysis
        assert result is None
    
    def test_empty_method_key_returns_unchanged(self, mock_route_analysis):
        """Test that empty string method_key returns original route analysis."""
        result_analysis, result = apply_preprocessing_phase(
            mock_route_analysis,
            method_key="",
            parameters={},
            x_column='Milepoint',
            y_column='IRI'
        )
        
        # Should return original unchanged
        assert result_analysis is mock_route_analysis
        assert result is None
    
    def test_valid_preprocessing_method(self, mock_route_analysis):
        """Test applying valid preprocessing method (Tukey Fences)."""
        result_analysis, result = apply_preprocessing_phase(
            mock_route_analysis,
            method_key="tukey_fences",
            parameters={'k_factor': 1.5, 'action': 'remove'},
            x_column='Milepoint',
            y_column='IRI'
        )
        
        # Should return PreprocessingResult
        assert isinstance(result, PreprocessingResult)
        assert isinstance(result_analysis, RouteAnalysis)
        assert result.preprocessing_metadata is not None
        assert result.modification_log is not None
    
    def test_parameter_defaults_applied(self, mock_route_analysis):
        """Test that default parameters are applied when not provided."""
        # Call without explicit parameters
        result_analysis, result = apply_preprocessing_phase(
            mock_route_analysis,
            method_key="tukey_fences",
            parameters={},  # Empty - should use defaults
            x_column='Milepoint',
            y_column='IRI'
        )
        
        # Should succeed with defaults
        assert isinstance(result, PreprocessingResult)
        assert result.preprocessing_metadata['k_factor'] == 1.5  # Default
        assert result.preprocessing_metadata['action'] == 'remove'  # Default
    
    def test_parameter_validation_error(self, mock_route_analysis):
        """Test that invalid parameters raise ValueError."""
        with pytest.raises(ValueError, match="Parameter validation failed"):
            apply_preprocessing_phase(
                mock_route_analysis,
                method_key="tukey_fences",
                parameters={'k_factor': 999.0},  # Out of valid range (0.5-5.0)
                x_column='Milepoint',
                y_column='IRI'
            )
    
    def test_log_callback_invoked(self, mock_route_analysis):
        """Test that log_callback is called when provided."""
        log_messages = []
        
        def log_callback(msg):
            log_messages.append(msg)
        
        apply_preprocessing_phase(
            mock_route_analysis,
            method_key="tukey_fences",
            parameters={'k_factor': 1.5, 'action': 'remove'},
            x_column='Milepoint',
            y_column='IRI',
            log_callback=log_callback
        )
        
        # Should have logged method name
        assert len(log_messages) > 0
        assert any("Tukey Fences" in msg for msg in log_messages)
    
    def test_invalid_method_key_raises_error(self, mock_route_analysis):
        """Test that invalid method_key raises appropriate error."""
        with pytest.raises(ValueError, match="Unknown preprocessing method key"):
            apply_preprocessing_phase(
                mock_route_analysis,
                method_key="nonexistent_method",
                parameters={},
                x_column='Milepoint',
                y_column='IRI'
            )


class TestProcessRouteWithPreprocessing:
    """Test the process_route_with_preprocessing orchestration function."""
    
    @pytest.fixture
    def sample_dataframe(self):
        """Create sample route data DataFrame."""
        return pd.DataFrame({
            'Milepoint': [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
            'IRI': [100.0, 105.0, 110.0, 108.0, 112.0, 107.0, 110.0]
        })
    
    @pytest.fixture
    def no_preprocessing_config(self):
        """Create empty preprocessing configuration."""
        return PreprocessingRunConfig(
            pre_gap_method=None,
            pre_gap_parameters={},
            primary_method=None,
            primary_parameters={},
            secondary_method=None,
            secondary_parameters={},
            enabled=False
        )
    
    @pytest.fixture
    def primary_only_config(self):
        """Create config with only primary preprocessing."""
        return PreprocessingRunConfig(
            pre_gap_method=None,
            pre_gap_parameters={},
            primary_method="tukey_fences",
            primary_parameters={'k_factor': 1.5, 'action': 'remove'},
            secondary_method=None,
            secondary_parameters={},
            enabled=True
        )
    
    @pytest.fixture
    def full_config(self):
        """Create config with both primary and secondary preprocessing."""
        return PreprocessingRunConfig(
            pre_gap_method=None,
            pre_gap_parameters={},
            primary_method="tukey_fences",
            primary_parameters={'k_factor': 1.5, 'action': 'cap'},
            secondary_method="tukey_fences",
            secondary_parameters={'k_factor': 2.0, 'action': 'interpolate'},
            enabled=True
        )
    
    def test_no_preprocessing_returns_route_analysis(self, sample_dataframe, no_preprocessing_config):
        """Test that no preprocessing returns standard route analysis."""
        route_analysis, preprocess_results = process_route_with_preprocessing(
            sample_dataframe,
            'Milepoint',
            'IRI',
            'TEST_ROUTE',
            gap_threshold=0.6,
            preprocessing_config=no_preprocessing_config
        )
        
        # Should return route analysis with no preprocessing results
        assert isinstance(route_analysis, RouteAnalysis)
        assert len(preprocess_results) == 0
        assert route_analysis.route_id == 'TEST_ROUTE'
    
    def test_primary_preprocessing_only(self, sample_dataframe, primary_only_config):
        """Test with only primary preprocessing configured."""
        route_analysis, preprocess_results = process_route_with_preprocessing(
            sample_dataframe,
            'Milepoint',
            'IRI',
            'TEST_ROUTE',
            gap_threshold=0.6,
            preprocessing_config=primary_only_config
        )
        
        # Should return route analysis with one preprocessing result
        assert isinstance(route_analysis, RouteAnalysis)
        assert len(preprocess_results) == 1
        assert isinstance(preprocess_results[0], PreprocessingResult)
        assert preprocess_results[0].preprocessing_metadata['method_key'] == 'tukey_fences'
    
    def test_full_preprocessing_pipeline(self, sample_dataframe, full_config):
        """Test with both primary and secondary preprocessing."""
        route_analysis, preprocess_results = process_route_with_preprocessing(
            sample_dataframe,
            'Milepoint',
            'IRI',
            'TEST_ROUTE',
            gap_threshold=0.6,
            preprocessing_config=full_config
        )
        
        # Should return route analysis with two preprocessing results
        assert isinstance(route_analysis, RouteAnalysis)
        assert len(preprocess_results) == 2
        
        # First should be primary
        assert preprocess_results[0].preprocessing_metadata['method_key'] == 'tukey_fences'
        assert preprocess_results[0].preprocessing_metadata['action'] == 'cap'
        
        # Second should be secondary
        assert preprocess_results[1].preprocessing_metadata['method_key'] == 'tukey_fences'
        assert preprocess_results[1].preprocessing_metadata['action'] == 'interpolate'
    
    def test_with_first_attribute_columns(self, sample_dataframe, no_preprocessing_config):
        """Test that first_attribute_columns are passed to gap analysis."""
        # Add an attribute column
        sample_dataframe['District'] = ['A', 'A', 'B', 'B', 'B', 'C', 'C']
        
        route_analysis, preprocess_results = process_route_with_preprocessing(
            sample_dataframe,
            'Milepoint',
            'IRI',
            'TEST_ROUTE',
            gap_threshold=0.6,
            preprocessing_config=no_preprocessing_config,
            first_attribute_columns=['District']
        )
        
        # Should have attribute break metadata
        assert isinstance(route_analysis, RouteAnalysis)
        assert route_analysis.must_break_columns_used is not None
    
    def test_log_callback_integration(self, sample_dataframe, primary_only_config):
        """Test that log_callback works throughout the pipeline."""
        log_messages = []
        
        def log_callback(msg):
            log_messages.append(msg)
        
        route_analysis, preprocess_results = process_route_with_preprocessing(
            sample_dataframe,
            'Milepoint',
            'IRI',
            'TEST_ROUTE',
            gap_threshold=0.6,
            preprocessing_config=primary_only_config,
            log_callback=log_callback
        )
        
        # Should have logged preprocessing messages
        assert len(log_messages) > 0
        assert any("Tukey Fences" in msg for msg in log_messages)
    
    def test_sequential_preprocessing_data_flow(self, sample_dataframe, full_config):
        """Test that secondary preprocessing operates on primary-preprocessed data."""
        # Add outliers to trigger preprocessing
        sample_dataframe.loc[0, 'IRI'] = 10.0  # Low outlier
        sample_dataframe.loc[6, 'IRI'] = 500.0  # High outlier
        
        route_analysis, preprocess_results = process_route_with_preprocessing(
            sample_dataframe,
            'Milepoint',
            'IRI',
            'TEST_ROUTE',
            gap_threshold=0.6,
            preprocessing_config=full_config
        )
        
        # Both preprocessing phases should have been applied
        assert len(preprocess_results) == 2
        
        # Secondary should operate on data modified by primary
        # (We can't easily verify the exact data flow here without inspecting internals,
        # but we can verify both ran successfully)
        assert preprocess_results[0].preprocessing_metadata is not None
        assert preprocess_results[1].preprocessing_metadata is not None


class TestIntegrationScenarios:
    """Integration tests for complete preprocessing workflows."""
    
    def test_realistic_workflow_with_gaps_and_outliers(self):
        """Test a realistic scenario with gaps and outliers."""
        # Create data with a gap and outliers
        data = pd.DataFrame({
            'Mile': [0.0, 1.0, 2.0, 5.0, 6.0, 7.0, 8.0],  # Gap between 2.0 and 5.0
            'Value': [100.0, 5.0, 110.0, 108.0, 112.0, 500.0, 107.0]  # Outliers at indices 1, 5
        })
        
        config = PreprocessingRunConfig(
            pre_gap_method=None,
            pre_gap_parameters={},
            primary_method="tukey_fences",
            primary_parameters={'k_factor': 1.5, 'action': 'remove'},
            secondary_method=None,
            secondary_parameters={},
            enabled=True
        )
        
        route_analysis, preprocess_results = process_route_with_preprocessing(
            data,
            'Mile',
            'Value',
            'REALISTIC_TEST',
            gap_threshold=2.0,
            preprocessing_config=config
        )
        
        # Should detect gap
        assert len(route_analysis.gap_segments) > 0
        
        # Should have preprocessing result
        assert len(preprocess_results) == 1
        
        # Should have removed outliers
        assert preprocess_results[0].preprocessing_metadata['outliers_detected'] > 0
    
    def test_error_propagation(self):
        """Test that errors from preprocessing are properly propagated."""
        data = pd.DataFrame({
            'X': [0.0, 0.5, 1.0, 1.5, 2.0],  # No gaps with threshold of 0.6
            'Y': [100.0, 105.0, 110.0, 108.0, 105.0]
        })
        
        config = PreprocessingRunConfig(
            pre_gap_method=None,
            pre_gap_parameters={},
            primary_method="tukey_fences",
            primary_parameters={'k_factor': 999.0},  # Invalid parameter (out of 0.5-5.0 range)
            secondary_method=None,
            secondary_parameters={},
            enabled=True
        )
        
        with pytest.raises(ValueError, match="Parameter validation failed"):
            process_route_with_preprocessing(
                data,
                'X',
                'Y',
                'ERROR_TEST',
                gap_threshold=0.6,
                preprocessing_config=config
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
