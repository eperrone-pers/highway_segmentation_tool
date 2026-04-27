# UI Refactor Plan — Fixed Required Controls + Scrollable Dynamic Parameter Grid

Branch: `ui/dynamic-params-grid`

## Objective
Refactor the left pane so:

- **Top (non-scrollable)**: required controls (file operations, method selection/description, etc.) remain visible.
- **Bottom (scrollable)**: method-specific dynamic parameters are displayed in a **native-scrollable grid** (Treeview) and edited via a simple editor panel.

Primary motivation: improve cross-platform scroll behavior (macOS trackpad) and reduce event-binding complexity.

## Non-goals
- No changes to optimization algorithms.
- No new analysis methods.
- No new “extra” UI pages or flows.

## Relevant Current Code Touchpoints
- UI construction:
  - `src/gui_main.py` → `HighwaySegmentationGUI._create_interface()`
  - `src/ui_builder.py` → `UIBuilder.create_scrollable_left_pane()` and method/dynamic parameter UI
- Method change:
  - `src/gui_main.py` → `HighwaySegmentationGUI.on_method_change()`
  - `src/parameter_manager.py` → `ParameterManager.on_method_change()`
- Parameter collection/validation used by runtime:
  - `src/ui_builder.py` → `get_parameter_values()`, `validate_parameter_values()`
  - `src/parameter_manager.py` → `get_optimization_parameters()`, `validate_parameters()`
  - `src/optimization_controller.py` → `start_optimization()`
- Parameter save/load:
  - `src/file_manager.py` → reads `ui_builder.get_parameter_values()`

## Decisions (Lock These Early)
- Error UX for invalid dynamic input: **messagebox** (initially).
- Optional numeric display: show `none_text` (e.g., `(None)`) for `OptionalNumericParameter`.
- Editing model: **editor panel below grid** (not in-cell editing) for simplicity and robustness.

## Milestones (Match Todo List)

### 1) Split left pane layout
**Goal**: left pane becomes two vertical sections.

**Implementation sketch**
- Replace the current “everything is inside one scrollable frame” approach.
- Create a left pane container with:
  - `required_frame` (top)
  - `dynamic_frame` (bottom)

**Done when**
- Required controls render as before.
- Dynamic section placeholder exists below.
- Right pane is unaffected.

**Status**: DONE

---

### 2) Add Treeview params grid (read-only)
**Goal**: dynamic area shows a native-scrollable grid of parameters.

**Implementation sketch**
- Add a Treeview with columns: `Parameter`, `Value`.
- Populate from `config.get_optimization_method(method_key).parameters`.
- On method change: clear + repopulate rows.

**Done when**
- Switching method updates grid rows.
- Scrolling the grid works on macOS/Windows.

**Status**: DONE

---

### 3) Implement editor panel below grid
**Goal**: edit values directly in the grid (inline).

**Implementation sketch**
- Double-click the **Value** cell to edit in-place.
- Editor widget type chosen by parameter definition:
  - `NumericParameter`, `OptionalNumericParameter`, `TextParameter` → inline Entry
  - `SelectParameter` → inline Combobox
  - `BoolParameter` → toggle on double-click
- Validation uses `param_def.validate_value()` before persisting.

**Done when**
- Commit updates the displayed value in the grid.
- Invalid values are blocked with a clear error.

**Status**: DONE

---

### 4) Persist per-method parameter values
**Goal**: edits are saved per method and restored on method switch.

**Implementation sketch**
- Use existing settings storage:
  - `settings['optimization']['dynamic_parameters_by_method'][method_key]`
- Grid + editor read/write only through that store.

**Done when**
- Switching methods back/forth preserves edits.

**Status**: DONE

---

### 5) Wire validation + start optimization flow
**Goal**: optimization runs with the new values and validation works.

**Implementation sketch**
- Ensure `ui_builder.get_parameter_values()` returns the store-backed method params.
- Ensure `validate_parameters()` validates store-backed values.
- Confirm `OptimizationController.start_optimization()` still blocks on validation failure.

**Done when**
- Start optimization uses edited values.
- Invalid values prevent start.

**Status**: DONE

**Verification**
- Unit/controller smoke: `tests/test_simple_controller.py`, `tests/test_controller_all_methods.py` ✅
- Integration workflows: `tests/integration/test_phase1_complete_workflow.py`, `tests/integration/test_json_validation_workflow.py` ✅
- Regression outputs schema validation: `tests/regression/validate_regression_outputs.py` ✅ (8/8 JSON files valid)

---

### 6) Minimal UX polish
**Candidate items (keep minimal)**
- “Reset all parameters for this method to defaults” button.
- Better formatting of displayed values (e.g., numeric decimal places).

**Done when**
- UX is usable without surprises.

**Status**: PARTIAL

---

### 7) Manual cross-platform smoke test
**Checklist**
- Windows: grid scroll works; method combobox doesn’t change on wheel when pointer is in grid.
- macOS: trackpad scroll works both directions in the grid.
- Method switching retains per-method edits.
- Save/load parameters still works.

## Notes
- Treeview is chosen specifically because it handles scrolling natively and avoids fighting ttk widget wheel behaviors on macOS.

## Follow-ups
- Slim default settings to avoid reintroducing legacy “global GA params” into `app_settings.json` for new installs.
- Optional: add a small automated GUI-free save/load roundtrip test for the new parameter JSON shape (keep legacy load compatibility).
