# Highway Segmentation Tool - Regression Test Suite

Comprehensive regression tests that validate the complete workflow for all optimization methods and data configurations.

## Overview

This test suite runs an end-to-end regression matrix covering:

- **Methods**: derived from `tests/regression/test_parameters_template.json`; currently `single`, `multi`, `aashto_cda`, `constrained`, `constrained_deb`, and `pelt_segmentation`.
- **Datasets**: derived from the same template; currently `single_route`, `multi_route`, `single_route_with_outliers`, and `multi_route_with_outliers`.

## Test Structure

```text
tests/regression/
├── test_complete_workflow_regression.py      # GUI / controller regression matrix
├── test_cli_workflow_regression.py           # CLI regression matrix
├── test_preprocessing_workflow_regression.py # Preprocessing-focused regression coverage
├── test_zz_cli_gui_structure_equivalence.py  # CLI/GUI output structure equivalence
├── test_pelt_segmentation_method.py          # PELT-specific regression checks
├── regression_matrix.py                      # Derives methods/datasets from template
├── test_parameters_template.json             # Standardized regression parameters
├── conftest.py                               # Fixtures and utilities
├── outputs/                                  # Test artifacts (gitignored)
│   ├── json/                                 # JSON results
│   └── excel/                                # Excel exports
└── README.md                                 # This file
```

## What Each Test Does

For each GUI-regression method/dataset combination:

1. **Load Data**: Verify test data exists and has correct columns
2. **Configure Parameters**: Apply method-specific standardized parameters  
3. **Run Optimization**: Execute complete optimization workflow
4. **Save JSON**: Save results to `outputs/json/regression_{method}_{dataset}.json`
   - CLI regression tests also write separate artifacts as `outputs/json/cli_regression_{method}_{dataset}.json`
5. **Validate Schema**: Check JSON against schema specification
6. **Export Excel**: Create Excel file in `outputs/excel/regression_{method}_{dataset}.xlsx`
7. **Validate Export**: Verify Excel content matches JSON data
8. **Assert Success**: Confirm all steps completed successfully

Additional regression modules cover:

- CLI run-spec execution via `cli.main()`
- preprocessing workflow invariants on outlier-containing datasets
- GUI/CLI output structure equivalence checks
- method-specific regression cases such as PELT segmentation

## Running the Tests

### Run All Regression Tests

```bash
python -m pytest tests/regression -q
```

### Run Specific Method

```bash
python -m pytest tests/regression/test_complete_workflow_regression.py -k "single" -v
```

### Run Specific Dataset

```bash
python -m pytest tests/regression/test_complete_workflow_regression.py -k "multi_route" -v
```

### Run Single Test Case

```bash
python -m pytest tests/regression/test_complete_workflow_regression.py -k "single and single_route" -v
```

### Run CLI Regression Coverage

```bash
python -m pytest tests/regression/test_cli_workflow_regression.py -v
```

### Run Preprocessing Regression Coverage

```bash
python -m pytest tests/regression/test_preprocessing_workflow_regression.py -v
```

## Test Data Configuration

### Single Route Data (`test_data_single_route.csv`)

- **X Column**: `milepoint`  
- **Y Column**: `structural_strength_ind`
- **Route Column**: `null` (no route separation)

### Multi Route Data (`TestMultiRoute.csv`)

- **X Column**: `BDFO`
- **Y Column**: `D60`
- **Route Column**: `RDB`

### Outlier Regression Datasets

- `single_route_with_outliers`: `test_data_single_route_with_outliers.csv`
- `multi_route_with_outliers`: `TestMultiRoute_with_outliers.csv`

## Expected Outputs

After successful test run, you'll find:

```text
outputs/
├── json/
│   ├── regression_{method}_{dataset}.json
│   ├── cli_regression_{method}_{dataset}.json
│   └── ... (one pair per method×dataset)
└── excel/
        ├── regression_{method}_{dataset}.xlsx
        └── ... (GUI regression suite exports Excel)
```

Notes:

- The **GUI regression suite** writes JSON (`outputs/json/regression_{method}_{dataset}.json`) and Excel (`outputs/excel/regression_{method}_{dataset}.xlsx`).
- The **CLI regression suite** writes JSON (`outputs/json/cli_regression_{method}_{dataset}.json`).
- The active method/dataset matrix is derived dynamically from `test_parameters_template.json` via `regression_matrix.py`.

Examples (names will vary with the active method matrix):

- `outputs/json/regression_single_single_route.json`
- `outputs/json/cli_regression_single_single_route.json`
- `outputs/excel/regression_single_single_route.xlsx`

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

**Missing Test Data**: Verify the datasets referenced in `tests/regression/test_parameters_template.json` exist under `tests/test_data/`.

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
- **`test_cli_workflow_regression.py`**: CLI run-spec regression coverage
- **`test_preprocessing_workflow_regression.py`**: preprocessing regression scenarios
- **`test_zz_cli_gui_structure_equivalence.py`**: structural parity checks for CLI vs GUI outputs
- **`conftest.py`**: Fixture documentation and validation framework explanation
- **`regression_matrix.py`**: method/dataset derivation helpers
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
