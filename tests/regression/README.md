# Highway Segmentation GA - Regression Test Suite

Comprehensive regression tests that validate the complete workflow for all optimization methods and data configurations.

## Overview

This test suite runs **8 total tests** covering all combinations of:
- **4 Methods**: `single`, `multi`, `constrained`, `aashto_cda`  
- **2 Datasets**: `single_route` (txdot_data.csv), `multi_route` (AndreTestMultiRoute.csv)

## Test Structure

```
tests/regression/
├── test_complete_workflow_regression.py    # Main test file (8 parametrized tests)
├── test_parameters_template.json          # Standardized test parameters
├── conftest.py                            # Test fixtures and utilities
├── outputs/                               # Test artifacts (gitignored)
│   ├── json/                             # JSON results
│   └── excel/                            # Excel exports
└── README.md                             # This file
```

## What Each Test Does

For each method/dataset combination:

1. **Load Data**: Verify test data exists and has correct columns
2. **Configure Parameters**: Apply method-specific standardized parameters  
3. **Run Optimization**: Execute complete optimization workflow
4. **Save JSON**: Save results to `outputs/json/regression_{method}_{dataset}.json`
5. **Validate Schema**: Check JSON against schema specification
6. **Export Excel**: Create Excel file in `outputs/excel/regression_{method}_{dataset}.xlsx`
7. **Validate Export**: Verify Excel content matches JSON data
8. **Assert Success**: Confirm all steps completed successfully

## Running the Tests

### Run All Regression Tests
```bash
cd tests/regression
pytest test_complete_workflow_regression.py -v
```

### Run Specific Method
```bash
pytest test_complete_workflow_regression.py -k "single" -v
```

### Run Specific Dataset
```bash
pytest test_complete_workflow_regression.py -k "multi_route" -v  
```

### Run Single Test Case
```bash
pytest test_complete_workflow_regression.py -k "single and single_route" -v
```

## Test Data Configuration

### Single Route Data (txdot_data.csv)
- **X Column**: `milepoint`  
- **Y Column**: `structural_strength_ind`
- **Route Column**: `null` (no route separation)

### Multi Route Data (AndreTestMultiRoute.csv)  
- **X Column**: `BDFO`
- **Y Column**: `D60`
- **Route Column**: `RDB`

## Expected Outputs

After successful test run, you'll find:

```
outputs/
├── json/
│   ├── regression_single_single_route.json
│   ├── regression_single_multi_route.json
│   ├── regression_multi_single_route.json
│   ├── regression_multi_multi_route.json
│   ├── regression_constrained_single_route.json
│   ├── regression_constrained_multi_route.json
│   ├── regression_aashto_cda_single_route.json
│   └── regression_aashto_cda_multi_route.json
└── excel/
    ├── regression_single_single_route.xlsx
    ├── regression_single_multi_route.xlsx
    ├── regression_multi_single_route.xlsx
    ├── regression_multi_multi_route.xlsx
    ├── regression_constrained_single_route.xlsx
    ├── regression_constrained_multi_route.xlsx
    ├── regression_aashto_cda_single_route.xlsx
    └── regression_aashto_cda_multi_route.xlsx
```

## Using as Regression Detection

This test suite is designed to catch:

- **Breaking API changes** in optimization methods
- **Data loading/column mapping issues**  
- **JSON schema compatibility problems**
- **Excel export functionality breakage**
- **Parameter handling regressions**
- **File I/O and path resolution issues**

## Test Parameters

Standardized parameters optimized for:
- ✅ **Speed**: Reduced population/generations for faster testing
- ✅ **Reliability**: Conservative settings that should always work
- ✅ **Coverage**: All method-specific parameters included

See `test_parameters_template.json` for full configuration.

## Troubleshooting

### Common Issues

**Import Errors**: Ensure you're running from the correct directory and have all dependencies installed.

**Missing Test Data**: Verify `tests/test_data/txdot_data.csv` and `AndreTestMultiRoute.csv` exist.

**Schema Validation Fails**: Check that `src/highway_segmentation_results_schema.json` exists and is valid.

**Permission Errors**: Ensure write access to `tests/regression/outputs/` directory.

### Debug Mode

To keep test artifacts for inspection, comment out cleanup in `conftest.py`:
```python
# Optional: Clean up after test (comment out to keep artifacts for inspection)  
# if outputs_dir.exists():
#     shutil.rmtree(outputs_dir)
```

## Integration with CI/CD

This test suite is perfect for:
- **Pre-commit hooks**: Validate changes don't break core functionality
- **Pull request validation**: Ensure new features don't introduce regressions  
- **Release verification**: Confirm all workflows work before deployment
- **Performance benchmarking**: Track optimization performance over time

## Documentation Architecture

The regression test suite includes comprehensive documentation across all components:

### Module Documentation
- **`__init__.py`**: Package overview, test matrix, and integration guidelines
- **`test_complete_workflow_regression.py`**: Detailed workflow architecture and test design philosophy
- **`conftest.py`**: Fixture documentation and validation framework explanation
- **`validate_regression_outputs.py`**: Schema validation utility with comprehensive error reporting

### Class and Method Documentation
- **MockGUIApp**: Complete production-equivalent GUI application mock
- **Test Classes**: Detailed test methodology and validation criteria
- **Fixture Functions**: Parameter loading, data configuration, and validation utilities
- **Validation Functions**: JSON/Excel consistency checking and schema compliance

### Testing Methodology
- **Production Equivalence**: Same code paths as GUI application
- **Comprehensive Coverage**: All method/dataset combinations validated
- **Error Handling**: Detailed diagnostics and troubleshooting guidance
- **Integration Support**: CI/CD pipeline integration and automated quality assurance