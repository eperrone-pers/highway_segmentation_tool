# CLI Usage (Run Spec)

This repository supports running analyses headlessly (no GUI) using a **run spec JSON**.

A run spec can be:

- generated from the GUI via **Create Batch Command** (opens a dialog with Single file and Directory batch modes), or
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

- **Missing required field:**

```text
'data_file_path' is a required property at $.input
```

Fix: add the required field to your run spec.

- **Invalid method_key:**

```text
'unknown_method' is not one of ['single', 'multi', 'constrained', 'constrained_deb', 'aashto_cda', 'pelt_segmentation']
```

Fix: use a valid `method_key` from the [Available Methods](#available-methods) table.

- **Invalid parameter value:**

```text
0.5 is not of type 'integer' at $.method.method_parameters.population_size
```

Fix: ensure parameter types match expectations, for example `population_size` must be an integer.

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

Execute an analysis using a run spec file. Omit `--input-dir` for a single-file
run; provide `--input-dir` to activate **batch mode** and process a whole directory.

**Single-file usage:**

```bash
highway-seg run --spec <path>
```

**Batch usage:**

```bash
highway-seg run --spec <path> --input-dir <dir> --output-dir <dir>
```

**Options:**

| Option | Default | Description |
| --- | --- | --- |
| `--spec` | *(required)* | Path to the run spec JSON file |
| `--no-validate-spec` | off | Skip JSON schema validation before execution |
| `--quiet` | off | Suppress progress logging; prints only the final output path or summary path |

**Batch-mode options** *(activated when `--input-dir` is provided):*

| Option | Default | Description |
| --- | --- | --- |
| `--input-dir` | — | Directory containing input CSV files (activates batch mode) |
| `--output-dir` | *(required with `--input-dir`)* | Directory where per-file JSON results are written |
| `--glob` | `*.csv` | Glob pattern for file discovery |
| `--recurse` | off | Recurse into subdirectories when discovering files |
| `--summary-json` | `<output-dir>/batch_summary.json` | Path for the batch summary JSON |
| `--stop-on-error` | off | Stop immediately on the first failure (default: continue and report all failures at the end) |
| `--export-excel` | off | Write a `.xlsx` workbook alongside each result JSON |

**Exit codes (batch mode):**

| Code | Meaning |
| --- | --- |
| `0` | All files processed successfully |
| `1` | Batch completed but one or more files failed (summary JSON still written) |
| `2` | Hard error before execution started (missing directory, stem collision, invalid spec) |

**Single-file output:** Writes results JSON to the path specified in `output.output_json_path`.

**Batch output:** Prints the path to the batch summary JSON as the final line, suitable for scripting.

**Example — process all CSVs in a directory:**

```bash
highway-seg run \
  --spec Results/my_network.run_spec.json \
  --input-dir data/incoming \
  --output-dir Results/batch_out \
  --quiet
```

**Example — recurse, export Excel, stop on first error:**

```bash
highway-seg run \
  --spec Results/network.run_spec.json \
  --input-dir data/networks \
  --output-dir Results/batch_out \
  --recurse \
  --export-excel \
  --stop-on-error
```

### Alternative: Direct Python invocation

If you haven't installed the package, you can invoke the CLI directly:

```bash
python src/cli.py validate-spec --spec path/to/spec.json
python src/cli.py run --spec path/to/spec.json
python src/cli.py run --spec path/to/spec.json \
    --input-dir data/ --output-dir Results/batch_out/
```

## Run an analysis from a run spec

```bash
highway-seg run --spec path/to/your.run_spec.json
```

This writes the results JSON to the `output.output_json_path` location defined inside the run spec.

## Batch Processing

Batch mode lets you apply the same analysis configuration to every CSV file in a
directory without writing a separate run spec for each one.

### Concepts

| Term | Description |
| --- | --- |
| **Run spec (batch)** | A standard run spec whose `data_file_path` is substituted per-file at runtime. All other fields (method, columns, gap threshold) apply to every file. |
| **Batch manifest** | A companion JSON file that records the batch configuration — template spec path, input directory, glob pattern, output directory, and flags — for full reproducibility. |
| **Batch summary** | A JSON file written incrementally during the run that records the outcome (success/failure) for every input file. |

### Output naming

Output files are named after the **stem** of each input file:

```text
data/incoming/route_A123.csv  →  Results/batch_out/route_A123.json
data/incoming/route_B456.csv  →  Results/batch_out/route_B456.json
```

If `--export-excel` is set, an XLSX workbook is written alongside each JSON:

```text
Results/batch_out/route_A123.json
Results/batch_out/route_A123.xlsx
```

### Collision detection

If two input files would produce the same output stem (e.g. `data/a/route.csv`
and `data/b/route.csv` when using `--recurse`), the run is blocked **before any
analysis starts** and exits with code 2. Resolve by renaming files or adjusting
the directory / glob / recurse settings.

The GUI's batch mode preflight panel shows matched file counts and highlights
collisions in real time as you configure the dialog.

### Batch workflow (GUI → CLI)

The **Create Batch Command** dialog (accessible from the **Create Batch Command** button)
has a **Directory batch** mode that generates all required files in one step:

1. **Open the dialog** — click "Create Batch Command" in the GUI with an analysis configured.
2. **Switch to "Directory batch"** mode using the radio button.
3. **Set the input directory** containing your CSV files and adjust the glob / recurse settings. The preflight panel shows how many files match and warns about naming collisions.
4. **Click "Save spec files"** (or "Copy command") — the dialog writes:
   - `*.batch_template.run_spec.json` — the template spec
   - `*.batch_manifest.json` — the reproducibility manifest
5. **Run the CLI** using the generated command shown in the preview, e.g.:

   ```bash
   python src/cli.py run \
     --spec "Results/my_network.run_spec.json" \
     --input-dir "data/incoming" \
     --glob "*.csv" \
     --output-dir "Results/my_network_batch" \
     --summary-json "Results/my_network_batch/batch_summary.json"
   ```

### Batch manifest format

The manifest is a plain JSON file that captures the full batch configuration so
a run can be re-executed or audited later. Key fields:

```json
{
  "manifest_version": "1.0.0",
  "run_spec_path": "Results/my_network.run_spec.json",
  "input_dir": "data/incoming",
  "glob": "*.csv",
  "recurse": false,
  "output_dir": "Results/my_network_batch",
  "summary_json": "Results/my_network_batch/batch_summary.json",
  "continue_on_error": true,
  "export_excel": false,
  "created_at": "2026-05-23T14:00:00Z",
  "created_by": {
    "application": "Highway Segmentation",
    "version": "1.2.0"
  }
}
```

### Batch summary format

The summary JSON is written to `<output-dir>/batch_summary.json` (or
`--summary-json` if specified) and updated after **every file** so partial
progress is preserved if the run is interrupted.

```json
{
  "batch_version": "1.0.0",
  "started_at": "2026-05-23T14:00:00Z",
  "finished_at": "2026-05-23T14:02:15Z",
  "template_spec_path": "Results/my_network.run_spec.json",
  "input_dir": "data/incoming",
  "glob": "*.csv",
  "recurse": false,
  "output_dir": "Results/my_network_batch",
  "total_files": 3,
  "completed": 2,
  "failed": 1,
  "results": [
    {
      "input_file": "data/incoming/route_A123.csv",
      "output_json": "Results/my_network_batch/route_A123.json",
      "status": "success"
    },
    {
      "input_file": "data/incoming/route_B456.csv",
      "output_json": "Results/my_network_batch/route_B456.json",
      "status": "failed",
      "error": "Y column 'IRI' not found in input file"
    }
  ]
}
```

## Run Spec Structure

A run spec JSON contains three main sections: `input`, `method`, and `output`.
When used in **batch mode** (`run --input-dir`), the `data_file_path` and
`output_json_path` fields are substituted per-file at runtime — all other
fields apply uniformly to every file in the batch.

### Minimal Example (Single-Objective Genetic Algorithm)

```json
{
  "input": {
    "data_file_path": "data/my_highway_data.csv",
    "route_column": "ROUTE_ID",
    "x_column": "MILEPOINT",
    "y_column": "IRI",
    "gap_threshold": 0.5
  },
  "method": {
    "method_key": "single",
    "method_parameters": {
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

- `data_file_path`: Path to input CSV/XLSX file
- `x_column`: Column name for x-axis values (typically milepoints)
- `y_column`: Column name for y-axis values (the metric to analyze, e.g., IRI, rutting)
- `gap_threshold`: Positive gap threshold used to create mandatory breakpoints

**`method` section:**

- `method_key`: Analysis method identifier (see [Available Methods](#available-methods) below)
- `method_parameters`: Method-specific parameters (see examples below)

**`output` section:**

- `output_json_path`: Where to write the results JSON file

### Optional Fields

**`input` section:**

- `must_break_columns`: Array of column names that trigger mandatory breakpoints on value changes (see [below](#optional-force-breaks-on-attribute-changes-inputmust_break_columns))
- `secondary_break_columns`: Secondary attribute columns that also trigger mandatory breakpoints
- `route_column`: Column name containing route identifiers for multi-route data; omit or set `null` for single-route input
- `selected_routes`: Explicit subset of routes to analyze; omit or set `null` to process all routes

**`preprocessing` section:**

- `enabled`: Master switch for preprocessing stages
- `pre_gap_method` / `pre_gap_parameters`: Optional method applied before gap analysis
- `primary_method` / `primary_parameters`: Optional main preprocessing method
- `secondary_method` / `secondary_parameters`: Optional later-stage preprocessing method

## Available Methods

The following `method_key` values are available (must match entries in `OPTIMIZATION_METHODS` registry in `src/config.py`):

| Method Key | Display Name | Type | Description |
| --- | --- | --- | --- |
| `single` | Single-Objective GA | Genetic Algorithm | Minimizes total deviation using standard GA |
| `multi` | Multi-Objective NSGA-II | Genetic Algorithm | Returns Pareto front trading off deviation vs segment length |
| `constrained` | Constrained GA (Penalty) | Genetic Algorithm | GA with penalty-based constraint handling |
| `constrained_deb` | Constrained GA (Deb Rules) | Genetic Algorithm | GA with Deb feasibility constraint domination |
| `aashto_cda` | AASHTO CDA Statistical Analysis | Statistical | Deterministic change-point detection using cumulative difference approach |
| `pelt_segmentation` | PELT Segmentation (ruptures) | Statistical | Deterministic change-point detection using PELT with optional smoothing |

## Run Spec Examples by Method

### Example 1: AASHTO CDA (Statistical Method)

```json
{
  "input": {
    "data_file_path": "data/highway_condition.csv",
    "route_column": "ROUTE",
    "x_column": "MILEPOINT",
    "y_column": "IRI",
    "gap_threshold": 0.5
  },
  "method": {
    "method_key": "aashto_cda",
    "method_parameters": {
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
    "data_file_path": "data/pavement_data.csv",
    "route_column": "ROUTE_ID",
    "x_column": "STATION",
    "y_column": "RUTTING",
    "gap_threshold": 0.25
  },
  "method": {
    "method_key": "multi",
    "method_parameters": {
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
    "data_file_path": "data/multi_attribute_highway.csv",
    "route_column": "ROUTE",
    "x_column": "MILEPOINT",
    "y_column": "PSI",
    "gap_threshold": 0.5,
    "must_break_columns": ["PAVEMENT_TYPE", "LANE_COUNT"]
  },
  "method": {
    "method_key": "constrained",
    "method_parameters": {
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

### Example 4: PELT with Preprocessing

```json
{
  "input": {
    "data_file_path": "data/pavement_data.csv",
    "route_column": "ROUTE_ID",
    "x_column": "MILEPOINT",
    "y_column": "IRI",
    "gap_threshold": 0.5,
    "must_break_columns": ["PAVEMENT_TYPE"],
    "secondary_break_columns": ["SURFACE_CLASS"]
  },
  "preprocessing": {
    "enabled": true,
    "primary_method": "tukey_fences",
    "primary_parameters": {
      "k_factor": 1.5,
      "action": "cap"
    }
  },
  "method": {
    "method_key": "pelt_segmentation",
    "method_parameters": {
      "model": "l2",
      "penalty": 12.0,
      "jump": 1,
      "min_length": 0.5,
      "smooth_window_miles": 1.0,
      "smoothing_method": "median"
    }
  },
  "output": {
    "output_json_path": "results/pelt_results.json",
    "overwrite": true
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

The GUI's **Create Batch Command** dialog generates the correct command:

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

Each route result typically includes:

- `route_info`: Route identifier and route-level summary
- `processing_results.pareto_points`: One or more solutions with segmentation payloads
- `input_data_analysis`: Gap analysis, data quality metrics, and attribute break analysis
- Method-specific statistics and preprocessing metadata when available

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
       route_id = route['route_info']['route_id']
       point = route['processing_results']['pareto_points'][0]
       print(f"Route: {route_id}")
       print(f"Segments: {point['segmentation']['segment_count']}")
       print(f"Breakpoints: {point['segmentation']['breakpoints']}")
   ```

### Example Output Excerpt

```json
{
  "analysis_metadata": {
    "analysis_method": "single",
    "timestamp": "2026-05-15T10:30:00",
    "software_version": {
      "application": "Highway Segmentation",
      "version": "1.0.0"
    }
  },
  "input_parameters": {
    "optimization_method_config": {
      "method_key": "single"
    },
    "method_parameters": {
      "population_size": 50,
      "num_generations": 100
    }
  },
  "route_results": [
    {
      "route_info": {
        "route_id": "I-40"
      },
      "processing_results": {
        "pareto_points": [
          {
            "point_id": 0,
            "objective_values": [2.47],
            "segmentation": {
              "breakpoints": [0.0, 2.5, 5.3, 8.7, 12.0],
              "segment_count": 4,
              "segment_details": [
                {
                  "segment_index": 0,
                  "start": 0.0,
                  "end": 2.5,
                  "length": 2.5
                }
              ]
            }
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

- Check that `data_file_path` in your run spec points to an existing file
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

- Use one of the valid method keys: `single`, `multi`, `constrained`, `constrained_deb`, `aashto_cda`, `pelt_segmentation`
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

- Check that the parent path in `output.output_json_path` is valid
- The CLI creates the output directory automatically, so failures usually indicate an invalid path or permissions issue

#### 7. Insufficient Data

```text
ValueError: Route 'I-40' has only 2 datapoints after gap removal, minimum is 3
```

**Solution:**

- Check your input data for gaps or missing values
- Adjust `gap_threshold` parameter if gaps are splitting your data
- Ensure your route has sufficient valid datapoints

#### 8. Batch: Stem collision (exit code 2)

```text
Stem collisions detected — output names would overwrite each other: route, section_a
```

**Solution:**

- Two input files share the same filename stem (e.g. `dir_a/route.csv` and `dir_b/route.csv`)
- Rename the conflicting files, or adjust `--glob` / `--recurse` to exclude one of the directories
- The GUI preflight panel highlights collisions before you export

#### 9. Batch: Partial failures (exit code 1)

The batch run completes but one or more files failed. The batch summary JSON
records which files failed and why:

```bash
# Check the summary for error details
cat Results/batch_out/batch_summary.json | python -m json.tool
```

Look for `"status": "failed"` entries and their `"error"` field. Common causes:

- A file uses different column names than the template spec
- A file has too few data points for the selected method
- A file is malformed or not a valid CSV

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
- **Preprocessing:** The optional `preprocessing` block uses the same preprocessing registry as the GUI workflow.
- **Results format:** The runner writes results using `ExtensibleJsonResultsManager`, producing schema-compliant results JSON.
- **Multi-route datasets:** If your CSV contains multiple routes (identified by the `route_column`), the CLI automatically processes all routes and includes all results in the output JSON.
- **Batch run spec:** The `data_file_path` and `output_json_path` fields in the run spec are replaced per-file at runtime when using batch mode. All other fields — columns, method, parameters — apply uniformly to every file in the batch.
- **Batch summary is incremental:** The summary JSON is written after every file, so it captures partial results if a batch run is interrupted.
- **Batch exit codes:** Exit code 1 means some files failed but the run completed; the summary JSON contains the full per-file breakdown. Exit code 2 means a hard error stopped the run before processing began.

## Related Documentation

- **[configuring_new_analysis_method.md](configuring_new_analysis_method.md)** - Detailed parameter definitions for all analysis methods
- **[json_format_specification.md](json_format_specification.md)** - Complete output JSON schema documentation
- **`src/highway_segmentation_run_spec_schema.json`** - Run spec JSON schema (machine-readable)
- **`src/highway_segmentation_results_schema.json`** - Results JSON schema (machine-readable)

## Quick Reference

### Typical Workflow — Single file

1. **Prepare your data:** CSV with route, x-coordinate (milepoint), and y-coordinate (metric) columns
2. **Create run spec:** Use the GUI's **Create Batch Command** dialog (Single file mode) or write manually
3. **Validate:** `highway-seg validate-spec --spec your_spec.json`
4. **Run analysis:** `highway-seg run --spec your_spec.json`
5. **View results:** Load output JSON in GUI or process programmatically

### Typical Workflow — Directory batch

1. **Prepare your data:** A directory of CSVs all sharing the same column layout
2. **Create batch artifacts:** Use the GUI's **Create Batch Command** dialog in **Directory batch** mode — it writes the template run spec and batch manifest, and shows the command to copy
3. **Run the batch:** `highway-seg run --spec template.run_spec.json --input-dir data/ --output-dir Results/batch_out/`
4. **Check the summary:** Review `batch_summary.json` for per-file status; re-run failed files individually using `highway-seg run` if needed
5. **View results:** Load any result JSON in the GUI, or process the batch summary programmatically

### Method Selection Guide

| Use Case | Recommended Method | Key Benefit |
| --- | --- | --- |
| Fast, deterministic segmentation | `aashto_cda` | Statistical rigor, no tuning needed |
| Deterministic change-point detection with penalty tuning | `pelt_segmentation` | Fast segmentation with optional smoothing |
| Single optimal solution | `single` | Simple, well-understood GA optimization |
| Trade-off analysis | `multi` | Explore multiple solutions on Pareto front |
| Hard constraints on segment count | `constrained` or `constrained_deb` | Enforces min/max segment limits |
| Attribute-based segmentation | Any method + `must_break_columns` | Forces breaks on attribute changes |
| Process many files with the same method | Any method + `run --input-dir` | One command, per-file results, incremental summary |
