# Developer Guide

Audience: Python developers extending or maintaining the Highway Segmentation Tool.

This guide covers the system architecture, module map, end-to-end data flow, and key design patterns. It is the starting point for all developer work. For task-specific instructions, follow the links in the [Extension points](#5-extension-points) section.

---

## 1. System overview

The Highway Segmentation Tool optimizes the placement of segment boundaries along highway routes using configurable analysis methods (genetic algorithms, statistical CDA, etc.). It exposes both a GUI and a CLI; both paths share the same analysis core.

The system is designed around three extensibility principles:

- **Config-driven dispatch** — new methods and preprocessing steps are registered in `src/config.py` and imported at runtime. No controller code changes required.
- **Declarative parameters** — `ParameterDefinition` classes drive both GUI widget rendering and parameter validation from a single declaration.
- **Standardized result contract** — all analysis methods return `AnalysisResult`; serialization is handled by `AnalysisResult.to_route_result_dict()`, not the caller.

---

## 2. Module map

### Entry points

| Module | Responsibility |
| --- | --- |
| `gui_main.py` | Root GUI class. Coordinates six specialized managers; owns app-level state (loaded data, column selections, running flags). |
| `cli.py` | CLI entry point. Parses arguments and delegates to `cli_runner.py`. |
| `cli_runner.py` | Headless optimization runner. Shares the same analysis methods and results writer as the GUI path — no tkinter dependency. |
| `run.py` | Launcher script that starts the GUI. |

### GUI layer

| Module | Responsibility |
| --- | --- |
| `ui_builder.py` | Builds the main window layout and dynamic parameter widgets. |
| `visualization_ui.py` | Enhanced results visualization window (Pareto + segmentation panes). |
| `visualization_ui_builder.py` | Builds the visualization window layout (extracted from `visualization_ui.py`). |
| `parameter_manager.py` | Parameter validation, state management, and UI updates. |
| `file_manager.py` | File I/O: data loading, CSV processing, result file management. |
| `settings_manager.py` | Persists user settings (column selections, parameters) between sessions. |
| `cli_export_dialog.py` | "Create Batch Command" dialog — exports current GUI settings as a CLI run spec. |

### Configuration

| Module | Responsibility |
| --- | --- |
| `config.py` | Single source of truth: method registry (`OPTIMIZATION_METHODS`), preprocessing registry (`PREPROCESSING_METHODS`), parameter definitions, application constants. |
| `parameter_definitions.py` | `ParameterDefinition` widget classes (`NumericParameter`, `SelectParameter`, `BoolParameter`, etc.). |
| `app_constants.py` | Pure constants with no framework dependencies (`AlgorithmConstants`, `UIConfig`). |
| `optimization_handler.py` | Protocol definition for the app object that `OptimizationController` depends on. |

### Optimization pipeline

| Module | Responsibility |
| --- | --- |
| `optimization_controller.py` | Thread lifecycle, worker orchestration, per-route execution loop. |
| `route_utils.py` | Route ID normalization, filtering, listing. `prepare_routes_for_optimization()` runs gap analysis and preprocessing for all selected routes before the GA starts. |
| `data_loader.py` | Gap detection, attribute break analysis, preprocessing pipeline integration. Produces `RouteAnalysis` objects. |
| `optimization_results_saver.py` | Bridges controller result dicts to `AnalysisResult` objects and writes JSON via `ExtensibleJsonResultsManager`. |

### Analysis framework

| Module | Responsibility |
| --- | --- |
| `analysis/base.py` | `AnalysisResult` dataclass (result contract for all methods) and `AnalysisMethodBase` ABC. `AnalysisResult.to_route_result_dict()` handles all method-specific serialization. |
| `analysis/methods/` | Concrete method implementations (`single_objective.py`, `multi_objective.py`, `constrained.py`, `aashto_cda.py`, `constrained_deb.py`, `pelt_segmentation.py`). |
| `analysis/utils/` | Shared GA utilities: `HighwaySegmentGA` engine (`genetic_algorithm.py`), NSGA-II helpers (`ga_utilities.py`). |
| `plugins/` | Method-specific result plugins that extend `ExtensibleJsonResultsManager` with per-method JSON statistics. |

### Results and export

| Module | Responsibility |
| --- | --- |
| `extensible_results_manager.py` | Writes schema-compliant JSON results. Discovers and dispatches method plugins for per-method statistics sections. |
| `excel_export.py` | Exports JSON results to Excel workbooks. |
| `validate_json_schema.py` | Validates a results JSON file against the schema (also usable from CLI). |

---

## 3. End-to-end data flow

### GUI path

```text
User loads CSV
  └─ FileManager.load_data_file()
       └─ data_loader.load_data() → app.data (RouteAnalysis)

User configures parameters
  └─ UIBuilder (dynamic widgets from ParameterDefinition list)
       └─ ParameterManager.validate_and_show_errors()

User clicks Start
  └─ OptimizationController.start_optimization()
       └─ [worker thread]
            │
            ├─ route_utils.prepare_routes_for_optimization()
            │     For each selected route:
            │       1. filter_data_by_route()
            │       2. sort by x_column
            │
            │       3a. [preprocessing configured] process_route_with_preprocessing()
            │             Phase 1 [optional]: pre-gap method applied to raw DataFrame
            │             Phase 2 [always]:   analyze_route_gaps()
            │                                   + must_break_columns [optional]
            │             Phase 3 [optional]: primary method applied to RouteAnalysis
            │             Phase 4 [optional]: secondary_break_columns applied
            │             Phase 5 [optional]: secondary method applied to RouteAnalysis
            │             → (RouteAnalysis, preprocessing_results)
            │
            │       3b. [no preprocessing] analyze_route_gaps()
            │             + must_break_columns      [optional]
            │             + secondary_break_columns [optional]
            │             → RouteAnalysis
            │
            │       RouteAnalysis carries: route_data, gap_segments, mandatory_breakpoints
            │       → yields (route_id, RouteAnalysis, preprocessing_results)
            │
            ├─ For each prepared route:
            │     config.resolve_method_class(method_key)
            │       → method_instance.run_analysis(RouteAnalysis, ...)
            │       → AnalysisResult
            │       → analysis_result.to_route_result_dict()
            │       → route_result dict appended to all_route_results
            │
            └─ [all routes complete]
                  OptimizationResultsSaver.save()
                    └─ ExtensibleJsonResultsManager.save_analysis_results()
                         └─ JSON file on disk

[main thread]
  visualization_ui.show_enhanced_visualization(json_path)
    └─ EnhancedVisualizationWindow (Pareto + segmentation panes)
```

### CLI path

```text
cli.py main()
  └─ cli_runner.run_from_spec(run_spec)
       ├─ data_loader.load_data()  →  RouteAnalysis
       ├─ route_utils.prepare_routes_for_optimization()
       │     (same per-route filter → sort → gap/attribute-break/preprocessing logic as GUI path)
       ├─ For each route:
       │     config.resolve_method_class(method_key)
       │       → method_instance.run_analysis()
       │       → AnalysisResult
       └─ ExtensibleJsonResultsManager.save_analysis_results()
            └─ JSON file on disk
```

The CLI path deliberately mirrors the GUI worker thread. Both use the same `data_loader`, `route_utils`, analysis methods, and results manager. No analysis logic lives exclusively in either path.

---

## 4. Key design patterns

### 4.1 Config-driven dispatch

Analysis methods and preprocessing methods are registered in `src/config.py` as dataclasses (`OptimizationMethodConfig`, `PreprocessingMethodConfig`) that include a `method_class_path` string. The controller resolves these at runtime:

```python
# src/config.py
OptimizationMethodConfig(
    method_key="aashto_cda",
    method_class_path="analysis.methods.aashto_cda.AashtoCdaMethod",
    return_type="single_objective",
    parameters=AASHTO_CDA_PARAMETERS,
    ...
)

# Runtime (optimization_controller.py / cli_runner.py)
cls = config.resolve_method_class(method_key)
result = cls().run_analysis(route_analysis, ...)
```

**Consequence:** adding a new method requires no controller code changes — only a config entry and an implementation class.

### 4.2 AnalysisResult as the result contract

All analysis methods return `AnalysisResult` (defined in `analysis/base.py`). The result object knows how to serialize itself:

```python
# After run_analysis() returns:
route_result = analysis_result.to_route_result_dict()
```

`to_route_result_dict()` handles all method-specific keys (Pareto front, constrained penalty fields, AASHTO statistical parameters, convergence history) based on `method_key` and the content of `best_solution` and `optimization_stats`. The controller and saver have no per-method branching.

**Consequence:** new methods that produce output matching an existing shape (single-objective, multi-objective, constrained) need no changes to `to_route_result_dict()`. New output shapes require adding a block there — not in the controller.

### 4.3 Declarative parameters

Method parameters are declared as `ParameterDefinition` instances in `src/config.py`. The same list drives:

- **GUI widget rendering** — `UIBuilder` creates widgets dynamically from the definition (type, bounds, grouping, ordering)
- **Parameter validation** — `ParameterManager` validates values using the same definition
- **CLI run spec parsing** — `cli_runner.py` reads and validates run-spec parameters against the same definition
- **Default values** — methods read defaults from config rather than hardcoding them

```python
# In your method's run_analysis():
method_config = get_optimization_method(self.method_key)
param_defaults = {p.name: p.default_value for p in method_config.parameters}
alpha = kwargs.get("alpha", param_defaults["alpha"])
```

### 4.4 Route preparation ownership

All route data preparation (gap detection, attribute break analysis, preprocessing pipeline) lives in `route_utils.prepare_routes_for_optimization()`, which calls into `data_loader`. The controller only iterates the returned list:

```python
prepared_routes, preprocessed_data = prepare_routes_for_optimization(
    app.data, route_column, selected_routes, x_column, y_column,
    gap_threshold=gap_threshold, preprocessing_config=preprocessing_config,
    must_break_columns=..., log_callback=app.log_message,
)

for route_id, route_analysis, preprocessing_results in prepared_routes:
    result = method.run_analysis(route_analysis, ...)
```

### 4.5 Logging conventions

| Context | Mechanism | Why |
| --- | --- | --- |
| User-visible progress (GUI panel / CLI stdout) | `log_callback` passed via `**kwargs` | Routes output to the right destination in both GUI and headless contexts |
| Internal warnings and errors | `logging.getLogger(__name__)` | Goes to Python logging subsystem; `WARNING+` is forwarded to GUI panel automatically |
| Visualization window output | `safe_print()` from `visualization/utils.py` | Viz window is a separate window with no access to `log_callback`; handles Windows Unicode encoding |
| CLI and script output | `print()` | Correct for terminal-facing code |

**Rule for method implementations:** never call `print()` directly. Use `log = kwargs.get("log_callback") or print` and call `log(...)`.

---

## 5. Extension points

| Task | Where to start |
| --- | --- |
| Add a new analysis method | [`docs/configuring_new_analysis_method.md`](configuring_new_analysis_method.md) |
| Add a new preprocessing method | [`docs/configuring_new_preprocessing_method.md`](configuring_new_preprocessing_method.md) |
| Change the JSON output schema | `src/extensible_results_manager.py` + [`docs/json_format_specification.md`](json_format_specification.md) |
| Add CLI arguments or run-spec fields | `src/cli.py` + `src/cli_runner.py` |
| Add a new parameter type to the UI | `src/parameter_definitions.py` + `src/config.py` |
| Modify result serialization for all methods | `AnalysisResult.to_route_result_dict()` in `src/analysis/base.py` |
| Modify result serialization for one method | Add a block in `to_route_result_dict()` gated on `self.method_key` |

---

## 6. Testing

The test suite is under `tests/` with three layers:

| Layer | Location | Purpose |
| --- | --- | --- |
| Unit | `tests/unit/` | Individual functions and classes in isolation |
| Integration | `tests/integration/` | Cross-module workflows (JSON export, schema validation) |
| Regression | `tests/regression/` | End-to-end method + dataset matrix via both GUI and CLI paths |

Run the full suite:

```bash
python -m pytest tests/ -x -q
```

Run smoke tests only (fast, no data-dependent tests):

```bash
python run_tests.py --smoke
```

Run the regression suite (requires test data):

```bash
python run_tests.py --regression
```

New methods should include entries in `tests/regression/test_parameters_template.json` to be picked up automatically by the regression matrix. See Appendix C of [`configuring_new_analysis_method.md`](configuring_new_analysis_method.md) for details.
