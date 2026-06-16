# Highway Segmentation Tool

This tool provides a framework for segmenting highway and pavement network data based on condition measurements. While the framework is extensible for any attribute-based segmentation, it's specifically designed for pavement condition analysis (IRI, PCI, rutting, cracking, etc.) with features tailored to pavement engineering workflows. The framework allows Python developers to add their own segmentation algorithms and display results graphically. As of now, there are 6 segmentation methods included in the framework.

## Features

- **Optimization Methods (config-driven):**
  - Single-objective GA: Looks for segmentation that minimizes variation in a pavement measure to the average measure across all segments for a given route.
  - NSGA-II multi-objective segmentation: Performs a multi-objective analysis that minimizes variation of an attribute compared to average within each chosen segment while also trying to maximize the average segment length along a route.
  - Constrained single-objective GA: Target-length optimization using penalty-based fitness that tries to achieve a selected target average length while minimizing deviation.
  - Constrained GA (Deb Feasibility): Constrained single-objective GA using Deb feasibility rules (constraint domination) for multi-objective constraint handling instead of penalty weights.
  - Enhanced AASHTO Cumulative Difference Approach (CDA) for Pavement Data Segmentation Method: Statistical change-point detection (Katicha, S., Flintsch, G. (2025), "Enhanced AASHTO Cumulative Difference Approach (CDA) for Pavement Data Segmentation" Transportation Research Record, Accepted.)
  - PELT Segmentation (ruptures): Deterministic change-point detection using PELT (Pruned Exact Linear Time). Penalty parameter controls sensitivity; supports optional smoothing and minimum segment length constraints.

- **Preprocessing Methods (config-driven):**
  - Invalid Data Handler: Cleans rows with missing or non-numeric Y values before gap detection and analysis run. Supports drop, moving-average, and linear-interpolation strategies. Runs in the Pre-Gap slot (Step 1) so data is clean before gap boundaries are computed. Configurable threshold to skip routes with excessive missing data.
  - Tukey Fences Outlier Detection: IQR-based outlier detection applied after gap and attribute-break analysis. Configurable k-factor and action (remove, cap, or interpolate).

## Quick Start

Prereq: install dependencies (see **Developer Quickstart** below).

### Option 1: Simple Launcher (Recommended)

```bash
python src/run.py
```

Launches the GUI interface directly.

### Option 2: Direct GUI Launch

```bash
python src/gui_main.py
```

### Option 3: Headless CLI (Run Spec)

You can run an analysis without the GUI using a **run spec JSON**.

- In the GUI, click **Copy command line for this analysis** to generate a run spec and copy a runnable command.
- Or run directly:

```bash
highway-seg validate-spec --spec path/to/your.run_spec.json
highway-seg run --spec path/to/your.run_spec.json
```

See `docs/CLI_USAGE.md` for details.

## Developer Quickstart (Recommended for Delivery)

### 1) Create + activate a venv

Windows (PowerShell):

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
```

Notes:

- `pip install -e .` installs this repo in editable mode and creates the convenience commands `highway-seg` (CLI) and `highway-seg-gui` (GUI).

### 3) Run the regression gate (must be green)

```bash
python run_tests.py --regression
```

Recommended test lanes:

- Fast local development: `python run_tests.py --smoke`
- Regression gate: `python run_tests.py --regression`
- Full suite except performance: `python run_tests.py --full`

### 4) Run the GUI

```bash
python src/run.py
```

More details:

- **For pavement engineers**: See `USER_GUIDE.md` for pavement-specific guidance, parameter selection, and practical scenarios
- **For developers**: See `SETUP_ENVIRONMENT.md`, `docs/`, and `tests/README.md` for technical details
- **For CLI usage**: See `docs/CLI_USAGE.md`

## GUI Interface Features

The GUI provides an intuitive way to configure all parameters:

### Configuration Sections

- **Data Source:** Select source type (CSV or Database), click **Connect / Open** to load a file or connect to a database, then pick X/Y columns, optional route column, gap threshold, and results save path
- **Optimization Method:** Dropdown selection populated from the method registry (`OPTIMIZATION_METHODS`)
- **Method Parameters:** Dynamically generated, method-specific parameters (defined in `src/config.py`). Double-click a parameter value in the table to edit.
- **Performance & Caching:** Caching and performance options (where applicable)
- **Real-time Status:** Progress tracking and results logging

### GUI Benefits

- **Parameter Validation:** Automatic validation of numeric inputs
- **Tool Tips:** Helpful explanations for each parameter
- **Visual Feedback:** Data loading status, optimization progress
- **Results Integration:** Automatic file export and plot generation

## Configuration Parameters

Defaults are defined in `src/config.py` and vary by selected method.

Notes:

- Only a small set of controls are truly global (file selection, route/x/y columns, and gap threshold).
- All other optimization knobs (GA, constrained, AASHTO CDA, etc.) are configured per-method in the Method Parameters table.

| Parameter | Default | Applies To | Description |
| --- | --- | --- | --- |
| Gap Threshold | 0.5 miles | All methods | Data gaps ≥ this create mandatory breakpoints |
| Min Segment Length | 0.5 miles | GA-based & PELT methods | Minimum allowed segment length |
| Max Segment Length | 10 miles | GA-based methods | Maximum allowed segment length |
| Population Size | 100 | GA-based methods | Number of individuals per generation |
| Generations (single-objective GA) | 200 | `single` | Generations for the single-objective GA |
| Generations (NSGA-II multi-objective) | 100 | `multi` | Generations for the multi-objective NSGA-II |
| Generations (constrained) | 150 | `constrained` and `constrained_deb` | Generations for constrained optimization |
| Target Avg Length | 2.0 miles | `constrained` and `constrained_deb` | Target average segment length |
| Alpha | 0.05 | `aashto_cda` | Significance level for CDA change-point detection |
| Penalty | 12.0 | `pelt_segmentation` | PELT sensitivity knob (higher=fewer breakpoints) |
| Smoothing Window | None | `pelt_segmentation` | Optional smoothing window in miles for noise reduction |
| Cost Model | L2 | `pelt_segmentation` | PELT cost function (L2=mean shifts, L1=robust, RBF=kernel) |

## Data Format

### CSV files

The repository includes sample CSVs in `data/`. Required column structure:

- **Distance column**: Highway milepoint or station locations  
- **Measurement column**: Numeric condition values (e.g., IRI, PCI, rutting depth, structural indices)
- **Route column** (optional): Route identifiers for multi-route analysis

```csv
milepoint,structural_strength_ind
196.853,75.2
196.901,73.8
197.043,82.1
```

### Database sources (GUI and CLI)

The tool connects directly to relational databases via SQLAlchemy. Supported engines:

| Driver key | Database |
| --- | --- |
| `postgresql` | PostgreSQL / PostGIS |
| `oracle` | Oracle Database |
| `sqlserver` | SQL Server |
| `mysql` | MySQL / MariaDB |
| `snowflake` | Snowflake |
| `bigquery` | Google BigQuery |
| `redshift` | Amazon Redshift |
| `azuresynapse` | Azure Synapse |
| `sqlite` | SQLite (no server required) |

**GUI:** choose **Database (SQL)** in the Data Source dropdown, click **Connect / Open**, select the driver and credentials, then browse tables/views.

**CLI:** use a `data_source` block in the run spec instead of `data_file_path`. See [`docs/CLI_USAGE.md`](docs/CLI_USAGE.md#database-input).

Passwords are stored in the system keyring (GUI) or the `HST_DB_PASSWORD` environment variable (CLI) — never in settings files.

The tool works with any numeric pavement condition index including IRI, PCI, rutting depth, cracking indices, structural numbers, deflection data, and custom metrics.

## Output Files

### Canonical output: schema-compliant JSON

- Results are written as JSON (one file per run) to the selected save location (default is `Results/`).
- `Results/` contains generated output artifacts and is git-ignored in this repo.

### Optional: Excel export

- The enhanced visualization supports exporting the analysis to an `.xlsx` file.

## Algorithm Features

### Mandatory Breakpoint System

- **Automatic Gap Detection:** Identifies data gaps ≥ threshold
- **Smart Merging:** Resolves conflicts between mandatory breakpoints and min length constraints
- **Constraint Preservation:** Ensures critical data boundaries are maintained

### Multi-Objective Optimization (NSGA-II)

- **Objective 1:** Minimize segmentation deviation (fitness)
- **Objective 2:** Optimize average segment length
- **Pareto Front:** Multiple optimal trade-off solutions
- **Interactive Visualization:** Click points to explore different segmentations

### Performance Optimizations

- **Fitness Caching:** Avoid redundant evaluations
- **Diversity Tracking:** Monitor population genetic diversity
- **Memory Management:** Periodic cache clearing
- **Progress Tracking:** Real-time optimization statistics

## Usage Examples

### GUI Workflow

1. Launch: `python src/run.py`
2. Load data file using "Browse" button
3. Adjust parameters as needed (hover for tooltips)
4. Select optimization method from the dropdown
5. Click "Start Optimization"
6. View results in status panel and exported files

## Requirements

- Python 3.9+
- Install all dependencies via:

```bash
pip install -r requirements.txt
```

## Tips for Best Results

- **Start with GUI:** Easier parameter experimentation
- **Population Size:** 50-100 typically sufficient
- **Generations:** Single-objective can handle 200+, Multi-objective 50-100
- **Gap Threshold:** 0.5 miles good starting point
- **Multi-objective:** Provides more insights into trade-offs
- **Interactive Plots:** Click Pareto points to explore solutions

## File Structure

```text
highway_segmentation_tool/
├── src/
│   ├── run.py                     # Launcher
│   ├── gui_main.py                # Tkinter GUI
│   ├── config.py                  # Method registry + parameters (dispatch via method_class_path)
│   ├── optimization_controller.py # Orchestrates dispatch (config-driven) + saving
│   └── analysis/                  # Methods + GA utilities
├── data/                           # Bundled sample CSV inputs
├── tests/                          # Test suite (includes regression gate)
├── README.md
└── requirements.txt
```

## Citations

This software incorporates research methods that require proper attribution. When using this software in academic work:

- **For AASHTO CDA method results**: Please cite the research paper and respect the BSD license terms
- **For complete software framework**: Acknowledge the Highway Segmentation GA project

See [`CITATIONS.md`](CITATIONS.md) for detailed attribution information, license terms, and academic citations.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
