# CLI Usage (Run Spec)

This repository supports running analyses headlessly (no GUI) using a **run spec JSON**.

A run spec can be:

- generated from the GUI via **Copy CLI command**, or
- written/edited manually.

The run spec schema is defined in:

- `src/highway_segmentation_run_spec_schema.json`

## Install (developer-friendly)

Create and activate a virtual environment:

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS/Linux (bash):**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Then install dependencies:

```bash
pip install -r requirements.txt
pip install -e .
```

The `pip install -e .` step installs this repository in editable mode and creates
the convenience commands:

- `highway-seg` (CLI)
- `highway-seg-gui` (GUI)

## Validate a run spec

```bash
highway-seg validate-spec --spec path/to/your.run_spec.json
```

**Successful validation:**

```text
✓ Run spec is valid
OK
```

**Validation failure example:**

```text
✗ Validation failed:
  - 'method_key' is a required property at $.method
  - Additional properties are not allowed ('invalid_field' was unexpected) at $.input
```

**Common validation errors:**

1. **Missing required field:**

   ```text
   'csv_path' is a required property at $.input
   ```

   **Fix:** Add the required field to your run spec.

2. **Invalid method_key:**

   ```text
   'unknown_method' is not one of ['single', 'multi', 'aashto_cda', 'constrained', 'constrained_deb']
   ```

   **Fix:** Use a valid method_key from the [Available Methods](#available-methods) table.

3. **Invalid parameter value:**

   ```text
   0.5 is not of type 'integer' at $.method.parameters.population_size
   ```

   **Fix:** Ensure parameter types match expectations (e.g., population_size must be an integer).

## CLI Command Reference

### `highway-seg --help`

Display help information and list all available commands.

```bash
highway-seg --help
```

### `highway-seg validate-spec`

Validate a run spec JSON file against the schema.

**Usage:**

```bash
highway-seg validate-spec --spec <path>
```

**Options:**

- `--spec`: Path to the run spec JSON file (required)

**Returns:** Exit code 0 if valid, non-zero if invalid.

### `highway-seg run`

Execute an analysis using a run spec file.

**Usage:**

```bash
highway-seg run --spec <path>
```

**Options:**

- `--spec`: Path to the run spec JSON file (required)

**Output:** Writes results JSON to the path specified in `output.output_json_path`.

### Alternative: Direct Python invocation

If you haven't installed the package, you can invoke the CLI directly:

```bash
python src/cli.py validate-spec --spec path/to/spec.json
python src/cli.py run --spec path/to/spec.json
```

## Run an analysis from a run spec

```bash
highway-seg run --spec path/to/your.run_spec.json
```

This writes the results JSON to the `output.output_json_path` location defined inside the run spec.

## Run Spec Structure

A run spec JSON contains three main sections: `input`, `method`, and `output`.

### Minimal Example (Single-Objective Genetic Algorithm)

```json
{
  "input": {
    "csv_path": "data/my_highway_data.csv",
    "route_column": "ROUTE_ID",
    "x_column": "MILEPOINT",
    "y_column": "IRI"
  },
  "method": {
    "method_key": "single",
    "parameters": {
      "population_size": 50,
      "num_generations": 100,
      "min_length": 0.5,
      "max_length": 5.0,
      "crossover_rate": 0.8,
      "mutation_rate": 0.1
    }
  },
  "output": {
    "output_json_path": "results/analysis_results.json"
  }
}
```

### Required Fields

**`input` section:**

- `csv_path`: Path to input CSV file
- `route_column`: Column name containing route identifiers
- `x_column`: Column name for x-axis values (typically milepoints)
- `y_column`: Column name for y-axis values (the metric to analyze, e.g., IRI, rutting)

**`method` section:**

- `method_key`: Analysis method identifier (see [Available Methods](#available-methods) below)
- `parameters`: Method-specific parameters (see examples below)

**`output` section:**

- `output_json_path`: Where to write the results JSON file

### Optional Fields

**`input` section:**

- `must_break_columns`: Array of column names that trigger mandatory breakpoints on value changes (see [below](#optional-force-breaks-on-attribute-changes-inputmust_break_columns))

## Available Methods

The following `method_key` values are available (must match entries in `OPTIMIZATION_METHODS` registry in `src/config.py`):

| Method Key | Display Name | Type | Description |
| ---------- | ------------ | ---- | ----------- |
| `single` | Single-Objective GA | Genetic Algorithm | Minimizes total deviation using standard GA |
| `multi` | Multi-Objective NSGA-II | Genetic Algorithm | Returns Pareto front trading off deviation vs segment length |
| `aashto_cda` | AASHTO CDA Statistical Analysis | Statistical | Deterministic change-point detection using cumulative difference approach |
| `constrained` | Constrained GA (Penalty) | Genetic Algorithm | GA with penalty-based constraint handling |
| `constrained_deb` | Constrained GA (Deb Rules) | Genetic Algorithm | GA with Deb feasibility constraint domination |

## Run Spec Examples by Method

### Example 1: AASHTO CDA (Statistical Method)

```json
{
  "input": {
    "csv_path": "data/highway_condition.csv",
    "route_column": "ROUTE",
    "x_column": "MILEPOINT",
    "y_column": "IRI"
  },
  "method": {
    "method_key": "aashto_cda",
    "parameters": {
      "alpha": 0.05,
      "method": 2,
      "use_segment_length": true,
      "min_segment_datapoints": 3,
      "max_segments": null,
      "min_section_difference": 0.0
    }
  },
  "output": {
    "output_json_path": "results/aashto_analysis.json"
  }
}
```

**AASHTO CDA Parameters:**

- `alpha`: Significance level (0.001-0.49, lower = more conservative)
- `method`: Error estimation method (1=MAD, 2=StdDev of Differences, 3=StdDev)
- `use_segment_length`: Use segment-specific vs total length (boolean)
- `min_segment_datapoints`: Minimum datapoints per segment (integer)
- `max_segments`: Maximum segments allowed (integer or null for no limit)
- `min_section_difference`: Minimum difference between adjacent segment means

### Example 2: Multi-Objective NSGA-II

```json
{
  "input": {
    "csv_path": "data/pavement_data.csv",
    "route_column": "ROUTE_ID",
    "x_column": "STATION",
    "y_column": "RUTTING"
  },
  "method": {
    "method_key": "multi",
    "parameters": {
      "population_size": 100,
      "num_generations": 200,
      "min_length": 0.25,
      "max_length": 3.0,
      "crossover_rate": 0.9,
      "mutation_rate": 0.15,
      "tournament_size": 3
    }
  },
  "output": {
    "output_json_path": "results/pareto_front.json"
  }
}
```

**Multi-Objective Parameters:**

- `population_size`: Number of solutions per generation
- `num_generations`: Number of evolutionary iterations
- `min_length`, `max_length`: Segment length constraints (same units as x_column)
- `crossover_rate`, `mutation_rate`: GA operator probabilities (0.0-1.0)
- `tournament_size`: Selection tournament size (typically 2-5)

### Example 3: Constrained GA with Must-Break Columns

```json
{
  "input": {
    "csv_path": "data/multi_attribute_highway.csv",
    "route_column": "ROUTE",
    "x_column": "MILEPOINT",
    "y_column": "PSI",
    "must_break_columns": ["PAVEMENT_TYPE", "LANE_COUNT"]
  },
  "method": {
    "method_key": "constrained",
    "parameters": {
      "population_size": 80,
      "num_generations": 150,
      "min_length": 0.5,
      "max_length": 10.0,
      "min_segments": 3,
      "max_segments": 20,
      "penalty_weight": 1000.0
    }
  },
  "output": {
    "output_json_path": "results/constrained_segmentation.json"
  }
}
```

**Constrained GA Parameters:**

- `min_segments`, `max_segments`: Hard limits on segment count
- `penalty_weight`: Penalty multiplier for constraint violations
- Other parameters same as single-objective GA

### Optional: Force breaks on attribute changes (`input.must_break_columns`)

You can optionally provide an array of additional column headers under `input.must_break_columns`.
If set, a mandatory breakpoint is inserted whenever the attribute value changes along the route.

Example snippet:

```json
{
    "input": {
        "must_break_columns": ["pavement_type", "lane_count"]
    }
}
```

Note: the GUI's **Copy CLI command** currently copies a command of the form:

```bash
python src/cli.py run --spec "path/to/your.run_spec.json"
```

If you've installed the package (see above), you can equivalently run:

```bash
highway-seg run --spec path/to/your.run_spec.json
```

## Understanding the Output

The CLI writes a schema-compliant JSON file to the location specified in `output.output_json_path`.

### Output JSON Structure

The results file contains:

1. **`analysis_metadata`**: Method used, timestamp, version info
2. **`input_parameters`**: Complete record of all inputs (data file, columns, method parameters, route processing settings)
3. **`route_results`**: Array of per-route analysis results
   - Each route contains:
     - `route_id`: Route identifier
     - `segmentation`: Optimal breakpoint locations and segment details
     - `solutions` (multi-objective only): Full Pareto front
     - `input_data_analysis`: Gap analysis, data quality metrics, attribute break analysis
     - `optimization_stats`: Algorithm performance metrics

### Viewing Results

To visualize the results:

1. **GUI Visualization Tool:**

   ```bash
   highway-seg-gui
   ```

   Then use **File → Load Results JSON** to view interactive plots.

2. **Programmatic Access:**

   ```python
   import json
   
   with open('results/analysis_results.json', 'r') as f:
       results = json.load(f)
   
   # Access route results
   for route in results['route_results']:
       print(f"Route: {route['route_id']}")
       print(f"Segments: {route['segmentation']['num_segments']}")
       breakpoints = route['segmentation']['breakpoints']
       print(f"Breakpoints: {breakpoints}")
   ```

### Example Output Excerpt

```json
{
  "analysis_metadata": {
    "analysis_method": "single",
    "timestamp": "2026-05-15T10:30:00",
    "application_version": "1.0.0"
  },
  "input_parameters": {
    "data_source": {
      "csv_path": "data/my_highway_data.csv",
      "route_column": "ROUTE_ID",
      "x_column": "MILEPOINT",
      "y_column": "IRI"
    },
    "method_parameters": {
      "population_size": 50,
      "num_generations": 100
    }
  },
  "route_results": [
    {
      "route_id": "I-40",
      "segmentation": {
        "breakpoints": [0.0, 2.5, 5.3, 8.7, 12.0],
        "num_segments": 4,
        "segment_details": [
          {
            "segment_id": 1,
            "start": 0.0,
            "end": 2.5,
            "length": 2.5,
            "mean_value": 95.2
          }
        ]
      }
    }
  ]
}
```

## Troubleshooting

### Common Issues and Solutions

#### 1. File Not Found Error

```text
FileNotFoundError: [Errno 2] No such file or directory: 'data/missing.csv'
```

**Solution:**

- Check that `csv_path` in your run spec points to an existing file
- Use absolute paths or ensure relative paths are correct relative to the run spec location
- Verify file permissions

#### 2. Column Not Found Error

```text
KeyError: "Column 'MILEPOINT' not found in DataFrame"
```

**Solution:**

- Verify column names in your CSV file match exactly (case-sensitive)
- Check for leading/trailing spaces in column names
- Ensure the CSV file is properly formatted

#### 3. Invalid Method Key

```text
ValueError: Unknown method key: 'invalid_method'
```

**Solution:**

- Use one of the valid method keys: `single`, `multi`, `aashto_cda`, `constrained`, `constrained_deb`
- Check for typos in the `method_key` field

#### 4. Schema Validation Failure

```text
jsonschema.exceptions.ValidationError: 'method' is a required property
```

**Solution:**

- Ensure all required sections (`input`, `method`, `output`) are present
- Run `highway-seg validate-spec` to see detailed validation errors
- Compare your run spec against the examples in this document

#### 5. Method Parameter Type Mismatch

```text
TypeError: population_size must be an integer, got <class 'float'>
```

**Solution:**

- Ensure parameter types match expectations:
  - Population/generation counts: integers
  - Rates/thresholds: floats
  - Flags: booleans
- Remove quotes around numeric values in JSON

#### 6. Output Directory Doesn't Exist

```text
FileNotFoundError: No such file or directory: 'nonexistent_dir/results.json'
```

**Solution:**

- Create the output directory before running: `mkdir -p results/`
- Or use an existing directory in `output.output_json_path`

#### 7. Insufficient Data

```text
ValueError: Route 'I-40' has only 2 datapoints after gap removal, minimum is 3
```

**Solution:**

- Check your input data for gaps or missing values
- Adjust `gap_threshold` parameter if gaps are splitting your data
- Ensure your route has sufficient valid datapoints

### Getting Help

If you encounter issues not covered here:

1. Check the run spec schema: `src/highway_segmentation_run_spec_schema.json`
2. Validate your run spec: `highway-seg validate-spec --spec your_spec.json`
3. Review method parameter documentation: `docs/configuring_new_analysis_method.md`
4. Check application logs for detailed error messages

## Notes

- **Path handling:** Paths are quoted in generated commands to support spaces (Windows and macOS/Linux).
- **Relative path resolution:** Relative paths in a run spec are resolved relative to the run spec file location.
- **Method registry:** The CLI runner uses the same method registry as the GUI (`OPTIMIZATION_METHODS` in `src/config.py`).
- **Results format:** The runner writes results using `ExtensibleJsonResultsManager`, producing schema-compliant results JSON.
- **Multi-route datasets:** If your CSV contains multiple routes (identified by the `route_column`), the CLI automatically processes all routes and includes all results in the output JSON.

## Related Documentation

- **[configuring_new_analysis_method.md](configuring_new_analysis_method.md)** - Detailed parameter definitions for all analysis methods
- **[json_format_specification.md](json_format_specification.md)** - Complete output JSON schema documentation
- **`src/highway_segmentation_run_spec_schema.json`** - Run spec JSON schema (machine-readable)
- **`src/highway_segmentation_results_schema.json`** - Results JSON schema (machine-readable)

## Quick Reference

### Typical Workflow

1. **Prepare your data:** CSV with route, x-coordinate (milepoint), and y-coordinate (metric) columns
2. **Create run spec:** Use GUI's "Copy CLI command" or write manually following examples above
3. **Validate:** `highway-seg validate-spec --spec your_spec.json`
4. **Run analysis:** `highway-seg run --spec your_spec.json`
5. **View results:** Load output JSON in GUI or process programmatically

### Method Selection Guide

| Use Case | Recommended Method | Key Benefit |
| -------- | ------------------ | ----------- |
| Fast, deterministic segmentation | `aashto_cda` | Statistical rigor, no tuning needed |
| Single optimal solution | `single` | Simple, well-understood GA optimization |
| Trade-off analysis | `multi` | Explore multiple solutions on Pareto front |
| Hard constraints on segment count | `constrained` or `constrained_deb` | Enforces min/max segment limits |
| Attribute-based segmentation | Any method + `must_break_columns` | Forces breaks on attribute changes |
