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

import datetime as _dt
import json
import logging
import os
from collections import Counter
from dataclasses import dataclass, replace as _dc_replace
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

import pandas as pd
import jsonschema

from config import OptionalNumericParameter, get_optimization_method, resolve_method_class, PreprocessingRunConfig, get_preprocessing_method
from data_loader import RouteAnalysis, analyze_route_gaps, process_route_with_preprocessing
from data_sources.base import DataSourceConfig
from extensible_results_manager import ExtensibleJsonResultsManager
from route_utils import filter_data_by_route, list_routes, normalize_route_id
from value_parsing import coerce_none_like

if TYPE_CHECKING:
    from analysis.base import AnalysisResult

_logger = logging.getLogger(__name__)

LogCallback = Callable[[str], None]


def _coerce_numeric(value: Any, default: float = 0.0) -> float:
    """Convert a JSON-serialized numeric value to float, unwrapping single-element lists.

    Some analysis methods return numeric fields as ``[1.23]`` rather than ``1.23``
    (a serialization artifact). This function handles both forms transparently.

    Args:
        value: The raw value from an AnalysisResult field — may be int, float, or a
            single-element list of int/float.
        default: Value to return when ``value`` is None, empty, or an unsupported type.

    Returns:
        The numeric value as a float, or ``default`` if conversion is not possible.
    """
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


class BatchPartialFailureError(RunSpecError):
    """Raised when a batch run completes but one or more input files failed."""


@dataclass(frozen=True)
class ResolvedRunSpec:
    """Normalized, execution-ready run spec produced by ``load_and_resolve_run_spec``.

    All paths are absolute. All string fields are stripped. Optional fields that
    were absent or null in the JSON are represented as ``None``.

    Attributes:
        spec_path: Absolute path to the run-spec JSON file (used as the path
            resolution root for relative paths inside the spec).
        spec_version: Version string from the spec (e.g., ``"1.0"``).
        data_file_path: Absolute path to the input CSV or Excel file. ``None``
            when ``data_source_config`` is set (the two are mutually exclusive).
        x_column: Column name for the x-axis values (distance / station).
        y_column: Column name for the y-axis values (pavement metric).
        gap_threshold: Minimum distance gap (in the x-axis unit, typically miles)
            that triggers a forced segment break between consecutive data points.
        route_column: Column name that identifies individual routes. ``None``
            means the file is treated as a single route.
        selected_routes: Subset of route IDs to process. ``None`` means all routes
            found in ``route_column`` are processed.
        must_break_columns: Column names whose value changes force a mandatory
            breakpoint regardless of the GA solution (e.g., district or jurisdiction
            boundaries). ``None`` means no forced attribute breaks.
        method_key: Analysis method identifier
            (e.g., ``"single"``, ``"multi"``, ``"aashto_cda"``).
        method_parameters: Method-specific parameters, merged with per-method
            defaults so every parameter has a value.
        preprocessing_config: Optional preprocessing configuration. ``None`` means
            no preprocessing is applied.
        output_json_path: Absolute path where the results JSON file will be written.
        overwrite: When ``True``, overwrite an existing output file. When ``False``,
            ``run_analysis_from_spec_file`` raises ``RunSpecError`` if the file exists.
        data_source_config: Database connection parameters when the run spec uses
            a ``data_source`` block instead of ``data_file_path``. ``None`` for
            file-based inputs. Password is read at runtime from the
            ``HST_DB_PASSWORD`` environment variable — never stored in the spec.
    """

    spec_path: Path
    spec_version: str

    data_file_path: Optional[Path]
    x_column: str
    y_column: str
    gap_threshold: float
    route_column: Optional[str]
    selected_routes: Optional[List[str]]
    must_break_columns: Optional[List[str]]
    secondary_break_columns: Optional[List[str]]

    method_key: str
    method_parameters: Dict[str, Any]

    preprocessing_config: Optional[PreprocessingRunConfig]

    output_json_path: Path
    overwrite: bool

    data_source_config: Optional[DataSourceConfig] = None


def _now_utc() -> str:
    """Return the current UTC time as an ISO-8601 string with Z suffix."""
    return (
        _dt.datetime.now(tz=_dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _default_logger(msg: str) -> None:
    """Fallback log handler used when no ``log_callback`` is provided."""
    print(msg)


def _load_json(path: Path) -> Dict[str, Any]:
    """Read and parse a JSON file, returning its contents as a dict.

    Uses ``utf-8-sig`` encoding to silently strip a UTF-8 BOM if present.
    PowerShell's ``Set-Content -Encoding UTF8`` and some editors emit a BOM
    that breaks the standard ``utf-8`` codec when passed to ``json.loads``.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        json.JSONDecodeError: If the file content is not valid JSON.
    """
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolve_path(base_dir: Path, p: str) -> Path:
    """Resolve a path string to an absolute Path, relative to ``base_dir``.

    Absolute paths in ``p`` are returned unchanged. Relative paths are joined
    onto ``base_dir`` (typically the directory containing the run-spec file).
    Empty strings should be caught by schema validation before reaching here.
    """
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

    data_file_path: Optional[Path] = None
    data_source_config: Optional[DataSourceConfig] = None

    if "data_source" in input_block:
        ds_block = input_block["data_source"]
        try:
            data_source_config = DataSourceConfig(
                source_type="database",
                driver_key=str(ds_block["driver"]).strip(),
                table_or_view=str(ds_block["table_or_view"]).strip(),
                host=str(ds_block["host"]).strip() if ds_block.get("host") else None,
                port=int(ds_block["port"]) if ds_block.get("port") is not None else None,
                database=str(ds_block["database"]).strip() if ds_block.get("database") else None,
                schema=str(ds_block["schema"]).strip() if ds_block.get("schema") else None,
                username=str(ds_block["username"]).strip() if ds_block.get("username") else None,
                connection_name=str(ds_block["connection_name"]).strip() if ds_block.get("connection_name") else None,
            )
        except KeyError as exc:
            raise RunSpecError(f"input.data_source is missing required field: {exc}") from exc
    elif "data_file_path" in input_block:
        data_file_path = _resolve_path(base_dir, str(input_block["data_file_path"]))
    else:
        raise RunSpecError("input block must contain either 'data_file_path' or 'data_source'")

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

    secondary_break_raw = input_block.get("secondary_break_columns", None)
    secondary_break_columns: Optional[List[str]]
    if secondary_break_raw is None:
        secondary_break_columns = None
    else:
        if not isinstance(secondary_break_raw, list):
            raise RunSpecError("input.secondary_break_columns must be an array of strings or null")
        secondary_break_columns = [str(c).strip() for c in secondary_break_raw if str(c).strip()]

    method_key = str(method_block["method_key"]).strip()
    method_parameters = method_block.get("method_parameters") or {}
    if not isinstance(method_parameters, dict):
        raise RunSpecError("method.method_parameters must be an object")

    # Parse preprocessing configuration (optional section)
    preprocessing_block = instance.get("preprocessing", None)
    preprocessing_config: Optional[PreprocessingRunConfig]
    if preprocessing_block is None or not isinstance(preprocessing_block, dict):
        preprocessing_config = None
    else:
        enabled = bool(preprocessing_block.get("enabled", True))
        if not enabled:
            preprocessing_config = None
        else:
            # Extract preprocessing methods and parameters
            pre_gap_method = preprocessing_block.get("pre_gap_method", None)
            if pre_gap_method is not None:
                pre_gap_method = str(pre_gap_method).strip() or None
            
            primary_method = preprocessing_block.get("primary_method", None)
            if primary_method is not None:
                primary_method = str(primary_method).strip() or None
            
            secondary_method = preprocessing_block.get("secondary_method", None)
            if secondary_method is not None:
                secondary_method = str(secondary_method).strip() or None
            
            pre_gap_params = preprocessing_block.get("pre_gap_parameters", {})
            if not isinstance(pre_gap_params, dict):
                raise RunSpecError("preprocessing.pre_gap_parameters must be an object")
            
            primary_params = preprocessing_block.get("primary_parameters", {})
            if not isinstance(primary_params, dict):
                raise RunSpecError("preprocessing.primary_parameters must be an object")
            
            secondary_params = preprocessing_block.get("secondary_parameters", {})
            if not isinstance(secondary_params, dict):
                raise RunSpecError("preprocessing.secondary_parameters must be an object")
            
            # Validate each method is permitted in the stage it is assigned to
            for pp_method_key, stage_name in (
                (pre_gap_method, "pre_gap"),
                (primary_method, "primary"),
                (secondary_method, "secondary"),
            ):
                if pp_method_key is None:
                    continue
                method_cfg = get_preprocessing_method(pp_method_key)
                if method_cfg.allowed_stages is not None and stage_name not in method_cfg.allowed_stages:
                    allowed = ", ".join(f'"{s}"' for s in method_cfg.allowed_stages)
                    raise RunSpecError(
                        f"Preprocessing method '{pp_method_key}' cannot be used in the '{stage_name}' slot "
                        f"(allowed stages: {allowed})."
                    )

            # Create PreprocessingRunConfig if any method is specified
            if pre_gap_method or primary_method or secondary_method:
                preprocessing_config = PreprocessingRunConfig(
                    pre_gap_method=pre_gap_method,
                    pre_gap_parameters=pre_gap_params,
                    primary_method=primary_method,
                    primary_parameters=primary_params,
                    secondary_method=secondary_method,
                    secondary_parameters=secondary_params,
                    enabled=True
                )
            else:
                preprocessing_config = None

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
        secondary_break_columns=secondary_break_columns,
        method_key=method_key,
        method_parameters=method_parameters,
        preprocessing_config=preprocessing_config,
        output_json_path=output_json_path,
        overwrite=overwrite,
        data_source_config=data_source_config,
    )


def _read_tabular_file(path: Path) -> pd.DataFrame:
    """Read a CSV or Excel file into a DataFrame with all columns as strings.

    Reading as ``dtype=str`` defers numeric type inference to
    ``_convert_columns_for_analysis``, which mirrors the GUI load pipeline and
    avoids pandas silently dropping leading zeros or misinterpreting mixed types.

    Args:
        path: Path to the input file. Supported extensions: ``.csv``,
            ``.xlsx``, ``.xls``.

    Returns:
        DataFrame with every column as object (string) dtype.

    Raises:
        RunSpecError: If the file extension is not supported.
    """
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, dtype=str)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, dtype=str)
    raise RunSpecError(f"Unsupported input file type: {path.suffix}")


def _convert_columns_for_analysis(df: pd.DataFrame, *, x_column: str, y_column: str, route_column: Optional[str]) -> pd.DataFrame:
    """Coerce DataFrame columns from string dtype to appropriate types for analysis.

    Mirrors the GUI data-load pipeline so the CLI produces identical input to
    the analysis methods. Key behaviors:

    - ``x_column`` is coerced to numeric; rows where it is non-numeric or missing raise
      ``RunSpecError`` (wrong column choice is always fatal).
    - ``y_column`` is coerced to numeric; rows with non-numeric or missing Y values are
      left in the DataFrame as ``NaN`` with a warning logged. Configure the
      ``invalid_data_handler`` pre-gap preprocessing method to clean these before analysis.
    - ``route_column`` (when present) is normalized to stripped strings.
    - All other columns undergo safe numeric coercion: if every non-null value
      can be parsed as a number, the column becomes numeric. Columns that contain
      any leading-zero integers (e.g., zip codes, padded section IDs) are left as
      strings to avoid silently dropping the leading zero.

    Args:
        df: Input DataFrame with all columns as string dtype (from ``_read_tabular_file``).
        x_column: Name of the distance/station column.
        y_column: Name of the pavement-metric column.
        route_column: Name of the route-ID column, or ``None`` for single-route files.

    Returns:
        DataFrame with x/y as numeric, route column as string, and other columns
        coerced where safe. Rows with missing x, y, or route values are dropped.

    Raises:
        RunSpecError: If ``x_column`` or ``y_column`` is absent from the DataFrame,
            or if either contains non-numeric values after coercion.
    """

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

    # Validate X column — non-numeric X is always fatal (wrong column choice).
    if pd.to_numeric(df[x_column], errors="coerce").isna().any():
        bad = df.loc[pd.to_numeric(df[x_column], errors="coerce").isna(), x_column].iloc[0]
        raise RunSpecError(f"X column {x_column!r} contains non-numeric values (example: {bad!r})")

    # Warn on non-numeric Y — NaN-Y rows pass through for the Invalid Data Handler to clean.
    nan_y_mask = pd.to_numeric(df[y_column], errors="coerce").isna()
    if nan_y_mask.any():
        n = int(nan_y_mask.sum())
        _logger.warning(
            "Y column %r has %d row%s with missing or non-numeric values. "
            "Configure 'invalid_data_handler' in pre_gap_method to handle these before analysis.",
            y_column, n, "s" if n != 1 else "",
        )

    # Drop rows where X or route column are missing; leave NaN-Y rows for preprocessing.
    required_cols = [x_column]
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

        all_routes = list_routes(df, actual_route_column)

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
    """Build a complete parameter dict by merging spec overrides on top of method defaults.

    Starts from the declared default value for every parameter in the method's
    config, then applies ``overrides`` from the run spec. After merging:

    - ``OptionalNumericParameter`` values that are none-like (empty string, ``"None"``,
      etc.) are normalized to ``None`` so method code can test with ``is None``.
    - ``gap_threshold`` is removed — it belongs to the framework input section and
      must not be passed as a method parameter.

    Args:
        method_key: Analysis method identifier (e.g., ``"single"``).
        overrides: Parameter values from the run spec's ``method.method_parameters``
            block. Missing keys fall back to the method's declared defaults.

    Returns:
        Dict mapping every parameter name to its resolved value.

    Raises:
        KeyError / AttributeError: If ``method_key`` is not registered in config.
    """
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
    """Validate a fully-merged parameter dict against the method's declared constraints.

    Iterates every ``ParameterDefinition`` in the method's config and calls its
    ``validate_value()`` method. All validation errors are collected before raising
    so the caller sees the complete list of problems in a single exception.

    Args:
        method_key: Analysis method identifier (e.g., ``"single_objective"``).
        params: Merged parameter dict from ``_merge_method_defaults``.

    Raises:
        RunSpecError: If any required parameter is missing or any value fails
            its ``ParameterDefinition.validate_value()`` check.
    """
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


def _run_analysis_from_resolved_spec(
    spec: ResolvedRunSpec,
    *,
    log_callback: Optional[LogCallback] = None,
) -> str:
    """Shared execution core for single-file and batch runs.

    Callers load and resolve the spec (and may substitute fields via
    ``_dc_replace``), then pass the ready ``ResolvedRunSpec`` here.
    Returns the absolute path to the written results JSON file.
    """
    log = log_callback or _default_logger

    if spec.data_source_config is not None:
        from data_sources.database_source import DatabaseDataSource
        from data_sources.base import DataSourceError
        _ds_label = f"{spec.data_source_config.driver_key}/{spec.data_source_config.table_or_view}"
        log(f"Connecting to database: {_ds_label}")
        try:
            _active_source = DatabaseDataSource(spec.data_source_config)
            _row_count = _active_source.get_row_count()
            if _row_count > 0:
                from app_constants import ValidationConfig
                _threshold = ValidationConfig().large_table_row_threshold
                if _row_count > _threshold:
                    log(
                        f"WARNING: Table '{spec.data_source_config.table_or_view}' "
                        f"contains {_row_count:,} rows — load may be slow. "
                        f"Consider pre-filtering via a database view."
                    )
            raw_df = _active_source.load_data(
                x_col=spec.x_column,
                y_col=spec.y_column,
                route_col=spec.route_column,
                selected_routes=spec.selected_routes,
            )
        except DataSourceError as exc:
            raise RunSpecError(f"Database load failed: {exc}") from exc
        input_file_stem = spec.data_source_config.table_or_view or "database_source"
    else:
        log(f"Loading input file: {spec.data_file_path}")
        if not spec.data_file_path.exists():
            raise RunSpecError(f"Input file does not exist: {spec.data_file_path}")
        raw_df = _read_tabular_file(spec.data_file_path)
        from data_sources.file_source import FileDataSource
        from data_sources.base import DataSourceConfig as _DSConfig
        _active_source = FileDataSource(_DSConfig(source_type="file", file_path=str(spec.data_file_path)))
        input_file_stem = spec.data_file_path.stem

    df = _convert_columns_for_analysis(
        raw_df, x_column=spec.x_column, y_column=spec.y_column, route_column=spec.route_column
    )

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
    preprocessing_results_by_route: Dict[str, List] = {}  # Store preprocessing results

    for route_id in routes_to_process:
        if actual_route_column:
            route_df = filter_data_by_route(df, actual_route_column, route_id)
        else:
            route_df = df.copy()

        if len(route_df) < 3:
            log(f"Skipping route {route_id!r}: insufficient data ({len(route_df)} points)")
            continue

        route_df = route_df.sort_values(spec.x_column).reset_index(drop=True)

        # Apply preprocessing if configured
        if spec.preprocessing_config:
            log(f"Applying preprocessing to route {route_id!r}...")
            route_analysis, preprocessing_results = process_route_with_preprocessing(
                route_df,
                spec.x_column,
                spec.y_column,
                route_id=route_id,
                gap_threshold=spec.gap_threshold,
                preprocessing_config=spec.preprocessing_config,
                first_attribute_columns=spec.must_break_columns,
                second_attribute_columns=spec.secondary_break_columns,
                log_callback=log
            )
            preprocessing_results_by_route[route_id] = preprocessing_results
        else:
            # No preprocessing - use standard gap analysis
            route_analysis = analyze_route_gaps(
                route_df,
                spec.x_column,
                spec.y_column,
                route_id=route_id,
                gap_threshold=spec.gap_threshold,
                must_break_columns=spec.must_break_columns,
                secondary_break_columns=spec.secondary_break_columns,
            )
        
        prepared.append((route_id, route_analysis))
        original_data_by_route[route_id] = route_df.copy()

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

        # Attach preprocessing metadata if preprocessing was applied
        if route_id in preprocessing_results_by_route:
            preprocess_results = preprocessing_results_by_route[route_id]
            if preprocess_results:
                # Add preprocessing metadata to result
                res.preprocessing_metadata = [
                    r.preprocessing_metadata for r in preprocess_results
                ]
                res.preprocessing_summary = [
                    r.modifications_summary for r in preprocess_results
                ]
                res.preprocessing_modification_log = [
                    [
                        {
                            'modification_type': m.modification_type,
                            'x_value': m.x_value,
                            'original_y_value': m.original_y_value,
                            'new_y_value': m.new_y_value,
                            'reason': m.reason,
                            'timestamp': m.timestamp  # Already ISO format string
                        }
                        for m in r.modification_log
                    ]
                    for r in preprocess_results
                ]

        # Enrich data_summary with attribute break analysis (mirrors controller post-processing)
        if not res.data_summary:
            res.data_summary = {}
        from data_loader import build_attribute_break_analysis, build_secondary_attribute_break_analysis
        attr_analysis = build_attribute_break_analysis(route_analysis)
        if attr_analysis:
            res.data_summary['attribute_break_analysis'] = attr_analysis
        sec_attr_analysis = build_secondary_attribute_break_analysis(route_analysis)
        if sec_attr_analysis:
            res.data_summary['secondary_attribute_break_analysis'] = sec_attr_analysis

        _normalize_analysis_result_for_json_parity(res, method_params=method_params)
        results.append(res)

    out_path = spec.output_json_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and not spec.overwrite:
        raise RunSpecError(f"Output file already exists and overwrite=false: {out_path}")

    input_file_info = {
        **_active_source.get_traceability_info(),
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
    
    if spec.secondary_break_columns is not None:
        route_processing_info["secondary_break_columns"] = spec.secondary_break_columns
    
    # Add preprocessing config to route_processing_info for JSON export
    if spec.preprocessing_config is not None:
        route_processing_info["preprocessing_config"] = {
            "enabled": spec.preprocessing_config.enabled,
            "pre_gap_method": spec.preprocessing_config.pre_gap_method,
            "pre_gap_parameters": spec.preprocessing_config.pre_gap_parameters,
            "primary_method": spec.preprocessing_config.primary_method,
            "primary_parameters": spec.preprocessing_config.primary_parameters,
            "secondary_method": spec.preprocessing_config.secondary_method,
            "secondary_parameters": spec.preprocessing_config.secondary_parameters,
        }

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
    return _run_analysis_from_resolved_spec(spec, log_callback=log)


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def discover_batch_input_files(
    input_dir: Path,
    glob_pattern: str,
    *,
    recurse: bool,
) -> List[Path]:
    """Return sorted list of files matching ``glob_pattern`` in ``input_dir``.

    When ``recurse`` is True, searches all subdirectories recursively.
    """
    if recurse:
        return sorted(input_dir.rglob(glob_pattern))
    return sorted(input_dir.glob(glob_pattern))


def _detect_stem_collisions(files: List[Path]) -> List[str]:
    """Return list of stems that appear more than once across ``files``."""
    counts: Counter[str] = Counter(f.stem for f in files)
    return sorted(stem for stem, n in counts.items() if n > 1)


def _write_batch_summary(path: Path, summary: Dict[str, Any]) -> None:
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def run_batch_analysis_from_spec_file(
    spec_path: str | os.PathLike[str],
    input_dir: str | os.PathLike[str],
    output_dir: str | os.PathLike[str],
    *,
    glob_pattern: str = "*.csv",
    recurse: bool = False,
    summary_json: Optional[str | os.PathLike[str]] = None,
    continue_on_error: bool = True,
    export_excel: bool = False,
    export_csv: bool = False,
    validate_spec: bool = True,
    log_callback: Optional[LogCallback] = None,
) -> str:
    """Execute a batch analysis run using a template run spec.

    Discovers every file matching ``glob_pattern`` in ``input_dir``, substitutes
    that file's path into a per-file copy of the template spec (via
    ``dataclasses.replace``), runs the analysis, and writes results to
    ``output_dir/<stem>.json``. A JSON summary is written incrementally so partial
    progress is preserved even if the run is interrupted.

    Args:
        spec_path: Path to the template run-spec JSON file.
        input_dir: Directory to scan for input files.
        output_dir: Directory where per-file JSON (and optionally XLSX) results land.
        glob_pattern: Glob pattern used to discover files (default ``*.csv``).
        recurse: When True, scan subdirectories recursively.
        summary_json: Path for the batch summary JSON. Defaults to
            ``<output_dir>/batch_summary.json``.
        continue_on_error: When True, log failures and continue. When False, stop
            immediately and raise ``RunSpecError`` on the first failure.
        export_excel: When True, export each result JSON to an adjacent XLSX file.
        export_csv: When True, export segment results for each JSON to an adjacent CSV file.
        validate_spec: When True, validate the template spec against the JSON schema.
        log_callback: Optional log sink; defaults to stdout.

    Returns:
        Absolute path to the written batch summary JSON file.

    Raises:
        RunSpecError: On a hard error (bad spec, missing dir, stem collision, or
            first-failure when ``continue_on_error`` is False).
        BatchPartialFailureError: When ``continue_on_error`` is True and at least
            one file failed — raised after all files are attempted.
    """
    log = log_callback or _default_logger

    input_dir_path = Path(input_dir).expanduser().resolve()
    output_dir_path = Path(output_dir).expanduser().resolve()
    spec_path = Path(spec_path).expanduser().resolve()
    summary_json_path = (
        Path(summary_json).expanduser().resolve()
        if summary_json is not None
        else output_dir_path / "batch_summary.json"
    )

    if not input_dir_path.is_dir():
        raise RunSpecError(f"Input directory does not exist: {input_dir_path}")

    template_spec = load_and_resolve_run_spec(spec_path, validate=validate_spec)

    input_files = discover_batch_input_files(input_dir_path, glob_pattern, recurse=recurse)

    if not input_files:
        raise RunSpecError(
            f"No files matching {glob_pattern!r} found in {input_dir_path}"
        )

    collisions = _detect_stem_collisions(input_files)
    if collisions:
        raise RunSpecError(
            "Stem collisions detected — output names would overwrite each other: "
            + ", ".join(collisions)
        )

    output_dir_path.mkdir(parents=True, exist_ok=True)
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)

    log(f"Batch run: {len(input_files)} file(s) in {input_dir_path}")
    log(f"Output dir: {output_dir_path}")
    log(f"Template spec: {spec_path}")

    if export_excel:
        from excel_export import export_json_to_excel
    if export_csv:
        from csv_export import export_json_to_csv

    summary: Dict[str, Any] = {
        "batch_version": "1.0.0",
        "started_at": _now_utc(),
        "template_spec_path": str(spec_path),
        "input_dir": str(input_dir_path),
        "glob": glob_pattern,
        "recurse": recurse,
        "output_dir": str(output_dir_path),
        "summary_json": str(summary_json_path),
        "continue_on_error": continue_on_error,
        "export_excel": export_excel,
        "export_csv": export_csv,
        "total_files": len(input_files),
        "completed": 0,
        "failed": 0,
        "results": [],
    }

    failed_names: List[str] = []

    for i, input_file in enumerate(input_files, 1):
        stem = input_file.stem
        out_json = output_dir_path / f"{stem}.json"

        log(f"[{i}/{len(input_files)}] {input_file.name}")

        file_spec = _dc_replace(
            template_spec,
            data_file_path=input_file,
            output_json_path=out_json,
            overwrite=True,
        )

        file_result: Dict[str, Any] = {
            "input_file": str(input_file),
            "output_json": str(out_json),
            "status": "pending",
        }

        try:
            json_path = _run_analysis_from_resolved_spec(file_spec, log_callback=log)
            file_result["status"] = "success"
            file_result["output_json"] = json_path

            if export_excel:
                xlsx_path = output_dir_path / f"{stem}.xlsx"
                ok = export_json_to_excel(json_path, str(xlsx_path), str(input_file))
                file_result["output_xlsx"] = str(xlsx_path) if ok else None
                if not ok:
                    log(f"  Warning: Excel export failed for {input_file.name}")

            if export_csv:
                csv_path = output_dir_path / f"{stem}.csv"
                ok, err = export_json_to_csv(json_path, str(csv_path))
                file_result["output_csv"] = str(csv_path) if ok else None
                if not ok:
                    log(f"  Warning: CSV export failed for {input_file.name}: {err}")

            summary["completed"] += 1

        except Exception as exc:
            file_result["status"] = "failed"
            file_result["error"] = str(exc)
            failed_names.append(input_file.name)
            summary["failed"] += 1
            log(f"  ERROR: {input_file.name}: {exc}")

            if not continue_on_error:
                summary["results"].append(file_result)
                summary["finished_at"] = _now_utc()
                _write_batch_summary(summary_json_path, summary)
                raise RunSpecError(
                    f"Batch run stopped on first error ({input_file.name}): {exc}"
                ) from exc

        summary["results"].append(file_result)
        _write_batch_summary(summary_json_path, summary)

    summary["finished_at"] = _now_utc()
    _write_batch_summary(summary_json_path, summary)

    log(
        f"Batch complete: {summary['completed']} succeeded, {summary['failed']} failed"
    )
    log(f"Summary written: {summary_json_path}")

    if failed_names:
        raise BatchPartialFailureError(
            f"Batch run completed with {len(failed_names)} failure(s): "
            + ", ".join(failed_names)
        )

    return str(summary_json_path)
