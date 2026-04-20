# Highway Segmentation GA

Highway segmentation analysis using genetic algorithms (single/multi-objective, constrained) and AASHTO Enhanced CDA. Results are written as schema-compliant JSON (with optional Excel export) and the GUI supports multi-route inputs.

## Features

- **Two Optimization Methods:**
  - Single-objective GA: Fast convergence to one best solution
  - NSGA-II multi-objective: Find multiple trade-off solutions (Pareto front)

- **Smart Constraint Handling:**
  - Automatic data gap detection and mandatory breakpoint insertion
  - Smart constraint merging to resolve conflicts between gap preservation and segment length limits
  - Configurable segment length constraints (min/max miles)

- **Advanced Performance Features:**
  - Fitness result caching for improved performance
  - Population diversity tracking and analysis
  - Interactive Pareto front visualization
  - Results export (schema-compliant JSON + Excel)

- **GUI Interface:** Easy parameter configuration with visual controls

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

## GUI Interface Features

The GUI provides an intuitive way to configure all parameters:

### Configuration Sections:
- **Data File:** Browse and load CSV highway data
- **Segmentation Parameters:** 
  - Min/Max segment lengths (miles)
  - Data gap threshold for mandatory breakpoints
  - Population size
- **Optimization Method:** Radio buttons for Single vs Multi-objective
- **Performance Settings:** Enable statistics, cache management
- **Real-time Status:** Progress tracking and results logging

### GUI Benefits:
- **Parameter Validation:** Automatic validation of numeric inputs
- **Tool Tips:** Helpful explanations for each parameter
- **Visual Feedback:** Data loading status, optimization progress
- **Results Integration:** Automatic file export and plot generation

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Min Segment Length | 0.5 miles | Minimum allowed segment length |
| Max Segment Length | 10 miles | Maximum allowed segment length |
| Gap Threshold | 0.5 miles | Data gaps ≥ this create mandatory breakpoints |
| Population Size | 100 | Number of individuals per generation |
| Single-Obj Generations | 200 | Generations for single-objective method |
| Multi-Obj Generations | 100 | Generations for NSGA-II method |
| Cache Clear Interval | 50 | Clear fitness cache every N generations |

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

### GUI Workflow:
1. Launch: `python src/run.py` → Select option 1
2. Load data file using "Browse" button
3. Adjust parameters as needed (hover for tooltips)
4. Select optimization method (Single/Multi-objective)
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
```
highway-segmentation-ga/
├── src/
│   ├── run.py                     # Launcher
│   ├── gui_main.py                # Tkinter GUI
│   ├── optimization_controller.py # Orchestrates analysis + saving
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