# Configuring a New Analysis Method (Extensible Architecture Guide)

Audience: Python developers extending the Highway Segmentation GA application.

This document describes **how to connect a new analysis method to the system** so that:

- it appears in the GUI,
- its parameters are validated and rendered dynamically,
- it can run across single-route or multi-route datasets,
- it produces standardized outputs (`AnalysisResult`),
- it exports schema-compliant JSON, and
- it displays correctly in the enhanced visualization.

We use **AASHTO CDA** as the concrete example of a **single-objective (single-result) method**.

Section 6 includes the **multi-objective** example (showing Pareto outputs and multi-file utilities).

---

## 1) Method inputs and outputs

Each analysis method consumes route data and produces a segmentation.

In practice, each analysis method produces:

- A **list of breakpoint locations** (milepoints) that define the segment boundaries.
- (Optionally) per-segment statistics (length, mean value, etc.).

You can implement **your own breakpoint-selection method** (GA, NSGA-II, statistical CDA, ML, rules-based, etc.) and register it so it appears in the GUI, runs under the controller, exports JSON, and visualizes correctly.

## 2) Files and configuration involved

The application is split into:

1. **Method configuration (declarative)**
   - Defines what methods exist and what parameters they expose.
   - Lives primarily in `src/config.py` via `OPTIMIZATION_METHODS` and per-method parameter lists.

2. **Method implementation (imperative)**
   - The actual algorithm, implemented as a class deriving from `AnalysisMethodBase`.
   - Lives in `src/analysis/methods/<your_method>.py`.

3. **Controller dispatch (runtime method selection)**
    - Chooses which method to instantiate and run based on the GUI-selected `method_key`.
    - Dispatch is **config-driven** via `OptimizationMethodConfig.method_class_path`.
    - Lives in `src/optimization_controller.py` (dispatch) and `src/config.py` (registry + class resolver).

4. **Results export**
    - JSON schema output is written by `ExtensibleJsonResultsManager`.
    - Lives in `src/extensible_results_manager.py`.

5. **Visualization behavior**
   - Determines whether to show Pareto plots based on the configured `return_type`.
   - Lives in `src/enhanced_visualization.py`.

### 1.1 Runtime flow

```mermaid
flowchart TD
  GUI[GUI method dropdown] -->|method_key| PM[ParameterManager / UIBuilder]
  PM -->|method_config.parameters| UI[Dynamic parameter widgets + validation]

  GUI -->|Start| OC[OptimizationController]
    OC -->|method_key| CFG[config: OPTIMIZATION_METHODS]
    CFG -->|method_class_path| IMPORT[import + instantiate method]
    IMPORT --> CALL[method.run_analysis]
    CALL --> AR[AnalysisResult]

  AR --> J[ExtensibleJsonResultsManager.save_analysis_results]
  J --> JSON[Schema JSON file]

  JSON --> VIZ[Enhanced visualization]
    VIZ -->|is_multi_objective_method| LAYOUT[layout: pareto + segmentation OR segmentation only]
```

---

### 1.2 AASHTO CDA integration (single-objective example)

This diagram focuses on the **AASHTO CDA** method and the configuration points it uses.

```mermaid
flowchart TD
    CFG[src/config.py] -->|AASHTO_CDA_PARAMETERS| PARAMS[AASHTO_CDA_PARAMETERS]
    CFG -->|OPTIMIZATION_METHODS entry| REG[OptimizationMethodConfig:<br/>method_key=aashto_cda<br/>return_type=single_objective<br/>method_class_path set]

    GUI[GUI dropdown] -->|method_key=aashto_cda| OC[OptimizationController]
    OC -->|resolve method_class_path| CALL[AashtoCdaMethod.run_analysis]

    CALL -->|reads defaults from config| DEFAULTS[get_optimization_method aashto_cda<br/>param_defaults]
    CALL --> AR[AnalysisResult:<br/>all_solutions=list]

    AR --> JSON[ExtensibleJsonResultsManager.save_analysis_results]
    JSON --> VIZ[Enhanced visualization]
    VIZ -->|return_type=single_objective| LAYOUT[segmentation view only]
```

---

## 3) Extension points

When you add a new method, the system expects you to provide **four** things:

1. A **unique `method_key`** string (internal identifier)
2. A **parameter list** (`List[ParameterDefinition]`) for dynamic UI + validation
3. A **method implementation** deriving from `AnalysisMethodBase` that returns an `AnalysisResult`
4. A **config registry entry** that points at your implementation via `method_class_path`

The controller dispatches methods by importing the class specified by `OptimizationMethodConfig.method_class_path`.

Method registry entries are validated at app startup via `validate_optimization_method_registry()` (called from `src/gui_main.py`).

---

### 3.1 Configuration reference (what you can configure)

This section lists the *available configuration knobs* in `src/config.py` that control method registration, parameter UI/validation, and (for multi-objective) Pareto plotting.

#### `OptimizationMethodConfig` (method registry entry)

Each method registered in `OPTIMIZATION_METHODS` is an `OptimizationMethodConfig`:

- `method_key` (str): Internal identifier. This is what the GUI/controller store and what JSON export persists as the analysis method.
- `display_name` (str): User-facing name shown in the dropdown.
- `description` (str): Help/tooltip text shown in the UI.
- `method_class_path` (str): Importable Python path to the analysis method class (example: `"analysis.methods.aashto_cda.AashtoCdaMethod"`). Used for dispatch.
- `parameters` (`List[ParameterDefinition]`): The complete list of method-specific parameters.
  - This drives both dynamic UI creation and validation.
- `return_type` (str): Controls high-level behavior.
  - Supported values in this repo: `"single_objective"` and `"multi_objective"`.
- `objective_names` / `objective_descriptions` (optional): Objective metadata.
    - These fields exist in config but are not currently consumed by the enhanced visualization.
- `objective_plot_configs` (optional): The preferred, per-objective plotting configuration for multi-objective methods (see `ObjectivePlotConfig` below).

#### `ParameterDefinition` and parameter types (method parameters)

All method parameters are declared using `ParameterDefinition` subclasses. Common fields across all parameter types:

- `name` (str): Key used in parameter dicts and passed into methods (e.g., `"alpha"`, `"population_size"`).
- `display_name` (str): UI label text.
- `description` (str): Help text.
- `group` (str): Logical group name used to organize dynamic UI sections.
- `order` (int): Sort order within a group.
- `default_value` (Any): Default used for UI initialization and fallback.
- `required` (bool): Whether the parameter must be present.

Parameter types available in `src/config.py`:

- `NumericParameter`
  - Additional fields: `min_value`, `max_value`, `decimal_places`, `widget_width`.
  - Validation behavior:
    - Enforces bounds if `min_value`/`max_value` are set.
    - If `decimal_places == 0`, the value must be an integer.
- `OptionalNumericParameter`
  - Like `NumericParameter`, but also accepts `None`.
  - Additional fields: `none_text` (what the UI shows for `None`).
  - Validation behavior:
    - `None` is always valid.
    - Otherwise, bounds and integer-ness rules apply.
- `SelectParameter`
  - Additional field: `options: List[Tuple[str, Any]]` where each tuple is `(display_text, value)`.
  - Validation behavior:
    - The value must match one of the `value` entries in `options`.
- `BoolParameter`
  - Checkbox-style boolean parameter.
  - Validation behavior:
    - Must be a Python `bool`.
- `TextParameter`
  - String parameter.
  - Additional fields include `min_length`, `max_length`, `allowed_chars` (regex), `multiline`.

#### `ObjectivePlotConfig` (multi-objective plotting)

For multi-objective methods, `objective_plot_configs` can define how each objective is displayed in the Pareto plot.

Fields:

- `name` (str): Axis label.
- `description` (str): Intended for tooltips/help.
- `transform` (optional str): Transformation to apply before plotting.
  - Implemented in the current enhanced visualization:
    - `"negate"` only.
  - Behavior for `transform="negate"`:
    - Values are multiplied by `-1` before plotting.
    - This is used for the methods where an objective used for the pareto might be negated in order to either maximize or minimize aa value (Many optmizations maximizes a negative value to minimize a score).
- `reverse_scale` (bool): Defined in config, but not currently used by the enhanced visualization.

## 4) Step-by-step: AASHTO CDA as a single-objective method

### Step 1 — Choose your `method_key` and `return_type`

Your `method_key` is used everywhere:

- GUI selection stores a method key
- JSON export writes `analysis_metadata.analysis_method = method_key`
- visualization checks whether a method is multi-objective

AASHTO CDA uses:

- `method_key = "aashto_cda"`
- `return_type = "single_objective"`

You can see this in `src/config.py` in the `OPTIMIZATION_METHODS` registry:

```python
# src/config.py
OptimizationMethodConfig(
    method_key="aashto_cda",
    display_name="AASHTO CDA Statistical Analysis",
    description="Enhanced AASHTO Cumulative Difference Approach for deterministic statistical change point detection. Fast, statistically-justified segmentation without evolutionary computation.",
    parameters=AASHTO_CDA_PARAMETERS,
    return_type="single_objective",  # Shows segmentation graph only
    method_class_path="analysis.methods.aashto_cda.AashtoCdaMethod",
)
```

Notes:

- The controller resolves and imports the configured `method_class_path`.
- `return_type` is crucial for visualization behavior (e.g., whether a Pareto panel is shown).

---

### Step 2 — Define your method parameters (dynamic UI + validation)

Parameters are defined as `ParameterDefinition` instances in `src/config.py`. AASHTO CDA provides a concrete pattern for a non-GA deterministic method.

AASHTO CDA parameter list:

```python
# src/config.py
AASHTO_CDA_PARAMETERS = [
    NumericParameter(
        name="alpha", display_name="Significance Level",
        description="Statistical significance level for change point detection (lower = more conservative)",
        group="statistical_analysis", order=1, default_value=0.05,
        min_value=0.001, max_value=0.49, decimal_places=3
    ),
    SelectParameter(
        name="method", display_name="Error Estimation Method",
        description="Method for estimating standard deviation of measurement error",
        group="statistical_analysis", order=2, default_value=2,
        options=[
            ("MAD with Normal Distribution", 1),
            ("Std Dev of Differences (Recommended)", 2),
            ("Std Dev of Measurements", 3)
        ]
    ),
    BoolParameter(
        name="use_segment_length", display_name="Use Segment-Specific Length",
        description="Use individual segment lengths (recommended) vs. total data length in statistical calculations",
        group="statistical_analysis", order=3, default_value=True
    ),
    NumericParameter(
        name="min_segment_datapoints", display_name="Min Segment Datapoints",
        description="Minimum number of datapoints required per segment",
        group="segment_constraints", order=1, default_value=3,
        min_value=3, max_value=1000, decimal_places=0
    ),
    OptionalNumericParameter(
        name="max_segments", display_name="Max Segments",
        description="Maximum number of segments allowed (None=no limit, algorithm may find fewer)",
        group="segment_constraints", order=2, default_value=None,
        min_value=2, max_value=10000, decimal_places=0
    ),
    NumericParameter(
        name="min_section_difference", display_name="Min Section Difference",
        description="Minimum difference in average values between adjacent segments (0=disabled)",
        group="segment_constraints", order=3, default_value=0.0,
        min_value=0.0, max_value=10.0, decimal_places=3
    ),
    BoolParameter(
        name="enable_diagnostic_output", display_name="Diagnostic Output",
        description="Enable detailed diagnostic information during processing",
        group="processing", order=1, default_value=False
    )
]
```

Parameter meaning (AASHTO CDA):

- `alpha` (`NumericParameter`): Significance level for change-point detection.
  - Lower values are more conservative (fewer change points).
- `method` (`SelectParameter`): Error estimation method.
  - Options map display text to numeric codes (1/2/3).
- `use_segment_length` (`BoolParameter`): Controls whether the CDA statistical calculations use segment-specific length vs. total length.
- `min_segment_datapoints` (`NumericParameter`, integer): Minimum required datapoints per segment (enforced in the CDA method implementation).
- `max_segments` (`OptionalNumericParameter`): Optional upper bound on number of segments.
  - If `None`, the algorithm has no configured hard cap.
- `min_section_difference` (`NumericParameter`): Minimum difference between adjacent segment means (0 disables this filter).
- `enable_diagnostic_output` (`BoolParameter`): Enables additional diagnostic printing (primarily for debugging).

What this configuration buys you:

- GUI can render parameter widgets dynamically (grouped + ordered)
- validation is declarative (`param_def.validate_value(...)`)
- methods can obtain defaults from config consistently (single source of truth)

Where it is used:

- `src/parameter_manager.py` validates parameters by iterating `method_config.parameters`
- `src/ui_builder.py` creates parameter widgets dynamically from the same list

---

### Step 3 — Register your method in the config registry

To make the method appear in the GUI dropdown and be recognized system-wide, you must add an entry to `OPTIMIZATION_METHODS`.

AASHTO CDA’s entry (abridged):

```python
# src/config.py
OPTIMIZATION_METHODS = [
    # ... other methods ...
    OptimizationMethodConfig(
        method_key="aashto_cda",
        display_name="AASHTO CDA Statistical Analysis",
        description="...",
        parameters=AASHTO_CDA_PARAMETERS,
        return_type="single_objective",
        method_class_path="analysis.methods.aashto_cda.AashtoCdaMethod"
    )
]
```

Important fields:

- `method_key`: must be unique
- `display_name`: what the user sees in the dropdown
- `parameters`: drives UI + validation
- `return_type`: drives visualization behavior
- `method_class_path`: tells the controller what class to import and run

Dispatch configuration (no controller code changes):

- You add `method_class_path="analysis.methods.your_method.YourMethod"` in `OPTIMIZATION_METHODS`.
- The controller imports and instantiates that class at runtime (and the app validates these paths at startup).

---

### Step 4 — Implement the method (derive from `AnalysisMethodBase`)

All methods should implement:

- `method_name` property
- `method_key` property
- `run_analysis(...)` that returns an `AnalysisResult`

AASHTO CDA defines a method class in `src/analysis/methods/aashto_cda.py`:

```python
# src/analysis/methods/aashto_cda.py
class AashtoCdaMethod(AnalysisMethodBase):
    @property
    def method_name(self) -> str:
        return "AASHTO CDA Statistical Analysis"

    @property
    def method_key(self) -> str:
        return "aashto_cda"

    def run_analysis(self,
                    data,  # RouteAnalysis object (primary) or DataFrame (fallback)
                    route_id: str,
                    x_column: str,
                    y_column: str,
                    gap_threshold: float,
                    **kwargs) -> AnalysisResult:
        # ... implementation ...
        return AnalysisResult(...)
```

#### 3.1 Pull parameter defaults from config

AASHTO CDA reads defaults from `config.py`:

```python
# src/analysis/methods/aashto_cda.py
method_config = get_optimization_method('aashto_cda')
param_defaults = {param.name: param.default_value for param in method_config.parameters}

alpha = kwargs.get('alpha', param_defaults['alpha'])
method = kwargs.get('method', param_defaults['method'])
use_segment_length = kwargs.get('use_segment_length', param_defaults['use_segment_length'])
```

#### 3.2 Return results in the unified `AnalysisResult` format

Your method must return an `AnalysisResult` such that:

- `method_key` matches your registry entry
- `all_solutions` is always a list
  - for single-objective: `[best_solution]`
  - for multi-objective: `[{...}, {...}, ...]` (Pareto front)

AASHTO CDA returns a deterministic single result:

```python
# src/analysis/methods/aashto_cda.py
return AnalysisResult(
    method_name=self.method_name,
    method_key=self.method_key,
    route_id=route_id,
    all_solutions=[{
        'chromosome': all_breakpoints.tolist(),
        'fitness': 0.0,
        'avg_segment_length': ...,
        'num_segments': len(segment_stats)
    }],
    mandatory_breakpoints=list(mandatory_breakpoints),
    optimization_stats=diagnostics,
    input_parameters={
        'alpha': alpha,
        'method': method,
        'use_segment_length': use_segment_length,
        'min_segment_datapoints': min_segment_datapoints,
        'max_segments': max_segments,
        'min_section_difference': min_section_difference,
        'gap_threshold': gap_threshold
    },
    data_summary={...}
)
```

Output contract:

- Each solution must include breakpoint locations in `'chromosome'` (sorted list of milepoints including start and end).
- Include `input_parameters` for reproducibility.

---

### Step 5 — Ensure visualization behavior matches your return type

The enhanced visualization decides whether to show the Pareto panel using the configured method return type:

```python
# src/enhanced_visualization.py
analysis_method = self.json_results.get('analysis_metadata', {}).get('analysis_method', 'single')
from config import is_multi_objective_method
self.is_multi_objective = is_multi_objective_method(analysis_method)
```

So for new methods:

- if your method is single-result: set `return_type="single_objective"`
- if your method returns a Pareto front: set `return_type="multi_objective"`

---

## 5) Checklist: adding your own new single-objective method

Use this checklist when you build your own method (not CDA):

1. **Config**: add `YOUR_METHOD_PARAMETERS` in `src/config.py`
2. **Config**: add `OptimizationMethodConfig(method_key="your_key", ..., return_type="single_objective", method_class_path="analysis.methods.your_method.YourMethod")`
3. **Implementation**: create `src/analysis/methods/your_method.py` implementing `AnalysisMethodBase`
4. **Startup check**: run the app (or tests) to confirm registry validation passes (bad import paths fail fast with a clear error)

---

## 6) Multi-objective example (NSGA-II)

This section shows how the existing **multi-objective** method is configured and how it differs from the single-objective CDA example.

The core differences are:

- The method is configured as `return_type="multi_objective"`.
- The method returns **multiple solutions** (a Pareto front) in `AnalysisResult.all_solutions`.
- The visualization shows a **Pareto panel** in addition to the segmentation view.

### 6.1 Configuration: return type + objective plot semantics

The method is registered in `src/config.py` as:

```python
# src/config.py
OptimizationMethodConfig(
    method_key="multi",
    display_name="Multi-Objective NSGA-II",
    description="Pareto front optimization exploring trade-offs between total deviation and average segment length. Multiple optimal solutions.",
    parameters=MULTI_OBJECTIVE_NSGA2_PARAMETERS,
    return_type="multi_objective",  # Shows pareto front + segmentation graph
    method_class_path="analysis.methods.multi_objective.MultiObjectiveMethod",
    objective_names=["Total Deviation", "Average Segment Length"],
    objective_descriptions=[
        "Total deviation from target values (algorithm maximizes negative deviation for minimization)",
        "Average length of highway segments (algorithm maximizes positive length)"
    ],
    objective_plot_configs=[
        ObjectivePlotConfig(
            name="Total Deviation",
            description="Total deviation - convert negative GA value to positive for minimization display",
            transform="negate"
        ),
        ObjectivePlotConfig(
            name="Average Segment Length",
            description="Average segment length - use positive GA value directly for maximization display"
        )
    ]
)
```

The method returns raw GA objective values (including negative deviation). The configuration provides plotting/interpretation transforms.

What `transform="negate"` means (current implementation):

- In the enhanced visualization (`update_pareto_graph`), if an objective config has `transform == 'negate'`, the plotted values are negated before display.
- `"negate"` is the only transform implemented in the visualization.

### 6.2 Dispatch behavior (config-driven)

For multi-objective methods, the controller still invokes `run_analysis(...)` the same way, but it selects the implementation class via `method_class_path`.

Requirements:

- Keep the same `run_analysis(data, route_id, x_column, y_column, gap_threshold, **kwargs)` calling convention.
- Put the **full Pareto set** in `AnalysisResult.all_solutions`.
- In config, set `return_type="multi_objective"` so the visualization shows the Pareto panel.

### 6.3 Method implementation: building a Pareto front into `AnalysisResult.all_solutions`

The method itself lives in `src/analysis/methods/multi_objective.py` and builds a list of solution dictionaries from the final Pareto front indices:

```python
# src/analysis/methods/multi_objective.py
final_fronts, final_fitness_values = ga.fast_non_dominated_sort(population)
pareto_front_indices = final_fronts[0] if final_fronts else []

all_solutions = []
for idx in pareto_front_indices:
    chromosome = population[idx]
    negative_deviation, avg_segment_length = final_fitness_values[idx]

    solution_info = {
        'chromosome': chromosome,
        'fitness': [negative_deviation, avg_segment_length],
        'objective_values': [negative_deviation, avg_segment_length],
        'deviation_fitness': negative_deviation,
        'segment_fitness': avg_segment_length,
        'num_segments': segment_count,
        'avg_segment_length': calculated_avg_length,
        'segment_lengths': segments
    }
    all_solutions.append(solution_info)

return AnalysisResult(
    method_name=self.method_name,
    method_key=self.method_key,
    route_id=route_id,
    all_solutions=all_solutions,
    optimization_stats=optimization_stats,
    mandatory_breakpoints=sorted(list(ga.mandatory_breakpoints)),
    processing_time=time.time() - start_time,
    input_parameters=input_parameters,
    data_summary=data_summary
)
```

Multi-objective output structure:

- Put the objective vector in both `fitness` and `objective_values` as a list in a consistent order.
- Put derived metrics (e.g., segment count, average segment length) as separate scalar fields.

### 6.4 Multi-file utilities: where shared GA logic lives

Multi-objective methods in this repo call shared utility modules for common operators.

#### Shared operators and NSGA-II helpers

`src/analysis/utils/ga_utilities.py` contains reusable functions used by `MultiObjectiveMethod`:

```python
# src/analysis/methods/multi_objective.py
from ..utils.ga_utilities import (
    nsga2_tournament_selection, fast_non_dominated_sort, calculate_crowding_distance,
    crossover_with_retries, mutation_with_retries, analyze_population_diversity
)
```

Those utilities implement common pieces like:

- NSGA-II tournament selection (`nsga2_tournament_selection`)
- Retry-based operators (`crossover_with_retries`, `mutation_with_retries`)

#### The core GA engine

The heavy lifting (data prep, constraints, caching, and fitness evaluation) lives in `src/analysis/utils/genetic_algorithm.py` as `HighwaySegmentGA`.

`MultiObjectiveMethod` uses it directly:

```python
# src/analysis/methods/multi_objective.py
from analysis.utils.genetic_algorithm import HighwaySegmentGA

ga = HighwaySegmentGA(
    actual_data, x_column, y_column,
    min_length=min_length, max_length=max_length,
    population_size=population_size,
    crossover_rate=crossover_rate,
    mutation_rate=mutation_rate,
    gap_threshold=gap_threshold,
)
```

How to apply this pattern to your own new method:

- Put any reusable operators/statistics in `src/analysis/utils/<something>.py`.
- Keep `src/analysis/methods/<your_method>.py` focused on orchestration and producing a correct `AnalysisResult`.

---

## Appendix A — Single Objective output Template

Copy/paste starter for a new *single-objective (single-result)* method implementation.

Filename to create:

- `src/analysis/methods/<new_analysis_method>.py`

Required behavior summary:

- Must implement `AnalysisMethodBase`.
- Must expose `method_name` and `method_key`.
- Must implement `run_analysis(data, route_id, x_column, y_column, gap_threshold, **kwargs)`.
- Must return an `AnalysisResult` with exactly **one primary solution** in `all_solutions`.
- The primary solution must include `'chromosome'` (sorted breakpoints including start/end).

```python
"""<New Analysis Method> (Single Objective)

Template for implementing a single-objective analysis method under the
config-driven dispatch architecture.

How to register this method in the application:
1) Add a method entry in `src/config.py` with:
   - method_key="<your_key>"
   - return_type="single_objective"
   - method_class_path="analysis.methods.<new_analysis_method>.<NewMethodClass>"
2) Add `List[ParameterDefinition]` in `src/config.py` and reference it from the
   `OptimizationMethodConfig.parameters` field.

Notes:
- Avoid hardcoding parameter defaults; read them from config.
- Keep results schema-friendly: always include `input_parameters` and `data_summary`.
"""

from __future__ import annotations

import time
from typing import Any, Dict

import numpy as np

from analysis.base import AnalysisMethodBase, AnalysisResult
from config import get_optimization_method


class <NewMethodClass>(AnalysisMethodBase):
    @property
    def method_name(self) -> str:
        return "<New Analysis Method (Single)>"

    @property
    def method_key(self) -> str:
        return "<your_method_key>"  # Must match config registry

    def run_analysis(
        self,
        data: Any,
        route_id: str,
        x_column: str,
        y_column: str,
        gap_threshold: float,
        **kwargs,
    ) -> AnalysisResult:
        """Run the analysis for one route.

        Required inputs (provided by the framework/controller):
        - data: RouteAnalysis (preferred) or DataFrame fallback
        - route_id: str route identifier
        - x_column/y_column: column names for DataFrame fallback
        - gap_threshold: framework-level gap detection threshold

        Method-specific inputs:
        - passed via **kwargs and should map to ParameterDefinition names.
        """
        start_time = time.time()

        # 1) Resolve parameter defaults from config (single source of truth)
        method_config = get_optimization_method(self.method_key)
        if not method_config:
            raise ValueError(f"Method configuration not found for '{self.method_key}'")

        param_defaults = {p.name: p.default_value for p in method_config.parameters}

        # 2) Read method parameters (example placeholders)
        # NOTE: Keep these in sync with the config parameter list.
        min_length = kwargs.get("min_length", param_defaults.get("min_length"))
        max_length = kwargs.get("max_length", param_defaults.get("max_length"))
        enable_diagnostic_output = kwargs.get(
            "enable_diagnostic_output", param_defaults.get("enable_diagnostic_output", False)
        )

        # 3) Normalize/prepare input data
        # Preferred: RouteAnalysis objects expose route_data + mandatory_breakpoints.
        if hasattr(data, "route_data") and hasattr(data, "mandatory_breakpoints"):
            route_analysis = data
            route_df = route_analysis.route_data
            mandatory_breakpoints = sorted(list(route_analysis.mandatory_breakpoints))
        else:
            # Fallback: DataFrame; build RouteAnalysis via analyze_route_gaps
            from data_loader import analyze_route_gaps

            route_analysis = analyze_route_gaps(
                data,
                x_column,
                y_column,
                route_id=route_id,
                gap_threshold=gap_threshold,
            )
            route_df = route_analysis.route_data
            mandatory_breakpoints = sorted(list(route_analysis.mandatory_breakpoints))

        # 4) TODO: run your algorithm
        # Output must be a sorted list of breakpoints including start and end.
        x_values = np.asarray(route_df.iloc[:, 0])
        route_start = float(x_values.min())
        route_end = float(x_values.max())

        # Example placeholder: trivial segmentation (replace with your algorithm)
        chromosome = [route_start, route_end]

        # 5) Build the standardized solution payload
        # REQUIRED: 'chromosome'
        # RECOMMENDED: 'fitness', 'objective_values', derived stats
        solution: Dict[str, Any] = {
            "chromosome": chromosome,
            "fitness": 0.0,
            "objective_values": [0.0],
            "num_segments": max(0, len(chromosome) - 1),
            "avg_segment_length": float(route_end - route_start) if route_end > route_start else 0.0,
        }

        # 6) Return AnalysisResult (single-objective => list of exactly 1 solution)
        input_parameters = {
            "gap_threshold": gap_threshold,
            "min_length": min_length,
            "max_length": max_length,
            "enable_diagnostic_output": enable_diagnostic_output,
        }

        data_summary = {
            "route_id": route_id,
            "num_points": int(len(route_df)),
            "x_min": float(route_start),
            "x_max": float(route_end),
            "mandatory_breakpoints": mandatory_breakpoints,
        }

        return AnalysisResult(
            method_name=self.method_name,
            method_key=self.method_key,
            route_id=route_id,
            all_solutions=[solution],
            mandatory_breakpoints=mandatory_breakpoints,
            processing_time=float(time.time() - start_time),
            optimization_stats={},
            input_parameters=input_parameters,
            data_summary=data_summary,
        )
```

---

## Appendix B — Multi-Objective Output Template

Copy/paste starter for a new *multi-objective (Pareto front)* method implementation.

Filename to create:

- `src/analysis/methods/<new_analysis_method>.py`

Required behavior summary:

- Must implement `AnalysisMethodBase`.
- Must return an `AnalysisResult` where `all_solutions` is a **Pareto set** (length ≥ 1).
- Each solution must include:
  - `'chromosome'`: sorted breakpoints
  - `'objective_values'`: a list of floats in a consistent order (length = number of objectives)
  - `'fitness'`: typically identical to `'objective_values'` (kept for compatibility)
- In `src/config.py`, set:
  - `return_type="multi_objective"`
  - `objective_plot_configs=[...]` so the Pareto plot knows transforms/labels.

```python
"""<New Analysis Method> (Multi Objective)

Template for implementing a multi-objective analysis method that returns a Pareto
front in `AnalysisResult.all_solutions`.

Configuration requirements:
- `OptimizationMethodConfig.return_type = "multi_objective"`
- `OptimizationMethodConfig.method_class_path` points at this class
- `OptimizationMethodConfig.objective_plot_configs` defines labels/transforms
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

import numpy as np

from analysis.base import AnalysisMethodBase, AnalysisResult
from config import get_optimization_method


class <NewMethodClass>(AnalysisMethodBase):
    @property
    def method_name(self) -> str:
        return "<New Analysis Method (Multi)>"

    @property
    def method_key(self) -> str:
        return "<your_method_key>"  # Must match config registry

    def run_analysis(
        self,
        data: Any,
        route_id: str,
        x_column: str,
        y_column: str,
        gap_threshold: float,
        **kwargs,
    ) -> AnalysisResult:
        start_time = time.time()

        method_config = get_optimization_method(self.method_key)
        if not method_config:
            raise ValueError(f"Method configuration not found for '{self.method_key}'")
        param_defaults = {p.name: p.default_value for p in method_config.parameters}

        # Example placeholders — update to your actual parameters.
        min_length = kwargs.get("min_length", param_defaults.get("min_length"))
        max_length = kwargs.get("max_length", param_defaults.get("max_length"))

        # Normalize/prepare input
        if hasattr(data, "route_data") and hasattr(data, "mandatory_breakpoints"):
            route_analysis = data
            route_df = route_analysis.route_data
            mandatory_breakpoints = sorted(list(route_analysis.mandatory_breakpoints))
        else:
            from data_loader import analyze_route_gaps

            route_analysis = analyze_route_gaps(
                data,
                x_column,
                y_column,
                route_id=route_id,
                gap_threshold=gap_threshold,
            )
            route_df = route_analysis.route_data
            mandatory_breakpoints = sorted(list(route_analysis.mandatory_breakpoints))

        x_values = np.asarray(route_df.iloc[:, 0])
        route_start = float(x_values.min())
        route_end = float(x_values.max())

        # TODO: run your multi-objective algorithm and produce a Pareto front.
        # The objective vector ordering must match the method's config plotting metadata.
        # Example objective order:
        #   objective_values = [objective_1_value, objective_2_value]
        pareto_solutions: List[Dict[str, Any]] = []

        # Example placeholder: one trivial solution (replace with actual Pareto set)
        chromosome = [route_start, route_end]
        objective_values = [0.0, 0.0]
        pareto_solutions.append(
            {
                "chromosome": chromosome,
                "objective_values": objective_values,
                "fitness": objective_values,
                "num_segments": max(0, len(chromosome) - 1),
                "avg_segment_length": float(route_end - route_start) if route_end > route_start else 0.0,
            }
        )

        input_parameters = {
            "gap_threshold": gap_threshold,
            "min_length": min_length,
            "max_length": max_length,
        }
        data_summary = {
            "route_id": route_id,
            "num_points": int(len(route_df)),
            "x_min": float(route_start),
            "x_max": float(route_end),
            "mandatory_breakpoints": mandatory_breakpoints,
        }

        return AnalysisResult(
            method_name=self.method_name,
            method_key=self.method_key,
            route_id=route_id,
            all_solutions=pareto_solutions,
            mandatory_breakpoints=mandatory_breakpoints,
            processing_time=float(time.time() - start_time),
            optimization_stats={},
            input_parameters=input_parameters,
            data_summary=data_summary,
        )
```
