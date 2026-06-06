"""Saves consolidated multi-route optimization results to JSON.

Separates result persistence logic from OptimizationController, keeping the
controller focused on thread lifecycle and per-route execution.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

from config import get_optimization_method
from route_utils import (
    ROUTE_COLUMN_NONE_SENTINEL,
    filter_data_by_route,
    normalize_route_column_selection,
)


class OptimizationResultsSaver:
    """Converts per-route result dicts into AnalysisResult objects and writes JSON.

    Owns the bridge between controller-level app state (column selections, file paths,
    preprocessed data) and the schema-driven ExtensibleJsonResultsManager.
    """

    def __init__(self, app) -> None:
        self.app = app

    def save(
        self,
        all_route_results: list,
        method_key: str,
        params: dict,
        preprocessed_data_by_route: dict | None = None,
    ) -> str | None:
        """Save consolidated results from all routes.

        Args:
            all_route_results: List of result dicts from _run_single_route_optimization.
            method_key: Optimization method key ('single', 'constrained', 'multi').
            params: Optimization parameters dictionary.
            preprocessed_data_by_route: Dict of route_id -> preprocessed DataFrame.
                When provided and non-empty, used for accurate segment statistics.

        Returns:
            JSON file path on success, None on failure or user cancel.
        """
        try:
            self.app.log_message(f"Saving consolidated results from {len(all_route_results)} route(s)...")

            save_name = self.app.custom_save_name.get()
            output_path = self._prepare_save_filename(save_name)

            if not output_path:
                self.app.log_message("Save cancelled - no output path selected")
                return None

            if output_path.endswith('.csv'):
                json_path = output_path.replace('.csv', '.json')
            elif output_path.endswith('.json'):
                json_path = output_path
            else:
                json_path = f"{output_path}.json"

            from extensible_results_manager import ExtensibleJsonResultsManager
            from analysis.base import AnalysisResult

            actual_x_column = self.app.x_column.get()
            actual_y_column = self.app.y_column.get()
            actual_route_column = self.app.route_column.get() if hasattr(self.app, 'route_column') else None
            actual_data_file = self.app.file_manager.get_data_file_path()

            method_config = get_optimization_method(method_key)
            if not method_config:
                raise ValueError(f"Unknown optimization method: {method_key}")

            method_display_name = method_config.display_name
            analysis_method = method_config.method_key

            analysis_results = []
            for route_result in all_route_results:
                if method_key == 'multi' and route_result.get('all_solutions'):
                    all_solutions = []
                    for sol in (route_result.get('all_solutions') or []):
                        if isinstance(sol, dict):
                            sol_copy = dict(sol)
                            sol_copy.pop('segmentation', None)
                            all_solutions.append(sol_copy)
                        else:
                            all_solutions.append(sol)
                else:
                    all_solutions = [{
                        'chromosome': route_result.get('best_chromosome', []),
                        'fitness': route_result.get('best_fitness'),
                        'segments': route_result.get('segments_data', []),
                        'total_length': route_result.get('total_length', 0)
                    }]

                result = AnalysisResult(
                    method_name=method_display_name,
                    method_key=analysis_method,
                    route_id=route_result.get('route_id', 'unknown'),
                    processing_time=route_result.get('execution_time', route_result.get('processing_time', 0)),
                    timestamp=route_result.get('timestamp', datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
                    analysis_version="1.95.2",

                    all_solutions=all_solutions,
                    optimization_stats=route_result.get('optimization_stats', {}) or {
                        'best_fitness': route_result.get('best_fitness'),
                        'generations_run': route_result.get('generations_run', 0),
                        'population_size': route_result.get('population_size', 0),
                        'final_generation': route_result.get('generations_run', 0),
                        'pareto_front_size': route_result.get('pareto_front_size', 0),
                        'best_deviation_fitness': route_result.get('best_deviation_fitness'),
                        'best_segment_count': route_result.get('best_segment_count')
                    },

                    mandatory_breakpoints=route_result.get('mandatory_breakpoints', []),
                    input_parameters=route_result.get('input_parameters', {}),
                    data_summary=route_result.get('data_summary', {
                        'total_data_points': route_result.get('num_data_points', 0)
                    }),

                    preprocessing_metadata=route_result.get('preprocessing_metadata', []),
                    preprocessing_summary=route_result.get('preprocessing_summary', []),
                    preprocessing_modification_log=route_result.get('preprocessing_modification_log', [])
                )
                analysis_results.append(result)

            manager = ExtensibleJsonResultsManager()
            data_file_path = Path(actual_data_file) if actual_data_file else None

            in_memory_columns = []
            if hasattr(self.app, 'data') and hasattr(self.app.data, 'route_data'):
                try:
                    in_memory_columns = list(self.app.data.route_data.columns)
                except Exception:
                    in_memory_columns = []

            route_col_requested = actual_route_column
            if route_col_requested == ROUTE_COLUMN_NONE_SENTINEL:
                route_col_requested = None

            if route_col_requested and route_col_requested in in_memory_columns:
                route_col_used = route_col_requested
            elif 'route' in in_memory_columns:
                route_col_used = 'route'
            else:
                route_col_used = None
                self.app.log_message(
                    f"Warning: Selected route column '{actual_route_column}' not present in loaded data; "
                    "saving will omit route_column metadata"
                )

            # Build traceability metadata from the active data source.
            from data_sources.base import DataSourceBase as _DataSourceBase
            active_source = getattr(self.app, '_active_data_source', None)
            if isinstance(active_source, _DataSourceBase):
                input_file_info = active_source.get_traceability_info()
            elif data_file_path is not None:
                try:
                    from data_sources.file_source import FileDataSource
                    from data_sources.base import DataSourceConfig
                    _fs = FileDataSource(DataSourceConfig(source_type="file", file_path=str(data_file_path)))
                    input_file_info = _fs.get_traceability_info()
                except Exception:
                    input_file_info = {
                        "source_type": "file",
                        "data_file_path": str(data_file_path),
                        "data_file_name": data_file_path.name,
                        "data_file_size_bytes": data_file_path.stat().st_size if data_file_path.exists() else None,
                    }
            else:
                input_file_info = {"source_type": "file"}

            # Merge in runtime stats that require the loaded DataFrame.
            input_file_info.update({
                'total_data_rows': len(self.app.data.route_data) if hasattr(self.app.data, 'route_data') else None,
                'total_routes_available': (
                    len(self.app.data.route_data[route_col_used].unique())
                    if (hasattr(self.app.data, 'route_data') and route_col_used)
                    else 1
                ),
                'column_info': {
                    'total_columns': len(self.app.data.route_data.columns) if hasattr(self.app.data, 'route_data') else None,
                    'x_column': actual_x_column,
                    'y_column': actual_y_column,
                    'route_column': (
                        route_col_requested
                        if (route_col_requested and route_col_requested in in_memory_columns and route_col_requested != 'route')
                        else None
                    )
                }
            })

            route_processing_config = {
                'route_mode': 'multi_route' if len(all_route_results) > 1 else 'single_route',
                'selected_routes': [r.get('route_id') for r in all_route_results],
                'x_column': actual_x_column,
                'y_column': actual_y_column,
                'route_column': (
                    route_col_requested
                    if (route_col_requested and route_col_requested in in_memory_columns and route_col_requested != 'route')
                    else None
                ),
                'route_filtering_applied': len(all_route_results) > 1,
                'total_routes_in_source': len(all_route_results),
                'total_routes_processed': len(all_route_results),
                'custom_save_name': params.get('custom_save_name')
            }

            must_break_cols = getattr(self.app, 'must_break_columns', None)
            if must_break_cols and isinstance(must_break_cols, list) and any(must_break_cols):
                route_processing_config['must_break_columns'] = [str(c).strip() for c in must_break_cols if str(c).strip()]

            secondary_break_cols = getattr(self.app, 'secondary_break_columns', None)
            if secondary_break_cols and isinstance(secondary_break_cols, list) and any(secondary_break_cols):
                route_processing_config['secondary_break_columns'] = [str(c).strip() for c in secondary_break_cols if str(c).strip()]

            json_output_path = manager.save_analysis_results(
                analysis_results,
                json_path,
                input_file_info=input_file_info,
                route_processing_info=route_processing_config,
                original_data_by_route=self._build_data_by_route_for_export(
                    analysis_results, preprocessed_data_by_route or {}
                )
            )

            self.app.log_message(f"Results saved: {json_output_path}")

            if hasattr(self.app, 'file_manager') and hasattr(self.app, 'root'):
                try:
                    self.app.root.after(0, lambda p=json_output_path: self.app.file_manager.display_json_summary(p))
                except Exception as e:
                    if hasattr(self.app, 'handle_error'):
                        self.app.handle_error("Could not update Results Files tab", e, severity="warning", show_messagebox=False)
                    else:
                        self.app.log_message(f"Warning: Could not update Results Files tab: {e}")

            return json_output_path

        except Exception as e:
            if hasattr(self.app, 'handle_error'):
                self.app.handle_error("Error saving consolidated results", e, severity="error", show_messagebox=False)
            else:
                self.app.log_message(f"❌ Error saving consolidated results: {e}")
            return None

    def _prepare_save_filename(self, custom_name: str) -> str | None:
        """Resolve a user-provided filename to a full path, prompting on overwrite.

        Returns None if the user cancels the overwrite dialog or name is empty.
        """
        if not custom_name:
            return None

        json_filename = custom_name if custom_name.lower().endswith('.json') else f"{custom_name}.json"

        save_path = self.app.file_manager.get_save_file_path()
        if save_path:
            save_dir = os.path.dirname(save_path)
            full_path = os.path.join(save_dir, json_filename)
        else:
            full_path = json_filename

        if os.path.exists(full_path):
            response = messagebox.askyesno(
                "File Exists",
                f"The following file already exists:\n{json_filename}\n\nDo you want to overwrite it?",
                icon='warning'
            )
            if not response:
                return None

        return full_path

    def _build_data_by_route_for_export(
        self,
        analysis_results: list,
        preprocessed_data_by_route: dict,
    ) -> dict:
        """Build data dict by route ID for segment statistics calculation.

        Prefers preprocessed data when available so segment statistics match
        what the GA actually optimized against.

        Args:
            analysis_results: List of AnalysisResult objects.
            preprocessed_data_by_route: Dict of route_id -> preprocessed DataFrame
                (empty when no preprocessing was applied).

        Returns:
            Dict mapping route_id -> DataFrame.
        """
        if not analysis_results:
            return {}

        try:
            if preprocessed_data_by_route:
                self.app.log_message(
                    f"Using preprocessed data for {len(preprocessed_data_by_route)} route(s) segment statistics"
                )
                return preprocessed_data_by_route.copy()

            if not self.app.data:
                return {}

            route_column = normalize_route_column_selection(
                self.app.route_column.get() if hasattr(self.app, 'route_column') else None
            )

            original_data_by_route = {}
            for result in analysis_results:
                route_id = result.route_id
                try:
                    if route_column is not None:
                        route_df = filter_data_by_route(self.app.data.route_data, route_column, route_id)
                    else:
                        route_df = self.app.data.route_data.copy()

                    if not route_df.empty:
                        original_data_by_route[route_id] = route_df

                except Exception as e:
                    self.app.log_message(f"Warning: Could not extract data for route {route_id}: {e}")
                    continue

            self.app.log_message(
                f"Using original CSV data for {len(original_data_by_route)} route(s) segment statistics"
            )
            return original_data_by_route

        except Exception as e:
            self.app.log_message(f"Warning: Could not build original data by route: {e}")
            return {}
