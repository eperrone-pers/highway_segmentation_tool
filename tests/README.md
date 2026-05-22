# Highway Segmentation Tool - Test Suite

This directory contains the automated test suites for the Highway Segmentation Tool application.

## Test Structure

```text
tests/
├── conftest.py                         # Shared fixtures and test helpers
├── unit/                              # Focused unit tests
├── integration/                       # End-to-end and workflow integration tests
├── regression/                        # Regression gates and output validation
├── ui/                                # GUI-focused tests
├── test_data/                         # Sample datasets used by tests
├── test_cli_*.py                      # CLI / run-spec coverage
├── test_preprocessing_*.py            # Preprocessing framework coverage
├── test_visualization_*.py            # Visualization data-prep and rendering logic
├── test_*controller*.py               # Controller behavior across methods and flows
└── run_phase*_tests.py / run_*.py     # Legacy convenience scripts for targeted suites
```

## Running Tests

## Recommended Test Lanes

Use the lightest lane that answers the question you have:

### Smoke Suite (default local workflow)

Fast local gate for active development. Excludes regression and performance suites.

```bash
python run_tests.py --smoke
```

Equivalent pytest command:

```bash
python -m pytest tests/ -m "not regression and not performance"
```

### Regression Gate (primary branch quality signal)

Run this before sharing results or merging behavior changes:

```bash
python run_tests.py --regression
```

Equivalent pytest command:

```bash
python -m pytest tests/regression -q
```

### Full Suite

Runs the full suite except performance benchmarks:

```bash
python run_tests.py --full
```

### Prerequisites

Install dependencies (includes testing framework):

```bash
pip install -r requirements.txt
```

### Quick Start

```bash
# Default fast local run
python run_tests.py

# Explicit fast local run
python run_tests.py --smoke

# Regression gate
python run_tests.py --regression

# Full suite except performance
python run_tests.py --full

# Run specific test categories
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --ui

# Run with coverage report
python run_tests.py --coverage

# Run specific test file
python run_tests.py --file tests/unit/test_parameter_manager.py

# Run tests matching a pattern
python run_tests.py --pattern "test_validate"
```

### Using pytest directly

```bash
# Default root run uses pytest.ini defaults
python -m pytest

# Full suite except performance
python -m pytest tests/ -m "not performance"

# Fast local suite
python -m pytest tests/ -m "not regression and not performance"

# Unit tests only
python -m pytest -m unit tests/unit/

# Integration tests
python -m pytest -m integration tests/integration/

# UI tests
python -m pytest -m ui tests/ui/

# With verbose output
python -m pytest -v

# With coverage
python -m pytest --cov=src --cov-report=html
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation:

- **Parameter and settings logic**: parameter validation, defaults, JSON round-tripping, settings behavior
- **Method-specific behavior**: AASHTO CDA, attribute-must-break handling, numeric parameter parsing
- **Results/export helpers**: JSON result shaping, Excel export, parameter restoration

**Markers**: `@pytest.mark.unit`

### Integration Tests (`tests/integration/`)

Test component interactions and end-to-end workflows:

- Analysis method objective integration
- JSON validation workflow
- Complete workflow coverage across routes and preprocessing
- Gap-analysis demos and cross-component interactions

**Markers**: `@pytest.mark.integration`

### Regression Tests (`tests/regression/`)

Regression tests are the primary branch-quality gate for this repo:

- Complete workflow regression across representative GUI/controller cases
- Full CLI workflow regression across the complete method/dataset matrix
- Preprocessing workflow regression
- PELT regression coverage

Notes:

- The CLI regression suite is the exhaustive matrix.
- The GUI/controller regression suite is intentionally smaller and representative.
- The CLI/GUI structure-equivalence test is opt-in and only runs when persisted artifacts are enabled.

Primary command:

```bash
python run_tests.py --regression
```

See `tests/regression/README.md` for the detailed regression matrix and artifact layout.

### Performance Tests

Long-running tests for performance benchmarking:

- Large dataset optimization
- Performance-oriented controller / algorithm checks
- Slow-running scenarios separated via markers

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
import pytest

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

Note: the shared `tests/conftest.py` already adds `src/` to `sys.path`, so most new tests do not need to modify `sys.path` manually.

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
        python run_tests.py --regression
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure `src` directory is in Python path
2. **Missing dependencies**: Install `requirements.txt`
3. **Slow tests**: Use `python run_tests.py --smoke` for the normal local lane, or `python -m pytest -m "not slow and not regression"`
4. **GUI test issues**: Use headless mode: `export DISPLAY=:99` (Linux)

### Regression Artifacts

Regression tests now default to isolated `tmp_path` outputs so stale files do not affect later runs.

To keep JSON/Excel artifacts under `tests/regression/outputs/` for manual inspection, enable:

```bash
HST_KEEP_REGRESSION_ARTIFACTS=1
```

On Windows PowerShell:

```powershell
$env:HST_KEEP_REGRESSION_ARTIFACTS = "1"
python run_tests.py --regression
```

### Debug Mode

```bash
# Run with debug output
python -m pytest -vvv -s tests/unit/test_your_test.py::TestClass::test_method
```

### Test Coverage

View detailed coverage report:

```bash
python run_tests.py --coverage
# Open htmlcov/index.html in browser
```

---

## Quick Examples for Common Testing Tasks

### Example 1: Testing a New Parameter

When you add a new parameter to `src/config.py`, add validation tests:

```python
# In tests/unit/test_parameter_manager.py

@pytest.mark.unit
def test_new_parameter_validation(self):
    """Test that new parameter accepts valid values and rejects invalid ones."""
    manager = ParameterManager()
    
    # Test valid values
    assert manager.validate_parameter("my_new_param", 10.5) is True
    assert manager.validate_parameter("my_new_param", 0.1) is True
    
    # Test invalid values
    assert manager.validate_parameter("my_new_param", -5) is False
    assert manager.validate_parameter("my_new_param", "invalid") is False
    
    # Test boundary conditions
    assert manager.validate_parameter("my_new_param", 0.0) is True
    assert manager.validate_parameter("my_new_param", 100.0) is True

@pytest.mark.unit
def test_new_parameter_default_value(self):
    """Test that new parameter has correct default value."""
    manager = ParameterManager()
    params = manager.get_default_parameters("your_method")
    
    assert "my_new_param" in params
    assert params["my_new_param"] == 5.0  # Expected default
```

### Example 2: Testing a New Analysis Method

Complete test suite for a new analysis method:

```python
# In tests/integration/test_new_method.py

import pytest
import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from analysis.methods.your_new_method import YourNewMethod
from optimization_controller import RouteAnalysis

class TestYourNewMethod:
    """Test suite for YourNewMethod."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        return pd.DataFrame({
            'milepoint': np.linspace(0, 10, 101),
            'value': np.sin(np.linspace(0, 10, 101)) + np.random.normal(0, 0.1, 101)
        })
    
    @pytest.fixture
    def route_analysis(self, sample_data):
        """Create RouteAnalysis object."""
        return RouteAnalysis(
            route_id="TestRoute",
            x=sample_data['milepoint'].values,
            y=sample_data['value'].values,
            gap_threshold=0.5
        )
    
    @pytest.fixture
    def method_params(self):
        """Default parameters for the method."""
        return {
            'param1': 10,
            'param2': 0.5,
            'param3': True
        }
    
    @pytest.mark.integration
    def test_basic_execution(self, route_analysis, method_params):
        """Test that method runs without errors."""
        method = YourNewMethod()
        result = method.run_analysis(route_analysis, **method_params)
        
        assert result is not None
        assert len(result.breakpoints) > 0
        assert result.breakpoints[0] == route_analysis.x[0]  # First point
        assert result.breakpoints[-1] == route_analysis.x[-1]  # Last point
    
    @pytest.mark.integration
    def test_respects_mandatory_breakpoints(self, sample_data, method_params):
        """Test that method respects mandatory breakpoints from gaps."""
        # Create data with a gap
        x = np.concatenate([np.linspace(0, 5, 50), np.linspace(6, 10, 50)])
        y = np.sin(x) + np.random.normal(0, 0.1, 100)
        
        route_analysis = RouteAnalysis(
            route_id="GapTest",
            x=x,
            y=y,
            gap_threshold=0.5  # Gap at 5.0 should force breakpoint
        )
        
        method = YourNewMethod()
        result = method.run_analysis(route_analysis, **method_params)
        
        # Should have breakpoint near the gap
        gap_breakpoints = [bp for bp in result.breakpoints if 4.9 <= bp <= 6.1]
        assert len(gap_breakpoints) > 0, "Method should respect mandatory gap breakpoints"
    
    @pytest.mark.integration
    def test_segment_length_constraints(self, route_analysis, method_params):
        """Test that method respects min/max length constraints."""
        method_params['min_length'] = 1.0
        method_params['max_length'] = 3.0
        
        method = YourNewMethod()
        result = method.run_analysis(route_analysis, **method_params)
        
        # Calculate segment lengths
        breakpoints = result.breakpoints
        segment_lengths = np.diff(breakpoints)
        
        # Allow small tolerance for edge cases
        assert np.all(segment_lengths >= 0.95), f"Min length violated: {segment_lengths.min()}"
        assert np.all(segment_lengths <= 3.05), f"Max length violated: {segment_lengths.max()}"
    
    @pytest.mark.integration
    def test_parameter_sensitivity(self, route_analysis):
        """Test that parameter changes affect results appropriately."""
        method = YourNewMethod()
        
        # Run with conservative parameters
        conservative_params = {'param1': 5, 'param2': 0.1}
        result_conservative = method.run_analysis(route_analysis, **conservative_params)
        
        # Run with aggressive parameters
        aggressive_params = {'param1': 20, 'param2': 0.9}
        result_aggressive = method.run_analysis(route_analysis, **aggressive_params)
        
        # Results should differ based on parameters
        assert len(result_conservative.breakpoints) != len(result_aggressive.breakpoints), \
            "Parameter changes should affect segmentation"
    
    @pytest.mark.integration
    def test_deterministic_behavior(self, route_analysis, method_params):
        """Test that method produces consistent results (if deterministic)."""
        method = YourNewMethod()
        
        result1 = method.run_analysis(route_analysis, **method_params)
        result2 = method.run_analysis(route_analysis, **method_params)
        
        # For deterministic methods, results should be identical
        np.testing.assert_array_equal(
            result1.breakpoints, 
            result2.breakpoints,
            err_msg="Deterministic method should produce identical results"
        )
        
        # For stochastic methods, comment out above and test similarity:
        # similarity = len(set(result1.breakpoints) & set(result2.breakpoints)) / len(result1.breakpoints)
        # assert similarity > 0.8, "Stochastic method should produce similar results"
    
    @pytest.mark.integration
    def test_json_output_format(self, route_analysis, method_params):
        """Test that method produces schema-compliant output."""
        method = YourNewMethod()
        result = method.run_analysis(route_analysis, **method_params)
        
        # Check required fields
        assert hasattr(result, 'breakpoints')
        assert hasattr(result, 'fitness') or hasattr(result, 'total_deviation')
        assert hasattr(result, 'segment_stats')
        
        # Check segment stats structure
        for segment in result.segment_stats:
            assert 'start' in segment
            assert 'end' in segment
            assert 'length' in segment
            assert 'mean' in segment
            assert 'std' in segment
```

### Example 3: Parametrized Test for Multiple Scenarios

Test the same logic across different data configurations:

```python
@pytest.mark.parametrized
@pytest.mark.parametrize("gap_threshold,expected_mandatory_breaks", [
    (0.5, 2),   # Large threshold -> fewer breaks
    (0.1, 5),   # Small threshold -> more breaks
    (1.0, 1),   # Very large -> minimal breaks
])
def test_gap_threshold_sensitivity(self, gap_threshold, expected_mandatory_breaks):
    """Test how gap threshold affects mandatory breakpoint detection."""
    # Create data with known gaps
    x = np.concatenate([
        np.linspace(0, 2, 20),
        np.linspace(2.6, 4, 20),
        np.linspace(4.8, 6, 20),
        np.linspace(7.0, 9, 20)
    ])
    y = np.sin(x)
    
    route_analysis = RouteAnalysis(
        route_id="GapTest",
        x=x,
        y=y,
        gap_threshold=gap_threshold
    )
    
    # Check mandatory breakpoints detected
    assert len(route_analysis.mandatory_breakpoints) == expected_mandatory_breaks

@pytest.mark.parametrized
@pytest.mark.parametrize("method_key,min_segments,max_segments", [
    ("single", 5, 50),
    ("multi", 5, 50),
    ("constrained", 8, 15),  # Constrained should target specific range
    ("aashto_cda", 10, 100),
])
def test_method_produces_reasonable_segmentation(self, method_key, min_segments, max_segments):
    """Test that each method produces sensible number of segments."""
    # Use standard test data
    data = load_test_data("test_data_single_route.csv")
    
    # Run method
    result = run_optimization_for_method(method_key, data)
    
    num_segments = len(result.breakpoints) - 1
    assert min_segments <= num_segments <= max_segments, \
        f"{method_key} produced {num_segments} segments (expected {min_segments}-{max_segments})"
```

### Example 4: Mocking GUI Components

Test controller logic without launching actual GUI:

```python
@pytest.fixture
def mock_gui_app(self):
    """Create a mock GUI application with all required attributes."""
    class MockGUIApp:
        def __init__(self):
            self.data = None
            self.results = None
            self.status_text = ""
            self.progress_value = 0
            
        def update_status(self, message):
            self.status_text = message
            
        def update_progress(self, value):
            self.progress_value = value
            
        def show_error(self, message):
            self.error_message = message
            
        def load_data(self, filepath):
            self.data = pd.read_csv(filepath)
            
    return MockGUIApp()

@pytest.mark.integration
def test_optimization_controller_with_mock_gui(self, mock_gui_app):
    """Test controller workflow using mock GUI."""
    from optimization_controller import OptimizationController
    
    controller = OptimizationController(mock_gui_app)
    
    # Configure parameters
    params = {
        'method': 'single',
        'population_size': 50,
        'generations': 20,
        'min_length': 0.5,
        'max_length': 10.0
    }
    
    # Run optimization
    result = controller.run_optimization("data/test_data_single_route.csv", params)
    
    # Verify mock was updated
    assert mock_gui_app.progress_value == 100
    assert "complete" in mock_gui_app.status_text.lower()
    assert mock_gui_app.results is not None
```

### Example 5: JSON Schema Validation

Validate that results comply with the JSON schema:

```python
@pytest.mark.integration
def test_result_matches_schema(self):
    """Test that optimization results match the JSON schema."""
    import json
    import jsonschema
    
    # Load schema
    with open('src/highway_segmentation_results_schema.json', 'r') as f:
        schema = json.load(f)
    
    # Run optimization and get results
    result_json = run_optimization_and_save_json("single", "test_data_single_route.csv")
    
    with open(result_json, 'r') as f:
        result_data = json.load(f)
    
    # Validate against schema
    try:
        jsonschema.validate(instance=result_data, schema=schema)
    except jsonschema.exceptions.ValidationError as e:
        pytest.fail(f"Result JSON does not match schema: {e.message}")
```

---

## Step-by-Step: Adding a New Analysis Method

### Step 1: Implement the Method

```python
# In src/analysis/methods/my_new_method.py

from src.analysis.analysis_base import AnalysisMethodBase

class MyNewMethod(AnalysisMethodBase):
    """Your new analysis method."""
    
    def run_analysis(self, route_analysis, **params):
        """Run the analysis."""
        # Implementation here
        pass
```

### Step 2: Register in Config

```python
# In src/config.py

from src.analysis.methods.my_new_method import MyNewMethod

OPTIMIZATION_METHODS = {
    # ... existing methods ...
    "my_new_method": {
        "display_name": "My New Method",
        "description": "Description of what it does",
        "method_class": MyNewMethod,
        "parameters": [
            NumericParameter("param1", 10, "Description", min_val=1, max_val=100),
            # ... more parameters ...
        ]
    }
}
```

### Step 3: Add Unit Tests

Create `tests/unit/test_my_new_method.py` with basic functionality tests:

```python
class TestMyNewMethodCore:
    """Unit tests for core algorithm logic."""
    
    @pytest.mark.unit
    def test_initialization(self):
        """Test method initializes correctly."""
        method = MyNewMethod()
        assert method is not None
    
    @pytest.mark.unit
    def test_parameter_handling(self):
        """Test parameter validation."""
        method = MyNewMethod()
        # Test valid parameters
        # Test invalid parameters
```

### Step 4: Add Integration Tests

Create `tests/integration/test_my_new_method_integration.py`:

```python
class TestMyNewMethodIntegration:
    """Integration tests for complete workflow."""
    
    @pytest.mark.integration
    def test_end_to_end_workflow(self):
        """Test complete analysis workflow."""
        # Load data -> Run method -> Validate output
        pass
```

### Step 5: Add to Regression Suite

Edit `tests/regression/test_parameters_template.json`:

```json
{
  "method_specific": {
    "single": { ... },
    "multi": { ... },
    "my_new_method": {
      "param1": 10,
      "param2": 0.5,
      "min_length": 0.5,
      "max_length": 10.0
    }
  }
}
```

The regression suite will automatically pick up your new method and test it!

### Step 6: Verify Regression Tests Pass

```bash
python -m pytest tests/regression -v -k "my_new_method"
```

You should see tests for both single_route and multi_route datasets.

### Step 7: Add Method-Specific Documentation

Create `src/analysis/methods/docs/my_new_method/README.md` explaining:

- Method purpose and theory
- Parameter guidance
- Use cases
- Examples

---

## Step-by-Step: Adding a Test Case to Regression Suite

### Scenario: Add a new test dataset

**Step 1**: Add data file to `data/` or `tests/test_data/`:

```bash
# Add your new CSV
cp my_new_test_data.csv tests/test_data/
```

**Step 2**: Update `tests/regression/conftest.py` to include new dataset:

```python
@pytest.fixture
def dataset_configs():
    """Define all dataset configurations."""
    return {
        "single_route": {
            "file": "test_data_single_route.csv",
            "x_col": "milepoint",
            "y_col": "structural_strength_ind",
            "route_col": None
        },
        "multi_route": {
            "file": "TestMultiRoute.csv",
            "x_col": "BDFO",
            "y_col": "D60",
            "route_col": "RDB"
        },
        "my_new_dataset": {  # ADD THIS
            "file": "my_new_test_data.csv",
            "x_col": "distance",
            "y_col": "condition_index",
            "route_col": None
        }
    }
```

**Step 3**: The parametrized tests automatically run with new dataset:

```bash
python -m pytest tests/regression -v
```

You'll now see tests for:

- `single_single_route`
- `single_multi_route`
- `single_my_new_dataset`  ← NEW
- `multi_single_route`
- etc.

---

## Common Testing Patterns

### Pattern 1: Testing with Edge Cases

```python
@pytest.mark.parametrize("edge_case", [
    "empty_data",
    "single_point",
    "two_points",
    "all_same_values",
    "extreme_outliers",
    "missing_values"
])
def test_edge_cases(self, edge_case):
    """Test method handles edge cases gracefully."""
    data = create_edge_case_data(edge_case)
    
    if edge_case in ["empty_data", "single_point"]:
        with pytest.raises(ValueError):
            run_analysis(data)
    else:
        result = run_analysis(data)
        assert result is not None
```

### Pattern 2: Testing Error Messages

```python
def test_helpful_error_messages(self):
    """Test that errors provide actionable guidance."""
    with pytest.raises(ValueError) as exc_info:
        run_analysis_with_invalid_params()
    
    error_msg = str(exc_info.value)
    assert "min_length" in error_msg
    assert "must be greater than 0" in error_msg
```

### Pattern 3: Testing File Output

```python
def test_creates_valid_output_files(self, tmp_path):
    """Test that output files are created and valid."""
    output_path = tmp_path / "results.json"
    
    run_analysis_and_save(output_path)
    
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    
    # Verify contents
    with open(output_path, 'r') as f:
        data = json.load(f)
        assert "route_results" in data
```

### Pattern 4: Performance Benchmarking

```python
@pytest.mark.performance
@pytest.mark.slow
def test_performance_benchmark(self, benchmark):
    """Benchmark method performance."""
    large_data = create_large_dataset(n_points=10000)
    
    result = benchmark(
        lambda: run_analysis(large_data),
        rounds=5,
        iterations=1
    )
    
    # Verify performance is acceptable
    assert result.stats['mean'] < 60.0  # Should complete in < 60 seconds
```

---

## Troubleshooting Test Failures

### Issue: "Module not found" errors

**Solution**: Ensure src is in path at top of test file:

```python
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
```

### Issue: Tests pass individually but fail when run together

**Cause**: Tests are sharing state or not cleaning up properly.

**Solution**: Use fixtures with proper cleanup:

```python
@pytest.fixture
def isolated_test_env(tmp_path):
    """Create isolated environment for test."""
    original_dir = os.getcwd()
    os.chdir(tmp_path)
    
    yield tmp_path
    
    os.chdir(original_dir)  # Cleanup
```

### Issue: Regression tests fail after code change

**Step 1**: Determine if change is intentional:

```bash
# Run specific failing test with verbose output
python -m pytest tests/regression -v -k "failing_test_name"
```

**Step 2**: If behavior change is intentional, update test expectations:

- Update `test_parameters_template.json` if default parameters changed
- Update assertions if output format changed
- Regenerate reference outputs if schema changed

**Step 3**: If behavior change is unintentional, debug:

```bash
# Run with debug output
python -m pytest tests/regression -vvv -s -k "failing_test_name"
```

### Issue: Schema validation fails

**Solution**: Check the schema version and result structure:

```python
# Add debug output to see what's failing
import jsonschema
try:
    jsonschema.validate(instance=result, schema=schema)
except jsonschema.exceptions.ValidationError as e:
    print(f"Field: {e.path}")
    print(f"Message: {e.message}")
    print(f"Schema: {e.schema}")
```

### Issue: Slow test suite

**Solutions**:

1. Skip slow tests during development: `pytest -m "not slow"`
2. Run specific test files: `pytest tests/unit/test_specific.py`
3. Use smaller test datasets for unit tests
4. Mock expensive operations (file I/O, optimization)

---

## For AI Agents: Test Generation Guidelines

When generating tests for this codebase:

### Required Imports

```python
import pytest
import sys
import os
import numpy as np
import pandas as pd

# Always add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
```

### Fixture Pattern

```python
@pytest.fixture
def component_under_test():
    """Clear docstring explaining what fixture provides."""
    # Setup
    instance = create_test_instance()
    
    yield instance
    
    # Teardown (if needed)
    instance.cleanup()
```

### Test Method Pattern

```python
@pytest.mark.unit  # or .integration, .performance
def test_specific_behavior_under_specific_condition(self, fixture_name):
    """
    Test that [component] [does what] when [condition].
    
    This test verifies [specific behavior/requirement].
    """
    # Arrange
    setup_test_data()
    
    # Act
    result = perform_action()
    
    # Assert
    assert result == expected_value, "Helpful failure message"
```

### Coverage Checklist for New Methods

When adding a new analysis method, generate tests for:

- ✅ Basic initialization and parameter handling
- ✅ Execution with valid inputs (happy path)
- ✅ Mandatory breakpoint respect
- ✅ Length constraint enforcement (if applicable)
- ✅ Edge cases (empty, single point, gaps)
- ✅ Error handling and messages
- ✅ Determinism (if applicable)
- ✅ JSON output format compliance
- ✅ Integration with controller
- ✅ Regression suite inclusion

### Test Naming Conventions

- `test_[method]_[scenario]_[expected_outcome]`
- Examples:
  - `test_initialization_with_valid_params_succeeds`
  - `test_run_analysis_with_gaps_creates_mandatory_breaks`
  - `test_validate_params_with_negative_value_raises_error`

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run regression gate
      run: python -m pytest tests/regression -q
    
    - name: Run full test suite
      run: python -m pytest tests/ -v --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit

#!/bin/bash
echo "Running regression tests..."
python -m pytest tests/regression -q

if [ $? -ne 0 ]; then
    echo "Regression tests failed. Commit aborted."
    exit 1
fi

echo "All tests passed!"
```

---

## Additional Resources

- **Pytest Documentation**: <https://docs.pytest.org/>
- **Mocking Guide**: <https://docs.python.org/3/library/unittest.mock.html>
- **JSON Schema**: <https://json-schema.org/>
- **Parametrize Examples**: <https://docs.pytest.org/en/stable/parametrize.html>

For questions or issues with testing, check existing test files for patterns or consult the team.
