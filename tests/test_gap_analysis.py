"""
Test suite for gap analysis functionality in data_loader.py

This test suite verifies:
1. Gap detection accuracy with known data
2. Adjacent gap merging behavior  
3. Endpoint validation (fatal error conditions)
4. Edge case handling
5. RouteAnalysis data structure integrity
"""

import pytest
import pandas as pd
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_loader import analyze_route_gaps, RouteAnalysis, _merge_adjacent_gaps, _validate_route_endpoints


class TestGapDetection:
    """Test core gap detection functionality."""
    
    def test_txdot_known_gaps(self):
        """Test gap detection with known gaps in txdot_data.csv."""
        # Load actual TXDOT data
        data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'txdot_data.csv')
        if not os.path.exists(data_path):
            pytest.skip("txdot_data.csv not available")
            
        df = pd.read_csv(data_path)
        analysis = analyze_route_gaps(
            df,
            "milepoint",
            "structural_strength_ind",
            "TXDOT_VALIDATION",
            gap_threshold=0.5,
        )
        
        # Expected gaps with 0.5-mile threshold (no merging needed)
        expected_gaps = [
            (198.104, 198.649),  # Gap 1: 0.545 miles
            (229.54, 230.242),   # Gap 2: 0.702 miles  
            (234.834, 236.594)   # Gap 3: 1.760 miles
        ]
        
        assert len(analysis.gap_segments) == 3, f"Expected 3 gaps, found {len(analysis.gap_segments)}"
        
        # Verify gap locations within tolerance
        tolerance = 0.05  # 0.05 mile tolerance for gap boundaries
        for i, (expected_start, expected_end) in enumerate(expected_gaps):
            actual_start, actual_end = analysis.gap_segments[i]
            assert abs(actual_start - expected_start) < tolerance, \
                f"Gap {i+1} start: expected {expected_start}, got {actual_start}"
            assert abs(actual_end - expected_end) < tolerance, \
                f"Gap {i+1} end: expected {expected_end}, got {actual_end}"
        
        # Verify that gap detection works correctly for consecutive datapoints
        # In this case, no gap merging occurs, so all points remain valid
        total_points = analysis.route_stats['total_points'] 
        valid_points = analysis.route_stats['valid_points']
        assert valid_points == total_points, "No gap merging should mean all points valid"
    
    def test_no_gaps_data(self):
        """Test with data that has no gaps."""
        # Create continuous data
        milepoints = [i * 0.05 for i in range(100)]  # 0.0 to 4.95 in 0.05 increments
        df = pd.DataFrame({
            'milepoint': milepoints,
            'structural_strength_ind': [1.0] * len(milepoints)
        })
        
        analysis = analyze_route_gaps(df, "milepoint", "structural_strength_ind", "NO_GAPS", gap_threshold=0.5)
        
        assert len(analysis.gap_segments) == 0, "Should detect no gaps in continuous data"
        assert len(analysis.valid_x_values) == len(milepoints), "All points should be valid"
        assert analysis.route_stats['valid_points'] == analysis.route_stats['total_points'], "No exclusions for continuous data"
        assert len(analysis.mandatory_breakpoints) == 2, "Only start/end should be mandatory"
    
    def test_single_gap_data(self):
        """Test with data containing a single clear gap."""
        milepoints = [0.0, 0.1, 0.2, 0.8, 0.9, 1.0]  # Gap between 0.2 and 0.8 (0.6 miles)
        df = pd.DataFrame({
            'milepoint': milepoints,
            'structural_strength_ind': [1.0] * len(milepoints)
        })
        
        analysis = analyze_route_gaps(df, "milepoint", "structural_strength_ind", "SINGLE_GAP", gap_threshold=0.5)
        
        assert len(analysis.gap_segments) == 1, "Should detect exactly one gap"
        gap_start, gap_end = analysis.gap_segments[0]
        assert gap_start == 0.2 and gap_end == 0.8, f"Gap should be 0.2 to 0.8, got {gap_start} to {gap_end}"
        
        # All original points remain valid (no merging in single gap case)
        assert len(analysis.valid_x_values) == len(milepoints), "All original points should be valid for single gap"
        assert analysis.route_stats['valid_points'] == analysis.route_stats['total_points'], "No exclusions for single gap"
    
    def test_multiple_consecutive_gaps(self):
        """Test multiple consecutive gaps that should be merged."""
        # Create data with multiple large consecutive gaps
        milepoints = [0.0, 0.1, 0.2, 1.0, 1.8, 2.5, 2.6]  # Multiple 0.6+ mile gaps
        df = pd.DataFrame({
            'milepoint': milepoints,
            'structural_strength_ind': [1.0] * len(milepoints)
        })
        
        analysis = analyze_route_gaps(df, "milepoint", "structural_strength_ind", "MULTIPLE_GAPS", gap_threshold=0.5)
        
        # Should detect gaps that get merged into single gap (0.2 -> 2.5)
        assert len(analysis.gap_segments) == 1, f"Should merge into 1 gap, got {len(analysis.gap_segments)}"
        gap_start, gap_end = analysis.gap_segments[0]
        assert gap_start == 0.2 and gap_end == 2.5, f"Merged gap should be 0.2->2.5, got {gap_start}->{gap_end}"
        
        # Intermediate points 1.0 and 1.8 should now be excluded (inside merged gap)
        expected_valid = [0.0, 0.1, 0.2, 2.5, 2.6]  # Excluding 1.0 and 1.8
        assert len(analysis.valid_x_values) == len(expected_valid), \
            f"Expected {len(expected_valid)} valid points, got {len(analysis.valid_x_values)}"
        assert analysis.valid_x_values == expected_valid, \
            f"Expected {expected_valid}, got {analysis.valid_x_values}"
        
        # Should have excluded 2 points (1.0 and 1.8)
        points_excluded = analysis.route_stats['raw_points'] - analysis.route_stats['total_points']
        assert points_excluded == 2, f"Expected 2 points excluded, got {points_excluded}"
        
        # Should have gap coverage
        assert analysis.route_stats['gap_total_length'] > 2.0, "Should have significant gap coverage"
    
    def test_route_with_gap_at_start_integration(self):
        """Test full route analysis with gap at start (should fail)."""
        # Create data where first gap starts at route beginning
        milepoints = [0.0, 1.0, 1.1, 1.2]  # Large gap from start
        df = pd.DataFrame({
            'milepoint': milepoints,
            'structural_strength_ind': [1.0] * len(milepoints)
        })
        
        # Should raise fatal error during analysis
        with pytest.raises(ValueError, match="FATAL.*Gap at route start"):
            analyze_route_gaps(df, "milepoint", "structural_strength_ind", "GAP_AT_START", gap_threshold=0.5)
    
    def test_route_with_gap_at_end_integration(self):
        """Test full route analysis with gap at end (should fail)."""
        # Create data where last gap ends at route end
        milepoints = [0.0, 0.1, 0.2, 1.5]  # Large gap to end
        df = pd.DataFrame({
            'milepoint': milepoints,
            'structural_strength_ind': [1.0] * len(milepoints)
        })
        
        # Should raise fatal error during analysis
        with pytest.raises(ValueError, match="FATAL.*Gap at route end"):
            analyze_route_gaps(df, "milepoint", "structural_strength_ind", "GAP_AT_END", gap_threshold=0.5)


class TestAdjacentGapMerging:
    """Test adjacent gap merging logic."""
    
    def test_merge_adjacent_gaps(self):
        """Test merging of adjacent gaps."""
        gaps = [(1.0, 1.5), (1.5, 2.0), (3.0, 3.2)]  # First two are adjacent
        merged = _merge_adjacent_gaps(gaps)
        
        assert len(merged) == 2, "Should merge adjacent gaps"
        assert merged[0] == (1.0, 2.0), "Should merge first two gaps"
        assert merged[1] == (3.0, 3.2), "Third gap should remain separate"
    
    def test_overlapping_gaps(self):
        """Test merging of overlapping gaps."""
        gaps = [(1.0, 1.8), (1.5, 2.0)]  # Overlapping
        merged = _merge_adjacent_gaps(gaps)
        
        assert len(merged) == 1, "Should merge overlapping gaps"
        assert merged[0] == (1.0, 2.0), "Should extend to cover both gaps"
    
    def test_close_gaps_merging(self):
        """Gaps separated by a positive-length interval should NOT merge."""
        gaps = [(1.0, 1.2), (1.3, 1.5)]  # 0.1 mile apart, within 0.2 tolerance
        merged = _merge_adjacent_gaps(gaps)
        
        assert len(merged) == 2, "Should not merge gaps separated by non-gap spacing"
        assert merged == gaps
    
    def test_no_adjacent_gaps(self):
        """Test that non-adjacent gaps remain separate."""
        gaps = [(1.0, 1.2), (2.0, 2.3), (4.0, 4.1)]  # All gaps > 0.2 miles apart
        merged = _merge_adjacent_gaps(gaps)
        
        assert len(merged) == 3, "Non-adjacent gaps should remain separate"
        assert merged == gaps, "Gap list should be unchanged"
    
    def test_multiple_large_gaps_merging(self):
        """Large gaps separated by positive-length spacing should NOT merge."""
        gaps = [(1.0, 1.6), (1.8, 2.4), (2.6, 3.2)]  # 0.6, 0.6, 0.6 mile gaps, 0.2 apart
        merged = _merge_adjacent_gaps(gaps)

        assert len(merged) == 3, "Should not merge gaps separated by non-gap spacing"
        assert merged == gaps


class TestEndpointValidation:
    """Test route endpoint validation."""
    
    def test_valid_endpoints(self):
        """Test that valid endpoints pass validation."""
        gaps = [(1.0, 1.5), (3.0, 3.5)]
        route_start, route_end = 0.0, 5.0
        
        # Should not raise any exception
        _validate_route_endpoints(gaps, route_start, route_end)
    
    def test_gap_at_start_fatal(self):
        """Test that gap at route start raises fatal error."""
        gaps = [(0.0, 0.5)]  # Gap at start
        route_start, route_end = 0.0, 5.0
        
        with pytest.raises(ValueError, match="FATAL.*Gap at route start"):
            _validate_route_endpoints(gaps, route_start, route_end)
    
    def test_gap_at_end_fatal(self):
        """Test that gap at route end raises fatal error."""
        gaps = [(4.5, 5.0)]  # Gap at end
        route_start, route_end = 0.0, 5.0
        
        with pytest.raises(ValueError, match="FATAL.*Gap at route end"):
            _validate_route_endpoints(gaps, route_start, route_end)


class TestRouteAnalysisDataStructure:
    """Test RouteAnalysis data structure integrity."""
    
    def test_route_analysis_structure(self):
        """Test that RouteAnalysis contains all required fields."""
        # Create simple test data
        milepoints = [0.0, 0.1, 0.5, 0.6]  # Gap between 0.1 and 0.5
        df = pd.DataFrame({
            'milepoint': milepoints,
            'structural_strength_ind': [1.0] * len(milepoints)
        })
        
        analysis = analyze_route_gaps(df, "milepoint", "structural_strength_ind", "STRUCTURE_TEST", gap_threshold=0.5)
        
        # Verify all fields exist and have correct types
        assert isinstance(analysis.route_id, str)
        assert isinstance(analysis.route_data, pd.DataFrame)
        assert isinstance(analysis.gap_segments, list)
        assert isinstance(analysis.mandatory_breakpoints, set)
        assert isinstance(analysis.valid_x_values, list)
        assert isinstance(analysis.route_stats, dict)
        
        # Verify data integrity
        assert analysis.route_id == "STRUCTURE_TEST"
        assert analysis.route_stats['raw_points'] == len(df)
        assert len(analysis.route_data) == analysis.route_stats['total_points']
        assert len(analysis.mandatory_breakpoints) >= 2  # At least start/end
        assert len(analysis.valid_x_values) <= len(milepoints)  # May exclude merged gap interiors
        # Note: valid_points may be less than total_points if gap merging occurs
        
        # Verify route_stats contains expected keys
        expected_keys = ['raw_points', 'total_points', 'gap_count', 'valid_points', 
                        'route_start', 'route_end', 'total_length',
                        'gap_total_length', 'valid_length']
        for key in expected_keys:
            assert key in analysis.route_stats, f"Missing route_stats key: {key}"


if __name__ == "__main__":
    """Run basic tests and gap analysis demonstration."""
    print("Running Gap Analysis Tests...")
    
    # Run the demo test from integration test module
    from integration.test_gap_analysis_demo import test_gap_analysis
    test_gap_analysis()
    
    print("\nTo run full test suite, use: pytest tests/test_gap_analysis.py -v")