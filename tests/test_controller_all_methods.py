#!/usr/bin/env python3

import sys
from pathlib import Path
from unittest.mock import Mock
import pandas as pd
import numpy as np
import time

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from optimization_controller import OptimizationController
from data_loader import analyze_route_gaps


def create_test_highway_data():
    """Create test highway data for testing."""
    milepoints = np.linspace(0, 3, 31)  # 0.1-mile intervals to avoid gap detection issues
    base_values = 60 + 25 * np.sin(milepoints * 0.15) + np.random.normal(0, 3, 31)
    trend = milepoints * 0.2
    structural_values = base_values + trend
    
    return pd.DataFrame({
        'milepoint': milepoints,
        'structural_strength_ind': structural_values,
        'pavement_condition': np.random.uniform(65, 95, 31),
        'traffic_volume': np.random.uniform(1200, 4500, 31)
    })


def create_mock_app_for_method(method_key):
    """Create a mock application for testing a specific optimization method."""
    mock_app = Mock()

    mock_app.gap_threshold = Mock()
    mock_app.gap_threshold.get.return_value = 1.0
    
    # Mock GUI attributes
    # Create RouteAnalysis object from test data
    test_data = create_test_highway_data()
    mock_app.data = analyze_route_gaps(
        test_data,
        x_column="milepoint",
        y_column="structural_strength_ind",
        route_id="CONTROLLER_TEST",
        gap_threshold=float(mock_app.gap_threshold.get()),
    )
    mock_app.is_running = False
    mock_app.stop_requested = False
    
    # Mock route configuration
    mock_app.route_column = Mock()
    mock_app.route_column.get.return_value = "None - treat as single route"
    mock_app.selected_routes = []
    
    # Mock GUI controls
    mock_app.start_button = Mock()
    mock_app.stop_button = Mock() 
    mock_app.results_text = Mock()
    mock_app.results_notebook = Mock()
    mock_app.custom_save_name = Mock()
    mock_app.custom_save_name.get.return_value = ""
    mock_app.root = Mock()
    
    # Mock file manager
    mock_app.file_manager = Mock()
    mock_app.file_manager.get_data_file_path.return_value = f"test_{method_name.lower().replace(' ', '_')}_data.csv"
    mock_app.file_manager.display_results_file = Mock()
    
    # Mock parameter manager - METHOD-SPECIFIC CONFIGURATION
    mock_app.parameter_manager = Mock()
    mock_app.parameter_manager.validate_and_show_errors.return_value = True
    
    # Base parameters for all methods
    base_params = {
        'optimization_method': method_key,
        'min_length': 2.0,
        'max_length': 8.0,
        'population_size': 25,
        'num_generations': 12,
        'mutation_rate': 0.06,
        'crossover_rate': 0.8,
        'elite_ratio': 0.08,
        'cache_clear_interval': 30,
        'enable_performance_stats': True,
    }
    
    # Add method-specific parameters
    if method_key == 'constrained':
        base_params.update({
            'target_avg_length': 4.0,
            'penalty_weight': 1500,
            'length_tolerance': 0.5
        })
    
    mock_app.parameter_manager.get_optimization_parameters.return_value = base_params
    
    # Mock logging with method-specific tracking
    mock_app.messages = []
    def mock_log(message):
        mock_app.messages.append(message)
        print(f"[{method_key.upper()}] {message}")
    mock_app.log_message = mock_log
    
    return mock_app


def test_controller_with_all_methods():
    """Test controller integration with ALL three optimization methods."""
    print("🧪" + "="*80)
    print("🎯 COMPREHENSIVE CONTROLLER TEST - ALL OPTIMIZATION METHODS")
    print("="*80)
    
    methods_to_test = [
        ('Single-Objective GA', 'single'),
        ('Multi-Objective NSGA-II', 'multi'), 
        ('Constrained Single-Objective', 'constrained')
    ]
    
    results = {}
    
    for method_display, method_key in methods_to_test:
        print(f"\n{'='*20} TESTING {method_display.upper()} {'='*20}")
        
        try:
            # Create method-specific mock app
            mock_app = create_mock_app_for_method(method_key)
            controller = OptimizationController(mock_app)
            
            print(f"📊 Method: {method_display}")
            print(f"   • Data points: {len(mock_app.data.route_data)}")
            print(f"   • Population: {mock_app.parameter_manager.get_optimization_parameters()['population_size']}")
            print(f"   • Generations: {mock_app.parameter_manager.get_optimization_parameters()['num_generations']}")
            
            # Mock synchronous execution
            def mock_start_optimization():
                if controller.app.data is None:
                    return
                if not controller.app.parameter_manager.validate_and_show_errors():
                    return
                controller.app.is_running = True
                controller.app.stop_requested = False
                controller._run_optimization_worker()
                controller.app.is_running = False
            
            controller.start_optimization = mock_start_optimization
            
            # Execute optimization
            print(f"🚀 Starting {method_display} optimization...")
            start_time = time.time()
            controller.start_optimization()
            elapsed_time = time.time() - start_time
            
            print(f"✅ {method_display} completed in {elapsed_time:.1f}s")
            
            # Validate method-specific behavior
            messages = mock_app.messages
            
            # Check for method identification
            method_messages = [msg for msg in messages if method_key in msg.lower() or method_display.lower() in msg.lower()]
            unified_messages = [msg for msg in messages if "unified" in msg.lower()]
            route_messages = [msg for msg in messages if "route" in msg.lower()]
            
            results[method_display] = {
                'executed': True,
                'elapsed_time': elapsed_time,
                'method_messages': len(method_messages),
                'unified_messages': len(unified_messages), 
                'route_messages': len(route_messages),
                'total_messages': len(messages)
            }
            
            print(f"📈 Validation Results:")
            print(f"   ✓ Method-specific messages: {len(method_messages)}")
            print(f"   ✓ Unified processing messages: {len(unified_messages)}")
            print(f"   ✓ Route processing messages: {len(route_messages)}")
            print(f"   ✓ Total log messages: {len(messages)}")
            
            # Method-specific validations
            if 'Single-Objective GA' in method_display:
                single_obj_messages = [msg for msg in messages if "single" in msg.lower() and "objective" in msg.lower()]
                assert single_obj_messages, "Should contain single-objective processing messages"
                print(f"   ✓ Single-objective processing confirmed: {len(single_obj_messages)} messages")
                
            elif 'Multi-Objective NSGA-II' in method_display:
                nsga2_messages = [msg for msg in messages if "nsga" in msg.lower() or "pareto" in msg.lower() or "multi" in msg.lower()]
                assert nsga2_messages, "Should contain NSGA-II/multi-objective processing messages"
                print(f"   ✓ NSGA-II/Multi-objective processing confirmed: {len(nsga2_messages)} messages")
                
            elif 'Constrained' in method_display:
                constrained_messages = [msg for msg in messages if "constrained" in msg.lower()]
                target_messages = [msg for msg in messages if "target" in msg.lower()]
                penalty_messages = [msg for msg in messages if "penalty" in msg.lower()]
                assert constrained_messages, "Should contain constrained processing messages"
                print(f"   ✓ Constrained processing confirmed: {len(constrained_messages)} messages")
                if target_messages:
                    print(f"   ✓ Target-length processing: {len(target_messages)} messages")
                if penalty_messages:
                    print(f"   ✓ Penalty system active: {len(penalty_messages)} messages")
            
            print(f"✅ {method_display} CONTROLLER INTEGRATION PASSED")
            
        except Exception as e:
            print(f"❌ {method_display} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results[method_display] = {
                'executed': False,
                'error': str(e),
                'elapsed_time': 0
            }
    
    # Final comprehensive summary
    print("\n" + "="*80)
    print("🎉 COMPREHENSIVE CONTROLLER TEST RESULTS")
    print("="*80)
    
    successful_methods = [method for method, result in results.items() if result.get('executed', False)]
    failed_methods = [method for method, result in results.items() if not result.get('executed', False)]
    
    print(f"✅ SUCCESSFUL METHODS ({len(successful_methods)}/3):")
    for method in successful_methods:
        result = results[method]
        print(f"   • {method}: {result['elapsed_time']:.1f}s, {result['total_messages']} log messages")
    
    if failed_methods:
        print(f"\n❌ FAILED METHODS ({len(failed_methods)}/3):")
        for method in failed_methods:
            print(f"   • {method}: {results[method].get('error', 'Unknown error')}")
    
    print(f"\n📊 OVERALL STATUS:")
    if len(successful_methods) == 3:
        print(f"🎉 ALL THREE OPTIMIZATION METHODS WORKING WITH CONTROLLER!")
        print(f"✅ Single-Objective GA: Controller integration complete")
        print(f"✅ Multi-Objective NSGA-II: Controller integration complete") 
        print(f"✅ Constrained Single-Objective: Controller integration complete")
        print(f"✅ Unified multi-route architecture fully integrated")
        print(f"✅ Controller ready for production use with all methods")
        print("="*80)
        return True
    else:
        print(f"⚠️  Controller integration incomplete: {len(successful_methods)}/3 methods working")
        print("="*80)
        return False


if __name__ == "__main__":
    success = test_controller_with_all_methods()
    if success:
        print("\n🚀 CONTROLLER COMPREHENSIVE TEST PASSED!")
    else:
        print("\n❌ CONTROLLER COMPREHENSIVE TEST FAILED!")
        sys.exit(1)