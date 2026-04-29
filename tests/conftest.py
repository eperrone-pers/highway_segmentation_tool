"""
pytest configuration and fixtures for Highway Segmentation GA tests.

This module provides reusable test fixtures including data loading,
mock objects, and temporary file handling for comprehensive testing.
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import shutil
import os
from unittest.mock import Mock, MagicMock
from pathlib import Path


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "excel_export: Tests for Excel export functionality",
    )


@pytest.fixture(autouse=True)
def _disable_tk_messageboxes(monkeypatch):
    """Prevent real Tkinter dialogs during tests.

    Some code paths (e.g., overwrite confirmation) use `tkinter.messagebox`.
    In automated tests this can block the run waiting for user input.
    """
    try:
        import tkinter.messagebox as tk_messagebox

        monkeypatch.setattr(tk_messagebox, "askyesno", lambda *args, **kwargs: True)
        monkeypatch.setattr(tk_messagebox, "showerror", lambda *args, **kwargs: None)
        monkeypatch.setattr(tk_messagebox, "showwarning", lambda *args, **kwargs: None)
        monkeypatch.setattr(tk_messagebox, "showinfo", lambda *args, **kwargs: None)
    except Exception:
        # If Tk isn't available in the test environment, just skip patching.
        pass

# Add src directory to path for imports
import sys
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

# Import RouteAnalysis and analyze_route_gaps for creating test fixtures
from data_loader import RouteAnalysis, analyze_route_gaps

# Test data paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "tests" / "test_data"
TXDOT_DATA_PATH = DATA_DIR / "test_data_single_route.csv"

# === DATA FIXTURES ===

@pytest.fixture(scope="session")
def txdot_data():
    """Load the single-route test data for realistic testing."""
    if TXDOT_DATA_PATH.exists():
        return pd.read_csv(TXDOT_DATA_PATH)
    else:
        pytest.skip(f"Single-route test data file not found: {TXDOT_DATA_PATH}")

@pytest.fixture
def sample_highway_data():
    """Generate a small, controlled dataset for unit testing."""
    np.random.seed(42)  # Reproducible results
    milepoints = np.linspace(0, 10, 100)
    values = 5 + 2 * np.sin(milepoints) + np.random.normal(0, 0.5, 100)
    return pd.DataFrame({
        'milepoint': milepoints,
        'structural_strength_ind': values
    })

@pytest.fixture
def sample_route_analysis(sample_highway_data):
    """Generate RouteAnalysis object from sample highway data for testing."""
    return analyze_route_gaps(
        sample_highway_data,
        "milepoint",
        "structural_strength_ind",
        route_id="TEST_ROUTE",
        gap_threshold=0.5,
    )

@pytest.fixture
def edge_case_datasets():
    """Provide datasets for edge case testing."""
    return {
        'empty': pd.DataFrame(columns=['milepoint', 'structural_strength_ind']),
        'single_point': pd.DataFrame({
            'milepoint': [0.0],
            'structural_strength_ind': [5.0]
        }),
        'two_points': pd.DataFrame({
            'milepoint': [0.0, 1.0],
            'structural_strength_ind': [5.0, 3.0]
        }),
        'duplicate_milepoints': pd.DataFrame({
            'milepoint': [0.0, 0.0, 1.0, 1.0, 2.0],
            'structural_strength_ind': [5.0, 5.1, 3.0, 3.1, 4.0]
        }),
        'large_gaps': pd.DataFrame({
            'milepoint': [0.0, 10.0, 50.0, 100.0],
            'structural_strength_ind': [5.0, 3.0, 7.0, 2.0]
        })
    }

@pytest.fixture
def edge_case_route_analyses(edge_case_datasets):
    """Provide RouteAnalysis objects for edge case testing."""
    route_analyses = {}
    for case_name, data in edge_case_datasets.items():
        if len(data) >= 3:  # Only create RouteAnalysis for viable datasets
            route_analyses[case_name] = analyze_route_gaps(
                data, 
                x_column='milepoint', 
                y_column='structural_strength_ind',
                route_id=f"TEST_{case_name.upper()}",
                gap_threshold=0.5,
            )
        else:
            # For datasets too small for RouteAnalysis, keep as DataFrame
            route_analyses[case_name] = data
    return route_analyses

@pytest.fixture
def performance_test_data():
    """Generate larger dataset for performance testing."""
    np.random.seed(123)
    size = 10000
    milepoints = np.linspace(0, 1000, size)
    values = np.random.uniform(1, 10, size)
    return pd.DataFrame({
        'milepoint': milepoints,
        'structural_strength_ind': values
    })

@pytest.fixture
def multi_route_test_data():
    """Generate multi-route test data for route filter testing."""
    return pd.DataFrame({
        'RDB': ['FM1836 K', 'FM1836 K', 'FM1836 K', 'FM1936 Test', 'FM1936 Test', 'FM1936 Test'],
        'BDFO': [0.0, 0.01, 0.02, 0.0, 0.01, 0.02], 
        'EDFO': [0.01, 0.02, 0.03, 0.01, 0.02, 0.03],
        'SCI': [2.2, 0.88, 1.04, 1.8, 2.1, 1.5],
        'D00': [0.68, 10.52, 8.53, 1.2, 2.3, 1.9]
    })

@pytest.fixture  
def andre_test_multi_route_data():
    """Load the anonymized multi-route test data (TestMultiRoute.csv)."""
    test_data_path = PROJECT_ROOT / "tests" / "test_data" / "TestMultiRoute.csv"
    if test_data_path.exists():
        return pd.read_csv(test_data_path)
    else:
        # Fallback to sample data if file doesn't exist
        return pd.DataFrame({
            'FY': [2025] * 6,
            'RDB': ['FM1836 K', 'FM1836 K', 'FM1836 K', 'FM1936 Test', 'FM1936 Test', 'FM1936 Test'],
            'BDFO': [0.0, 0.01, 0.02, 0.0, 0.01, 0.02],
            'EDFO': [0.01, 0.02, 0.03, 0.01, 0.02, 0.03],
            'SCI': [2.22, 0.882, 1.039, 1.8, 2.1, 1.5]
        })

# === MOCK FIXTURES ===

@pytest.fixture
def mock_gui_app():
    """Mock GUI application for testing components in isolation."""
    mock_app = Mock()
    
    # Mock tkinter variables
    mock_app.min_length = Mock()
    mock_app.min_length.get.return_value = 1.0
    mock_app.max_length = Mock()
    mock_app.max_length.get.return_value = 5.0
    mock_app.gap_threshold = Mock()
    mock_app.gap_threshold.get.return_value = 0.1
    mock_app.population_size = Mock()
    mock_app.population_size.get.return_value = 50
    mock_app.num_generations = Mock()
    mock_app.num_generations.get.return_value = 100
    mock_app.mutation_rate = Mock()
    mock_app.mutation_rate.get.return_value = 0.1
    mock_app.crossover_rate = Mock()
    mock_app.crossover_rate.get.return_value = 0.8
    mock_app.optimization_method = 'multi'  # Direct string value, not Mock
    mock_app.custom_save_name = Mock()
    mock_app.custom_save_name.get.return_value = 'test_results'
    
    # FileManager-specific attributes  
    mock_app.data_file = Mock()
    mock_app.data_file.set = Mock()
    mock_app.data_file.get.return_value = 'No file selected'
    mock_app.x_column = Mock()
    mock_app.x_column.set = Mock()
    mock_app.x_column.get.return_value = 'milepoint'
    mock_app.y_column = Mock()
    mock_app.y_column.set = Mock()
    mock_app.y_column.get.return_value = 'structural_strength_ind'
    mock_app.available_columns = []
    mock_app._data_file_path = ''
    mock_app._save_file_path = ''
    
    # Route-specific attributes (fix for Mock iterable error)
    mock_app.available_routes = []
    mock_app.selected_routes = []
    mock_app.route_column = Mock()
    mock_app.route_column.get.return_value = "None - treat as single route"
    
    # Mock UI route components  
    mock_app._update_route_info_display = Mock()
    
    # Mock data
    mock_app.data = None
    mock_app.is_running = False
    mock_app.stop_requested = False
    
    # Mock UI components
    mock_app.root = Mock()
    mock_app.log_message = Mock()
    
    # Mock UI builder components
    mock_app.ui_builder = Mock()
    mock_app.ui_builder.get_parameter_values.return_value = {
        'min_length': 1.0,
        'max_length': 5.0,
        'gap_threshold': 0.1
    }
    
    # Mock additional required attributes for parameter manager
    mock_app.target_avg_length = Mock()
    mock_app.target_avg_length.get.return_value = 3.0
    mock_app.penalty_weight = Mock()
    mock_app.penalty_weight.get.return_value = 1000.0
    mock_app.length_tolerance = Mock()
    mock_app.length_tolerance.get.return_value = 0.2
    mock_app.cache_clear_interval = Mock()
    mock_app.cache_clear_interval.get.return_value = 50
    mock_app.elite_ratio = Mock()
    mock_app.elite_ratio.get.return_value = 0.1
    
    return mock_app

@pytest.fixture
def mock_optimization_result():
    """Mock optimization result for testing result handlers."""
    return {
        'population': [
            np.array([0.0, 2.5, 5.0, 7.5, 10.0]),
            np.array([0.0, 3.0, 6.0, 10.0]),
            np.array([0.0, 1.5, 4.0, 8.0, 10.0])
        ],
        'fitness_values': [
            (0.15, 2.5),  # (deviation, avg_length)
            (0.20, 3.3),
            (0.12, 2.0)
        ],
        'pareto_front': [0, 2],  # Indices of Pareto optimal solutions
        'best_fitness': 0.12,
        'best_chromosome': np.array([0.0, 1.5, 4.0, 8.0, 10.0]),
        'best_avg_length': 2.0,
        'length_deviation': 0.5,
        'elapsed_time': 15.2,
        'mandatory_breakpoints': {0.0, 10.0}
    }

# === FILE SYSTEM FIXTURES ===

@pytest.fixture
def temp_directory():
    """Provide temporary directory for file testing, cleaned up after test."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def temp_csv_file(temp_directory, sample_highway_data):
    """Create temporary CSV file with sample data."""
    file_path = os.path.join(temp_directory, 'test_data.csv')
    sample_highway_data.to_csv(file_path, index=False)
    return file_path

# === PHASE 1 ROUTE PROCESSING FIXTURES ===

@pytest.fixture
def multi_route_sample_data():
    """Generate multi-route sample data for Phase 1 testing."""
    return pd.DataFrame({
        'route': ['US-35', 'US-35', 'US-35', 'I-75', 'I-75', 'I-75', 
                  'SR-123', 'SR-123', 'SR-123', 'US-50', 'US-50'],
        'milepoint': [0.0, 0.1, 0.2, 0.0, 0.1, 0.2, 0.0, 0.1, 0.2, 0.0, 0.1],
        'structural_strength_ind': [5.2, 5.1, 4.9, 6.1, 6.0, 5.8, 4.5, 4.2, 3.8, 5.5, 5.3]
    })

@pytest.fixture
def temp_multi_route_csv(temp_directory, multi_route_sample_data):
    """Create temporary CSV file with multi-route data for testing."""
    file_path = os.path.join(temp_directory, 'multi_route_data.csv')
    multi_route_sample_data.to_csv(file_path, index=False)
    return file_path

@pytest.fixture
def route_test_cases():
    """Provide various route data scenarios for comprehensive testing."""
    return {
        'basic_routes': ['US-35', 'I-75', 'SR-123'],
        'interstate_only': ['I-75', 'I-71', 'I-70'],
        'us_routes_only': ['US-35', 'US-50', 'US-23'],
        'state_routes_only': ['SR-123', 'SR-456', 'SR-789'],
        'mixed_with_nulls': ['US-35', 'I-75', None, 'SR-123'],
        'single_route': ['US-35'],
        'empty_routes': [],
        'duplicate_routes': ['US-35', 'US-35', 'I-75', 'I-75', 'SR-123'],
        'numeric_routes': ['1', '2', '35', '75', '123'],
        'alphanumeric_mix': ['US-35A', 'I-75N', 'SR-123E', 'Route-1']
    }

@pytest.fixture
def mock_route_app():
    """Mock app specifically configured for route processing testing."""
    mock_app = Mock()
    
    # Route-specific attributes
    mock_app.available_routes = []
    mock_app.selected_routes = []
    mock_app.route_column = Mock()
    mock_app.route_column.get.return_value = "route"
    mock_app.available_columns = []
    
    # Data and file management
    mock_app.data_file_path = Mock()
    mock_app.data_file_path.get.return_value = ""
    
    # UI components for route handling
    mock_app.column_dropdown = Mock()
    mock_app.strength_dropdown = Mock()
    mock_app.route_dropdown = Mock()
    mock_app.route_info_label = Mock()
    mock_app.route_info_label.config = Mock()
    
    # Configure dropdown mocks
    for dropdown in [mock_app.column_dropdown, mock_app.strength_dropdown, mock_app.route_dropdown]:
        dropdown.__getitem__ = Mock(return_value=Mock())
        dropdown.__setitem__ = Mock()
        dropdown.set = Mock()
        dropdown.get = Mock()
    
    # File manager integration  
    mock_app.file_manager = Mock()
    mock_app.file_manager.detect_available_routes = Mock()
    mock_app.file_manager.get_data_file_path = Mock()
    
    # Logging
    mock_app.log_message = Mock()
    
    return mock_app

@pytest.fixture
def route_filter_test_data():
    """Test data specifically for route filter dialog testing."""
    return {
        'all_routes': ['US-35', 'US-50', 'US-23', 'I-75', 'I-71', 'I-77', 'SR-123', 'SR-456', 'SR-789'],
        'initial_selected': ['US-35', 'I-75'],
        'search_scenarios': {
            'US': ['US-35', 'US-50', 'US-23'],
            'I-': ['I-75', 'I-71', 'I-77'],
            'SR': ['SR-123', 'SR-456', 'SR-789'],
            '35': ['US-35'],
            '7': ['I-75', 'I-71', 'I-77']
        }
    }

@pytest.fixture(scope="module")
def tkinter_root():
    """Create tkinter root window for UI testing - module scoped for efficiency."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()  # Hide the window during testing
    yield root
    root.destroy()

@pytest.fixture
def phase1_integration_data():
    """Comprehensive data set for Phase 1 integration testing."""
    return """route,milepoint,structural_strength_ind,pavement_condition,traffic_volume
US-35,0.0,5.2,85,15000
US-35,0.1,5.1,83,14800
US-35,0.2,4.9,82,14600
US-35,0.3,4.8,80,14400
I-75,0.0,6.1,92,25000
I-75,0.1,6.0,91,24800
I-75,0.2,5.8,89,24600
I-75,0.3,5.7,88,24400
SR-123,0.0,4.5,75,8000
SR-123,0.1,4.2,73,7800
SR-123,0.2,3.8,70,7600
SR-123,0.3,3.5,68,7400
US-50,0.0,5.5,87,12000
US-50,0.1,5.3,85,11800
I-71,0.0,6.2,94,22000
I-71,0.1,6.1,93,21800"""

# === PARAMETER FIXTURES ===

@pytest.fixture
def valid_parameters():
    """Standard valid parameter set for testing."""
    return {
        'min_length': 1.0,
        'max_length': 5.0,
        'gap_threshold': 0.1,
        'population_size': 50,
        'num_generations': 100,
        'mutation_rate': 0.1,
        'crossover_rate': 0.8,
        'elite_ratio': 0.1,
        'target_avg_length': 3.0,
        'penalty_weight': 1000.0,
        'length_tolerance': 0.2
    }

@pytest.fixture
def invalid_parameters():
    """Invalid parameter sets for validation testing."""
    return {
        'negative_population': {'population_size': -10},
        'zero_generations': {'num_generations': 0},
        'invalid_mutation_rate': {'mutation_rate': 1.5},  # > 1.0
        'min_greater_than_max': {'min_length': 5.0, 'max_length': 1.0},
        'negative_gap_threshold': {'gap_threshold': -0.1}
    }

# === ALGORITHM TEST FIXTURES ===

@pytest.fixture
def simple_chromosomes():
    """Simple chromosome population for genetic algorithm testing."""
    return [
        np.array([0.0, 2.5, 5.0, 10.0]),
        np.array([0.0, 3.0, 6.0, 10.0]),
        np.array([0.0, 1.5, 4.0, 8.0, 10.0]),
        np.array([0.0, 2.0, 4.5, 7.0, 10.0])
    ]

# === PYTEST CONFIGURATION ===

@pytest.fixture(autouse=True)
def patch_optimization_config(monkeypatch):
    """Patch the optimization_config object with backwards-compatible attributes for tests.
    
    This fixture provides the missing default attributes that tests expect from the 
    old config system, without modifying core application code.
    """
    # Create a mock config object with both old and new attributes
    class TestOptimizationConfig:
        # Current attributes (keep existing functionality)
        init_population_max_retries = 10
        max_retries_chromosome_generation = 10  # backwards-compat alias
        operator_max_retries = 4
        tournament_size = 3
        elitism_logging_frequency = 20
        min_front_size = 2
        cache_clear_interval = 50
        
        # Backwards compatibility attributes for tests
        population_size_default = 50
        mutation_rate_default = 0.1
        crossover_rate_default = 0.8
        gap_threshold_default = 0.1
        elite_ratio_default = 0.1
        single_objective_generations = 200
        multi_objective_generations = 300
        constrained_generations = 250
    
    test_config = TestOptimizationConfig()
    
    # Patch all modules that import optimization_config
    modules_to_patch = [
        'analysis.utils.genetic_algorithm',
        'optimization_controller', 
        'optimization_runners',
        'parameter_manager'
    ]
    
    for module_name in modules_to_patch:
        try:
            monkeypatch.setattr(f'{module_name}.optimization_config', test_config)
        except (ImportError, AttributeError):
            # Module may not be imported yet, which is fine
            pass
    
    # Also patch the config module itself
    try:
        import config
        monkeypatch.setattr(config, 'optimization_config', test_config)
    except ImportError:
        pass
    
    return test_config

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "ui: User interface tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "data_dependent: Tests requiring data files")