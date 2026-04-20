# Phase 1 Testing Suite
## Multi-Route Processing Functionality Tests

This directory contains comprehensive tests for Phase 1 of the Highway Segmentation GA enhancement, which added multi-route processing capabilities.

## 📋 Test Organization

### Phase 1 Test Files
```
tests/
├── unit/
│   ├── test_phase1_file_manager.py      # FileManager route processing tests
│   └── test_phase1_parameter_manager.py # ParameterManager route handling tests
├── ui/
│   └── test_phase1_route_filter_dialog.py # Route filter dialog UI tests
├── integration/
│   └── test_phase1_complete_workflow.py  # End-to-end workflow tests
├── test_data/
│   └── multi_route_sample.csv          # Test data with multiple routes
└── run_phase1_tests.py                 # Dedicated test runner
```

## 🧪 Test Categories

### **Unit Tests**
- **FileManager Route Processing** (`test_phase1_file_manager.py`)
  - Route detection from CSV files
  - Column loading with route support
  - Error handling for missing files/columns
  - Route data validation and cleaning

- **ParameterManager Route Handling** (`test_phase1_parameter_manager.py`)
  - Route column validation  
  - Route settings persistence
  - Parameter reset with route data
  - Route column change event handling

### **UI Tests**
- **Route Filter Dialog** (`test_phase1_route_filter_dialog.py`)
  - Type-ahead search functionality
  - Multi-select route selection
  - Visual selection indicators
  - Dialog workflow (OK/Cancel)

### **Integration Tests**
- **Complete Workflow** (`test_phase1_complete_workflow.py`)
  - End-to-end route processing workflow
  - Component interaction testing
  - State consistency across operations
  - Error handling integration

## 🚀 Running Phase 1 Tests

### Quick Start
```bash
# Run all Phase 1 tests
python tests/run_phase1_tests.py

# Run specific test categories
python tests/run_phase1_tests.py unit        # Unit tests only
python tests/run_phase1_tests.py ui          # UI tests only  
python tests/run_phase1_tests.py integration # Integration tests only
```

### Individual Test Files
```bash
# Run specific test file
python -m pytest tests/unit/test_phase1_file_manager.py -v

# Run specific test class
python -m pytest tests/unit/test_phase1_file_manager.py::TestFileManagerRouteProcessing -v

# Run specific test method
python -m pytest tests/unit/test_phase1_file_manager.py::TestFileManagerRouteProcessing::test_detect_available_routes_success -v
```

### Using Pytest Markers
```bash
# Run tests by marker
python -m pytest -m phase1 -v              # All Phase 1 tests
python -m pytest -m route -v               # Route-specific tests  
python -m pytest -m "unit and phase1" -v   # Phase 1 unit tests only
python -m pytest -m ui -v                  # UI tests only
```

## 📊 Test Coverage

### **FileManager Route Processing**
- ✅ Route detection from CSV files
- ✅ Handling missing route columns
- ✅ Route data with null/empty values
- ✅ Duplicate route handling
- ✅ CSV column loading integration
- ✅ Error handling for invalid files
- ✅ Multi-route data consistency

### **ParameterManager Route Handling** 
- ✅ Route parameter validation
- ✅ Route column change event handling
- ✅ Parameter reset with route data
- ✅ Settings persistence (structure)
- ✅ Error handling for missing attributes

### **Route Filter Dialog UI**
- ✅ Dialog initialization and setup
- ✅ Type-ahead search functionality
- ✅ Case-insensitive filtering
- ✅ Route selection/deselection
- ✅ Selected count display updates
- ✅ Visual selection indicators
- ✅ OK/Cancel workflow

### **End-to-End Integration**
- ✅ Complete multi-route workflow  
- ✅ Single route mode workflow
- ✅ Route column switching
- ✅ Error handling integration
- ✅ State consistency validation

## 🔧 Test Configuration

### **Pytest Markers**
The following markers are available for organizing tests:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests  
- `@pytest.mark.ui` - UI/dialog tests
- `@pytest.mark.phase1` - Phase 1 specific tests
- `@pytest.mark.route` - Route processing tests
- `@pytest.mark.mock_only` - Tests using only mocks

### **Fixtures Available**
- `multi_route_sample_data` - DataFrame with multiple routes
- `temp_multi_route_csv` - Temporary CSV file with route data
- `route_test_cases` - Various route scenarios
- `mock_route_app` - Mock app with route support  
- `route_filter_test_data` - Route filter dialog test data
- `tkinter_root` - Root window for UI testing

## 📁 Test Data

### **multi_route_sample.csv**
Sample CSV file containing:
- Route column with: US-35, I-75, SR-123 routes
- Milepoint data for each route
- Structural strength indicators
- Used for realistic route detection testing

### **Dynamic Test Data**  
Tests also generate dynamic data for:
- Edge cases (null values, duplicates)
- Error conditions (missing files, invalid columns)
- Performance testing (large datasets)
- Integration scenarios (complex workflows)

## 🐛 Debugging Tests

### **Common Issues**
1. **Import Errors**: Ensure you're running from project root
2. **Tkinter Errors**: UI tests may fail in headless environments
3. **File Path Issues**: Tests use temporary files that may have permission issues

### **Debugging Commands**
```bash
# Verbose output with full tracebacks
python -m pytest tests/unit/test_phase1_file_manager.py -vvv --tb=long

# Stop on first failure  
python -m pytest tests/ -x --phase1

# Show test durations
python -m pytest tests/ --durations=0 -m phase1
```

## ✅ Expected Results

### **All Tests Passing**
When Phase 1 implementation is working correctly, you should see:
```
========== 4 passed, 0 failed ==========
🎉 ALL PHASE 1 TESTS PASSED!
✅ Multi-route processing functionality is working correctly
```

### **Test Performance**
- **Unit tests**: Should complete in < 1 second each
- **UI tests**: May take 2-5 seconds due to tkinter setup  
- **Integration tests**: Should complete in < 10 seconds total
- **Total runtime**: All Phase 1 tests should complete in under 30 seconds

## 📈 Extending Tests

### **Adding New Test Cases**
1. Add test methods to existing test classes
2. Use descriptive names: `test_<functionality>_<scenario>`
3. Follow the Arrange-Act-Assert pattern
4. Add appropriate pytest markers

### **Adding New Test Categories**
1. Create new test files following naming convention
2. Update `run_phase1_tests.py` with new categories
3. Add new markers to `pyproject.toml` if needed
4. Update this README with new test descriptions

## 🔗 Integration with CI/CD

The Phase 1 test suite is designed to integrate with automated testing:
- All tests use temporary files (no external dependencies)
- Mocked UI components work in headless environments
- Clear pass/fail indicators for build systems
- Comprehensive test coverage metrics

---

**Phase 1 Testing Complete** ✅  
These tests validate all multi-route processing functionality is working correctly before proceeding to Phase 2.