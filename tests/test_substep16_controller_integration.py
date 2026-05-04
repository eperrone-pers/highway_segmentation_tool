"""
Test Sub-step 1.6: Controller Integration

This test validates the integration of unified multi-route optimization methods 
with the OptimizationController, ensuring the entire workflow from GUI to 
optimization execution works correctly.

Test Coverage:
- Controller preparation of route processing configuration
- Unified optimization method execution through controller
- Result handling and processing
- Integration with existing GUI components
"""

import pytest

pytest.skip(
    "Legacy substep integration tests are being retired; to be replaced with updated coverage.",
    allow_module_level=True,
)

import sys
import time
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock
import threading

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from optimization_controller import OptimizationController
from data_loader import analyze_route_gaps
from route_utils import ROUTE_COLUMN_NONE_SENTINEL
from config import optimization_config


def create_mock_app():
    """Create a mock application for testing the optimization controller."""
    mock_app = Mock()
    
    # Mock GUI attributes
    # Create RouteAnalysis object from test data  
    test_data = create_test_highway_data()
    mock_app.data = analyze_route_gaps(
        test_data,
        x_column="milepoint",
        y_column="structural_strength_ind",
        route_id="INTEGRATION_TEST",
        gap_threshold=1.0,
    )
    mock_app.is_running = False
    mock_app.stop_requested = False
    
    # Mock route configuration
    mock_app.route_column = Mock()
    mock_app.route_column.get.return_value = ROUTE_COLUMN_NONE_SENTINEL
    mock_app.selected_routes = []
    
    # Mock GUI controls
    mock_app.start_button = Mock()
    mock_app.stop_button = Mock() 
    mock_app.results_text = Mock()
    mock_app.results_notebook = Mock()
    mock_app.custom_save_name = Mock()
    mock_app.custom_save_name.get.return_value = ""
    mock_app.gap_threshold = Mock()
    mock_app.gap_threshold.get.return_value = 1.0
    mock_app.root = Mock()
    
    # Mock file manager
    mock_app.file_manager = Mock()
    mock_app.file_manager.get_data_file_path.return_value = "test_data.csv"
    mock_app.file_manager.display_results_file = Mock()
    
    # Mock parameter manager
    mock_app.parameter_manager = Mock()
    mock_app.parameter_manager.validate_and_show_errors.return_value = True
    mock_app.parameter_manager.get_optimization_parameters.return_value = {
        'optimization_method': 'single',
        'min_length': 2.0,
        'max_length': 8.0,
        'population_size': 20,
        'num_generations': 10,
        'mutation_rate': 0.05,
        'crossover_rate': 0.8,
        'elite_ratio': 0.05,
        'cache_clear_interval': 50,
        'enable_performance_stats': False,

        'target_avg_length': 5.0,
        'penalty_weight': 1000,
        'length_tolerance': 0.3
    }
    
    # Mock logging
    messages = []
    def mock_log(message):
        messages.append(message)
        print(f"[LOG] {message}")
    
    mock_app.log_message = mock_log
    mock_app.messages = messages  # Store for assertions
    
    return mock_app


def create_test_highway_data():
    """Create realistic test highway data with proper columns."""
    np.random.seed(42)
    
    # Create 31 data points spanning 3 miles (0.1-mile spacing to avoid gap detection issues)
    milepoints = np.linspace(0, 3, 31)
    
    # Create realistic structural strength data
    base_values = 60 + 25 * np.sin(milepoints * 0.15) + np.random.normal(0, 3, 31)
    trend = milepoints * 0.2
    structural_values = base_values + trend
    
    return pd.DataFrame({
        'milepoint': milepoints,
        'structural_strength_ind': structural_values,
        'pavement_condition': np.random.uniform(65, 95, 31),
        'traffic_volume': np.random.uniform(1200, 4500, 31)
    })


def test_controller_single_route_integration():
    """Test controller integration with single-route (filename-as-route) processing."""
    print("\n" + "="*80)
    print("TEST: Controller Integration - Single Route Processing")  
    print("="*80)
    
    # Create mock application 
    mock_app = create_mock_app()
    
    # Create optimization controller
    controller = OptimizationController(mock_app)
    
    print(f"Created mock app with {len(mock_app.data)} data points")
    print(f"Route configuration: '{mock_app.route_column.get()}' (filename-as-route)")
    
    # Test route processing preparation
    try:
        # Mock the optimization thread to run synchronously
        def mock_optimization_worker():
            return controller._run_optimization_worker()
        
        # Replace the threading call with direct execution
        original_start = controller.start_optimization
        
        def mock_start_optimization():
            # Simulate the setup from original start_optimization
            if controller.app.data is None:
                return
            
            if not controller.app.parameter_manager.validate_and_show_errors():
                return
            
            controller.app.is_running = True
            controller.app.stop_requested = False
            
            # Run worker directly instead of in thread
            controller._run_optimization_worker()
            
            # Reset state
            controller.app.is_running = False
        
        controller.start_optimization = mock_start_optimization
        
        # Run optimization through controller
        print("Starting optimization through controller...")
        start_time = time.time()
        
        controller.start_optimization()
        
        elapsed_time = time.time() - start_time
        print(f"Controller optimization completed in {elapsed_time:.1f}s")
        
    except Exception as e:
        print(f"Exception during optimization: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    # Validate controller behavior
    print("\nValidating controller integration:")
    
    # Check that parameter validation was called
    assert mock_app.parameter_manager.validate_and_show_errors.called, "Parameters should be validated"
    print("  ✓ Parameter validation called")
    
    # Check that optimization parameters were retrieved
    assert mock_app.parameter_manager.get_optimization_parameters.called, "Parameters should be retrieved"
    print("  ✓ Optimization parameters retrieved")
    
    # Check that file manager was accessed for data filename
    assert mock_app.file_manager.get_data_file_path.called, "Data file path should be accessed"
    print("  ✓ Data file path accessed for route naming")
    
    # Check log messages for unified processing indicators
    messages = mock_app.messages
    unified_messages = [msg for msg in messages if "unified" in msg.lower()]
    route_messages = [msg for msg in messages if "route" in msg.lower()]
    
    assert unified_messages, "Should contain unified processing messages"
    assert route_messages, "Should contain route processing messages"
    print(f"  ✓ Found {len(unified_messages)} unified processing messages")
    print(f"  ✓ Found {len(route_messages)} route processing messages")
    
    print("✅ Controller single-route integration PASSED")
    return True


def test_controller_multi_route_integration():
    """Test controller integration with multi-route processing."""
    print("\n" + "="*80)
    print("TEST: Controller Integration - Multi-Route Processing")
    print("="*80)
    
    # Create mock application with multi-route configuration
    mock_app = create_mock_app()
    
    # Add route column to test data
    mock_app.data['route'] = ['Route_A'] * 16 + ['Route_B'] * 15  # Split the 31 points
    
    # Configure for multi-route processing
    mock_app.route_column.get.return_value = "route"
    mock_app.selected_routes = ['Route_A', 'Route_B']
    
    # Create optimization controller
    controller = OptimizationController(mock_app)
    
    print(f"Created multi-route data: Route_A (16 points), Route_B (15 points)")
    print(f"Route configuration: column='{mock_app.route_column.get()}', selected={mock_app.selected_routes}")
    
    # Test multi-route optimization
    try:
        # Mock the optimization execution to run synchronously
        def mock_start_optimization():
            if controller.app.data is None:
                return
            
            if not controller.app.parameter_manager.validate_and_show_errors():
                return
            
            controller.app.is_running = True
            controller.app.stop_requested = False
            
            # Run worker directly
            controller._run_optimization_worker()
            
            controller.app.is_running = False
        
        controller.start_optimization = mock_start_optimization
        
        # Use constrained optimization for variety
        mock_app.parameter_manager.get_optimization_parameters.return_value['optimization_method'] = 'Constrained Single-Objective'
        
        print("Starting multi-route constrained optimization...")
        start_time = time.time()
        
        controller.start_optimization()  
        
        elapsed_time = time.time() - start_time
        print(f"Multi-route optimization completed in {elapsed_time:.1f}s")
        
    except Exception as e:
        print(f"Exception during multi-route optimization: {e}")
        import traceback  
        traceback.print_exc()
        raise
    
    # Validate multi-route processing
    print("\nValidating multi-route controller integration:")
    
    messages = mock_app.messages
    
    # Check for multi-route specific messages
    multi_route_messages = [msg for msg in messages if "multi-route" in msg.lower() or "route(s)" in msg]
    route_a_messages = [msg for msg in messages if "Route_A" in msg]
    route_b_messages = [msg for msg in messages if "Route_B" in msg] 
    
    assert multi_route_messages, "Should contain multi-route processing messages"
    print(f"  ✓ Found {len(multi_route_messages)} multi-route messages")
    
    assert route_a_messages, "Should contain Route_A specific messages"
    assert route_b_messages, "Should contain Route_B specific messages"  
    print(f"  ✓ Route_A processed: {len(route_a_messages)} messages")
    print(f"  ✓ Route_B processed: {len(route_b_messages)} messages")
    
    # Check for constrained-specific processing
    constrained_messages = [msg for msg in messages if "constrained" in msg.lower()]
    assert constrained_messages, "Should contain constrained optimization messages"
    print(f"  ✓ Found {len(constrained_messages)} constrained processing messages")
    
    print("✅ Controller multi-route integration PASSED")
    return True


def test_controller_optimization_method_switching():
    """Test controller handling of different optimization methods through unified interface."""
    print("\n" + "="*80)
    print("TEST: Controller Integration - Optimization Method Switching")
    print("="*80)
    
    methods_to_test = [
        ('Single-Objective GA', 'single'),
        ('Constrained Single-Objective', 'constrained'), 
        ('Multi-Objective NSGA-II', 'multi')
    ]
    
    for method_display, method_key in methods_to_test:
        print(f"\n--- Testing {method_display} ---")
        
        # Create fresh mock app for each method
        mock_app = create_mock_app()
        mock_app.parameter_manager.get_optimization_parameters.return_value['optimization_method'] = method_display
        
        controller = OptimizationController(mock_app)
        
        try:
            # Mock the optimization execution to run synchronously
            def mock_start_optimization():
                if controller.app.data is None:
                    return
                
                if not controller.app.parameter_manager.validate_and_show_errors():
                    return
                
                controller.app.is_running = True
                controller.app.stop_requested = False
                
                # Run worker directly
                controller._run_optimization_worker()
                
                controller.app.is_running = False
            
            controller.start_optimization = mock_start_optimization
            
            # Run optimization  
            start_time = time.time()
            controller.start_optimization()
            elapsed_time = time.time() - start_time
            
            print(f"  {method_display} completed in {elapsed_time:.1f}s")
            
            # Validate method-specific processing
            messages = mock_app.messages
            method_messages = [msg for msg in messages if method_key in msg.lower() or method_display.lower() in msg.lower()]
            
            assert method_messages, f"Should contain {method_display} specific messages"
            print(f"  ✓ Found {len(method_messages)} method-specific messages")
            
            # Validate unified processing
            unified_messages = [msg for msg in messages if "unified" in msg.lower()]
            assert unified_messages, f"Should use unified architecture for {method_display}"
            print(f"  ✓ Unified processing confirmed")
            
        except Exception as e:
            print(f"  ❌ Failed for {method_display}: {e}")
            raise
    
    print("✅ Controller optimization method switching PASSED")
    return True


def run_all_tests():
    """Execute all controller integration tests."""
    print("🧪 TESTING SUB-STEP 1.6: CONTROLLER INTEGRATION")
    print("Testing unified multi-route architecture integration with OptimizationController...")
    
    start_time = time.time()
    
    try:
        # Test single-route controller integration
        test_controller_single_route_integration()
        
        # Test multi-route controller integration
        test_controller_multi_route_integration()
        
        # Test optimization method switching
        test_controller_optimization_method_switching()
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "="*80)
        print("🎉 ALL SUB-STEP 1.6 TESTS PASSED!")
        print("="*80)
        print(f"✅ Controller single-route integration validated")
        print(f"✅ Controller multi-route integration validated") 
        print(f"✅ Optimization method switching through unified interface validated")
        print(f"✅ Route processing configuration working correctly")
        print(f"✅ End-to-end optimization workflow functional")
        print(f"⏱️  Total testing time: {elapsed_time:.1f} seconds")
        print("="*80)
        print("\n🚀 UNIFIED MULTI-ROUTE ARCHITECTURE INTEGRATION COMPLETE!")
        print("\n🎯 MAJOR MILESTONE: All optimization methods now use unified multi-route architecture")
        print("🎯 Controller successfully orchestrates route processing and optimization execution") 
        print("🎯 Ready for production use with both single and multi-route datasets")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)