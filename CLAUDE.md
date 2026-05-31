# highway_segmentation_tool — Project Guide

## Project Purpose

This tool divides highway/pavement network data into homogeneous segments based on condition measurements (IRI, PCI, rutting, cracking, etc.). The segments support prioritization, budgeting, performance modeling, and maintenance planning. It ships as both a Tkinter GUI (`highway-seg-gui`) and a headless CLI (`highway-seg`).

Six analysis methods are available: four genetic algorithm variants (single-objective GA, NSGA-II multi-objective, penalty-weight constrained GA, Deb feasibility constrained GA), AASHTO enhanced CDA (statistical change-point detection), and PELT segmentation (deterministic cost minimization).

---

## Project Structure

```
highway_segmentation_tool/
├── src/                                  # All application source code
│   ├── run.py                            # GUI launcher (entry point for highway-seg-gui)
│   ├── gui_main.py                       # Tkinter GUI application
│   ├── cli.py                            # CLI interface (highway-seg validate-spec / run)
│   ├── cli_runner.py                     # Headless execution engine for CLI
│   ├── optimization_controller.py        # GUI orchestration, threading, multi-route dispatch
│   ├── config.py                         # *** THE EXTENSION POINT — both method registries,
│   │                                     #     all parameter definitions, dynamic dispatch
│   ├── parameter_definitions.py          # Parameter type classes (NumericParameter, etc.)
│   ├── app_constants.py                  # AlgorithmConstants, UIConfig, etc.
│   ├── data_loader.py                    # CSV loading, route parsing, gap detection
│   ├── parameter_manager.py              # Parameter collection and validation
│   ├── file_manager.py                   # File I/O and settings persistence
│   ├── extensible_results_manager.py     # JSON result schema and serialization
│   ├── json_results_manager.py           # Result loading and validation
│   ├── excel_export.py                   # XLSX export
│   │
│   ├── analysis/                         # Analysis method framework
│   │   ├── base.py                       # AnalysisMethodBase (ABC), AnalysisResult dataclass
│   │   ├── methods/                      # One file per method — add new methods here
│   │   │   ├── single_objective.py       # Single-objective GA
│   │   │   ├── multi_objective.py        # NSGA-II multi-objective GA
│   │   │   ├── constrained.py            # Penalty-weight constrained GA
│   │   │   ├── deb_feasibility_constrained.py
│   │   │   ├── aashto_cda.py             # AASHTO statistical change-point detection
│   │   │   ├── pelt_segmentation.py      # Deterministic PELT breakpoint detection
│   │   │   └── docs/                     # Per-method algorithm notes and tuning guides
│   │   └── utils/
│   │       └── ga_utilities.py           # Shared GA operators (crossover, mutation, NSGA-II)
│   │
│   ├── preprocessing/                    # Preprocessing framework
│   │   ├── base.py                       # PreprocessingMethodBase (ABC), DataModificationContext
│   │   └── methods/                      # One file per preprocessor — add new ones here
│   │       └── tukey_fences.py           # IQR-based outlier detection
│   │
│   └── visualization/                    # Plotting and results display
│       ├── results_binding.py
│       ├── pareto.py
│       ├── breakpoints.py
│       └── ...
│
├── tests/                                # Full test suite (see Test Suite section)
├── docs/                                 # Developer and user guides
│   ├── DEVELOPER_GUIDE.md
│   ├── CLI_USAGE.md
│   ├── configuring_new_analysis_method.md
│   ├── configuring_new_preprocessing_method.md
│   └── json_format_specification.md
├── data/                                 # Sample CSV input files
├── pyproject.toml                        # Build config, pytest settings, ruff config
├── requirements.txt
├── README.md
└── USER_GUIDE.md
```

---

## Extensibility Design — Adding Methods Without Changing Base Code

This is the central architectural principle. The GUI dropdown, CLI dispatch, parameter UI, validation, JSON serialization, and Excel export all adapt automatically when you add a new method. **No changes to the controller, GUI, or serializer are needed.**

> Full step-by-step walkthroughs with code examples live in the project docs:
>
> - `docs/configuring_new_analysis_method.md` — adding an analysis method
> - `docs/configuring_new_preprocessing_method.md` — adding a preprocessing method
>
> What follows is the conceptual map so you know how the pieces fit.

### How it works: the two registries in `src/config.py`

Both analysis methods and preprocessing methods follow identical patterns. Each registry is a list of config dataclasses. `resolve_method_class()` / `resolve_preprocessing_class()` use `importlib` to load the actual class from `method_class_path` at runtime — there are no hardcoded imports in the controller.

```python
# src/config.py — OPTIMIZATION_METHODS (analysis methods)
OPTIMIZATION_METHODS = [
    OptimizationMethodConfig(
        method_key="single",                          # Internal key used everywhere
        display_name="Single-Objective GA",           # What appears in the GUI dropdown
        description="...",                            # Tooltip text
        parameters=SINGLE_OBJECTIVE_GA_PARAMETERS,   # Parameter list drives the UI
        return_type="single_objective",               # Controls which viz tab shows
        method_class_path="analysis.methods.single_objective.SingleObjectiveMethod",
    ),
    # ... 5 more entries
]

# PREPROCESSING_METHODS (same pattern)
PREPROCESSING_METHODS = [
    PreprocessingMethodConfig(
        method_key="tukey_fences",
        display_name="Tukey Fences Outlier Detection",
        parameters=[...],
        method_class_path="preprocessing.methods.tukey_fences.TukeyFencesPreprocessor",
    ),
]
```

At startup, `validate_optimization_method_registry()` and `validate_preprocessing_method_registry()` import every registered class and verify it inherits from the correct base. Misconfigured entries fail fast before any user sees them.

### The `AnalysisMethodBase` contract (`src/analysis/base.py`)

Implement these to create a new analysis method:

```python
class MyMethod(AnalysisMethodBase):
    @property
    def method_name(self) -> str:       # Human-readable, shown in results
        return "My Custom Method"

    @property
    def method_key(self) -> str:        # Must match method_key in OPTIMIZATION_METHODS
        return "my_method"

    def run_analysis(
        self,
        data: RouteAnalysis,            # Contains .route_data DataFrame + gap metadata
        route_id: str,
        x_column: str,
        y_column: str,
        gap_threshold: float,
        **kwargs,                        # All configured parameters arrive here
    ) -> AnalysisResult:
        ...
        return AnalysisResult(
            method_name=self.method_name,
            method_key=self.method_key,
            route_id=route_id,
            all_solutions=[{"chromosome": breakpoints, "fitness": score, ...}],
            optimization_stats={...},
            mandatory_breakpoints=data.mandatory_breakpoints,
            processing_time=elapsed,
            input_parameters=kwargs,
            data_summary=self.prepare_data_summary(data.route_data, x_column, y_column),
        )
```

Optional overrides (all have working base implementations):

- `supports_multi_route` — default `True`
- `parameter_schema` — used by `validate_parameters()` for type/range checking
- `validate_parameters(**kwargs)` — pre-run parameter validation
- `validate_data(df, x_col, y_col)` — pre-run data validation
- `prepare_data_summary(df, x_col, y_col)` — summary stats for result traceability

### Why the controller never branches per-method

`AnalysisResult.to_route_result_dict()` (`src/analysis/base.py:118`) centralizes all method-specific key logic. It detects multi-objective results via `is_multi_objective()`, constrained results by inspecting solution fields, and AASHTO-specific stats by `method_key`. The controller calls this one method and gets a flat dict that works for any method — present and future. **Adding a new method never requires touching `optimization_controller.py` or `cli_runner.py`.**

### The `PreprocessingMethodBase` contract (`src/preprocessing/base.py`)

```python
class MyPreprocessor(PreprocessingMethodBase):
    def process(self, route_analysis: RouteAnalysis, **kwargs) -> PreprocessingResult:
        ctx = DataModificationContext(route_analysis.route_data, x_col, y_col)

        # DataModificationContext is the ONLY sanctioned way to modify data.
        # Every call auto-logs a DataModification record with type, location, values, reason.
        ctx.remove_point(x_val, reason="outlier beyond fence")
        ctx.modify_y_value(x_val, new_y, reason="capped to upper fence")

        return PreprocessingResult(
            modified_data=ctx.get_modified_data(),
            modification_log=ctx.get_modification_log(),
            ...
        )
```

`DataModificationContext` prevents modifying mandatory breakpoints and creates a complete audit trail that surfaces in JSON results and Excel exports automatically.

### Parameter definition types (`src/parameter_definitions.py`, re-exported from `config.py`)

Use these to define parameters for new methods. The GUI widget and validation are generated automatically from them:

| Type | Use for |
|------|---------- |
| `NumericParameter` | Float/int with min/max/decimal places |
| `OptionalNumericParameter` | Same but allows `None` (e.g., max_segments) |
| `SelectParameter` | Dropdown with `(label, value)` option pairs |
| `BoolParameter` | Checkbox |
| `ColumnSelectParameter` | Populated from CSV column names at runtime |
| `TextParameter` | Free text |

Group parameters with the `group` field (e.g., `"04_segment_constraints"`) — groups are sorted alphanumerically and displayed as labeled sections in the GUI.

### Step-by-step: adding a new analysis method

1. Create `src/analysis/methods/my_method.py` — implement `AnalysisMethodBase` as shown above.
2. Define its parameter list in `src/config.py` (e.g., `MY_METHOD_PARAMETERS = [...]`).
3. Append an `OptimizationMethodConfig` entry to `OPTIMIZATION_METHODS` in `config.py`.
   - Set `return_type="single_objective"` or `"multi_objective"` — this controls visualization.
4. Add unit tests in `tests/unit/test_my_method.py` and integration tests in `tests/integration/`.

See `docs/configuring_new_analysis_method.md` for a full worked example.

### Step-by-step: adding a new preprocessing method

1. Create `src/preprocessing/methods/my_preprocessor.py` — implement `PreprocessingMethodBase`.
2. Use `DataModificationContext` for all data changes — never modify the DataFrame directly.
3. Append a `PreprocessingMethodConfig` entry to `PREPROCESSING_METHODS` in `config.py`.

See `docs/configuring_new_preprocessing_method.md`.

---

## Data Flow

```
Load CSV → Gap Analysis → Early Attribute Breaks →
Primary Preprocessing → Late Attribute Breaks →
Analysis Method → Visualization / JSON Export / Excel Export
```

Mandatory breakpoints (gaps, attribute boundaries) are computed before analysis and passed into every method via `RouteAnalysis.mandatory_breakpoints`. No method should produce segments that span a gap.

---

## Key Files at a Glance

| File | Role |
|------|------|
| `src/config.py` | Both method registries, all parameter definitions, dynamic dispatch |
| `src/analysis/base.py` | `AnalysisMethodBase` ABC, `AnalysisResult` dataclass, `to_route_result_dict()` |
| `src/analysis/methods/` | 6 method implementations — add new methods here |
| `src/preprocessing/base.py` | `PreprocessingMethodBase` ABC, `DataModificationContext` |
| `src/preprocessing/methods/` | Preprocessor implementations — add new ones here |
| `src/data_loader.py` | CSV loading, route parsing, gap detection, `RouteAnalysis` dataclass |
| `src/optimization_controller.py` | GUI orchestration, threading, multi-route dispatch |
| `src/cli_runner.py` | Headless CLI execution engine |
| `src/extensible_results_manager.py` | JSON result schema and serialization |

---

## Coding Conventions

**Type hints** — on all function signatures and dataclass fields. Use `from typing import Dict, List, Optional, Tuple, TYPE_CHECKING`. Use `TYPE_CHECKING` guards when a type hint would create a circular import.

**Docstrings** — Google style on all public classes and methods: summary line, extended description, `Args:`, `Returns:`, `Raises:`. Keep them honest; they're the primary API reference.

**Logging** — module-level `_logger = logging.getLogger(__name__)`. Use `.debug()` for algorithm internals, `.warning()` for degraded-mode fallbacks, `.error()` for failures. Never use `print()` in library code.

**Naming** — `snake_case` for functions/variables/modules, `PascalCase` for classes, `UPPER_SNAKE_CASE` for module-level constants, `_underscore_prefix` for private methods.

**Constants** — all numeric defaults and algorithm settings live in `config.py` (`AlgorithmConstants`, parameter definition lists). No magic numbers in method implementations.

**Imports** — explicit only (`from module import Name`), never `*`. Relative imports within the package (`from ..base import AnalysisMethodBase`).

**Error handling** — validate at entry points with descriptive messages before computation starts. Raise `ValueError` for bad values, `TypeError` for wrong object types. Trust the framework inside validated boundaries.

---

## Adding a New Analysis Method

1. Create `src/analysis/methods/my_method.py` — implement `AnalysisMethodBase`.
   - Required properties: `method_name`, `method_key`, `supports_multi_route`, `parameter_schema`
   - Required method: `run_analysis(route_analysis) → AnalysisResult`
2. Define parameter list in `src/config.py` (e.g. `MY_METHOD_PARAMETERS`).
3. Register the method in `OPTIMIZATION_METHODS` dict in `config.py`.
4. Add unit tests in `tests/unit/test_my_method.py` and integration tests in `tests/integration/`.

See `docs/configuring_new_analysis_method.md` for the full walkthrough with code examples.

## Adding a New Preprocessing Method

1. Create `src/preprocessing/methods/my_preprocessor.py` — implement `PreprocessingMethodBase`.
2. Use `DataModificationContext` inside `process()` to log all data changes.
3. Register it in `config.py`.

See `docs/configuring_new_preprocessing_method.md`.

---

## Debugging

**Start here for any bug:**
1. `src/config.py` — confirm the method is registered correctly and parameters are defined.
2. `src/analysis/base.py` — check `AnalysisResult` fields; the bug is often in `to_route_result_dict()`.
3. `src/optimization_controller.py` (GUI) or `src/cli_runner.py` (CLI) — the dispatch path.

**Enable verbose logging** by setting log level to DEBUG before running. The GA logs per-generation statistics; the preprocessing pipeline logs every data modification.

**Fastest iteration loop** — use the CLI with a minimal run-spec JSON:
```bash
highway-seg validate-spec --spec my_spec.json   # catch config errors first
highway-seg run --spec my_spec.json             # run headless, prints output path
```
This avoids GUI overhead and is scriptable.

**For GA-related bugs** — the `HighwaySegmentGA` class in `src/analysis/methods/single_objective.py` is ~1,847 lines. Its `fitness()` and `_enforce_constraints()` methods are the most common sources of subtle issues. The multi-level cache (keyed on `tuple(chromosome)`) can hide stale results; call `ga.clear_cache()` when testing fitness changes.

---

## Test Suite

### Structure
```
tests/
├── conftest.py               # Shared fixtures (data, mocks, file system)
├── test_data/                # CSV fixtures (single-route, multi-route, outlier variants)
├── fixtures/                 # Run-spec JSON fixtures
├── unit/                     # 181 tests — isolated component tests (~1s total)
├── integration/              # 19 tests — workflow and method interaction tests
├── regression/               # 66 tests — full end-to-end across all methods
│   ├── conftest.py           # Auto-marks all files with @pytest.mark.regression
│   └── test_parameters_template.json  # GA params optimized for speed (pop=20, gen=10)
└── test_*.py (root-level)    # ~229 tests — CLI, batch, visualization, routing
```

### Running tests effectively

**During development — run only what's relevant:**
```bash
pytest tests/unit                          # Fast feedback: 181 tests in ~1s
pytest tests/integration                   # 19 tests, component interaction
pytest -k "my_feature_name"               # By name pattern across all tests
pytest tests/unit/test_excel_export.py    # Single file
```

**Before committing:**
```bash
pytest tests/unit tests/integration       # ~200 tests, still fast
```

**Full suite (takes longer due to regression GA runs):**
```bash
pytest                                     # All 535 tests
pytest --durations=10                      # Same, show 10 slowest tests
```

**By marker:**
```bash
pytest -m unit                            # Unit tests
pytest -m regression                      # Regression tests (auto-marked)
pytest -m "unit and not slow"             # Exclude slow tests
pytest -m "integration or regression"     # Both
pytest -m file_io                         # File I/O tests
```

**By method/feature:**
```bash
pytest -k "genetic_algorithm"
pytest -k "aashto_cda"
pytest -k "pelt"
pytest -k "excel"
pytest -k "preprocessing"
```

### Why regression tests are slower
Regression tests run real GA optimizations on real data. The parameters in `tests/regression/test_parameters_template.json` are intentionally small (`population_size: 20`, `num_generations: 10`) to keep them tractable, but they still involve actual algorithm execution across 5+ methods and multiple data configurations. Expect a few minutes for the full regression suite.

### Key fixtures (tests/conftest.py)
- `sample_highway_data` — 100-point controlled dataset (reproducible seed)
- `sample_route_analysis` — `RouteAnalysis` wrapping the above
- `edge_case_datasets` — minimal/boundary datasets (empty, single point, large gaps, etc.)
- `mock_gui_app` — comprehensive mock of the full GUI app (avoids Tkinter rendering)
- `temp_directory` / `temp_csv_file` — auto-cleaned temp files
- `valid_parameters` / `invalid_parameters` — ready-made parameter sets for validation testing

### Discovering tests
```bash
pytest --collect-only -q              # List all 535 tests
pytest --collect-only tests/unit -q   # Unit tests only
```

---

## Documentation

- `README.md` — quick start, data format, output descriptions
- `USER_GUIDE.md` — 2100+ line user reference with pavement-specific context
- `docs/DEVELOPER_GUIDE.md` — architecture, method lifecycle, how to extend
- `docs/CLI_USAGE.md` — run-spec format, batch options, exit codes
- `docs/json_format_specification.md` — output JSON schema reference
- `src/analysis/methods/docs/` — per-method algorithm explanations and parameter tuning
