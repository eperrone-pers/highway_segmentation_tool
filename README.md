# Highway Segmentation Tool

This tool provides a framework for segmenting routes based on attribute data and then displaying the results graphically. The framework allows Python developers to add their own segmentation algorithms and then display the segmentation results on screen.  As of nwo there are 4 segmentation methods included in the framework.

## Features

- **Optimization Methods (config-driven):**
  - Single-objective GA: Looks for segmentation that minimizes variation in a pavement measure to the average measure across all segments for a given route.
  - NSGA-II multi-objective segmentation: Performs a multi-objective analysis that minimizes variation of an attribute compared to average within each chosen segment while also trying to maximize the average segment length along a route.
  - Constrained single-objective GA: Target-length optimization using penalty-based fitness that tries to achieve a selected target average length while minimizing deviation.
  - Enhanced AASHTO Cumulative Difference Approach (CDA) for Pavement Data Segmentation Method (Katicha, S., Flintsch, G. (2025), "Enhanced AASHTO Cumulative Difference Approach (CDA) for Pavement Data Segmentation" Transportation Research Record, Accepted.)

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
```

### 3) Run the regression gate (must be green)

```bash
python -m pytest tests/regression -q
```

### 4) Run the GUI

```bash
python src/run.py
```

More details: see `SETUP_ENVIRONMENT.md`, `USER_GUIDE.md`, `docs/`, and `tests/README.md`.

To create a re-distributable zip package (excluding generated outputs), run `scripts/package_deliverable.ps1`.

## GUI Interface Features

The GUI provides an intuitive way to configure all parameters:

### Configuration Sections

- **File Operations:** Select CSV, optional route column, X/Y columns, gap threshold, and results save path
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
| Min Segment Length | 0.5 miles | GA-based methods | Minimum allowed segment length |
| Max Segment Length | 10 miles | GA-based methods | Maximum allowed segment length |
| Population Size | 100 | GA-based methods | Number of individuals per generation |
| Generations (single-objective GA) | 200 | `single` | Generations for the single-objective GA |
| Generations (NSGA-II multi-objective) | 100 | `multi` | Generations for the multi-objective NSGA-II |
| Generations (constrained) | 150 | `constrained` | Generations for constrained optimization |
| Target Avg Length | 2.0 miles | `constrained` | Target average segment length |
| Alpha | 0.05 | `aashto_cda` | Significance level for CDA change-point detection |

## Data Format

The repository is delivered with sample input CSVs in `data/`.

CSV file with columns:

- `milepoint`: Highway milepoint locations
- `structural_strength_ind`: Structural strength index values

Example:

```csv
milepoint,structural_strength_ind
196.853,75.2
196.901,73.8
197.043,82.1
```

## Output Files

### Canonical output: schema-compliant JSON

- Results are written as JSON (one file per run) to the selected save location (default is `Results/`).
- `Results/` and `test_results/` are intentionally git-ignored; they’re generated outputs.

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

- Python 3.8+
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
highway-segmentation-ga/
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
