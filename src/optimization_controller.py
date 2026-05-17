"""Optimization execution, threading, and result collection for the GUI.

Separates optimization concerns (thread lifecycle, route processing, file saving)
from the main GUI class.
"""

import threading
import time
import os
import json
from datetime import datetime
from tkinter import messagebox
from config import get_optimization_method, resolve_method_class
from route_utils import (
    INTERNAL_ROUTE_IDS_TO_SKIP_LOWER,
    ROUTE_COLUMN_NONE_SENTINEL,
    normalize_route_column_selection,
    normalize_route_id,
)


class OptimizationController:
    """
    Handles optimization execution, control, and monitoring.
    
    This class manages the optimization workflow including parameter preparation,
    thread execution, progress monitoring, result handling, and cleanup operations.
    """
    
    def __init__(self, main_app):
        """
        Initialize the optimization controller with a reference to the main application.
        
        Args:
            main_app: Reference to the main HighwaySegmentationGUI instance
        """
        self.app = main_app
        self.optimization_thread = None
        self.is_running = False
        self._optimization_start_time = None

    def reset_state(self):
        """
        Reset optimization controller state when loading new data.
        
        This prevents stale state from causing issues when switching between
        different datasets within the same app session.
        """
        self.optimization_thread = None
        self.is_running = False
        self._optimization_start_time = None
        # Note: do not mutate self.app.available_routes / self.app.selected_routes here.
        # Route selection is UI state owned by the GUI; clearing it here can erase a
        # user's filter right before optimization starts (especially when auto-loading).

    def _prepare_save_filename(self, custom_name):
        """Resolve a user-provided filename to a full path, prompting on overwrite.

        Adds a .json extension if missing and resolves the path relative to the
        configured save directory. Returns None if the user cancels the overwrite dialog.

        Args:
            custom_name (str): User-provided filename (with or without extension).

        Returns:
            str or None: Full resolved path for saving, or None if user cancels.
        """
        if not custom_name:
            return None
        
        if not custom_name.lower().endswith('.json'):
            json_filename = f"{custom_name}.json"
        else:
            json_filename = custom_name

        save_path = self.app.file_manager.get_save_file_path()
        if save_path:
            save_dir = os.path.dirname(save_path)
            full_path = os.path.join(save_dir, json_filename)
        else:
            full_path = json_filename
        
        json_exists = os.path.exists(full_path)
        
        if json_exists:
            response = messagebox.askyesno(
                "File Exists", 
                f"The following file already exists:\n{json_filename}\n\nDo you want to overwrite it?",
                icon='warning'
            )
            if not response:
                return None
        
        return full_path
    
    def start_optimization(self):
        """Validate inputs and launch the optimization worker thread.

        Checks data availability (auto-loading if a path is configured), validates
        parameters, updates UI state, and starts a daemon thread for the run.
        """
        if self.app.data is None:
            data_path = self.app.file_manager.get_data_file_path()
            if data_path and os.path.exists(data_path):
                self.app.log_message("No data loaded, attempting to load from configured file...")
                try:
                    self.app.load_data_file()
                    if self.app.data is None:
                        messagebox.showerror("Data Required", "No data is loaded and could not load data from the configured file. Please load data first.")
                        return
                except Exception as e:
                    messagebox.showerror("Data Loading Error", f"Could not load data from configured file:\n{str(e)}")
                    return
            else:
                messagebox.showerror("Data Required", "No data is loaded and no valid data file is configured. Please load data first.")
                return
        
        if not self.app.parameter_manager.validate_and_show_errors():
            return

        if self.app.is_running:
            messagebox.showwarning("Already Running", "Optimization is already in progress.")
            return
        
        self.app.is_running = True
        self.app.stop_requested = False

        if hasattr(self.app, 'start_button'):
            self.app.start_button.config(state="disabled")
        if hasattr(self.app, 'stop_button'):
            self.app.stop_button.config(state="normal")

        if hasattr(self.app, 'results_text'):
            self.app.results_text.delete(1.0, 'end')

        if hasattr(self.app, 'results_notebook'):
            self.app.results_notebook.select(0)  # Select Optimization Log tab

        self.optimization_thread = threading.Thread(target=self._run_optimization_worker, daemon=True)
        self.optimization_thread.start()
    
    def stop_optimization(self):
        """Request optimization to stop and wait for proper cleanup."""
        if self.app.is_running:
            self.app.stop_requested = True
            self.app.log_message("Stop requested - optimization will halt after current generation...")
            
            if hasattr(self.app, 'stop_button'):
                self.app.stop_button.config(text="Stopping...", state="disabled")
                
            if self.optimization_thread and self.optimization_thread.is_alive():
                try:
                    # Give the thread reasonable time to finish its current operation
                    self.optimization_thread.join(timeout=5.0)
                    if self.optimization_thread.is_alive():
                        self.app.log_message("Warning: Optimization thread did not stop cleanly")
                    else:
                        self.app.log_message("Optimization thread stopped successfully")
                except Exception as e:
                    self.app.log_message(f"Error stopping optimization thread: {e}")
                finally:
                    self.optimization_thread = None
    
    def _run_optimization_worker(self):
        """Worker method that runs in a separate thread to perform optimization."""
        try:
            self._optimization_start_time = time.time()

            params = self.app.parameter_manager.get_optimization_parameters()
            method_key = params['optimization_method']

            method_config = get_optimization_method(method_key)
            if not method_config:
                raise ValueError(f"Unknown optimization method: {method_key}")

            # Framework-level gap threshold (single source of truth: app.gap_threshold)
            gap_threshold = float(self.app.gap_threshold.get())
            if gap_threshold <= 0:
                raise ValueError(f"gap_threshold must be > 0 (got {gap_threshold})")

            # Segment length bounds are method-specific (may be absent for non-GA methods)
            min_length = params.get('min_length', None)
            max_length = params.get('max_length', None)
            
            route_column_raw = self.app.route_column.get() if hasattr(self.app, 'route_column') else None
            route_column = normalize_route_column_selection(route_column_raw)

            if route_column and route_column in self.app.data.route_data.columns:
                actual_route_column = route_column
                is_single_route_mode = False
            else:
                # Default to single route mode (covers ROUTE_COLUMN_NONE_SENTINEL and unselected cases)
                actual_route_column = None
                is_single_route_mode = True
            
            if is_single_route_mode:
                filename = os.path.basename(self.app.file_manager.get_data_file_path() or "unknown.csv")
                route_name = filename.replace('.csv', '').replace('.xlsx', '')
                all_routes = [route_name]
            else:
                if actual_route_column in self.app.data.route_data.columns:
                    # B1 behavior: exclude rows with missing/invalid route IDs.
                    # This matters when the user selects a route column after loading.
                    try:
                        route_series = self.app.data.route_data[actual_route_column]
                        normalized_series = route_series.apply(normalize_route_id)
                        invalid_mask = normalized_series.isna()
                        invalid_count = int(invalid_mask.sum())
                        if invalid_count > 0:
                            self.app.log_message(
                                f"Route column '{actual_route_column}' contains {invalid_count} record(s) "
                                "with missing route IDs. "
                                "Those records will be excluded from multi-route analysis."
                            )

                        if invalid_count == len(self.app.data.route_data):
                            raise ValueError(
                                f"All records in the selected route column '{actual_route_column}' are missing. "
                                "Choose a different route column, or select 'None - treat as single route'."
                            )

                        if invalid_count > 0:
                            filtered = self.app.data.route_data.loc[~invalid_mask].copy()
                            filtered[actual_route_column] = normalized_series.loc[~invalid_mask].astype("string")
                            self.app.data.route_data = filtered
                    except Exception:
                        # If normalization/filtering fails for unexpected reasons, treat as fatal.
                        raise

                    unique_routes = self.app.data.route_data[actual_route_column].unique()
                    normalized_routes = []
                    for route in unique_routes:
                        route_str = normalize_route_id(route)
                        if route_str is None:
                            continue
                        # Filter out internal/sentinel route IDs (case-insensitive)
                        if route_str.lower() in INTERNAL_ROUTE_IDS_TO_SKIP_LOWER:
                            continue
                        normalized_routes.append(route_str)
                    all_routes = sorted(set(normalized_routes))
                else:
                    self.app.log_message(f"[ERROR] Route column '{actual_route_column}' not found in data!")
                    return
            
            # Determine routes to process.
            # Important: an explicit empty selection ([]) is an error in multi-route mode.
            if is_single_route_mode:
                selected_routes = all_routes
            else:
                raw_selected_routes = getattr(self.app, 'selected_routes', None)
                if raw_selected_routes is None:
                    selected_routes = all_routes
                elif isinstance(raw_selected_routes, (list, tuple)):
                    if len(raw_selected_routes) == 0:
                        raise ValueError(
                            "No routes selected. Please open Route Filter and select at least one route."
                        )
                    selected_routes = list(raw_selected_routes)
                else:
                    selected_routes = all_routes

            selected_routes = [r for r in (normalize_route_id(r) for r in selected_routes) if r is not None]
            routes_to_process = [route for route in selected_routes if route in all_routes]

            if len(routes_to_process) == 0:
                if is_single_route_mode:
                    raise ValueError("No route could be determined for single-route processing")
                raise ValueError(
                    "No selected routes matched the data. "
                    "Re-open Route Filter (or re-load the file) and select at least one available route."
                )
            
            self.app.log_message(f"Starting optimization for {len(routes_to_process)} route(s)...")
            if len(routes_to_process) > 1:
                self.app.log_message(f"Route column: {actual_route_column}")
                self.app.log_message(f"Routes to process: {', '.join(routes_to_process)}")
            else:
                self.app.log_message(f"Processing single route: {routes_to_process[0]}")
            
            prepared_routes = self._prepare_multi_route_analyses(
                self.app.data,
                actual_route_column,
                routes_to_process,
                self.app.x_column.get(),
                self.app.y_column.get(),
                gap_threshold=gap_threshold,
                is_single_route_mode=is_single_route_mode,
            )
            if not prepared_routes:
                self.app.log_message("ERROR: No routes could be analyzed successfully")
                return
                
            self.app.log_message(f"Successfully prepared {len(prepared_routes)} route(s) for optimization")
            
            x_column = self.app.x_column.get()
            y_column = self.app.y_column.get()
            # All other parameters are passed directly to methods via params dict

            all_route_results = []
            total_routes = len(prepared_routes)
            for route_idx, (route_id, route_data) in enumerate(prepared_routes, 1):
                if self.app.stop_requested:
                    self.app.log_message("Optimization stopped by user request")
                    break
                
                if total_routes > 1:
                    self.app.log_message(f"Processing Route {route_id} ({route_idx}/{total_routes})...")
                else:
                    self.app.log_message(f"Processing Route {route_id}...")
                
                result = self._run_single_route_optimization(
                    route_data, method_config, method_key, params,
                    x_column, y_column, min_length, max_length, gap_threshold,
                    route_id, route_idx, total_routes
                )
                
                if result:
                    all_route_results.append(result)
                    self.app.log_message(f"Route {route_id} completed successfully")
                else:
                    self.app.log_message(f"Route {route_id} failed to produce results")
            
            if all_route_results and not self.app.stop_requested:
                if self.app.custom_save_name.get():
                    json_path = self._save_consolidated_results(all_route_results, method_key, params)
                    if json_path:
                        self.app.log_message(f"Consolidated results saved for {len(all_route_results)} route(s)")
                        
                        # Open enhanced visualization for multi-route results
                        self.app.root.after(0, lambda: self._show_enhanced_multi_route_visualization(json_path, all_route_results, method_key))
                    else:
                        self.app.log_message("Warning: Failed to save consolidated results - visualization not opened")
                else:
                    self.app.log_message("Multi-route results not saved (no save name specified)")
                    # Still show visualization even without saving
                    self.app.root.after(0, lambda: self._show_enhanced_multi_route_visualization(None, all_route_results, method_key))
            
            completion_msg = f"Optimization completed for {total_routes} route(s)"
            self.app.log_message(completion_msg)
        
        except Exception as e:
            if hasattr(self.app, 'handle_error'):
                self.app.handle_error(
                    "An error occurred during optimization",
                    e,
                    severity="error",
                    show_messagebox=True,
                )
            else:
                self.app.log_message(f"Optimization error: {str(e)}")
                messagebox.showerror("Optimization Error", f"An error occurred during optimization:\n{str(e)}")
        
        finally:
            # Always clean up UI state
            self.app.root.after(0, lambda: self._finalize_optimization(self.app.stop_requested))
    
    def _run_single_route_optimization(self, data, method_config, method_key, params, 
                                     x_column, y_column, min_length, max_length, gap_threshold,
                                     route_id, route_idx=1, total_routes=1):
        """
        Run optimization for a single route (unified architecture - always has route_id).
        
        Args:
            data: RouteAnalysis object containing the route data
            method_config: Optimization method configuration
            method_key: Method key (single, constrained, multi, aashto_cda)
            params: All optimization parameters (method-specific extraction handled by each method)
            x_column, y_column: Data column names
            min_length, max_length: Basic segment constraints for logging
            route_id: Route identifier (always present in unified architecture)
            route_idx: Current route index (1-based)
            total_routes: Total number of routes being processed
            
        Returns:
            dict: Optimization results or None if failed
        """
        try:
            route_data_points = len(data.route_data)
            self.app.log_message(f"Route {route_id}: Running {method_config.display_name} ({route_data_points} points)")

            # Dispatch is configuration-driven via method_class_path
            analysis_result = None
            try:
                cls = resolve_method_class(method_key)
                method_instance = cls()

                # Avoid passing gap_threshold twice (positional + kwargs)
                method_params = dict(params)
                method_params.pop('gap_threshold', None)

                # Reserve callback names so they cannot be overwritten by params
                method_params.pop('log_callback', None)
                method_params.pop('stop_callback', None)
                method_params.pop('input_parameters', None)

                analysis_kwargs = dict(method_params)
                analysis_kwargs['log_callback'] = self.app.log_message
                analysis_kwargs['stop_callback'] = lambda: self.app.stop_requested
                # Provide full parameter dict as a convenience for methods that want it (e.g., constrained)
                analysis_kwargs['input_parameters'] = method_params

                analysis_result = method_instance.run_analysis(
                    data, route_id, x_column, y_column, gap_threshold,
                    **analysis_kwargs,
                )
            except Exception as e:
                self.app.log_message(f"❌ Error running method '{method_key}': {e}")
                analysis_result = None

            if not analysis_result or self.app.stop_requested:
                self.app.log_message(f"Route {route_id}: Optimization failed for method_key='{method_key}'")
                return None

            best_solution = analysis_result.best_solution
            input_parameters = analysis_result.input_parameters or {}

            def _get_numeric(value, default=0.0):
                if isinstance(value, (int, float)):
                    return value
                if isinstance(value, list) and value and isinstance(value[0], (int, float)):
                    return value[0]
                return default

            result = {
                'route_id': route_id,
                'method_key': method_key,
                'best_fitness': _get_numeric(best_solution.get('deviation_fitness', best_solution.get('fitness', 0.0))),
                'objective_values': best_solution.get('objective_values', [best_solution.get('fitness', 0.0)]),
                'best_chromosome': best_solution.get('chromosome', []),
                'avg_segment_length': best_solution.get('avg_segment_length', 0.0),
                'execution_time': analysis_result.processing_time,
                'mandatory_breakpoints': analysis_result.mandatory_breakpoints,

                'data_summary': analysis_result.data_summary,
                'input_parameters': input_parameters,
                'optimization_stats': analysis_result.optimization_stats,
                'performance_metrics': analysis_result.optimization_stats.get('performance_metrics', {}),
                'final_population_fitness': analysis_result.optimization_stats.get('final_population_fitness', []),
                'generation_stats': analysis_result.optimization_stats.get('generation_stats', []),
            }

            # Derive segment count consistently when available
            if 'segments' in best_solution and isinstance(best_solution.get('segments'), list):
                result['best_segments'] = len(best_solution.get('segments', []))
            else:
                result['best_segments'] = (
                    best_solution.get('num_segments')
                    or best_solution.get('segment_count')
                    or best_solution.get('best_segments')
                    or 0
                )

            if getattr(method_config, 'return_type', None) == 'multi_objective':
                result['all_solutions'] = analysis_result.all_solutions
                result['pareto_front_size'] = analysis_result.optimization_stats.get(
                    'pareto_front_size', len(analysis_result.all_solutions)
                )
                result['best_deviation_fitness'] = analysis_result.optimization_stats.get('best_deviation_fitness')
                result['best_segment_count'] = analysis_result.optimization_stats.get('best_segment_count')

            if 'unconstrained_fitness' in best_solution:
                result['best_unconstrained_fitness'] = best_solution.get('unconstrained_fitness', 0.0)
            if 'length_deviation' in best_solution:
                result['length_deviation'] = best_solution.get('length_deviation', 0.0)
            if 'target_avg_length' in input_parameters:
                result['target_avg_length'] = input_parameters.get('target_avg_length')
            if 'length_tolerance' in input_parameters:
                result['tolerance'] = input_parameters.get('length_tolerance')

            if 'best_fitness_history' in analysis_result.optimization_stats:
                result['fitness_history'] = analysis_result.optimization_stats.get('best_fitness_history', [])
            if 'avg_length_history' in analysis_result.optimization_stats:
                result['length_history'] = analysis_result.optimization_stats.get('avg_length_history', [])

            if all(k in input_parameters for k in ['alpha', 'method', 'use_segment_length']):
                result['analysis_method'] = 'AASHTO Enhanced CDA'
                result['statistical_parameters'] = {
                    'alpha': input_parameters.get('alpha'),
                    'error_estimation_method': input_parameters.get('method'),
                    'use_segment_length': input_parameters.get('use_segment_length'),
                }
                result['all_solutions'] = analysis_result.all_solutions
                result['method_stats'] = analysis_result.optimization_stats

            return result
            
        except Exception as e:
            if route_id:
                self.app.log_message(f"Route {route_id}: Optimization error: {str(e)}")
            else:
                self.app.log_message(f"Optimization error: {str(e)}")
            return None
    
    def _finalize_optimization(self, stopped_early=False):
        """Finalize the optimization process and update UI."""
        self.app.is_running = False
        self.app.stop_requested = False

        if hasattr(self.app, 'start_button'):
            self.app.start_button.config(state="normal")
        if hasattr(self.app, 'stop_button'):
            self.app.stop_button.config(text="⏹ Stop", state="disabled")

        if stopped_early:
            self.app.log_message("Optimization stopped by user.")
        else:
            self.app.log_message("Optimization completed.")
    
    def _save_consolidated_results(self, all_route_results, method_key, params):
        """Save consolidated results from all routes using ExtensibleJsonResultsManager.

        Args:
            all_route_results: List of result dictionaries from all processed routes.
            method_key: Optimization method key ('single', 'constrained', 'multi').
            params: Optimization parameters dictionary.

        Returns:
            str: JSON file path if successful, None if failed.
        """
        try:
            self.app.log_message(f"Saving consolidated results from {len(all_route_results)} route(s)...")
            
            save_name = self.app.custom_save_name.get()
            output_path = self._prepare_save_filename(save_name)

            # User may cancel overwrite prompt or provide invalid name
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

            # Use the live GUI values rather than whatever was cached in params.
            actual_x_column = self.app.x_column.get()
            actual_y_column = self.app.y_column.get()
            actual_route_column = self.app.route_column.get() if hasattr(self.app, 'route_column') else None
            actual_data_file = self.app.file_manager.get_data_file_path()
            
            analysis_results = []

            method_config = get_optimization_method(method_key)
            if not method_config:
                raise ValueError(f"Unknown optimization method: {method_key}")

            method_display_name = method_config.display_name
            analysis_method = method_config.method_key
            
            for route_result in all_route_results:
                # For multi-objective, ensure we preserve the full Pareto front
                if method_key == 'multi' and route_result.get('all_solutions'):
                    all_solutions = []
                    for sol in (route_result.get('all_solutions') or []):
                        if isinstance(sol, dict):
                            sol_copy = dict(sol)
                            if 'chromosome' in sol_copy:
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
                    })
                )
                analysis_results.append(result)
            
            manager = ExtensibleJsonResultsManager()

            from pathlib import Path
            data_file_path = Path(actual_data_file) if actual_data_file else None
            
            # Determine a route column that actually exists in the in-memory data.
            # The UI selection can change after load; keep saving resilient.
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
                # Synthetic single-route column created at load time
                route_col_used = 'route'
            else:
                route_col_used = None
                if hasattr(self.app, 'log_message'):
                    self.app.log_message(
                        f"Warning: Selected route column '{actual_route_column}' not present in loaded data; "
                        f"saving will omit route_column metadata"
                    )

            input_file_info = {
                'data_file_path': str(data_file_path) if data_file_path else 'unknown.csv',
                'data_file_name': data_file_path.name if data_file_path else 'unknown.csv',
                'data_file_size_bytes': data_file_path.stat().st_size if data_file_path and data_file_path.exists() else None,
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
            }
            
            route_processing_config = {
                'route_mode': 'multi_route' if len(all_route_results) > 1 else 'single_route',
                'selected_routes': [result.get('route_id') for result in all_route_results],
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
            
            json_output_path = manager.save_analysis_results(
                analysis_results,
                json_path,
                input_file_info=input_file_info,
                route_processing_info=route_processing_config,
                original_data_by_route=self._build_original_data_by_route(analysis_results)
            )
            
            self.app.log_message(f"Results saved: {json_output_path}")

            # Populate Results Files tab with summary extracted from JSON
            if hasattr(self.app, 'file_manager') and hasattr(self.app, 'root'):
                try:
                    self.app.root.after(0, lambda p=json_output_path: self.app.file_manager.display_json_summary(p))
                except Exception as e:
                    # Non-fatal UI update failure; keep optimization results saved.
                    if hasattr(self.app, 'handle_error'):
                        self.app.handle_error("Could not update Results Files tab", e, severity="warning", show_messagebox=False)
                    elif hasattr(self.app, 'log_message'):
                        self.app.log_message(f"Warning: Could not update Results Files tab: {e}")
            return json_output_path
            
        except Exception as e:
            if hasattr(self.app, 'handle_error'):
                self.app.handle_error("Error saving consolidated results", e, severity="error", show_messagebox=False)
            else:
                self.app.log_message(f"❌ Error saving consolidated results: {e}")
            return None
    
    def _build_original_data_by_route(self, analysis_results):
        """Build original data dictionary by route ID for segment statistics calculation.
        
        Args:
            analysis_results: List of AnalysisResult objects
            
        Returns:
            Dict[str, DataFrame]: Original CSV data by route ID
        """
        if not self.app.data or not analysis_results:
            return {}
        
        try:
            from data_loader import filter_data_by_route
            
            original_data_by_route = {}
            route_column = normalize_route_column_selection(
                self.app.route_column.get() if hasattr(self.app, 'route_column') else None
            )
            
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
            
            self.app.log_message(f"Built original data for {len(original_data_by_route)} route(s)")
            return original_data_by_route
            
        except Exception as e:
            self.app.log_message(f"Warning: Could not build original data by route: {e}")
            return {}
    
    def is_optimization_running(self):
        """Check if optimization is currently running."""
        return self.app.is_running and (self.optimization_thread is not None and self.optimization_thread.is_alive())
    
    def _show_enhanced_multi_route_visualization(self, json_path, all_route_results, method_key):
        """Show visualization for multi-route optimization results."""
        try:
            from visualization_ui import show_enhanced_visualization

            json_data = None
            if json_path and os.path.exists(json_path):
                try:
                    with open(json_path, 'r') as f:
                        json_data = json.load(f)
                    self.app.log_message(f"[FILE] Loaded JSON data from: {os.path.basename(json_path)}")
                except Exception as e:
                    self.app.log_message(f"[WARN] Could not load JSON file: {e}")
            
            if not json_data:
                enhanced_routes = []
                
                for route_result in all_route_results:
                    route_data = {
                        'route_id': route_result.get('route_id', 'Unknown Route'),
                        'best_chromosome': route_result.get('best_chromosome', []),
                        'mandatory_breakpoints': route_result.get('mandatory_breakpoints', []),
                        'best_fitness': route_result.get('best_fitness', 0.0),
                        'fitness_history': route_result.get('fitness_history', [])
                    }
                    
                    # Augment multi-objective routes with Pareto data; single/constrained share the same structure.
                    method_config = get_optimization_method(method_key)
                    if method_config and method_config.return_type == 'multi_objective':
                        route_data.update({
                            'pareto_front': route_result.get('pareto_front', []),
                            'pareto_chromosomes': route_result.get('pareto_chromosomes', []),
                            'pareto_fitness_vals': route_result.get('pareto_fitness_vals', [])
                        })
                    
                    enhanced_routes.append(route_data)
                
                json_data = {
                    'optimization_metadata': {
                        'method': method_key,
                        'total_routes': len(all_route_results),
                        'generations': (
                            (all_route_results[0].get('input_parameters') or {}).get('num_generations')
                            if all_route_results
                            else None
                        ),
                        'timestamp': datetime.now().isoformat(),
                        'multi_route': True
                    },
                    'routes': enhanced_routes
                }
            
            viz_window = show_enhanced_visualization(
                parent_app=self.app,
                json_results_path=json_path,
                json_results_data=json_data
            )
            
            if viz_window:
                self.app.log_message("[SUCCESS] Multi-route visualization opened successfully!")
            else:
                self.app.log_message("[ERROR] Multi-route visualization failed to open")
                
        except ImportError as e:
            self.app.log_message(f"[ERROR] Error importing visualization UI: {str(e)}")
        except Exception as e:
            self.app.log_message(f"[ERROR] Error showing multi-route visualization: {str(e)}")

    def _prepare_multi_route_analyses(self, original_data, route_column, selected_routes, x_column, y_column, gap_threshold=0.5, is_single_route_mode=False):
        """
        Pre-analyze all selected routes to create RouteAnalysis objects.
        
        This separates route preparation from optimization execution for better architecture:
        - Early error detection for route analysis issues
        - Better progress reporting  
        - Clean separation of concerns
        
        Args:
            original_data: Original RouteAnalysis object (contains all routes mixed)
            route_column: Name of the route column (None for single-route mode)
            selected_routes: List of route IDs to process
            x_column: X-axis column name
            y_column: Y-axis column name
            is_single_route_mode: If True, treat entire dataset as single route
            
        Returns:
            List[Tuple[str, RouteAnalysis]]: List of (route_id, route_analysis) tuples
            Returns empty list if no routes could be analyzed successfully
        """
        from data_loader import filter_data_by_route, analyze_route_gaps
        
        prepared_routes = []
        self.app.log_message("Preparing route analyses...")
        
        for route_idx, route_id in enumerate(selected_routes, 1):
            try:
                self.app.log_message(f"Analyzing Route {route_id} ({route_idx}/{len(selected_routes)})...")
                
                if is_single_route_mode:
                    route_data_df = original_data.route_data.copy()
                else:
                    route_data_df = filter_data_by_route(original_data.route_data, route_column, route_id)

                if len(route_data_df) < 3:
                    self.app.log_message(f"Warning: Route {route_id} has insufficient data ({len(route_data_df)} points), skipping...")
                    continue
                
                # Sort within this route only — mixing rows across routes corrupts gap detection.
                route_data_df = route_data_df.sort_values(x_column).reset_index(drop=True)

                route_analysis = analyze_route_gaps(
                    route_data_df, 
                    x_column, 
                    y_column, 
                    route_id=route_id,
                    gap_threshold=gap_threshold,
                    must_break_columns=getattr(self.app, 'must_break_columns', None),
                )
                
                self.app.log_message(f"Route {route_id}: {len(route_data_df)} points, "
                                   f"{len(route_analysis.gap_segments)} gaps, "
                                   f"{len(route_analysis.mandatory_breakpoints)} mandatory breakpoints")
                
                prepared_routes.append((route_id, route_analysis))
                
            except Exception as e:
                self.app.log_message(f"Error analyzing route {route_id}: {str(e)}")
                # Continue with other routes instead of failing completely
                continue
        
        if prepared_routes:
            self.app.log_message(f"Route analysis completed: {len(prepared_routes)}/{len(selected_routes)} routes ready for optimization")
        else:
            self.app.log_message("ERROR: No routes could be analyzed successfully")
        
        return prepared_routes
    
    def get_optimization_status(self):
        """Get current optimization status information."""
        return {
            'is_running': self.app.is_running,
            'stop_requested': self.app.stop_requested,
            'thread_alive': self.optimization_thread is not None and self.optimization_thread.is_alive()
        }