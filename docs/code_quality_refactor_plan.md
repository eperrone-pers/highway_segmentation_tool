# Code Quality Review + Refactor Plan

Branch: `refactor/code-quality-audit`

## Goals
- Improve maintainability and readability without changing user-visible behavior.
- Reduce duplication and tighten module responsibilities.
- Make future changes safer via clearer interfaces and tests.

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

## Refactor Phases

### Phase 0 — Baseline + Guardrails (no behavior change)
- Ensure `pytest` is green and capture baseline runtime.
- Identify any tests that are slow/flaky and quarantine only if needed.
- Add lightweight developer docs for common commands.

### Phase 1 — Low-risk hygiene (high ROI)
Targets: duplicated logic, confusing naming, and non-local side effects.
- Centralize route-id normalization (✅ completed).
- Centralize common "safe string" handling for optional params (`None`, `"(None)"`, `"null"`).
- Extract small pure helpers from very large modules (no import cycles).
- Normalize logging patterns (consistent `logger` usage; avoid mixing `print` + GUI log unless intentional).

Exit criteria:
- All tests still pass.
- No new UI behavior.

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
- Centralize common "safe string" handling for optional params.
  - Goal: one helper for treating missing markers consistently (e.g. `None`, `""`, `"null"`, `"none"`, `"nan"`).
  - Candidate placement: new `src/string_utils.py` (keep it dependency-free) OR add a small helper to `src/route_utils.py`
    if scope stays strictly about route-ish identifiers.
  - Start with the highest-impact call sites (UI dropdown sentinels like
    `"None - treat as single route"`, results-loading paths, and route filtering).
  - Validation: add/extend unit tests first; run full `pytest -q`.

## How We’ll Validate
- Run `pytest -q` after each step.
- For any refactor touching routing, run `pytest -q tests/test_route_id_normalization.py`.

## Open Questions
- Should route IDs treat leading zeros as significant everywhere (default: yes, keep as strings)?
- Should we treat additional missing markers as empty (e.g., `"<NA>"`)?
