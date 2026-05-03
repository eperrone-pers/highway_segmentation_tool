"""
Optimization Controller Module for Highway Segmentation GA

This module handles the execution and control of optimization processes,
including threading, progress monitoring, and result handling, separating
these concerns from the main GUI class.
"""

import threading
import time
import os
import json
from datetime import datetime
from tkinter import messagebox
from config import get_optimization_method, resolve_method_class


def _normalize_route_value(route_value):
    """Normalize route identifiers to a stable string form for comparisons."""
    if route_value is None:
        return None
    route_str = str(route_value).strip()
    if not route_str:
        return None
    # Handle common missing-value string forms (e.g., from pandas/numpy)
    if route_str.lower() in {"nan", "none", "null"}:
        return None
    return route_str


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
        """
        Prepare and validate filename from user input with overwrite protection.
        
        This method handles filename preparation for optimization results,
        ensuring proper file extension, path resolution, and user confirmation
        for overwrite scenarios. Focused on JSON output format.
        
        Process:
            1. Validate and clean user input filename
            2. Ensure .json extension for consistency  
            3. Resolve full file path using configured save directory
            4. Check for existing files and prompt user for overwrite
            5. Return validated path or None if user cancels
        
        Args:
            custom_name (str): User-provided filename (with or without extension)
            
        Returns:
            str or None: Full path for saving, or None if user cancels overwrite
            
        File Handling:
            - Automatic .json extension addition if missing
            - Path resolution through file manager configuration
            - Overwrite protection with user confirmation dialog
            - Robust error handling for filesystem operations
        """
        if not custom_name:
            return None
        
        # Ensure .json extension
        if not custom_name.lower().endswith('.json'):
            json_filename = f"{custom_name}.json"
        else:
            json_filename = custom_name
        
        # Get full path
        save_path = self.app.file_manager.get_save_file_path()
        if save_path:
            save_dir = os.path.dirname(save_path)
            full_path = os.path.join(save_dir, json_filename)
        else:
            full_path = json_filename
        
        # Check for existing JSON file and warn user
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
        """
        Initialize and start the optimization process with comprehensive validation.
        
        This method serves as the main entry point for optimization execution,
        handling data validation, parameter preparation, thread management,
        and error recovery. Provides robust error handling and user feedback
        throughout the optimization pipeline.
        
        Pre-Optimization Validation:
            1. Data availability check with auto-loading fallback
            2. Route selection validation and processing
            3. Parameter validation and constraint checking
            4. UI state preparation for optimization
        
        Thread Management:
            - Creates separate thread for optimization calculation
            - Maintains responsive UI during long optimization runs
            - Provides progress feedback and cancellation capability
            - Handles thread cleanup and error recovery
            
        Error Handling:
            - Data loading failures with user notification
            - Parameter validation errors with specific feedback
            - Thread execution errors with graceful recovery
            - UI state restoration on failures
            
        User Experience:
            - Clear status messages throughout process
            - Progress indicators and time estimates
            - Cancellation capability during execution
            - Result presentation and saving options
        """
        # Check if data is loaded, if not try to auto-load from configured path
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
        
        # Validate parameters first
        if not self.app.parameter_manager.validate_and_show_errors():
            return
        
        # Check if already running
        if self.app.is_running:
            messagebox.showwarning("Already Running", "Optimization is already in progress.")
            return
        
        # Update UI state
        self.app.is_running = True
        self.app.stop_requested = False
        
        if hasattr(self.app, 'start_button'):
            self.app.start_button.config(state="disabled")
        if hasattr(self.app, 'stop_button'):
            self.app.stop_button.config(state="normal")
        
        # Clear previous results
        if hasattr(self.app, 'results_text'):
            self.app.results_text.delete(1.0, 'end')
        
        # Switch to optimization log tab
        if hasattr(self.app, 'results_notebook'):
            self.app.results_notebook.select(0)  # Select Optimization Log tab
        
        # Start optimization in separate thread
        self.optimization_thread = threading.Thread(target=self._run_optimization_worker, daemon=True)
        self.optimization_thread.start()
    
    def stop_optimization(self):
        """Request optimization to stop and wait for proper cleanup."""
        if self.app.is_running:
            self.app.stop_requested = True
            self.app.log_message("Stop requested - optimization will halt after current generation...")
            
            if hasattr(self.app, 'stop_button'):
                self.app.stop_button.config(text="Stopping...", state="disabled")
                
            # Proper thread cleanup - wait for thread to finish naturally
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
            # Record start time for elapsed time calculation
            self._optimization_start_time = time.time()
            
            # Get parameters
            params = self.app.parameter_manager.get_optimization_parameters()
            method_key = params['optimization_method']  # This is already a method key, not a display name

            # Get method configuration
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
            
            # UNIFIED ROUTE PROCESSING: Always use route-based processing
            # Determine actual route column name (user-selected or created from filename)
            route_column = self.app.route_column.get() if hasattr(self.app, 'route_column') else None
            
            if (route_column and 
                route_column != "None - treat as single route" and
                route_column in self.app.data.route_data.columns):
                # User selected specific route column that exists
                actual_route_column = route_column
                is_single_route_mode = False
            else:
                # Default to single route mode (covers "None - treat as single route" and unselected cases)
                actual_route_column = None
                is_single_route_mode = True
            
            # Handle route detection based on mode
            if is_single_route_mode:
                # Single route: create synthetic route identifier
                filename = os.path.basename(self.app.file_manager.get_data_file_path() or "unknown.csv")
                route_name = filename.replace('.csv', '').replace('.xlsx', '')
                all_routes = [route_name]
            else:
                # Multi-route: get unique values from route column
                if actual_route_column in self.app.data.route_data.columns:
                    unique_routes = self.app.data.route_data[actual_route_column].unique()
                    normalized_routes = []
                    for route in unique_routes:
                        route_str = _normalize_route_value(route)
                        if route_str is None:
                            continue
                        # Filter out internal/sentinel route IDs (case-insensitive)
                        if route_str.lower() in {"default", "_combined_data_"}:
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

            # Normalize selected routes to string form to match all_routes
            selected_routes = [r for r in (_normalize_route_value(r) for r in selected_routes) if r is not None]

            # Filter to only routes that actually exist in the data
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
            
            # UNIFIED: Always use route analysis preparation 
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
            
            # Get common parameters
            data = self.app.data
            x_column = self.app.x_column.get()
            y_column = self.app.y_column.get()
            # Note: All other parameters are now passed directly to methods via params dict
            
            # Import new analysis methods
            from analysis.methods.single_objective import SingleObjectiveMethod
            
            # PHASE 1B: Collect results from all routes for consolidated saving
            all_route_results = []
            
            # UNIFIED: Process all prepared routes (always have route IDs now)
            total_routes = len(prepared_routes)
            for route_idx, (route_id, route_data) in enumerate(prepared_routes, 1):
                if self.app.stop_requested:
                    self.app.log_message("Optimization stopped by user request")
                    break
                
                # Unified progress logging (always have route ID)
                if total_routes > 1:
                    self.app.log_message(f"Processing Route {route_id} ({route_idx}/{total_routes})...")
                else:
                    self.app.log_message(f"Processing Route {route_id}...")
                
                # Process this route with the current optimization method
                result = self._run_single_route_optimization(
                    route_data, method_config, method_key, params,
                    x_column, y_column, min_length, max_length, gap_threshold,
                    route_id, route_idx, total_routes
                )
                
                # PHASE 1B: Collect results instead of saving immediately
                if result:
                    all_route_results.append(result)
                    self.app.log_message(f"Route {route_id} completed successfully")
                else:
                    self.app.log_message(f"Route {route_id} failed to produce results")
            
            # PHASE 1B: Save consolidated results from all routes
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
            # Log route-specific start information (unified - always have route_id)
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

            # Convert AnalysisResult to legacy dict format for compatibility (generic adapter)
            best_solution = analysis_result.best_solution
            input_parameters = analysis_result.input_parameters or {}

            def _get_numeric(value, default=0.0):
                if isinstance(value, (int, float)):
                    return value
                if isinstance(value, list) and value and isinstance(value[0], (int, float)):
                    return value[0]
                return default

            # Base fields expected across the app
            result = {
                'route_id': route_id,
                'method_key': method_key,
                'best_fitness': _get_numeric(best_solution.get('deviation_fitness', best_solution.get('fitness', 0.0))),
                'objective_values': best_solution.get('objective_values', [best_solution.get('fitness', 0.0)]),
                'best_chromosome': best_solution.get('chromosome', []),
                'avg_segment_length': best_solution.get('avg_segment_length', 0.0),
                'execution_time': analysis_result.processing_time,
                'mandatory_breakpoints': analysis_result.mandatory_breakpoints,

                # Preserve data analysis information (generic to all methods)
                'data_summary': analysis_result.data_summary,
                'input_parameters': input_parameters,

                # Keep full optimization_stats for method-specific JSON extraction
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

            # Preserve Pareto front if this is a multi-objective method
            if getattr(method_config, 'return_type', None) == 'multi_objective':
                result['all_solutions'] = analysis_result.all_solutions
                result['pareto_front_size'] = analysis_result.optimization_stats.get(
                    'pareto_front_size', len(analysis_result.all_solutions)
                )
                result['best_deviation_fitness'] = analysis_result.optimization_stats.get('best_deviation_fitness')
                result['best_segment_count'] = analysis_result.optimization_stats.get('best_segment_count')

            # Preserve constrained method fields if present
            if 'unconstrained_fitness' in best_solution:
                result['best_unconstrained_fitness'] = best_solution.get('unconstrained_fitness', 0.0)
            if 'length_deviation' in best_solution:
                result['length_deviation'] = best_solution.get('length_deviation', 0.0)
            if 'target_avg_length' in input_parameters:
                result['target_avg_length'] = input_parameters.get('target_avg_length')
            if 'length_tolerance' in input_parameters:
                result['tolerance'] = input_parameters.get('length_tolerance')

            # Preserve history series if present (used by summaries and optional UI)
            if 'best_fitness_history' in analysis_result.optimization_stats:
                result['fitness_history'] = analysis_result.optimization_stats.get('best_fitness_history', [])
            if 'avg_length_history' in analysis_result.optimization_stats:
                result['length_history'] = analysis_result.optimization_stats.get('avg_length_history', [])

            # Provide AASHTO CDA metadata if the expected statistical fields exist
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
        
        # Update button states
        if hasattr(self.app, 'start_button'):
            self.app.start_button.config(state="normal")
        if hasattr(self.app, 'stop_button'):
            self.app.stop_button.config(text="⏹ Stop", state="disabled")
        
        # Log completion
        if stopped_early:
            self.app.log_message("Optimization stopped by user.")
        else:
            self.app.log_message("Optimization completed.")
    
    def _save_consolidated_results(self, all_route_results, method_key, params):
        """
        PHASE 1B: Save consolidated results from all routes using ExtensibleJsonResultsManager.
        
        Args:
            all_route_results: List of result dictionaries from all processed routes
            method_key: Optimization method ('single', 'constrained', 'multi')  
            params: Optimization parameters dictionary
            
        Returns:
            str: JSON file path if successful, None if failed
        """
        try:
            self.app.log_message(f"Saving consolidated results from {len(all_route_results)} route(s)...")
            
            # Prepare filename - use user's exact name for consolidated results
            save_name = self.app.custom_save_name.get()
            output_path = self._prepare_save_filename(save_name)

            # User may cancel overwrite prompt or provide invalid name
            if not output_path:
                self.app.log_message("Save cancelled - no output path selected")
                return None
            
            # Convert to JSON path
            if output_path.endswith('.csv'):
                json_path = output_path.replace('.csv', '.json')
            elif output_path.endswith('.json'):
                json_path = output_path
            else:
                json_path = f"{output_path}.json"
            
            # Use ExtensibleJsonResultsManager directly (no legacy results_manager)
            from extensible_results_manager import ExtensibleJsonResultsManager
            from analysis.base import AnalysisResult
            
            # Get ACTUAL column names from GUI (not hardcoded defaults)
            actual_x_column = self.app.x_column.get()
            actual_y_column = self.app.y_column.get()
            actual_route_column = self.app.route_column.get() if hasattr(self.app, 'route_column') else None
            actual_data_file = self.app.file_manager.get_data_file_path()
            
            self.app.log_message(f"📊 Actual columns: X='{actual_x_column}', Y='{actual_y_column}', Route='{actual_route_column}'")
            self.app.log_message(f"📁 Actual data file: {actual_data_file}")
            
            # Convert legacy result format to AnalysisResult objects
            analysis_results = []
            
            # Get method configuration dynamically (no hardcoding!)
            method_config = get_optimization_method(method_key)
            if not method_config:
                raise ValueError(f"Unknown optimization method: {method_key}")
            
            # Use dynamic values from config
            method_display_name = method_config.display_name  # Dynamic display name
            analysis_method = method_config.method_key        # Dynamic method key
            
            for route_result in all_route_results:
                # For multi-objective, ensure we preserve the full Pareto front
                if method_key == 'multi' and route_result.get('all_solutions'):
                    # Multi-objective: use the full Pareto front as all_solutions
                    all_solutions = route_result.get('all_solutions')
                else:
                    # Single-objective/constrained: use single best solution format
                    all_solutions = [{
                        'chromosome': route_result.get('best_chromosome', []),
                        'fitness': route_result.get('best_fitness'),
                        'segments': route_result.get('segments_data', []),
                        'total_length': route_result.get('total_length', 0)
                    }]
                
                result = AnalysisResult(
                    method_name=method_display_name,  # Dynamic from config!
                    method_key=analysis_method,
                    route_id=route_result.get('route_id', 'unknown'),
                    processing_time=route_result.get('execution_time', route_result.get('processing_time', 0)),
                    timestamp=route_result.get('timestamp', datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
                    analysis_version="1.95.2",
                    
                    # All solutions (full Pareto front for multi-objective)
                    all_solutions=all_solutions,
                    
                    # Optimization metadata
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
            
            # Create ExtensibleJsonResultsManager
            manager = ExtensibleJsonResultsManager()
            
            # Prepare CORRECT input file info (schema compliant)
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
            if route_col_requested == "None - treat as single route":
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
            
            # Prepare CORRECT route processing info (using actual GUI values)
            route_processing_config = {
                'route_mode': 'multi_route' if len(all_route_results) > 1 else 'single_route',
                'selected_routes': [result.get('route_id') for result in all_route_results],
                'x_column': actual_x_column,  # ACTUAL column name from GUI
                'y_column': actual_y_column,  # ACTUAL column name from GUI 
                'route_column': (
                    route_col_requested
                    if (route_col_requested and route_col_requested in in_memory_columns and route_col_requested != 'route')
                    else None
                ),
                # Include only route processing relevant parameters
                'route_filtering_applied': len(all_route_results) > 1,
                'total_routes_in_source': len(all_route_results), # Will be updated by caller if needed
                'total_routes_processed': len(all_route_results),
                'custom_save_name': params.get('custom_save_name')
            }
            
            # Save with ExtensibleJsonResultsManager
            json_output_path = manager.save_analysis_results(
                analysis_results,
                json_path,
                input_file_info=input_file_info,
                route_processing_info=route_processing_config,
                original_data_by_route=self._build_original_data_by_route(analysis_results)
            )
            
            self.app.log_message(f"✅ JSON results saved with CORRECT column info: {json_output_path}")
            self.app.log_message(f"✅ Column mapping: X='{actual_x_column}', Y='{actual_y_column}'")

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
            route_column = self.app.route_column.get() if hasattr(self.app, 'route_column') else None
            
            for result in analysis_results:
                route_id = result.route_id
                
                try:
                    if route_column and route_column != "None - treat as single route":
                        # Multi-route: filter by route ID
                        route_df = filter_data_by_route(self.app.data.route_data, route_column, route_id)
                    else:
                        # Single route: use all data
                        route_df = self.app.data.route_data.copy()
                    
                    if not route_df.empty:
                        original_data_by_route[route_id] = route_df
                    
                except Exception as e:
                    self.app.log_message(f"Warning: Could not extract data for route {route_id}: {e}")
                    continue
            
            self.app.log_message(f"✅ Built original data for {len(original_data_by_route)} route(s)")
            return original_data_by_route
            
        except Exception as e:
            self.app.log_message(f"Warning: Could not build original data by route: {e}")
            return {}
    
    def is_optimization_running(self):
        """Check if optimization is currently running."""
        return self.app.is_running and (self.optimization_thread is not None and self.optimization_thread.is_alive())
    
    def _show_enhanced_multi_route_visualization(self, json_path, all_route_results, method_key):
        """Show enhanced visualization for multi-route optimization results."""
        try:

            
            from enhanced_visualization import show_enhanced_visualization
            
            # Load JSON data if available, otherwise create from route results
            json_data = None
            if json_path and os.path.exists(json_path):
                try:
                    with open(json_path, 'r') as f:
                        json_data = json.load(f)
                    self.app.log_message(f"[FILE] Loaded JSON data from: {os.path.basename(json_path)}")
                except Exception as e:
                    self.app.log_message(f"[WARN] Could not load JSON file: {e}")
            
            # Create enhanced results data structure if no JSON or loading failed
            if not json_data:
                self.app.log_message("[DATA] Creating enhanced results from route data...")
                enhanced_routes = []
                
                for route_result in all_route_results:
                    route_data = {
                        'route_id': route_result.get('route_id', 'Unknown Route'),
                        'best_chromosome': route_result.get('best_chromosome', []),
                        'mandatory_breakpoints': route_result.get('mandatory_breakpoints', []),
                        'best_fitness': route_result.get('best_fitness', 0.0),
                        'fitness_history': route_result.get('fitness_history', [])
                    }
                    
                    # Add method-specific data based on return_type ONLY - no hardcoded method names
                    method_config = get_optimization_method(method_key)
                    if method_config and method_config.return_type == 'multi_objective':
                        route_data.update({
                            'pareto_front': route_result.get('pareto_front', []),
                            'pareto_chromosomes': route_result.get('pareto_chromosomes', []),
                            'pareto_fitness_vals': route_result.get('pareto_fitness_vals', [])
                        })
                    # Single-objective methods (single, constrained) are treated identically
                    # No method-specific data needed - they all have the same visualization structure
                    
                    enhanced_routes.append(route_data)
                
                json_data = {
                    'optimization_metadata': {
                        'method': method_key,
                        'total_routes': len(all_route_results),
                        'generations': params.get('num_generations'),
                        'timestamp': datetime.now().isoformat(),
                        'multi_route': True
                    },
                    'routes': enhanced_routes
                }
            
            # Show enhanced visualization
            viz_window = show_enhanced_visualization(
                parent_app=self.app,
                json_results_path=json_path,
                json_results_data=json_data
            )
            
            if viz_window:
                self.app.log_message("[SUCCESS] Enhanced multi-route visualization opened successfully!")
            else:
                self.app.log_message("[ERROR] Enhanced multi-route visualization failed to open")
                
        except ImportError as e:
            self.app.log_message(f"[ERROR] Error importing enhanced visualization: {str(e)}")
        except Exception as e:
            self.app.log_message(f"[ERROR] Error showing enhanced multi-route visualization: {str(e)}")

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
                    # Single route mode: use entire dataset
                    route_data_df = original_data.route_data.copy()
                else:
                    # Multi-route mode: filter data for this specific route  
                    route_data_df = filter_data_by_route(original_data.route_data, route_column, route_id)
                
                # Validate sufficient data
                if len(route_data_df) < 3:
                    self.app.log_message(f"Warning: Route {route_id} has insufficient data ({len(route_data_df)} points), skipping...")
                    continue
                
                # CRITICAL: Sort by X column within this route only (not mixed with other routes)
                route_data_df = route_data_df.sort_values(x_column).reset_index(drop=True)
                
                # Create proper RouteAnalysis object for THIS ROUTE ONLY
                # This ensures correct gap detection, mandatory breakpoints, etc.
                route_analysis = analyze_route_gaps(
                    route_data_df, 
                    x_column, 
                    y_column, 
                    route_id=route_id,
                    gap_threshold=gap_threshold,
                )
                
                # Log analysis results
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