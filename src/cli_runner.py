"""Headless runner for Highway Segmentation analyses.

This module is intentionally GUI-free. It is the shared execution core used by:
- the future CLI entrypoint (run-spec file)
- the GUI "Copy command line for this analysis" feature (export spec)

Primary API:
- run_analysis_from_spec_file(spec_path, ...)

The run spec format is defined by:
- src/highway_segmentation_run_spec_schema.json
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

import pandas as pd
import jsonschema

from config import OptionalNumericParameter, get_optimization_method, resolve_method_class
from data_loader import RouteAnalysis, analyze_route_gaps, filter_data_by_route
from extensible_results_manager import ExtensibleJsonResultsManager
from route_utils import INTERNAL_ROUTE_IDS_TO_SKIP_LOWER, normalize_route_id
from value_parsing import coerce_none_like

if TYPE_CHECKING:
    from analysis.base import AnalysisResult


LogCallback = Callable[[str], None]


def _coerce_numeric(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list) and value and isinstance(value[0], (int, float)):
        return float(value[0])
    return float(default)


def _normalize_analysis_result_for_json_parity(result: AnalysisResult, *, method_params: Dict[str, Any]) -> None:
    """Adjust a method-returned AnalysisResult to match the GUI JSON structure.

    The GUI save pipeline rebuilds `AnalysisResult.all_solutions` from legacy controller
    outputs (chromosome/fitness/segments) and injects a baseline set of GA stats into
    `optimization_stats` (even for deterministic methods). The CLI should mirror that
    so CLI+GUI JSON shapes match for structural parity testing.
    """

    # Ensure results writer computes segmentation + segment_details from chromosome.
    for solution in (result.all_solutions or []):
        if isinstance(solution, dict) and "chromosome" in solution:
            solution.pop("segmentation", None)

    # Mirror the GUI save pipeline behavior: if the method didn't provide any
    # optimization_stats (or provided an empty dict), inject a small baseline set
    # so plugins emit consistent sections (e.g., AASHTO CDA).
    if not isinstance(result.optimization_stats, dict) or not result.optimization_stats:
        best_solution = result.best_solution or {}
        result.optimization_stats = {
            "best_fitness": _coerce_numeric(
                best_solution.get("deviation_fitness", best_solution.get("fitness", 0.0))
            ),
            "generations_run": 0,
            "population_size": 0,
            "final_generation": 0,
        }


class RunSpecError(ValueError):
    """Raised when a run spec is invalid or cannot be executed."""


@dataclass(frozen=True)
class ResolvedRunSpec:
    """Normalized, execution-ready run spec."""

    spec_path: Path
    spec_version: str

    data_file_path: Path
    x_column: str
    y_column: str
    gap_threshold: float
    route_column: Optional[str]
    selected_routes: Optional[List[str]]
    must_break_columns: Optional[List[str]]

    method_key: str
    method_parameters: Dict[str, Any]

    output_json_path: Path
    overwrite: bool


def _default_logger(msg: str) -> None:
    print(msg)


def _load_json(path: Path) -> Dict[str, Any]:
    # Be permissive about UTF-8 BOM.
    # PowerShell's Set-Content -Encoding UTF8 and some editors may include a BOM,
    # which breaks strict 'utf-8' decoding for JSON.
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolve_path(base_dir: Path, p: str) -> Path:
    # Treat empty as error at the caller.
    candidate = Path(p)
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate


def validate_run_spec(instance: Dict[str, Any], schema_path: Optional[Path] = None) -> None:
    """Validate a run spec dict against the JSON schema.

    Raises:
        RunSpecError: when validation fails.
    """
    if schema_path is None:
        schema_path = Path(__file__).resolve().parent / "highway_segmentation_run_spec_schema.json"

    schema = _load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.json_path)
    if errors:
        msg = "\n".join([f"{e.json_path}: {e.message}" for e in errors])
        raise RunSpecError(f"Run spec failed schema validation:\n{msg}")


def load_and_resolve_run_spec(spec_path: str | os.PathLike[str], *, validate: bool = True) -> ResolvedRunSpec:
    """Load a run spec JSON file and normalize/resolve paths.

    Path resolution policy:
    - relative paths are resolved relative to the spec file's directory.
    """
    spec_path = Path(spec_path).expanduser().resolve()
    instance = _load_json(spec_path)

    if validate:
        validate_run_spec(instance)

    base_dir = spec_path.parent

    spec_version = str(instance["spec_version"])

    input_block = instance["input"]
    method_block = instance["method"]
    output_block = instance["output"]

    data_file_path = _resolve_path(base_dir, str(input_block["data_file_path"]))
    x_column = str(input_block["x_column"]).strip()
    y_column = str(input_block["y_column"]).strip()
    gap_threshold = float(input_block["gap_threshold"])

    route_column_raw = input_block.get("route_column", None)
    route_column = None
    if route_column_raw is not None:
        route_column = str(route_column_raw).strip() or None

    selected_routes_raw = input_block.get("selected_routes", None)
    selected_routes: Optional[List[str]]
    if selected_routes_raw is None:
        selected_routes = None
    else:
        if not isinstance(selected_routes_raw, list):
            raise RunSpecError("input.selected_routes must be an array of strings or null")
        selected_routes = [str(r).strip() for r in selected_routes_raw if str(r).strip()]

    must_break_raw = input_block.get("must_break_columns", None)
    must_break_columns: Optional[List[str]]
    if must_break_raw is None:
        must_break_columns = None
    else:
        if not isinstance(must_break_raw, list):
            raise RunSpecError("input.must_break_columns must be an array of strings or null")
        must_break_columns = [str(c).strip() for c in must_break_raw if str(c).strip()]

    method_key = str(method_block["method_key"]).strip()
    method_parameters = method_block.get("method_parameters") or {}
    if not isinstance(method_parameters, dict):
        raise RunSpecError("method.method_parameters must be an object")

    output_json_path = _resolve_path(base_dir, str(output_block["output_json_path"]))
    overwrite = bool(output_block.get("overwrite", False))

    return ResolvedRunSpec(
        spec_path=spec_path,
        spec_version=spec_version,
        data_file_path=data_file_path,
        x_column=x_column,
        y_column=y_column,
        gap_threshold=gap_threshold,
        route_column=route_column,
        selected_routes=selected_routes,
        must_break_columns=must_break_columns,
        method_key=method_key,
        method_parameters=method_parameters,
        output_json_path=output_json_path,
        overwrite=overwrite,
    )


def _read_tabular_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, dtype=str)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, dtype=str)
    raise RunSpecError(f"Unsupported input file type: {path.suffix}")


def _convert_columns_for_analysis(df: pd.DataFrame, *, x_column: str, y_column: str, route_column: Optional[str]) -> pd.DataFrame:
    """Mimic the GUI load behavior: read strings, then coerce numeric safely."""

    if x_column not in df.columns:
        raise RunSpecError(f"X column {x_column!r} not found in input file")
    if y_column not in df.columns:
        raise RunSpecError(f"Y column {y_column!r} not found in input file")

    # Normalize route column to string (categorical) if present.
    if route_column and route_column in df.columns:
        try:
            df[route_column] = df[route_column].astype("string").str.strip()
        except Exception as e:
            raise RunSpecError(f"Could not normalize route column {route_column!r} to string: {e}") from e

    def _has_leading_zero_integers(series: pd.Series) -> bool:
        try:
            s = series.astype("string")
            s = s.dropna().str.strip()
            if s.empty:
                return False
            return bool(s.str.match(r"^0\d+$").any())
        except Exception:
            return False

    def _safe_to_numeric(series: pd.Series) -> pd.Series:
        numeric = pd.to_numeric(series, errors="coerce")
        invalid_mask = series.notna() & numeric.isna()
        if invalid_mask.any():
            return series
        return numeric

    # Convert X/Y to numeric; for other columns, attempt safe numeric conversion.
    for col in list(df.columns):
        if route_column and col == route_column:
            continue
        if col == x_column or col == y_column:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            continue
        if _has_leading_zero_integers(df[col]):
            continue
        df[col] = _safe_to_numeric(df[col])

    # Validate that X/Y have numeric values
    if pd.to_numeric(df[x_column], errors="coerce").isna().any():
        bad = df.loc[pd.to_numeric(df[x_column], errors="coerce").isna(), x_column].iloc[0]
        raise RunSpecError(f"X column {x_column!r} contains non-numeric values (example: {bad!r})")

    if pd.to_numeric(df[y_column], errors="coerce").isna().any():
        bad = df.loc[pd.to_numeric(df[y_column], errors="coerce").isna(), y_column].iloc[0]
        raise RunSpecError(f"Y column {y_column!r} contains non-numeric values (example: {bad!r})")

    # Drop rows where X/Y are missing
    required_cols = [x_column, y_column]
    if route_column and route_column in df.columns:
        required_cols.append(route_column)

    return df.dropna(subset=required_cols)


def _determine_routes(
    df: pd.DataFrame,
    *,
    route_column: Optional[str],
    selected_routes: Optional[List[str]],
    input_file_stem: str,
    log: LogCallback,
) -> Tuple[Optional[str], List[str], List[str]]:
    """Return (actual_route_column, all_routes, routes_to_process)."""

    if route_column and route_column in df.columns:
        actual_route_column = route_column

        normalized_series = df[actual_route_column].apply(normalize_route_id)
        invalid_mask = normalized_series.isna()
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            log(
                f"Route column {actual_route_column!r} contains {invalid_count} record(s) with missing route IDs; excluding them."
            )
        if invalid_count == len(df):
            raise RunSpecError(
                f"All records in route column {actual_route_column!r} are missing route IDs."
            )
        if invalid_count:
            df.drop(df.index[invalid_mask], inplace=True)
            df[actual_route_column] = normalized_series.loc[~invalid_mask].astype("string")

        unique_routes = df[actual_route_column].unique()
        normalized_routes = []
        for route in unique_routes:
            route_str = normalize_route_id(route)
            if route_str is None:
                continue
            if route_str.lower() in INTERNAL_ROUTE_IDS_TO_SKIP_LOWER:
                continue
            normalized_routes.append(route_str)
        all_routes = sorted(set(normalized_routes))

        if selected_routes is None:
            routes_to_process = all_routes
        else:
            if len(selected_routes) == 0:
                raise RunSpecError("No routes selected (selected_routes is an empty list)")
            normalized_selected = [r for r in (normalize_route_id(r) for r in selected_routes) if r is not None]
            routes_to_process = [r for r in normalized_selected if r in all_routes]

        if not routes_to_process:
            raise RunSpecError("No selected routes matched the data")

        return actual_route_column, all_routes, routes_to_process

    # Single-route mode
    actual_route_column = None
    all_routes = [input_file_stem]
    routes_to_process = all_routes
    return actual_route_column, all_routes, routes_to_process


def _merge_method_defaults(method_key: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
    cfg = get_optimization_method(method_key)
    defaults = {p.name: p.default_value for p in (cfg.parameters or [])}

    merged = dict(defaults)
    merged.update(overrides or {})

    # Coerce optional numeric none-like values to None
    for p in (cfg.parameters or []):
        if isinstance(p, OptionalNumericParameter):
            merged[p.name] = coerce_none_like(merged.get(p.name))

    # Defensive: gap_threshold belongs to the framework input section.
    merged.pop("gap_threshold", None)

    return merged


def _validate_method_parameters(method_key: str, params: Dict[str, Any]) -> None:
    cfg = get_optimization_method(method_key)
    errors: List[str] = []

    for param_def in (cfg.parameters or []):
        if param_def.name not in params:
            if getattr(param_def, "required", True):
                errors.append(f"Missing required parameter: {param_def.display_name}")
            continue

        ok, msg = param_def.validate_value(params.get(param_def.name))
        if not ok and msg:
            errors.append(msg)

    if errors:
        raise RunSpecError("Method parameter validation failed:\n" + "\n".join([f"- {e}" for e in errors]))


def run_analysis_from_spec_file(
    spec_path: str | os.PathLike[str],
    *,
    validate_spec: bool = True,
    log_callback: Optional[LogCallback] = None,
) -> str:
    """Execute an analysis run defined by a run-spec JSON file.

    Loads and validates the spec, reads input data, runs the specified analysis
    method across all selected routes, and writes consolidated JSON results.

    Args:
        spec_path: Path to the run-spec JSON file.
        validate_spec: When True, validate the spec against the JSON schema before
            loading. Set to False only when the caller has already validated.
        log_callback: Optional callable that receives log messages; defaults to
            printing to stdout.

    Returns:
        Absolute path to the written results JSON file.

    Raises:
        RunSpecError: If the spec is invalid, input data is missing or malformed,
            no routes could be analyzed, or the output file exists and overwrite is False.
    """
    log = log_callback or _default_logger
    spec = load_and_resolve_run_spec(spec_path, validate=validate_spec)

    log(f"Loading input file: {spec.data_file_path}")
    if not spec.data_file_path.exists():
        raise RunSpecError(f"Input file does not exist: {spec.data_file_path}")

    raw_df = _read_tabular_file(spec.data_file_path)
    df = _convert_columns_for_analysis(raw_df, x_column=spec.x_column, y_column=spec.y_column, route_column=spec.route_column)

    input_file_stem = spec.data_file_path.stem

    # Mirror GUI behavior: in single-route mode, the GUI load pipeline creates a synthetic
    # route column in-memory (typically named "route"). This affects metadata like
    # input_file_info.column_info.total_columns.
    if spec.route_column is None and "route" not in df.columns:
        df["route"] = input_file_stem

    actual_route_column, all_routes, routes_to_process = _determine_routes(
        df,
        route_column=spec.route_column,
        selected_routes=spec.selected_routes,
        input_file_stem=input_file_stem,
        log=log,
    )

    log(f"Method: {spec.method_key} | Routes: {len(routes_to_process)}")

    method_params = _merge_method_defaults(spec.method_key, spec.method_parameters)
    # Mirror GUI parameter payload shape: the GUI passes a dict that includes
    # the selected method key under "optimization_method".
    method_params.setdefault("optimization_method", spec.method_key)
    _validate_method_parameters(spec.method_key, method_params)

    prepared: List[Tuple[str, RouteAnalysis]] = []
    original_data_by_route: Dict[str, pd.DataFrame] = {}

    for route_id in routes_to_process:
        if actual_route_column:
            route_df = filter_data_by_route(df, actual_route_column, route_id)
        else:
            route_df = df.copy()

        if len(route_df) < 3:
            log(f"Skipping route {route_id!r}: insufficient data ({len(route_df)} points)")
            continue

        route_df = route_df.sort_values(spec.x_column).reset_index(drop=True)

        route_analysis = analyze_route_gaps(
            route_df,
            spec.x_column,
            spec.y_column,
            route_id=route_id,
            gap_threshold=spec.gap_threshold,
            must_break_columns=spec.must_break_columns,
        )
        prepared.append((route_id, route_analysis))
        original_data_by_route[route_id] = route_analysis.route_data.copy()

    if not prepared:
        raise RunSpecError("No routes could be analyzed successfully")

    cls = resolve_method_class(spec.method_key)
    method_instance = cls()

    results = []
    for route_id, route_analysis in prepared:
        log(f"Running route {route_id!r} ({len(route_analysis.route_data)} points)...")

        analysis_kwargs = dict(method_params)
        analysis_kwargs["log_callback"] = log
        analysis_kwargs["stop_callback"] = lambda: False
        analysis_kwargs["input_parameters"] = dict(method_params)

        res = method_instance.run_analysis(
            route_analysis,
            route_id,
            spec.x_column,
            spec.y_column,
            float(spec.gap_threshold),
            **analysis_kwargs,
        )

        _normalize_analysis_result_for_json_parity(res, method_params=method_params)
        results.append(res)

    out_path = spec.output_json_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and not spec.overwrite:
        raise RunSpecError(f"Output file already exists and overwrite=false: {out_path}")

    input_file_info = {
        "data_file_path": str(spec.data_file_path),
        "data_file_name": spec.data_file_path.name,
        "data_file_size_bytes": spec.data_file_path.stat().st_size if spec.data_file_path.exists() else None,
        "total_data_rows": int(len(df)),
        "total_routes_available": int(len(all_routes)) if actual_route_column else 1,
        "column_info": {
            "total_columns": int(len(df.columns)),
            "x_column": spec.x_column,
            "y_column": spec.y_column,
            "route_column": actual_route_column,
        },
    }

    route_processing_info = {
        "route_mode": "multi_route" if len(results) > 1 else "single_route",
        "selected_routes": [r.route_id for r in results],
        "x_column": spec.x_column,
        "y_column": spec.y_column,
        "route_column": actual_route_column,
        # Match the GUI's semantics: treat multi-route execution as "route filtering applied".
        "route_filtering_applied": len(results) > 1,
        "total_routes_in_source": int(len(all_routes)) if actual_route_column else 1,
        "total_routes_processed": int(len(results)),
        # Mirror GUI shape: include custom_save_name (nullable).
        # The CLI already has output_json_path; unless the run spec explicitly
        # carries a custom name concept, keep this null for structural parity.
        "custom_save_name": None,
    }

    # Structural parity: the GUI omits must_break_columns when not set.
    if spec.must_break_columns is not None:
        route_processing_info["must_break_columns"] = spec.must_break_columns

    manager = ExtensibleJsonResultsManager()
    json_output_path = manager.save_analysis_results(
        results,
        str(out_path),
        input_file_info=input_file_info,
        route_processing_info=route_processing_info,
        original_data_by_route=original_data_by_route,
    )

    log(f"Wrote results JSON: {json_output_path}")
    return json_output_path
