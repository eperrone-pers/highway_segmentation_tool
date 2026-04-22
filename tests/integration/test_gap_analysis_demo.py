"""
Integration test demo for gap analysis functionality.

This module provides interactive gap analysis demonstrations that were
previously located in the production data_loader.py module.
"""

import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from data_loader import load_highway_data, analyze_route_gaps


def test_gap_analysis():
    """Test gap analysis with single-route test data to validate results."""
    print("\n" + "="*60)
    print("TESTING GAP ANALYSIS WITH TXDOT DATA")
    print("="*60)
    
    # Load test data
    data = load_highway_data("tests/test_data/test_data_single_route.csv")
    if data is None:
        print("ERROR: Could not load single-route test data")
        return
    
    # Analyze the route
    try:
        analysis = analyze_route_gaps(
            data,
            x_column="milepoint",
            y_column="structural_strength_ind",
            route_id="TXDOT_TEST",
            gap_threshold=0.5,
        )
        
        print(f"\n=== ANALYSIS COMPLETE ===")
        print(f"Route: {analysis.route_id}")
        print(f"Detected Gaps: {len(analysis.gap_segments)}")
        
        for i, (start, end) in enumerate(analysis.gap_segments, 1):
            print(f"  Gap {i}: {start:.3f} to {end:.3f} miles (length: {end-start:.3f})")
            
        print(f"\nMandatory Breakpoints: {len(analysis.mandatory_breakpoints)}")
        sorted_breakpoints = sorted(analysis.mandatory_breakpoints)
        print(f"  {sorted_breakpoints[:3]} ... {sorted_breakpoints[-3:]}")
        
        print(f"\nValid X Values: {len(analysis.valid_x_values)}")
        print(f"  Range: {min(analysis.valid_x_values):.3f} to {max(analysis.valid_x_values):.3f}")
        
        print(f"\nRoute Statistics:")
        for key, value in analysis.route_stats.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.3f}")
            else:
                print(f"  {key}: {value}")
                
    except Exception as e:
        # This is a test function - should re-raise with context
        raise RuntimeError(f"Route gap analysis failed: {str(e)}") from e
    
    print("\n" + "="*60)