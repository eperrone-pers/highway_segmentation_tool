#!/usr/bin/env python3

import sys
from pathlib import Path
from unittest.mock import Mock
import pandas as pd
import numpy as np

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


def create_mock_app():
    """Create a mock application for testing the optimization controller."""
    mock_app = Mock()
    
    # Mock GUI attributes
    # Create RouteAnalysis object from test data
    test_data = create_test_highway_data()
    mock_app.data = analyze_route_gaps(
        test_data,
        "milepoint",
        "structural_strength_ind",
        route_id="MINIMAL_TEST",
        gap_threshold=1.0,
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
    mock_app.messages = []
    def mock_log(message):
        mock_app.messages.append(message)
        print(f"[LOG] {message}")
    mock_app.log_message = mock_log
    
    return mock_app


def test_simple_controller_creation():
    """Test basic controller creation and validation."""
    print("🧪 Testing simple controller creation...")
    
    # Create mock application
    mock_app = create_mock_app()
    
    print(f"Created mock app with {len(mock_app.data)} data points")
    
    # Create optimization controller
    controller = OptimizationController(mock_app)
    
    print("✅ Controller created successfully")
    
    # Test parameter retrieval
    params = mock_app.parameter_manager.get_optimization_parameters()
    print(f"Method: {params['optimization_method']}")
    print(f"Population: {params['population_size']}, Generations: {params['num_generations']}")
    
    print("✅ Controller simple test PASSED")
    return True


if __name__ == "__main__":
    test_simple_controller_creation()