"""Optimization execution, threading, and result collection for the GUI.

Separates optimization concerns (thread lifecycle, route processing, file saving)
from the main GUI class.
"""

from __future__ import annotations

import threading
import time
import os
import json
from dataclasses import asdict, replace as dataclass_replace
from datetime import datetime
from tkinter import messagebox
from config import get_optimization_method, resolve_method_class
from optimization_handler import OptimizationHandler
from optimization_results_saver import OptimizationResultsSaver
from route_utils import (
    list_routes,
    normalize_route_column_selection,
    normalize_route_id,
    prepare_routes_for_optimization,
)


class OptimizationController:
    """
    Handles optimization execution, control, and monitoring.
    
    This class manages the optimization workflow including parameter preparation,
    thread execution, progress monitoring, result handling, and cleanup operations.
    """
    
    def __init__(self, main_app: OptimizationHandler):
        """
        Initialize the optimization controller with a reference to the main application.

        Args:
            main_app: Any object that satisfies the OptimizationHandler protocol
                (HighwaySegmentationGUI in the GUI path; a compatible stub in tests).
        """
        self.app = main_app
        self.optimization_thread = None
        self.is_running = False
        self._optimization_start_time = None
        self.preprocessed_data_by_route = {}  # Store preprocessed route data for accurate segment statistics

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

    def start_optimization(self):
        """Validate inputs and launch the optimization worker thread.

        Checks data availability (auto-loading if a path is configured), validates
        parameters, updates UI state, and starts a daemon thread for the run.
        """
        if self.app.data is None:
            data_path = self.app.file_manager.get_data_file_path()
            active_source = getattr(self.app, '_active_data_source', None)
            if data_path and os.path.exists(data_path):
                self.app.log_message("No data loaded — auto-loading from configured file...")
                try:
                    self.app.load_data_file()
                    if self.app.data is None:
                        messagebox.showerror("Data Required", "Could not load data from the configured file. Please load data first.")
                        return
                except Exception as e:
                    messagebox.showerror("Data Loading Error", f"Could not load data from configured file:\n{str(e)}")
                    return
            elif active_source is not None:
                self.app.log_message("No data loaded — auto-loading from active database connection...")
                try:
                    self.app.load_from_active_source()
                    if self.app.data is None:
                        messagebox.showerror("Data Required", "Could not load data from the database connection. Check column selections and try again.")
                        return
                except Exception as e:
                    messagebox.showerror("Data Loading Error", f"Could not load data from database:\n{str(e)}")
                    return
            else:
                messagebox.showerror("Data Required", "No data is loaded. Use 'Connect / Open' to load a CSV file or connect to a database.")
                return
        
        if not self.app.parameter_manager.validate_and_show_errors():
            return

        if self.app.is_running:
            messagebox.showwarning("Already Running", "Optimization is already in progress.")
            return
        
        self.app.is_running = True
        self.app.stop_requested = False
        self.app.on_optimization_started()

        self.optimization_thread = threading.Thread(target=self._run_optimization_worker, daemon=True)
        self.optimization_thread.start()
    
    def stop_optimization(self):
        """Request optimization to stop and wait for proper cleanup."""
        if self.app.is_running:
            self.app.stop_requested = True
            self.app.log_message("Stop requested - optimization will halt after current generation...")
            
            self.app.on_stop_requested()

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
        """Entry point for the daemon thread started by ``start_optimization``.

        Owns the full optimization lifecycle on the worker thread:

        1. Reads parameters and resolves the route list from ``self.app``.
        2. Calls ``_prepare_multi_route_analyses`` to build per-route
           ``RouteAnalysis`` objects (gap detection, mandatory breakpoints).
        3. Iterates routes, calling ``_run_single_route_optimization`` for each.
           Checks ``self.app.stop_requested`` between routes — this is the
           cooperative cancellation point; no mid-generation forced abort occurs.
        4. On completion (or partial completion), saves consolidated results via
           ``_save_consolidated_results`` if a save name is set, then schedules
           ``_show_enhanced_multi_route_visualization`` on the main thread via
           ``root.after(0, ...)``.
        5. Any unhandled exception is caught and routed to ``app.handle_error``
           (or a fallback ``messagebox``).
        6. The ``finally`` block always calls ``_finalize_optimization`` via
           ``root.after(0, ...)`` to restore UI state (buttons, flags) on the
           main thread regardless of success or failure.

        Does not return a value. Results are communicated through the sequence
        of ``log_message`` calls and the scheduled visualization callback.
        """
        try:
            self._optimization_start_time = time.time()

            params = self.app.parameter_manager.get_optimization_parameters()
            method_key = params['optimization_method']

            method_config = get_optimization_method(method_key)

            # Framework-level gap threshold (single source of truth: app.gap_threshold)
            gap_threshold = float(self.app.gap_threshold.get())
            if gap_threshold <= 0:
                raise ValueError(f"gap_threshold must be > 0 (got {gap_threshold})")

            # Segment length bounds are method-specific (may be absent for non-GA methods)
            min_length = params.get('min_length', None)
            max_length = params.get('max_length', None)
            
            routes_to_process, local_data, actual_route_column, is_single_route_mode = self._resolve_routes()

            self.app.log_message(f"Starting optimization for {len(routes_to_process)} route(s)...")
            if len(routes_to_process) > 1:
                self.app.log_message(f"Route column: {actual_route_column}")
                self.app.log_message(f"Routes to process: {', '.join(routes_to_process)}")
            else:
                self.app.log_message(f"Processing single route: {routes_to_process[0]}")

            preprocessing_config = self._assemble_preprocessing_config()
            
            prepared_routes, self.preprocessed_data_by_route = prepare_routes_for_optimization(
                local_data,
                actual_route_column,
                routes_to_process,
                self.app.x_column.get(),
                self.app.y_column.get(),
                gap_threshold=gap_threshold,
                is_single_route_mode=is_single_route_mode,
                preprocessing_config=preprocessing_config,
                must_break_columns=getattr(self.app, 'must_break_columns', None),
                secondary_break_columns=getattr(self.app, 'secondary_break_columns', None),
                log_callback=self.app.log_message,
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
            for route_idx, (route_id, route_data, preprocessing_results) in enumerate(prepared_routes, 1):
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
                    route_id, route_idx, total_routes, preprocessing_results
                )
                
                if result:
                    all_route_results.append(result)
                    self.app.log_message(f"Route {route_id} completed successfully")
                else:
                    self.app.log_message(f"Route {route_id} failed to produce results")
            
            if all_route_results and not self.app.stop_requested:
                if self.app.custom_save_name.get():
                    saver = OptimizationResultsSaver(self.app)
                    json_path = saver.save(all_route_results, method_key, params, self.preprocessed_data_by_route)
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

    def _resolve_routes(self):
        """Determine which routes to process for the current optimization run.

        Reads route column and selection state from the GUI, validates the selected
        route column, filters out records with missing/invalid route IDs, and
        intersects the full route list with the user's explicit selection.

        Returns:
            Tuple of (routes_to_process, local_data, actual_route_column, is_single_route_mode):
                - routes_to_process: Validated, ordered list of route IDs to analyze.
                - local_data: Thread-local data snapshot; either self.app.data or a
                  filtered copy with invalid-route-ID rows removed.
                - actual_route_column: Name of the active route column, or None in
                  single-route mode.
                - is_single_route_mode: True when no route column is in use.

        Raises:
            ValueError: If no valid routes can be determined (all records missing,
                no selection, or no selected routes match the data).
        """
        route_column_raw = self.app.route_column.get() if hasattr(self.app, 'route_column') else None
        route_column = normalize_route_column_selection(route_column_raw)

        if route_column and route_column in self.app.data.route_data.columns:
            actual_route_column = route_column
            is_single_route_mode = False
        else:
            # Default to single route mode (covers ROUTE_COLUMN_NONE_SENTINEL and unselected cases)
            actual_route_column = None
            is_single_route_mode = True

        # local_data is used for this run only — self.app.data is never mutated so the
        # main thread's view of the loaded dataset stays intact across multiple runs.
        local_data = self.app.data

        if is_single_route_mode:
            data_path = self.app.file_manager.get_data_file_path()
            if data_path:
                route_name = os.path.basename(data_path).replace('.csv', '').replace('.xlsx', '')
            else:
                active_source = getattr(self.app, '_active_data_source', None)
                route_name = (
                    getattr(active_source, '_config', None) and active_source._config.table_or_view
                    or (active_source.display_name if active_source else "data")
                )
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
                        local_data = dataclass_replace(self.app.data, route_data=filtered)
                except Exception:
                    # If normalization/filtering fails for unexpected reasons, treat as fatal.
                    raise

                all_routes = list_routes(local_data.route_data, actual_route_column)
            else:
                raise ValueError(
                    f"Route column '{actual_route_column}' not found in data. "
                    "Re-load the file or select a different route column."
                )

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

        return routes_to_process, local_data, actual_route_column, is_single_route_mode

    def _assemble_preprocessing_config(self):
        """Build preprocessing configuration from the current GUI panel state.

        Reads the three preprocessing panels (pre-gap, primary, secondary) and
        assembles a PreprocessingRunConfig. Panels that are absent or have no method
        selected contribute None / empty-dict for their respective slot.

        Returns:
            PreprocessingRunConfig populated from current GUI state.
        """
        from config import PreprocessingRunConfig
        preprocessing_config = PreprocessingRunConfig(
            pre_gap_method=None,
            pre_gap_parameters={},
            primary_method=None,
            primary_parameters={},
            secondary_method=None,
            secondary_parameters={}
        )

        if hasattr(self.app, 'pregap_preprocess_panel') and self.app.pregap_preprocess_panel:
            try:
                pre_gap_method_key = self.app.pregap_preprocess_panel.get_method_key()
                if pre_gap_method_key:
                    preprocessing_config.pre_gap_method = pre_gap_method_key
                    preprocessing_config.pre_gap_parameters = self.app.pregap_preprocess_panel.get_parameters()
                    self.app.log_message(f"Pre-gap preprocessing enabled: {pre_gap_method_key}")
            except Exception as e:
                self.app.log_message(f"Warning: Could not load pre-gap preprocessing config: {e}")

        if hasattr(self.app, 'primary_preprocess_panel') and self.app.primary_preprocess_panel:
            try:
                primary_method_key = self.app.primary_preprocess_panel.get_method_key()
                if primary_method_key:
                    preprocessing_config.primary_method = primary_method_key
                    preprocessing_config.primary_parameters = self.app.primary_preprocess_panel.get_parameters()
                    self.app.log_message(f"Primary preprocessing enabled: {primary_method_key}")
            except Exception as e:
                self.app.log_message(f"Warning: Could not load primary preprocessing config: {e}")

        if hasattr(self.app, 'secondary_preprocess_panel') and self.app.secondary_preprocess_panel:
            try:
                secondary_method_key = self.app.secondary_preprocess_panel.get_method_key()
                if secondary_method_key:
                    preprocessing_config.secondary_method = secondary_method_key
                    preprocessing_config.secondary_parameters = self.app.secondary_preprocess_panel.get_parameters()
                    self.app.log_message(f"Secondary preprocessing enabled: {secondary_method_key}")
            except Exception as e:
                self.app.log_message(f"Warning: Could not load secondary preprocessing config: {e}")

        return preprocessing_config

    def _run_single_route_optimization(self, data, method_config, method_key, params,
                                     x_column, y_column, min_length, max_length, gap_threshold,
                                     route_id, route_idx=1, total_routes=1, preprocessing_results=None):
        """Run the configured analysis method for one route and return a result dict.

        Resolves the method class from ``method_key``, strips framework-level keys
        (``gap_threshold``, ``log_callback``, ``stop_callback``, ``input_parameters``)
        from ``params`` before passing them as keyword arguments, then injects the
        live GUI callbacks so the method can log and honour stop requests.

        Args:
            data: ``RouteAnalysis`` object for this route (gap-aware, pre-sorted).
            method_config: ``OptimizationMethodConfig`` for the selected method.
            method_key: Short method identifier, e.g. ``"single"``, ``"multi"``,
                ``"constrained"``, ``"aashto_cda"``.
            params: Full parameter dict from ``parameter_manager``. Framework-level
                keys are stripped inside this method before forwarding.
            x_column: Column name for the x-axis (milepoint / distance).
            y_column: Column name for the y-axis (pavement metric).
            min_length: Minimum segment length from params (used for log messages only).
            max_length: Maximum segment length from params (used for log messages only).
            gap_threshold: Minimum gap distance that triggers a forced breakpoint.
            route_id: Unique identifier for this route.
            route_idx: 1-based position of this route in the processing sequence.
            total_routes: Total number of routes being processed in this run.

        Returns:
            A dict containing the route results on success, or ``None`` on failure.
            Common keys present for all methods:

            - ``route_id`` — route identifier
            - ``method_key`` — method used
            - ``best_fitness`` — scalar fitness of the best solution
            - ``best_chromosome`` — breakpoint list of the best solution
            - ``best_segments`` — segment count of the best solution
            - ``avg_segment_length`` — average segment length in miles
            - ``execution_time`` — wall-clock seconds for this route
            - ``mandatory_breakpoints`` — forced breakpoints from gap/attribute analysis
            - ``data_summary``, ``input_parameters``, ``optimization_stats`` — pass-through
              from the ``AnalysisResult``

            Additional keys for multi-objective runs:

            - ``all_solutions`` — full Pareto front solution list
            - ``pareto_front_size``, ``best_deviation_fitness``, ``best_segment_count``

            Additional keys for constrained runs:

            - ``best_unconstrained_fitness``, ``length_deviation``,
              ``target_avg_length``, ``tolerance``

            Additional keys for AASHTO CDA runs:

            - ``analysis_method``, ``statistical_parameters``, ``method_stats``
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

            # Enrich data_summary with attribute break analysis from RouteAnalysis
            if not analysis_result.data_summary:
                analysis_result.data_summary = {}
            
            # Import attribute break builders
            from data_loader import build_attribute_break_analysis, build_secondary_attribute_break_analysis
            
            # Add primary attribute break analysis if present
            attr_analysis = build_attribute_break_analysis(data)
            if attr_analysis:
                analysis_result.data_summary['attribute_break_analysis'] = attr_analysis
            
            # Add secondary attribute break analysis if present
            sec_attr_analysis = build_secondary_attribute_break_analysis(data)
            if sec_attr_analysis:
                analysis_result.data_summary['secondary_attribute_break_analysis'] = sec_attr_analysis
            
            # Attach preprocessing results if available (preprocessing_results is a list of PreprocessingResult objects)
            if preprocessing_results and isinstance(preprocessing_results, list) and len(preprocessing_results) > 0:
                for preproc_result in preprocessing_results:
                    # Extract metadata dict
                    if hasattr(preproc_result, 'preprocessing_metadata'):
                        analysis_result.preprocessing_metadata.append(preproc_result.preprocessing_metadata)
                    
                    # Extract summary string
                    if hasattr(preproc_result, 'modifications_summary'):
                        analysis_result.preprocessing_summary.append(preproc_result.modifications_summary)
                    
                    # Extract modification log (convert DataModification dataclass objects to dicts)
                    if hasattr(preproc_result, 'modification_log'):
                        mod_log_dicts = []
                        for mod in preproc_result.modification_log:
                            # DataModification is a dataclass, convert to dict
                            if hasattr(mod, '__dataclass_fields__'):
                                mod_log_dicts.append(asdict(mod))
                            elif isinstance(mod, dict):
                                mod_log_dicts.append(mod)
                        analysis_result.preprocessing_modification_log.append(mod_log_dicts)

            return analysis_result.to_route_result_dict()
            
        except Exception as e:
            if route_id:
                self.app.log_message(f"Route {route_id}: Optimization error: {str(e)}")
            else:
                self.app.log_message(f"Optimization error: {str(e)}")
            return None
    
    def _finalize_optimization(self, stopped_early=False):
        """Reset UI state after optimization completes or is stopped.

        Always called on the **main thread** via ``root.after(0, ...)`` from the
        worker thread's ``finally`` block so that Tkinter widget updates are safe.
        Resets ``app.is_running`` and ``app.stop_requested``, re-enables the Start
        button, and restores the Stop button label and disabled state.

        Args:
            stopped_early: When ``True``, logs a "stopped by user" message instead
                of the normal "completed" message.
        """
        self.app.is_running = False
        self.app.stop_requested = False
        self.app.on_optimization_finished(stopped_early)
    
    def is_optimization_running(self):
        """Return ``True`` only when both the running flag is set and the thread is alive.

        Checking both conditions avoids false positives during the brief window
        between ``start_optimization`` setting ``app.is_running`` and the thread
        actually starting, or after the thread finishes but before
        ``_finalize_optimization`` clears the flag.
        """
        return self.app.is_running and (self.optimization_thread is not None and self.optimization_thread.is_alive())
    
    def _show_enhanced_multi_route_visualization(self, json_path, all_route_results, method_key):
        """Open the enhanced visualization window for the completed optimization run.

        Always called on the **main thread** via ``root.after(0, ...)`` from the
        worker thread.

        Prefers loading data from ``json_path`` (the saved results file) because
        it contains the fully schema-compliant structure including segment details
        and plugin statistics. When ``json_path`` is ``None`` or the file cannot be
        read, falls back to assembling a minimal ``json_data`` dict from the
        in-memory ``all_route_results`` list. The fallback dict lacks segment-level
        detail but is sufficient to render the Pareto front and segmentation overlay.

        Args:
            json_path: Path to the saved results JSON file, or ``None`` when results
                were not saved (no custom save name was set).
            all_route_results: List of per-route result dicts from
                ``_run_single_route_optimization``.
            method_key: Method identifier used to decide whether to include Pareto
                data in the fallback dict.
        """
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

    def get_optimization_status(self):
        """Return a snapshot of the current optimization state.

        Returns:
            Dict with keys:

            - ``is_running`` (bool) — ``app.is_running`` flag value
            - ``stop_requested`` (bool) — ``app.stop_requested`` flag value
            - ``thread_alive`` (bool) — whether the worker thread exists and is alive
        """
        return {
            'is_running': self.app.is_running,
            'stop_requested': self.app.stop_requested,
            'thread_alive': self.optimization_thread is not None and self.optimization_thread.is_alive()
        }