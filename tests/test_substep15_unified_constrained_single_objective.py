"""
Test Sub-step 1.5: Unified Constrained Single-Objective Implementation

This test validates the transformation of run_constrained_single_objective() to the unified
multi-route architecture, following the established pattern from NSGA-II and Single-Objective.

Test Coverage:
- Multi-route processing with filename-as-route fallback
- Single route as N=1 multi-route case  
- Core constrained algorithm integrity preservation
- Route orchestration and result structure validation
"""

import sys
import time
import pandas as pd
import numpy as np
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analysis.methods.constrained import ConstrainedMethod
from data_loader import RouteAnalysis
# from data_loader import prepare_route_processing  # Function not implemented - removing unused import
from config import optimization_config


def create_test_data():
    """Create test highway data for constrained optimization validation."""
    # Create synthetic highway segment with known properties for constrained testing
    np.random.seed(42)  # Reproducible results
    
    # Create 51 data points spanning 5 miles (0.1-mile spacing to avoid gap detection issues)
    milepoints = np.linspace(0, 5, 51)  # 0, 0.1, 0.2, ..., 5.0 (51 points)
    
    # Create smooth base values that change gradually
    base_values = 50 + 20 * np.sin(milepoints * 0.1) + np.random.normal(0, 2, 51)  
    
    # Add some gradual trend
    trend = milepoints * 0.1
    structural_values = base_values + trend
    
    # Create additional synthetic engineering columns expected by HighwaySegmentGA
    return pd.DataFrame({
        'milepoint': milepoints,
        'structural_strength_ind': structural_values,  # Primary optimization value
        'value': structural_values,  # Alias for compatibility
        'pavement_condition': np.random.uniform(60, 95, 51),  # Additional realistic data
        'traffic_volume': np.random.uniform(1000, 5000, 51)
    })


def test_unified_constrained_filename_as_route():
    """Test unified constrained single-objective with filename-as-route (no route column)."""
    print("\n" + "="*80)
    print("TEST: Unified Constrained Single-Objective - Filename as Route")
    print("="*80)
    
    # Create test data without route column
    data = create_test_data()
    print(f"Created test data: {len(data)} points, {data['milepoint'].max():.1f} miles")
    
    # Configure for constrained optimization with target average length
    target_avg_length = 5.0  # Target 5-mile segments
    tolerance = 0.3  # ±0.3 mile tolerance
    
    # Initialize framework method
    constrained_method = ConstrainedMethod()
    
    # Create RouteAnalysis object for framework method
    route_analysis = RouteAnalysis(
        route_data=data,
        route_id="test_route",
        x_column='milepoint',
        y_column='structural_strength_ind'
    )
    
    # Run framework constrained analysis
    start_time = time.time()
    analysis_result = constrained_method.run_analysis(
        data=route_analysis,
        route_id="test_route",
        x_column='milepoint',
        y_column='structural_strength_ind',
        gap_threshold=2.0,
        min_length=2.0,
        max_length=8.0, 
        target_avg_length=target_avg_length,
        population_size=30,
        num_generations=20,
        penalty_weight=1000,
        tolerance=tolerance,
        enable_performance_stats=True
    )
    elapsed_time = time.time() - start_time
    
    print(f"\nOptimization completed in {elapsed_time:.1f}s")
    
    # Convert framework result to test-compatible format
    if analysis_result and analysis_result.best_solution:
        results = {
            'results_by_route': {
                'test_route': {
                    'best_fitness': analysis_result.best_solution.get('fitness', 0),
                    'best_chromosome': analysis_result.best_solution.get('chromosome', []),
                    'best_avg_length': analysis_result.best_solution.get('avg_segment_length', 0),
                    'target_avg_length': target_avg_length,
                    'length_deviation': analysis_result.best_solution.get('length_deviation', 0),
                    'tolerance': tolerance
                }
            },
            'route_names': ['test_route']
        }
    else:
        results = {
            'results_by_route': {},
            'route_names': []
        }
    
    # Validate unified result structure
    assert 'results_by_route' in results, "Missing results_by_route in unified structure"
    assert 'route_names' in results, "Missing route_names in unified structure"
    assert 'total_elapsed_time' in results, "Missing total_elapsed_time in unified structure"
    assert 'summary_stats' in results, "Missing summary_stats in unified structure"
    
    # Validate filename-as-route behavior  
    route_names = results['route_names']
    assert len(route_names) == 1, f"Expected 1 route, got {len(route_names)}"
    assert route_names[0] == "test_highway_data", f"Expected filename route (stem), got {route_names[0]}"
    
    # Validate route result structure
    route_result = results['results_by_route'][route_names[0]]
    required_keys = ['route_name', 'best_chromosome', 'best_fitness', 'best_unconstrained_fitness', 
                    'best_avg_length', 'target_avg_length', 'length_deviation', 'elapsed_time']
    for key in required_keys:
        assert key in route_result, f"Missing key '{key}' in route result"
    
    # Validate constrained optimization results
    assert route_result['target_avg_length'] == target_avg_length, "Target length mismatch"
    assert route_result['best_avg_length'] > 0, "Invalid average segment length"
    assert len(route_result['best_chromosome']) >= 2, "Should have at least 2 breakpoints"
    
    # Check if solution is within tolerance
    length_deviation = abs(route_result['best_avg_length'] - target_avg_length)
    print(f"  Target length: {target_avg_length:.2f} miles")
    print(f"  Achieved length: {route_result['best_avg_length']:.2f} miles")
    print(f"  Length deviation: {length_deviation:.3f} miles (tolerance: ±{tolerance:.1f})")
    print(f"  Within tolerance: {length_deviation <= tolerance}")
    
    print("✅ Unified constrained single-objective with filename-as-route PASSED")
    return results


def test_unified_constrained_multi_route():
    """Test unified constrained single-objective with actual multiple routes."""
    print("\n" + "="*80)
    print("TEST: Unified Constrained Single-Objective - Multi Route")
    print("="*80)
    
    # Create test data with multiple routes
    route_a_data = create_test_data()
    route_a_data['route'] = 'Route_A'
    
    # Create Route B with different characteristics
    np.random.seed(123)  # Different seed for variety
    milepoints_b = np.linspace(1, 4, 80)  # 0.0375-mile intervals, 3-mile span
    structural_values_b = 30 + 15 * np.cos(milepoints_b * 0.15) + np.random.normal(0, 3, 80)
    route_b_data = pd.DataFrame({
        'milepoint': milepoints_b,
        'structural_strength_ind': structural_values_b,
        'value': structural_values_b,
        'pavement_condition': np.random.uniform(55, 90, 80),
        'traffic_volume': np.random.uniform(800, 4000, 80),
        'route': 'Route_B'
    })
    
    # Combine routes into single dataset
    multi_route_data = pd.concat([route_a_data, route_b_data], ignore_index=True)
    print(f"Created multi-route data: {len(multi_route_data)} points, Routes: A & B")
    
    # Configure route processing info correctly
    route_processing_info = {
        'routes_to_process': ['Route_A', 'Route_B'],
        'route_column': 'route',
        'processing_mode': 'multi_route'
    }
    
    # Configure constrained optimization
    target_avg_length = 4.5  # Different target than previous test
    tolerance = 0.5
    
    # Run unified constrained single-objective
    start_time = time.time()
    results = run_constrained_single_objective(
        data=multi_route_data,
        x_column='milepoint',  # Add column parameters
        y_column='structural_strength_ind',
        min_length=1.5,
        max_length=10.0,
        target_avg_length=target_avg_length,
        population_size=25,  # Small for testing
        num_generations=15,  # Quick test
        penalty_weight=800,
        tolerance=tolerance,
        enable_performance_stats=True,
        gap_threshold=2.0  # Increased threshold to prevent 1-mile spacing from being treated as gaps
    )
    elapsed_time = time.time() - start_time
    
    print(f"\nMulti-route optimization completed in {elapsed_time:.1f}s")
    
    # Validate multi-route results
    route_names = results['route_names']
    assert len(route_names) == 2, f"Expected 2 routes, got {len(route_names)}"
    assert set(route_names) == {'Route_A', 'Route_B'}, f"Unexpected routes: {route_names}"
    
    # Validate each route's results
    for route_name in route_names:
        print(f"\n  Route '{route_name}' Results:")
        route_result = results['results_by_route'][route_name]
        
        # Validate required keys
        required_keys = ['route_name', 'best_chromosome', 'best_fitness', 'best_avg_length', 
                        'target_avg_length', 'length_deviation']
        for key in required_keys:
            assert key in route_result, f"Missing key '{key}' for route {route_name}"
        
        # Validate constrained results
        assert route_result['route_name'] == route_name, "Route name mismatch"
        assert route_result['target_avg_length'] == target_avg_length, "Target length mismatch"
        
        length_deviation = abs(route_result['best_avg_length'] - target_avg_length)
        print(f"    Target: {target_avg_length:.2f} miles")
        print(f"    Achieved: {route_result['best_avg_length']:.2f} miles")  
        print(f"    Deviation: {length_deviation:.3f} miles")
        print(f"    Fitness: {route_result['best_fitness']:.4f}")
        print(f"    Segments: {len(route_result['best_chromosome']) - 1}")
    
    # Validate summary statistics
    summary = results['summary_stats']
    assert summary['total_routes'] == 2, "Incorrect total route count"
    assert summary['avg_time_per_route'] > 0, "Invalid average time per route"
    assert summary['best_overall_fitness'] < 0, "Fitness should be negative (higher is better)"
    
    print(f"\n  Summary Statistics:")
    print(f"    Best overall fitness: {summary['best_overall_fitness']:.6f}")
    print(f"    Best avg length: {summary['best_avg_length']:.3f} miles")
    print(f"    Avg time per route: {summary['avg_time_per_route']:.1f}s")
    
    print("✅ Unified constrained single-objective with multi-route PASSED")
    return results


def test_algorithm_integrity_comparison():
    """Validate that unified implementation maintains same algorithmic behavior."""
    print("\n" + "="*80)
    print("TEST: Algorithm Integrity - Unified vs Original Behavior")
    print("="*80)
    
    # Create deterministic test data
    np.random.seed(999)  # Fixed seed for reproducibility
    data = create_test_data()
    
    print("Running constrained optimization with same parameters...")
    
    # Test parameters for consistency
    target_length = 6.0
    tolerance = 0.2
    
    # Run unified version (filename-as-route mode)
    results = run_constrained_single_objective(
        data=data,
        x_column='milepoint',  # Add column parameters
        y_column='structural_strength_ind',
        min_length=3.0,
        max_length=9.0,
        target_avg_length=target_length,
        population_size=40,
        num_generations=25,
        penalty_weight=1200,
        tolerance=tolerance,
        enable_performance_stats=False,  # Disable for cleaner output
        gap_threshold=2.0  # Avoid treating regular data spacing as gaps
    )
    
    # Extract single route result (unified structure)
    route_result = list(results['results_by_route'].values())[0]
    
    # Validate constraint-specific results
    assert 'best_unconstrained_fitness' in route_result, "Missing unconstrained fitness"
    assert 'length_deviation' in route_result, "Missing length deviation"
    assert 'tolerance' in route_result, "Missing tolerance value"
    assert 'penalty_weight' in route_result, "Missing penalty weight"
    
    # Validate fitness relationship  
    constrained_fitness = route_result['best_fitness']
    unconstrained_fitness = route_result['best_unconstrained_fitness']
    
    # Constrained fitness should be <= unconstrained (penalty reduces fitness)
    length_deviation = route_result['length_deviation']
    if length_deviation > tolerance:
        assert constrained_fitness <= unconstrained_fitness, "Constrained fitness should be reduced when outside tolerance"
        print("  ✓ Penalty correctly applied for length deviation")
    else:
        assert abs(constrained_fitness - unconstrained_fitness) < 0.01, "No penalty expected when within tolerance"
        print("  ✓ No penalty applied when within tolerance")
    
    # Validate length targeting
    achieved_length = route_result['best_avg_length']
    print(f"  Target length: {target_length:.2f} miles")
    print(f"  Achieved length: {achieved_length:.2f} miles")
    print(f"  Length deviation: {length_deviation:.3f} miles")
    print(f"  Constrained fitness: {constrained_fitness:.6f}")
    print(f"  Unconstrained fitness: {unconstrained_fitness:.6f}")
    
    # Validate mandatory breakpoints preservation
    assert 'mandatory_breakpoints' in route_result, "Missing mandatory breakpoints"
    mandatory_bps = route_result['mandatory_breakpoints']
    
    # Check that start/end are always mandatory breakpoints
    data_start = data['milepoint'].min()
    data_end = data['milepoint'].max()
    assert data_start in mandatory_bps, "Start point should be mandatory breakpoint"
    assert data_end in mandatory_bps, "End point should be mandatory breakpoint"
    
    print("✅ Algorithm integrity validation PASSED")
    return results


def run_all_tests():
    """Execute all sub-step 1.5 validation tests."""
    print("🧪 TESTING SUB-STEP 1.5: UNIFIED CONSTRAINED SINGLE-OBJECTIVE")
    print("Testing transformation to unified multi-route architecture...")
    
    start_time = time.time()
    
    try:
        # Test filename-as-route mode
        test_unified_constrained_filename_as_route()
        
        # Test actual multi-route processing
        test_unified_constrained_multi_route()
        
        # Test algorithm integrity preservation
        test_algorithm_integrity_comparison()
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "="*80)
        print("🎉 ALL SUB-STEP 1.5 TESTS PASSED!")
        print("="*80)
        print(f"✅ Unified constrained single-objective implementation validated")
        print(f"✅ Multi-route orchestration working correctly")
        print(f"✅ Filename-as-route fallback functioning")
        print(f"✅ Algorithm integrity maintained")
        print(f"✅ Result structure follows unified pattern")
        print(f"⏱️  Total testing time: {elapsed_time:.1f} seconds")
        print("="*80)
        print("\n🚀 Ready for Sub-step 1.6: Controller Integration!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)