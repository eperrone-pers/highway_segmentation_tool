# Highway Segmentation GA - Test Suite

This directory contains comprehensive test suites for the Highway Segmentation Genetic Algorithm application.

## Test Structure

```
tests/
├── conftest.py                 # Test configuration and fixtures
├── test_genetic_algorithm.py   # Legacy GA tests (converted to pytest)
├── unit/                      # Unit tests for individual components
│   ├── test_parameter_manager.py
│   ├── test_file_manager.py
│   └── test_optimization_algorithms.py
├── integration/               # Integration tests
│   └── test_component_integration.py
├── ui/                       # GUI tests (future expansion)
└── test_data/                # Sample test datasets
    └── sample_highway_data.csv
```

## Running Tests

## Regression Gate (Primary CI/Quality Signal)

Run this first after setup (it should be green before sharing results/changes):

```bash
python -m pytest tests/regression -q
```

### Prerequisites

Install dependencies (includes testing framework):
```bash
pip install -r requirements.txt
```

### Quick Start

```bash
# Run all tests
python run_tests.py --all

# Run specific test categories
python run_tests.py --unit
python run_tests.py --integration

# Run with coverage report
python run_tests.py --coverage

# Run specific test file
python run_tests.py --file tests/unit/test_parameter_manager.py

# Run tests matching a pattern
python run_tests.py --pattern "test_validate"
```

### Using pytest directly

```bash
# All tests
pytest

# Unit tests only
pytest -m unit tests/unit/

# Integration tests
pytest -m integration tests/integration/

# With verbose output
pytest -v

# With coverage
pytest --cov=src --cov-report=html
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation:

- **ParameterManager**: Parameter validation, settings persistence, method-specific parameters
- **FileManager**: Data loading, validation, file operations, result display
- **Optimization Algorithms**: NSGA-II, single-objective, constrained optimization core functions

**Markers**: `@pytest.mark.unit`

### Integration Tests (`tests/integration/`)

Test component interactions and end-to-end workflows:

- Complete optimization workflow (load data → set parameters → optimize → save results)
- Settings persistence across components
- JSON results generation and validation workflow
- Error propagation between components

**Markers**: `@pytest.mark.integration`

### Performance Tests

Long-running tests for performance benchmarking:

- Large dataset optimization
- Memory usage validation
- Algorithm convergence analysis  

**Markers**: `@pytest.mark.performance`, `@pytest.mark.slow`

## Test Data

### Fixtures Available

- `txdot_data`: Real TxDOT highway dataset (if available)
- `sample_highway_data`: Small synthetic dataset for quick tests
- `edge_case_datasets`: Edge cases (empty, single point, duplicates, gaps)
- `performance_test_data`: Large dataset for performance testing
- `mock_gui_app`: Mock GUI application with all required attributes

### Mock Objects

- `mock_optimization_result`: Standard optimization result structure
- `valid_parameters`/`invalid_parameters`: Parameter validation test sets
- `temp_directory`: Temporary directory with automatic cleanup

## Writing New Tests

### Test File Structure

```python
"""
Test description.
"""

import pytest
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from your_module import YourClass

class TestYourClass:
    """Test suite for YourClass."""
    
    @pytest.mark.unit
    def test_basic_functionality(self, mock_gui_app):
        """Test basic functionality."""
        instance = YourClass(mock_gui_app)
        result = instance.some_method()
        assert result == expected_value
```

### Best Practices

1. **Use appropriate markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
2. **Use fixtures**: Leverage existing fixtures for mock objects and test data
3. **Test edge cases**: Empty data, invalid parameters, error conditions
4. **Mock external dependencies**: File I/O, GUI components, long-running operations
5. **Keep tests fast**: Unit tests should run in milliseconds, use small datasets
6. **Clear test names**: Method names should describe what is being tested
7. **One assertion per concept**: Test one specific behavior per test method

### Adding Test Data

Add new test datasets to `tests/test_data/`:

```python
# In conftest.py
@pytest.fixture
def your_test_data():
    """Description of your test data."""
    return pd.read_csv("tests/test_data/your_data.csv")
```

## Coverage Goals

- **Unit Tests**: >90% code coverage for individual components
- **Integration Tests**: Cover all major workflows and component interactions
- **Edge Cases**: All error conditions and boundary values tested
- **Real Data**: At least smoke tests with actual TxDOT dataset

## Continuous Integration

The test suite is designed to run in CI/CD environments:

```yaml
# Example GitHub Actions
- name: Run Tests
  run: |
    pip install -r requirements.txt
    python run_tests.py --coverage
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure `src` directory is in Python path
2. **Missing dependencies**: Install `requirements.txt`
3. **Slow tests**: Use `pytest -m "not slow"` to skip performance tests
4. **GUI test issues**: Use headless mode: `export DISPLAY=:99` (Linux)

### Debug Mode

```bash
# Run with debug output
pytest -vvv -s tests/unit/test_your_test.py::TestClass::test_method
```

### Test Coverage

View detailed coverage report:
```bash
python run_tests.py --coverage
# Open htmlcov/index.html in browser
```