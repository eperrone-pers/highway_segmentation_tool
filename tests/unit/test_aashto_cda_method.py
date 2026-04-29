#!/usr/bin/env python3
"""
Unit tests for AASHTO Enhanced Cumulative Difference Approach (CDA) method.

Tests the core AashtoCdaMethod class implementation including:
- Basic algorithm functionality with controlled data
- Parameter validation and error handling  
- RouteAnalysis integration and segmented processing architecture
- Statistical change point detection accuracy
- Results format compliance with framework standards

CRITICAL PURPOSE: Ensure AASHTO CDA method correctly implements the translated
MATLAB algorithm and integrates properly with the RouteAnalysis framework.
"""

import pytest
import sys
import os
import numpy as np
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
import tempfile

# Add src to path for imports
current_dir = os.path.dirname(__file__)
tests_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(tests_dir)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from analysis.methods.aashto_cda import AashtoCdaMethod, aashto_cda, find_change_point
    from analysis.base import AnalysisResult
    from data_loader import RouteAnalysis, analyze_route_gaps
except ImportError as e:
    pytest.skip(f"Required AASHTO CDA modules not available: {e}", allow_module_level=True)


class TestAashtoCdaAlgorithm:
    """Test the core AASHTO CDA algorithm functions."""
    
    @pytest.fixture
    def simple_step_data(self):
        """Generate simple step function data for testing change point detection."""
        # Create data with clear change points
        n = 100
        x = np.arange(n)
        y = np.concatenate([
            np.full(30, 2.0) + np.random.normal(0, 0.1, 30),  # Level 1: 0-29
            np.full(40, 5.0) + np.random.normal(0, 0.1, 40),  # Level 2: 30-69  (change at 30)
            np.full(30, 1.0) + np.random.normal(0, 0.1, 30)   # Level 3: 70-99  (change at 70)
        ])
        return x, y
    
    def test_aashto_cda_detects_clear_change_points(self, simple_step_data):
        """Test that AASHTO CDA algorithm detects obvious change points."""
        x, y = simple_step_data
        
        # Run CDA with sensitive parameters
        uniform_sections, nodes, section_start, section_end, mu = aashto_cda(
            y, alpha=0.05, method=2, min_segment_datapoints=5, global_local=True
        )
        
        # Verify basic output structure
        assert len(nodes) >= 2, "Should detect at least start/end nodes"
        assert nodes[0] == 0, "First node should be at index 0"
        assert nodes[-1] == len(y) - 1, "Last node should be at final index"
        assert len(section_start) == len(section_end) == len(mu), "Section arrays should have same length"
        
        # Check if major change points were detected (allowing some tolerance)
        detected_changes = sorted(nodes[1:-1])  # Exclude start/end
        expected_changes = [30, 70]  # True change points
        
        # Should detect at least one of the major change points within reasonable tolerance
        found_changes = []
        for expected in expected_changes:
            for detected in detected_changes:
                if abs(detected - expected) <= 5:  # Allow 5-index tolerance
                    found_changes.append(expected)
                    break
        
        assert len(found_changes) >= 1, f"Should detect at least one major change point. Expected near {expected_changes}, got {detected_changes}"
    
    def test_aashto_cda_parameter_validation(self):
        """Test that AASHTO CDA validates parameters correctly."""
        test_data = np.random.normal(0, 1, 50)
        
        # Test valid parameters
        result = aashto_cda(test_data, alpha=0.05, method=2, min_segment_datapoints=3)
        assert len(result) == 5, "Should return 5 output arrays"
        
        # Test different methods
        for method in [1, 2, 3]:
            result = aashto_cda(test_data, alpha=0.05, method=method, min_segment_datapoints=3)
            assert len(result[1]) >= 2, f"Method {method} should return at least start/end nodes"
    
    def test_find_change_point_function(self):
        """Test the find_change_point helper function."""
        # Create simple test data
        np.random.seed(42)
        y = np.concatenate([np.full(25, 1.0), np.full(25, 3.0)])
        cy = np.cumsum(y)
        nodes = np.array([0, 49])  # Start and end
        x = np.arange(50)
        
        location, change_point = find_change_point(
            cy, nodes, x, sigma=0.5, alpha=0.05, min_segment_datapoints=5, global_local=True
        )
        
        assert isinstance(location, int), "Location should be integer index"
        assert change_point in [0, 1], "Change point indicator should be 0 or 1"
        
        if change_point == 1:
            assert 5 <= location <= 44, "Detected change point should respect min_segment_datapoints constraints"


class TestAashtoCdaMethod:
    """Test the AashtoCdaMethod class integration."""
    
    @pytest.fixture
    def sample_route_data(self):
        """Generate consistent test route data with known characteristics."""
        np.random.seed(42)  # Reproducible results
        milepoints = np.linspace(0, 10, 100)
        
        # Create step function with change points at miles 3 and 7
        values = np.concatenate([
            np.full(30, 2.0) + np.random.normal(0, 0.2, 30),  # 0-3 miles: level 2.0
            np.full(40, 5.0) + np.random.normal(0, 0.2, 40),  # 3-7 miles: level 5.0  
            np.full(30, 1.0) + np.random.normal(0, 0.2, 30)   # 7-10 miles: level 1.0
        ])
        
        df = pd.DataFrame({
            'milepoint': milepoints,
            'measurement': values
        })
        
        return df
    
    @pytest.fixture
    def route_analysis_object(self, sample_route_data):
        """Create RouteAnalysis object for testing segmented processing."""
        return analyze_route_gaps(
            sample_route_data, 
            x_column='milepoint',
            y_column='measurement',
            route_id='test_cda_route',
            gap_threshold=0.5,
        )
    
    @pytest.fixture
    def cda_method(self):
        """Create AashtoCdaMethod instance."""
        return AashtoCdaMethod()
    
    def test_aashto_cda_method_initialization(self, cda_method):
        """Test AashtoCdaMethod initializes correctly."""
        assert cda_method.method_name == "AASHTO CDA Statistical Analysis"
        assert cda_method.method_key == "aashto_cda"
        assert hasattr(cda_method, 'run_analysis')
    
    def test_run_analysis_with_route_analysis_object(self, cda_method, route_analysis_object):
        """Test run_analysis with RouteAnalysis object (primary use case)."""
        result = cda_method.run_analysis(
            data=route_analysis_object,
            route_id="test_cda_route",
            x_column='milepoint',
            y_column='measurement',
            gap_threshold=0.5,
            alpha=0.05,
            method=2,
            enable_diagnostic_output=False
        )
        
        # Verify result structure
        assert isinstance(result, AnalysisResult)
        assert result.method_name == "AASHTO CDA Statistical Analysis"
        assert result.method_key == "aashto_cda"
        assert result.route_id == "test_cda_route"
        
        # Verify solutions structure
        assert len(result.all_solutions) >= 1, "Should have at least one solution"
        solution = result.all_solutions[0]
        assert 'chromosome' in solution
        assert 'fitness' in solution
        assert 'num_segments' in solution
        assert 'avg_segment_length' in solution
        
        # Verify mandatory breakpoints are preserved
        assert isinstance(result.mandatory_breakpoints, list)
        assert len(result.mandatory_breakpoints) >= 2  # At least start/end
        
        # Verify input parameters were stored
        assert 'alpha' in result.input_parameters
        assert result.input_parameters['alpha'] == 0.05

    def test_run_analysis_uses_named_columns_not_order(self, cda_method):
        """Ensure run_analysis uses x_column/y_column names, not DataFrame column order."""
        np.random.seed(123)
        milepoints = np.linspace(0, 10, 100)
        measurement = np.concatenate([
            np.full(50, 1.0) + np.random.normal(0, 0.05, 50),
            np.full(50, 4.0) + np.random.normal(0, 0.05, 50),
        ])
        df = pd.DataFrame({
            'FY': [2025] * len(milepoints),
            'RDB': ['TestRoute'] * len(milepoints),
            'measurement': measurement,
            'milepoint': milepoints,
        })

        route_analysis = analyze_route_gaps(
            df,
            x_column='milepoint',
            y_column='measurement',
            route_id='test_cda_named_cols',
            gap_threshold=0.5,
        )

        result = cda_method.run_analysis(
            data=route_analysis,
            route_id='test_cda_named_cols',
            x_column='milepoint',
            y_column='measurement',
            gap_threshold=0.5,
            alpha=0.05,
            method=2,
            min_segment_datapoints=5,
            enable_diagnostic_output=False,
        )

        assert len(result.all_solutions) == 1
        chromosome = result.all_solutions[0].get('chromosome', [])
        assert chromosome, "Expected non-empty chromosome list"
        # At minimum, start/end breakpoints should match the x range.
        assert abs(chromosome[0] - float(milepoints.min())) < 1e-9
        assert abs(chromosome[-1] - float(milepoints.max())) < 1e-9
    
    def test_run_analysis_with_dataframe_fallback(self, cda_method, sample_route_data):
        """DataFrame inputs are no longer supported (RouteAnalysis required)."""
        with pytest.raises(TypeError):
            cda_method.run_analysis(
                data=sample_route_data,
                route_id="CDA_ANALYSIS",
                x_column='milepoint',
                y_column='measurement',
                gap_threshold=0.5,
                alpha=0.1,
                method=2,
            )
    
    def test_run_analysis_parameter_validation(self, cda_method, route_analysis_object):
        """Test parameter validation in run_analysis."""
        # Test invalid alpha
        result = cda_method.run_analysis(
            data=route_analysis_object,
            route_id="test_cda_route",
            x_column='milepoint',
            y_column='measurement',
            gap_threshold=0.5,
            alpha=0.6,  # Invalid: > 0.5
            method=2
        )
        # Should handle error gracefully
        assert isinstance(result, AnalysisResult)
        assert len(result.all_solutions) == 0  # No solutions due to error
        
        # Test invalid method
        result = cda_method.run_analysis(
            data=route_analysis_object,
            route_id="test_cda_route",
            x_column='milepoint',
            y_column='measurement',
            gap_threshold=0.5,
            alpha=0.05,
            method=5  # Invalid method
        )
        assert isinstance(result, AnalysisResult)
    
    def test_run_analysis_diagnostic_output(self, cda_method, route_analysis_object):
        """Test diagnostic output functionality."""
        result = cda_method.run_analysis(
            data=route_analysis_object,
            route_id="test_cda_route",
            x_column='milepoint',
            y_column='measurement',
            gap_threshold=0.5,
            alpha=0.05,
            method=2,
            enable_diagnostic_output=True
        )
        
        # Verify diagnostic information is included
        assert result.optimization_stats is not None
        assert 'algorithm' in result.optimization_stats
        assert 'architecture' in result.optimization_stats
        assert result.optimization_stats['architecture'] == 'segmented_processing'
        assert 'processing_summary' in result.optimization_stats
    
    def test_segmented_processing_architecture(self, cda_method, route_analysis_object):
        """Test that CDA properly processes segmentable sections."""
        # Run analysis with diagnostic output to verify segmented processing
        result = cda_method.run_analysis(
            data=route_analysis_object,
            route_id="test_cda_route",
            x_column='milepoint',
            y_column='measurement',
            gap_threshold=0.5,
            alpha=0.05,
            method=2,
            enable_diagnostic_output=True
        )
        
        # Verify segmented processing was used
        stats = result.optimization_stats
        assert 'processing_summary' in stats
        assert 'segmentable_sections_processed' in stats['processing_summary']
        
        # Should have processed at least one segmentable section
        sections_processed = stats['processing_summary']['segmentable_sections_processed']
        assert sections_processed >= 1
        
        # Verify mandatory breakpoints are respected
        mandatory_count = stats['processing_summary']['mandatory_breakpoints']
        assert mandatory_count >= 2  # Start and end at minimum
        
        # Final segments should include mandatory breakpoints
        solution = result.all_solutions[0]
        breakpoints = solution['chromosome']
        for mb in result.mandatory_breakpoints:
            assert mb in breakpoints, f"Mandatory breakpoint {mb} not found in final breakpoints"
    
    def test_different_statistical_methods(self, cda_method, route_analysis_object):
        """Test all three statistical error estimation methods."""
        methods_to_test = [1, 2, 3]  # MAD, StdDev Diff, StdDev Measurements
        
        for method in methods_to_test:
            result = cda_method.run_analysis(
                data=route_analysis_object,
                route_id="test_cda_route",
                x_column='milepoint',
                y_column='measurement',
                gap_threshold=0.5,
                alpha=0.05,
                method=method,
                min_segment_datapoints=5
            )
            
            assert isinstance(result, AnalysisResult), f"Method {method} should return valid result"
            assert len(result.all_solutions) >= 1, f"Method {method} should find at least one solution"
            assert result.input_parameters['method'] == method
    
    def test_min_segment_datapoints_constraint_compliance(self, cda_method, route_analysis_object):
        """Test that min_segment_datapoints constraints are respected (in data index space)."""
        min_segment_datapoints = 10

        result = cda_method.run_analysis(
            data=route_analysis_object,
            route_id="test_cda_route",
            x_column='milepoint',
            y_column='measurement',
            gap_threshold=0.5,
            alpha=0.05,
            method=2,
            min_segment_datapoints=min_segment_datapoints,
        )

        x_values = route_analysis_object.route_data['milepoint'].values
        solution = result.all_solutions[0]
        breakpoints = solution['chromosome']

        segment_point_counts = []
        for start, end in zip(breakpoints, breakpoints[1:]):
            start_idx = int(np.searchsorted(x_values, start, side='left'))
            end_idx = int(np.searchsorted(x_values, end, side='right') - 1)
            segment_point_counts.append(end_idx - start_idx + 1)

        too_small = [c for c in segment_point_counts if c < min_segment_datapoints]
        assert not too_small, f"Segments with too few datapoints (<{min_segment_datapoints}): {too_small}"


class TestAashtoCdaErrorHandling:
    """Test error handling and edge cases for AASHTO CDA method."""
    
    @pytest.fixture
    def cda_method(self):
        return AashtoCdaMethod()
    
    def test_empty_data_handling(self, cda_method):
        """Test handling of empty or invalid data."""
        empty_df = pd.DataFrame({'x': [], 'y': []})

        with pytest.raises(TypeError):
            cda_method.run_analysis(
                data=empty_df,
                route_id="empty",
                x_column='x',
                y_column='y',
                gap_threshold=0.5,
                alpha=0.05,
                method=2
            )
    
    def test_single_point_data(self, cda_method):
        """Test handling of data with only one point."""
        single_point_df = pd.DataFrame({'x': [0], 'y': [1.0]})

        with pytest.raises(TypeError):
            cda_method.run_analysis(
                data=single_point_df, 
                route_id="single_point",
                x_column='x',
                y_column='y',
                gap_threshold=0.5,
                alpha=0.05,
                method=2
            )
    
    def test_missing_columns_handling(self, cda_method):
        """Test handling of DataFrame with missing required columns."""
        bad_df = pd.DataFrame({'wrong': [1, 2, 3], 'columns': [4, 5, 6]})

        with pytest.raises(TypeError):
            cda_method.run_analysis(
                data=bad_df,
                route_id="missing_columns",
                x_column='x',
                y_column='y',
                gap_threshold=0.5,
                alpha=0.05,
                method=2
            )


if __name__ == "__main__":
    pytest.main([__file__])