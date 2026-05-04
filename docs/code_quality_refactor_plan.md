# Code Quality Review + Refactor Plan

Branch: `main`

## Goals

- Improve maintainability and readability without changing user-visible behavior.
- Reduce duplication and tighten module responsibilities.
- Make future changes safer via clearer interfaces and tests.

Note: One targeted user-visible behavior change was explicitly approved (see "B1 Route Null Exclusion" below).

## Ground Rules

- Keep refactors behavior-preserving unless explicitly agreed.
- Prefer small, verifiable steps (run pytest after each meaningful change).
- Avoid wide rewrites of the GUI and GA core in early steps.

## Current Hotspots (by file size)

Largest modules under `src/` (approx lines):

- `src/analysis/utils/genetic_algorithm.py` (~1870)
- `src/visualization_ui.py` (~1560)
- `src/gui_main.py` (~1390)
- `src/config.py` (~1270)
- `src/ui_builder.py` (~1170)
- `src/file_manager.py` (~1130)
- `src/optimization_controller.py` (~985)

## Completed Work (May 2026)

### Visualization Refactor (behavior-preserving)

- Renamed UI entrypoint:
  - `src/enhanced_visualization.py` → `src/visualization_ui.py`
  - Updated all call sites and monkeypatch targets accordingly.
- Consolidated visualization helpers into cohesive logical units under `src/visualization/`:
  - `pareto.py` (Pareto series prep + selection)
  - `autoscale.py` (visible window selection + y-limit autoscale)
  - `breakpoints.py` (mandatory extraction + vline specs + xlim from breakpoints)
  - `results_binding.py` (schema extraction: routes, x/y column resolution, original data grouping)
  - `graph_styling.py` (axis style constants + axis label formatting + legend de-dupe)
- Removed redundant small modules as they were merged into the above.
- Validation: full `pytest -q` remains green after each step.

### Phase 1 Starter — Route-ID Normalization Consolidation (behavior-preserving)

- Confirmed canonical normalizer exists in `src/route_utils.py`.
- Aligned route-id matching boundaries in `src/visualization_ui.py` to use `normalize_route_id()`
  (with safe fallback to prior `str(...).strip()` behavior to avoid regressions).
- Validation:
  - `pytest -q tests/test_route_id_normalization.py`
  - full `pytest -q`

### Phase 1 — Route Column Sentinel + Selection Normalization (behavior-preserving)

- Centralized the route-column dropdown sentinel text in `src/route_utils.py`:
  - `ROUTE_COLUMN_NONE_SENTINEL = "None - treat as single route"`
  - `normalize_route_column_selection()` helper
- Updated call sites in GUI/controller/visualization to use the shared constant/helper.
- Added unit test coverage for `normalize_route_column_selection()`.
- Validation: full `pytest -q` (223 passed, 14 skipped).

### B1 Route Null Exclusion (behavior change — explicitly approved)

When a user selects a real route column (multi-route mode):

- Rows where the route ID is missing (blank/empty/NA) are removed from analysis.
- Literal route IDs like "nan"/"null"/"none" are treated as data if they appear in the file.
- The application logs how many rows were removed and why.
- If all rows have missing route IDs, this is a hard error (multi-route analysis cannot proceed).

Implemented in:

- `src/file_manager.py`
  - `detect_available_routes()` now ignores missing route IDs (no "Default" bucket).
  - `load_data_file()` filters out rows with missing route IDs when a user-selected route column is used.
- `src/optimization_controller.py`
  - Safety net: if the route column is selected/changed after load, rows with missing route IDs are filtered before processing.

Validation:

- Targeted Phase 1 tests:
  - `pytest -q tests/unit/test_phase1_file_manager.py tests/integration/test_phase1_complete_workflow.py`
- Full suite:
  - `pytest -q` (223 passed, 14 skipped).

### Phase 1 — Optional UI Value Parsing Consolidation (behavior-preserving)

- Centralized optional UI parsing rules in `src/value_parsing.py`:
  - Missing markers are intentionally narrow and stable: `None`, empty/whitespace, `"(None)"`, `"null"`, `"none"`.
  - Literal `"nan"` is treated as data (not missing).
  - Optional numeric parsing rejects NaN values (including `"nan"` when parsed as a float) as invalid input.
- Updated dynamic-parameter parsing paths to use shared helpers:
  - `OptionalNumericParameter` in `src/config.py`
  - Inline dynamic-parameter editor in `src/ui_builder.py`
- Tightened required numeric validation: `NumericParameter` now treats NaN as invalid input.
- Validation: full `pytest -q` remains green.

## Refactor Phases

### Phase 0 — Baseline + Guardrails (no behavior change)

- Ensure `pytest` is green and capture baseline runtime.
- Identify any tests that are slow/flaky and quarantine only if needed.
- Add lightweight developer docs for common commands.

### Phase 1 — Low-risk hygiene (high ROI)

Targets: duplicated logic, confusing naming, and non-local side effects.

- Centralize route-id normalization (✅ completed).
- Centralize common "safe string" handling for optional params (`None`, `"(None)"`, `"null"`). (✅ completed)
- Extract small pure helpers from very large modules (no import cycles).
- Normalize logging patterns (consistent `logger` usage; avoid mixing `print` + GUI log unless intentional).

Exit criteria:

- All tests still pass.
- No new UI behavior unless explicitly approved.

### Phase 2 — Module seams + interfaces

Targets: tight coupling between GUI ↔ controller ↔ file I/O.

- Introduce small typed interfaces (Protocol) for the app surface used by managers (where it reduces coupling).
- Reduce cross-module imports that pull in tkinter at import-time (where not needed).
- Make method-resolution in `config.py` more explicit and testable.

Exit criteria:

- Clearer boundaries, fewer hidden dependencies.

### Phase 3 — Large-file decomposition (risk-managed)

Targets: `genetic_algorithm.py`, `enhanced_visualization.py`, `config.py`.

- Split into cohesive submodules (e.g., operators/fitness/cache/stats) with stable public entry points.
- Keep the original import path working (re-export symbols) to avoid churn.

Note: `enhanced_visualization.py` has been renamed to `visualization_ui.py`.

Exit criteria:

- Same external API, same outputs, easier navigation.

## Proposed Next Refactor (Phase 1)

Now that the route-column sentinel is centralized and B1 is implemented, the next Phase 1 targets are:

- Centralize "safe string" handling for other optional UI parameters (beyond routing).
  - Candidate placement: `src/value_parsing.py` (preferred, already exists) rather than a new module.
  - Validation: add/extend unit tests first; run full `pytest -q`.
- Audit remaining ad-hoc string sentinels in tests and replace with shared constants where appropriate.

## How We’ll Validate

- Run `pytest -q` after each step.
- For any refactor touching routing, run `pytest -q tests/test_route_id_normalization.py`.

## Open Questions

- Should route IDs treat leading zeros as significant everywhere (default: yes, keep as strings)?
- Should we treat additional missing markers as empty (e.g., `"<NA>"`)?
