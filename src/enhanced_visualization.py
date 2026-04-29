"""
Enhanced Integrated Visualization for Highway Segmentation GA

This module provides an enhanced paned window visualization that integrates directly
with the main application, replacing separate matplotlib windows with a professional
unified interface featuring:

- Resizable horizontal panes with movable divider
- Type-ahead route dropdown selection  
- Navigation toolbars for each pane
- Labeled frames with professional appearance
- Integration with optimization results and original data

Features:
- Automatic opening after optimization completion
- JSON results integration with original CSV data
- Interactive route selection with immediate updates
- Independent pane navigation and zooming
- Professional appearance matching main application UI

Author: Eric (Mott MacDonald)  
Date: April 2026
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from logger import create_logger
import json
import os
from pathlib import Path
from datetime import datetime
from matplotlib.ticker import MaxNLocator, MultipleLocator
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

# Import configuration for axis transforms
try:
    from CONFIG import get_optimization_method
except ImportError:
    from config import get_optimization_method

# Pleasant color scheme - updated for better contrast
COLORS = {
    'original_data': '#D3D3D3',      # Light gray (better contrast)
    'original_edge': '#A9A9A9',      # Dark gray edges  
    'mandatory_bp': '#DC143C',       # Crimson (softer red)
    'analysis_bp': '#228B22',        # Forest green 
    'segment_avg': '#0066CC',        # Bolder blue (was dodger blue)
    'pareto_normal': '#4169E1',      # Royal blue
    'pareto_selected': '#DC2626',    # Pleasant red (softer than primary)
    'pareto_border': '#191970',      # Midnight blue
    'grid': '#E5E5E5',              # Very light gray
    'text_secondary': '#696969'      # Dim gray
}


class EnhancedVisualizationWindow:
    """Enhanced paned window visualization for optimization results."""
    
    def __init__(self, parent_app, json_results_data=None, original_data=None, 
                 x_column=None, y_column=None):
        """
        Initialize the enhanced visualization window.
        
        Args:
            parent_app: Reference to main application
            json_results_data: Results from JSON file after optimization 
            original_data: Original CSV data that was optimized
            x_column: Column name for x-axis (REQUIRED - no default)
            y_column: Column name for y-axis (REQUIRED - no default)
        """
        # Validate required column parameters - fail fast with clear errors
        if not x_column or not y_column:
            logger = create_logger()
            error_msg = f"Column mapping configuration is required but missing: x_column='{x_column}', y_column='{y_column}'"
            logger.log(f"EnhancedVisualizationWindow initialization failed: {error_msg}")
            raise ValueError(f"Invalid column configuration: {error_msg}")
        
        self.parent_app = parent_app
        self.json_results = json_results_data or {}
        self.original_data = original_data
        self.x_column = x_column
        self.y_column = y_column
        
        # Create new window
        try:
            self.window = tk.Toplevel(parent_app.root)
            self.window.title("Enhanced Highway Segmentation Visualization")
            self.window.geometry("1400x800")
            # Enhanced visualization window created
        except Exception as e:
            error_msg = "Failed to create enhanced visualization window"
            if hasattr(parent_app, 'handle_error'):
                parent_app.handle_error(error_msg, e, severity="critical", show_messagebox=True)
            raise RuntimeError(error_msg) from e
        
        # Initialize selection tracking
        self.selected_pareto_point = None
        self.pareto_scatter_plots = {}  # Track scatter plot objects for highlighting
        self.point_id_map = {}  # Map from matplotlib artist to point_id for fast picker events
        
        # Setup route data and selection
        self.setup_route_data()
        
        # Create enhanced UI
        self.create_enhanced_interface()
        
        # Initial plot update
        self.update_visualizations()
        
        # Focus the new window
        self.window.lift()
        self.window.focus_force()
        
        # Enhanced visualization initialization complete
        
    def setup_route_data(self):
        """Setup route information from available data."""
        self.routes = []
        
        # Extract routes from JSON results using the ACTUAL schema structure
        if self.json_results and 'route_results' in self.json_results:
            for route_result in self.json_results['route_results']:
                route_id = route_result.get('route_info', {}).get('route_id', 'Unknown')
                self.routes.append(route_id)
        
        # Extract routes from original data as backup
        if not self.routes and self.original_data is not None:
            # Get route column name from parent app if available
            route_column = None
            if hasattr(self.parent_app, 'route_column'):
                route_column = self.parent_app.route_column.get()
                if route_column == "None - treat as single route":
                    route_column = None
                    
            # Try to find a route column in the data
            if route_column and route_column in self.original_data.columns:
                unique_routes = list(self.original_data[route_column].unique())
                # Remove NaN values and convert to strings
                unique_routes = [str(route) for route in unique_routes if str(route) != 'nan']
                self.routes.extend(unique_routes)
        
        # Simple fallback - should rarely be needed if optimization processed correctly
        if not self.routes:
            self.routes = ['Unknown Route']
            

        
    def create_enhanced_interface(self):
        """Create the enhanced paned window interface."""
        
        # Control frame at top
        control_frame = ttk.Frame(self.window)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        # Route selection with type-ahead
        ttk.Label(control_frame, text="Route:").pack(side='left', padx=(0,5))
        
        self.route_var = tk.StringVar(value=self.routes[0])
        self.route_combo = ttk.Combobox(
            control_frame,
            textvariable=self.route_var,
            values=self.routes,
            state='normal',  # Enable type-ahead
            width=25
        )
        self.route_combo.pack(side='left', padx=5)
        self.route_combo.bind('<KeyRelease>', self.on_route_keyrelease)
        self.route_combo.bind('<<ComboboxSelected>>', self.on_route_changed)
        
        # Excel Export Button next to route selection
        export_button = ttk.Button(control_frame, text="📊 Export to Excel", 
                                   command=self._export_to_excel)
        export_button.pack(side='left', padx=10)
        
        # Show optimization info
        opt_info = self.get_optimization_summary()
        info_label = ttk.Label(control_frame, text=opt_info)
        info_label.pack(side='left', padx=20)
        
        # Status on right
        self.status_label = ttk.Label(control_frame, text="📈 Results loaded")
        self.status_label.pack(side='right', padx=10)
        
        # Main paned window container with user-resizable divider
        main_paned = ttk.PanedWindow(self.window, orient='horizontal')
        main_paned.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Store reference for divider control
        self.main_paned = main_paned
        
        # Determine analysis method for layout (configuration-driven)
        analysis_method = self.json_results.get('analysis_metadata', {}).get('analysis_method')
        if not analysis_method:
            raise ValueError(
                "Results JSON is missing required analysis_metadata.analysis_method; cannot determine layout"
            )
        
        # LEFT PANE - Pareto Graph (only shown for multi-objective)  
        self.left_frame = ttk.LabelFrame(main_paned, text="🎯 Pareto Front Analysis", padding=5)
        
        # Configuration-driven multi-objective check
        from config import is_multi_objective_method
        self.is_multi_objective = is_multi_objective_method(analysis_method)
            
        if self.is_multi_objective:
            main_paned.add(self.left_frame, weight=1)
        
        # Create left figure (Pareto) with tight layout
        self.fig_left = Figure(figsize=(7, 6), dpi=100, tight_layout=True)
        self.ax_left = self.fig_left.add_subplot(111)
        
        # Canvas and toolbar for left pane
        self.canvas_left = FigureCanvasTkAgg(self.fig_left, self.left_frame)
        self.canvas_left.get_tk_widget().pack(fill='both', expand=True)
        
        toolbar_left = NavigationToolbar2Tk(self.canvas_left, self.left_frame)
        toolbar_left.update()
        
        # Connect click events for Pareto point selection
        self.canvas_left.mpl_connect('pick_event', self.on_pareto_pick)
        self.canvas_left.mpl_connect('button_press_event', self.on_pareto_click)
        
        # RIGHT PANE - Segmentation Graph  
        right_frame = ttk.LabelFrame(main_paned, text="📊 Highway Segmentation Analysis", padding=5)
        main_paned.add(right_frame, weight=1)  # Pane for segmentation display
        
        # Create right figure (Segmentation) with tight layout  
        self.fig_right = Figure(figsize=(7, 6), dpi=100, tight_layout=True)
        self.ax_right = self.fig_right.add_subplot(111)
        
        # Canvas and toolbar for right pane
        self.canvas_right = FigureCanvasTkAgg(self.fig_right, right_frame)
        self.canvas_right.get_tk_widget().pack(fill='both', expand=True)
        
        toolbar_right = NavigationToolbar2Tk(self.canvas_right, right_frame)
        toolbar_right.update()
        
        # Status message frame for original data loading issues
        self.status_frame = ttk.Frame(self.window)
        self.status_frame.pack(fill='x', padx=10, pady=(0,5))
        
        self.data_status_label = ttk.Label(self.status_frame, text="", foreground='red')
        self.data_status_label.pack(side='left')
        
        # Selection tracking
        self.analysis_method = analysis_method
        self.selected_pareto_point = None
        self.pareto_points_data = []
        
        # Load original data from input file info
        self.load_original_data()
        
        print("Enhanced visualization interface ready")
        
    def get_optimization_summary(self):
        """Get summary of optimization results using actual schema structure."""
        if not self.json_results:
            return "[INFO] No optimization data"
            
        # Read from actual schema structure: analysis_metadata.analysis_method
        method = self.json_results.get('analysis_metadata', {}).get('analysis_method', 'Unknown')
        total_routes = len(self.json_results.get('route_results', []))
        
        # Get generation/iteration info from input_parameters
        method_params = self.json_results.get('input_parameters', {}).get('method_parameters', {})
        generations = method_params.get('num_generations', 'N/A')
        
        return f"Method: {method} | Routes: {total_routes} | Generations: {generations}"
        
    def load_original_data(self):
        """Load original data from input file info in JSON schema."""
        self.original_data_by_route = {}
        
        if not self.json_results:
            return
            
        # Get file info from JSON schema
        input_file_info = self.json_results.get('analysis_metadata', {}).get('input_file_info', {})
        data_file_path = input_file_info.get('data_file_path')
        data_file_name = input_file_info.get('data_file_name')
        
        # Try to find the original data file with improved fallback logic
        file_to_load = None
        search_paths = []
        
        # Add absolute path if provided
        if data_file_path:
            search_paths.append(data_file_path)
        
        # Add fallback paths if filename is available
        if data_file_name:
            # Try relative to current working directory
            search_paths.extend([
                str(Path('data') / data_file_name),           # ./data/filename
                str(Path('Results') / data_file_name),        # ./Results/filename  
                data_file_name,                               # ./filename
                str(Path('..') / 'data' / data_file_name),    # ../data/filename
            ])
        
        # Search through all paths until we find the file
        for path in search_paths:
            if Path(path).exists():
                file_to_load = path
                print(f"[SUCCESS] Found original data file: {file_to_load}")
                break
                
        if file_to_load:
            try:
                self.original_data = pd.read_csv(file_to_load)
                
                # Get column names from JSON schema
                route_processing = self.json_results.get('input_parameters', {}).get('route_processing', {})
                route_column = route_processing.get('route_column')
                
                # Organize data by route
                if route_column and route_column in self.original_data.columns:
                    for route_id in self.routes:
                        route_data = self.original_data[self.original_data[route_column] == route_id].copy()
                        if not route_data.empty:
                            self.original_data_by_route[route_id] = route_data
                else:
                    # Single route data
                    if self.routes:
                        self.original_data_by_route[self.routes[0]] = self.original_data.copy()
                        
                print(f"[SUCCESS] Loaded original data from {file_to_load}")
                return
                
            except Exception as e:
                print(f"[ERROR] Failed to load original data: {e}")
                
        # Show error message if data not found
        error_msg = f"⚠️ Original data file not found: {data_file_name or 'Unknown file'}"
        self.data_status_label.config(text=error_msg)
        print(f"[WARNING] {error_msg}")
        
    def on_route_keyrelease(self, event=None):
        """Handle type-ahead functionality."""
        typed_text = self.route_combo.get().lower()
        
        if typed_text:
            matches = [route for route in self.routes if typed_text in route.lower()]
            if matches:
                self.route_combo['values'] = matches
                # Type-ahead filtering applied
                
    def on_route_changed(self, event=None):
        """Handle route selection change."""
        selected_route = self.route_var.get()
        # Route changed
        self.update_visualizations()
        
    def update_visualizations(self):
        """Update both visualizations based on selected route and analysis method."""
        route_id = self.route_var.get()
        
        # Get route results for this route
        route_results = self.get_route_results(route_id)
        if not route_results:
            return
            
        # Get pareto points
        pareto_points = route_results.get('processing_results', {}).get('pareto_points', [])
        if not pareto_points:
            return
            
        self.pareto_points_data = pareto_points
        
        # Auto-select point with highest X value BEFORE drawing graphs
        if pareto_points:
            best_point = max(pareto_points, key=lambda p: p.get('objective_values', [0])[0])
            best_point_id = best_point.get('point_id', 0)
            self.select_pareto_point(best_point_id)
        
        # Update Pareto graph (LEFT pane) - only if multi-objective
        if self.is_multi_objective:
            self.update_pareto_graph(route_id, pareto_points)
        else:
            # Single-objective: Hide Pareto pane (degenerate - just 1 point)
            if hasattr(self, 'main_paned') and hasattr(self, 'left_frame'):
                try:
                    self.main_paned.remove(self.left_frame)
                except (tk.TclError, ValueError):
                    pass  # May already be removed
                print(f"[ROUTE {route_id}] Hidden Pareto pane for single-objective (degenerate case)")
            
        # Update segmentation graph (RIGHT pane) with selected point
        self.update_segmentation_graph(route_id)
        
        # Redraw canvases
        if self.is_multi_objective:
            self.canvas_left.draw()
        self.canvas_right.draw()
        
    def get_current_route_data(self, route_id):
        """Get original data for the specified route from loaded data."""
        if hasattr(self, 'original_data_by_route') and route_id in self.original_data_by_route:
            return self.original_data_by_route[route_id]
        return None
        
    def get_route_results(self, route_id):
        """Get optimization results for the specified route using actual schema structure."""
        if not self.json_results or 'route_results' not in self.json_results:
            return None
            
        for route_result in self.json_results['route_results']:
            if route_result.get('route_info', {}).get('route_id') == route_id:
                return route_result
        return None
        
    def update_pareto_graph(self, route_id, pareto_points):
        """Update LEFT pane with Pareto front for the SELECTED ROUTE only."""
        self.ax_left.clear()
        
        # Debug: Pareto front update (removed verbose logging)
        
        if not pareto_points or len(pareto_points) <= 1:
            self.ax_left.text(0.5, 0.5, f'Single point for {route_id}\n(No Pareto front to display)', 
                            transform=self.ax_left.transAxes, ha='center', va='center',
                            fontsize=12, color=COLORS['text_secondary'])
            self.ax_left.set_title(f"Pareto Analysis - {route_id} (Single Point)")
            return
            
        # Extract objective values
        obj1_values = []
        obj2_values = []
        point_ids = []
        
        for point in pareto_points:
            objectives = point.get('objective_values', [])
            if len(objectives) >= 2:
                obj1_values.append(objectives[0])
                obj2_values.append(objectives[1])
                point_ids.append(point.get('point_id', 0))
        
        # Apply axis transforms based on method configuration
        if obj1_values and obj2_values:
            # Get analysis method from JSON (now contains method_key directly)  
            analysis_method = self.json_results.get('analysis_metadata', {}).get('analysis_method', 'multi')
            
            # Get method configuration directly using method_key
            try:
                # Get method configuration from config.py
                method_config = get_optimization_method(analysis_method)
                plot_configs = getattr(method_config, 'objective_plot_configs', None)
                
                # Set default labels that guide user to configuration
                x_label = 'X-Axis Label (Configure in config.py objective_plot_configs)'
                y_label = 'Y-Axis Label (Configure in config.py objective_plot_configs)'
                
                if plot_configs and len(plot_configs) >= 2:
                    # Apply transform to X-axis (first objective) if specified
                    x_config = plot_configs[0]  # X-axis configuration (first in list)
                    if hasattr(x_config, 'transform') and x_config.transform == 'negate':
                        obj1_values = [-x for x in obj1_values]
                        # Debug: Axis transformation (removed verbose logging)
                        
                    # Apply transform to Y-axis (second objective) if specified  
                    y_config = plot_configs[1]  # Y-axis configuration (second in list)
                    if hasattr(y_config, 'transform') and y_config.transform == 'negate':
                        obj2_values = [-y for y in obj2_values]
                        # Debug: Axis transformation (removed verbose logging)
                        
                    # Update axis labels from configuration
                    if hasattr(x_config, 'name'):
                        x_label = x_config.name
                    if hasattr(y_config, 'name'):
                        y_label = y_config.name
                        
            except Exception as e:
                print(f"[WARN] Could not apply axis transforms from CONFIG: {e}")
                
            # Clear previous scatter plot references
            self.pareto_scatter_plots = {}
            self.point_id_map = {}  # Map from matplotlib artist to point_id for fast picker events
            
            # Plot all Pareto points with optimized selection handling
            for i, (x, y, point_id) in enumerate(zip(obj1_values, obj2_values, point_ids)):
                is_selected = (self.selected_pareto_point == point_id)
                
                color = COLORS['pareto_selected'] if is_selected else COLORS['pareto_normal']
                size = 100 if is_selected else 50  # Selected point is larger
                alpha = 0.9 if is_selected else 0.7
                edge_color = COLORS['pareto_border']
                edge_width = 2.5 if is_selected else 1.5  # Selected has thicker border
                
                scatter = self.ax_left.scatter(x, y, s=size, color=color, alpha=alpha,
                                             edgecolors=edge_color, linewidth=edge_width,
                                             picker=5, zorder=6 if is_selected else 5)  # picker=5 means 5 pixel tolerance
                
                # Store scatter plot reference and coordinates for fast access
                self.pareto_scatter_plots[point_id] = {'scatter': scatter, 'x': x, 'y': y}
                self.point_id_map[scatter] = point_id  # Direct mapping for picker events
                
                # No text annotation needed - visual highlighting is sufficient
            
            # Set axis labels and title
            self.ax_left.set_xlabel(x_label)
            self.ax_left.set_ylabel(y_label)
            self.ax_left.set_title(f"Pareto Front - {route_id}")
            
            # Add grid with proper visibility
            self.ax_left.grid(True, alpha=0.3, color=COLORS['grid'], linestyle='-', linewidth=0.5)
            self.ax_left.set_axisbelow(True)  # Grid behind points
            
            # Set automatic tick intervals for better readability
            self.ax_left.xaxis.set_major_locator(MaxNLocator(nbins=8, prune='both'))
            self.ax_left.yaxis.set_major_locator(MaxNLocator(nbins=8, prune='both'))
            
            # Add minor ticks and minor grid for precision
            self.ax_left.xaxis.set_minor_locator(MaxNLocator(nbins=16))
            self.ax_left.yaxis.set_minor_locator(MaxNLocator(nbins=16))
            self.ax_left.grid(True, which='minor', alpha=0.1, color=COLORS['grid'], linestyle='-', linewidth=0.3)
            
            # Debug: Pareto points plotted (removed verbose logging)

            
    def on_pareto_pick(self, event):
        """Ultra-fast Pareto point selection using matplotlib's built-in picker."""
        if not hasattr(self, 'point_id_map'):
            return
            
        # Get point_id directly from the picked artist
        picked_artist = event.artist
        if picked_artist in self.point_id_map:
            point_id = self.point_id_map[picked_artist]
            route_id = self.route_var.get()
            
            # Instant selection with minimal processing
            self.select_pareto_point(point_id)
            self.update_pareto_selection_only(route_id)
            self.canvas_left.draw_idle()  # Non-blocking draw
            
            # Update segmentation immediately (synchronous for reliability)
            self.update_segmentation_graph(route_id)
            self.canvas_right.draw_idle()
            
    def on_pareto_click(self, event):
        """Fast Pareto point click handler with optimized performance."""
        if event.inaxes != self.ax_left:
            return
            
        # Get current route data - use cached transformed coordinates if available
        route_id = self.route_var.get()
        if not hasattr(self, 'pareto_scatter_plots') or not self.pareto_scatter_plots:
            return
            
        # Find closest point to click using cached plot coordinates
        click_x, click_y = event.xdata, event.ydata
        if click_x is None or click_y is None:
            return
            
        min_distance = float('inf')
        closest_point_id = None
        
        # Use cached transformed coordinates from scatter plots for fast lookup
        for point_id, plot_data in self.pareto_scatter_plots.items():
            point_x, point_y = plot_data['x'], plot_data['y']
            distance = ((point_x - click_x) ** 2 + (point_y - click_y) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_point_id = point_id
                
        # Select the closest point with improved tolerance for easier clicking
        if closest_point_id is not None and min_distance < 3.0:  # Increased from 1.0 to 3.0 for easier clicking
            self.select_pareto_point(closest_point_id)
            
            # Fast update: redraw the left pane with new selection
            self.update_pareto_selection_only(route_id)
            self.canvas_left.draw_idle()  # Non-blocking draw
            
            # Update segmentation graph immediately (synchronous for reliability)
            self.update_segmentation_graph(route_id)
            self.canvas_right.draw_idle()
            
    def select_pareto_point(self, point_id):
        """Select a Pareto point and update displays with clear visual feedback."""
        self.selected_pareto_point = point_id
        
        # Update status label with selection info
        self.status_label.config(text=f"🎯 Selected: Point {point_id}")
        
    def update_pareto_selection_only(self, route_id):
        """Fast update: only change point colors/sizes without full redraw."""
        if not hasattr(self, 'pareto_scatter_plots'):
            return
            
        # Update visual appearance of all points based on selection
        for point_id, plot_data in self.pareto_scatter_plots.items():
            is_selected = (self.selected_pareto_point == point_id)
            scatter = plot_data['scatter']
            
            # Update colors and sizes efficiently
            color = COLORS['pareto_selected'] if is_selected else COLORS['pareto_normal']
            size = 100 if is_selected else 50
            alpha = 0.9 if is_selected else 0.7
            
            scatter.set_facecolors([color])
            scatter.set_sizes([size])
            scatter.set_alpha(alpha)
            scatter.set_zorder(6 if is_selected else 5)
        
    def _preprocess_gap_intervals(self, gap_segments):
        """Preprocess gap segments into efficient interval tuples for fast overlap detection.
        
        Args:
            gap_segments: List of gap dictionaries with 'start' and 'end' keys
            
        Returns:
            list: Sorted list of (start, end) tuples for efficient interval matching
        """
        if not gap_segments:
            return []
            
        # Extract and validate gap intervals, sort for potential binary search optimization
        intervals = []
        for gap in gap_segments:
            start = gap.get('start')
            end = gap.get('end') 
            
            # Validate gap data
            if start is not None and end is not None and start < end:
                intervals.append((float(start), float(end)))
            
        return sorted(intervals)  # Sorted for potential future binary search optimization
        
    def _segments_outside_gaps(self, segments, gap_intervals):
        """Efficiently filter segments to exclude those overlapping with gaps.
        
        Args:
            segments: List of (start, end) segment tuples
            gap_intervals: Preprocessed sorted list of (start, end) gap tuples
            
        Returns:
            list: Segments that don't overlap with any gaps
        """
        if not gap_intervals:
            return segments
            
        valid_segments = []
        
        for seg_start, seg_end in segments:
            # Fast overlap check against all gaps
            overlaps = False
            for gap_start, gap_end in gap_intervals:
                # Early termination: if gap starts after segment ends, no more overlaps possible
                if gap_start >= seg_end:
                    break
                    
                # Check overlap: segment overlaps gap if NOT (seg_end <= gap_start OR seg_start >= gap_end)
                if seg_end > gap_start and seg_start < gap_end:
                    overlaps = True
                    break
                    
            if not overlaps:
                valid_segments.append((seg_start, seg_end))
                
        return valid_segments
        
    def update_segmentation_graph(self, route_id):
        """Update RIGHT pane with segmentation graph for the SELECTED ROUTE only."""
        self.ax_right.clear()
        
        # Debug: Segmentation update (removed verbose logging)
        
        # Get original data and optimization results for this specific route
        route_data = self.get_current_route_data(route_id)
        route_results = self.get_route_results(route_id)
        
        if not route_results:
            self.ax_right.text(0.5, 0.5, 'No optimization results available', 
                             transform=self.ax_right.transAxes, ha='center', va='center',
                             fontsize=12, color=COLORS['text_secondary'])
            self.ax_right.set_title(f"Segmentation - {route_id} (No Results)")
            return
            
        # Get pareto points and find selected point
        pareto_points = route_results.get('processing_results', {}).get('pareto_points', [])
        if not pareto_points:
            return
            
        # Find selected point (or use first if none selected)
        selected_point = None
        if hasattr(self, 'selected_pareto_point') and self.selected_pareto_point is not None:
            # Debug: Point selection (removed verbose logging)
            for point in pareto_points:
                point_id = point.get('point_id')
                if point_id == self.selected_pareto_point:
                    selected_point = point
                    # Debug: Found matching point (removed verbose logging)
                    break
        
        if not selected_point:
            selected_point = pareto_points[0]
            
        # Get segmentation data
        segmentation = selected_point.get('segmentation', {})
        breakpoints = segmentation.get('breakpoints', [])
        
        # Get column names from JSON schema - these should always be present 
        route_processing = self.json_results.get('input_parameters', {}).get('route_processing', {})
        x_col = route_processing.get('x_column')
        y_col = route_processing.get('y_column')
        
        # If missing from route_processing, try backup location in input_file_info
        if not x_col or not y_col:
            column_info = self.json_results.get('analysis_metadata', {}).get('input_file_info', {}).get('column_info', {})
            if not x_col:
                x_col = column_info.get('x_column')
            if not y_col:
                y_col = column_info.get('y_column')
                
        # If still missing, this indicates a data integrity problem
        if not x_col or not y_col:
            self.app.log_message(f"WARNING: Missing column information in JSON file - x_col={x_col}, y_col={y_col}")
            self.app.log_message("This may indicate a corrupted or outdated JSON results file")
            # Use first/second columns as emergency fallback, but log the problem
            if route_data is not None and not route_data.empty:
                if not x_col:
                    x_col = route_data.columns[0] if len(route_data.columns) > 0 else 'x'
                    self.app.log_message(f"Emergency fallback: Using '{x_col}' as x-column")
                if not y_col:
                    y_col = route_data.columns[1] if len(route_data.columns) > 1 else route_data.columns[0]
                    self.app.log_message(f"Emergency fallback: Using '{y_col}' as y-column")
        
        # Get mandatory breakpoints
        mandatory_breakpoints = set()
        if 'input_data_analysis' in route_results:
            mandatory_segments = route_results['input_data_analysis'].get('mandatory_segments', {})
            mandatory_breakpoints = set(mandatory_segments.get('mandatory_breakpoints', []))
        
        # Plot original input data points (Z-order: 2)
        if route_data is not None and not route_data.empty:
            # Ensure column names exist
            if x_col not in route_data.columns:
                x_col = route_data.columns[0] if len(route_data.columns) > 0 else 'x'
            if y_col not in route_data.columns:
                y_col = route_data.columns[1] if len(route_data.columns) > 1 else route_data.columns[0]
                
            # Plot with improved contrast colors (light gray for original data)
            self.ax_right.scatter(route_data[x_col], route_data[y_col], 
                               alpha=0.8, s=25, color=COLORS['original_data'], 
                               edgecolors=COLORS['original_edge'], linewidth=0.5,
                               label='Original Data Points', zorder=2)
            
            x_data = route_data[x_col].values
            y_data = route_data[y_col].values
            
            # Ensure route endpoints are included in mandatory breakpoints
            route_start = np.min(x_data)
            route_end = np.max(x_data)
            
            # Add route endpoints to mandatory breakpoints if not already present
            if route_start not in mandatory_breakpoints:
                mandatory_breakpoints.add(route_start)
            if route_end not in mandatory_breakpoints:
                mandatory_breakpoints.add(route_end)
                
            mandatory_breakpoints = sorted(set(mandatory_breakpoints))
            
            # Get gap segments from JSON data for this specific route (for display info only)
            route_results = self.get_route_results(route_id)
            gap_segments = []
            if route_results and 'input_data_analysis' in route_results:
                input_analysis = route_results['input_data_analysis']
                gap_analysis = input_analysis.get('gap_analysis', {})
                gap_segments = gap_analysis.get('gap_segments', [])
                total_gaps = gap_analysis.get('total_gaps', 0)
                if total_gaps > 0:
                    # Only print gap info once per route to avoid repetition
                    if not hasattr(self, '_gap_info_shown'):
                        self._gap_info_shown = set()
                    if route_id not in self._gap_info_shown:
                        print(f"[INFO] Route '{route_id}': {total_gaps} data gaps in original data")
                        self._gap_info_shown.add(route_id)
            
            # Plot breakpoints as vertical dashed lines (Z-order: 3)
            if breakpoints:
                mandatory_plotted = False
                analysis_plotted = False
                
                for bp in breakpoints:
                    if bp in mandatory_breakpoints:
                        # Mandatory breakpoints - slightly thicker crimson lines
                        self.ax_right.axvline(x=bp, color=COLORS['mandatory_bp'], linestyle='--', 
                                            linewidth=1.2, alpha=0.9, zorder=3,
                                            label='Mandatory Breakpoints' if not mandatory_plotted else "")
                        mandatory_plotted = True
                    else:
                        # Analysis-selected breakpoints - thin forest green lines  
                        self.ax_right.axvline(x=bp, color=COLORS['analysis_bp'], linestyle='--', 
                                            linewidth=0.8, alpha=0.8, zorder=3,
                                            label='Analysis Breakpoints' if not analysis_plotted else "")
                        analysis_plotted = True
                
                # Efficiently filter segments to exclude gaps (single-pass processing)
                sorted_breakpoints = sorted(breakpoints)
                segments = [(sorted_breakpoints[i], sorted_breakpoints[i + 1]) 
                           for i in range(len(sorted_breakpoints) - 1)]
                
                # Preprocess gap intervals once for efficient batch filtering  
                gap_intervals = self._preprocess_gap_intervals(gap_segments)
                valid_segments = self._segments_outside_gaps(segments, gap_intervals)
                
                segment_avg_plotted = False
                
                # Draw averages only for valid (non-gap) segments
                for start_bp, end_bp in valid_segments:
                    # Get data for this segment and draw average if data exists
                    segment_mask = (x_data >= start_bp) & (x_data <= end_bp)
                    if np.any(segment_mask):
                        segment_y = y_data[segment_mask]
                        if len(segment_y) > 0:
                            avg_y = np.mean(segment_y)
                            
                            # Draw horizontal segment average line with bolder blue
                            self.ax_right.plot([start_bp, end_bp], [avg_y, avg_y], 
                                             color=COLORS['segment_avg'], linewidth=3, alpha=0.9,
                                                 zorder=4, solid_capstyle='butt',
                                                 label='Segment Averages' if not segment_avg_plotted else "")
                            segment_avg_plotted = True
                                             
        else:
            # Show error if no original data
            if not hasattr(self, 'original_data_by_route') or route_id not in self.original_data_by_route:
                self.ax_right.text(0.02, 0.98, '⚠️ Original data file not found', 
                                 transform=self.ax_right.transAxes, fontsize=11, 
                                 verticalalignment='top', color=COLORS['mandatory_bp'], weight='bold',
                                 bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFF8E1', alpha=0.9, edgecolor=COLORS['mandatory_bp']))
        
        # Set labels and title with pleasant styling
        self.ax_right.set_xlabel(x_col.replace('_', ' ').title())
        self.ax_right.set_ylabel(y_col.replace('_', ' ').title())  
        self.ax_right.set_title(f"Highway Segmentation - {route_id}")
        self.ax_right.grid(True, alpha=0.2, color=COLORS['grid'], zorder=1)  # Grid at lowest Z-order
        
        # Set automatic tick intervals for better readability
        self.ax_right.xaxis.set_major_locator(MaxNLocator(nbins=10, prune='both'))
        self.ax_right.yaxis.set_major_locator(MaxNLocator(nbins=8, prune='both'))
        
        # Add minor ticks for precision
        self.ax_right.xaxis.set_minor_locator(MaxNLocator(nbins=20))
        self.ax_right.yaxis.set_minor_locator(MaxNLocator(nbins=16))
        
        # Add legend (remove duplicates)
        handles, labels = self.ax_right.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            self.ax_right.legend(by_label.values(), by_label.keys(), loc='best', framealpha=0.9)

    def _export_to_excel(self):
        """Export comprehensive optimization results using dedicated excel_export module."""
        try:
            # Check if we have any results to export
            if not hasattr(self, 'json_results') or not self.json_results:
                messagebox.showerror("Export Error", "No optimization results available for export.")
                return
            
            # Check if we have route results
            route_results = self.json_results.get('route_results', [])
            if not route_results:
                messagebox.showerror("Export Error", "No route results found in optimization data.")
                return
            
            # Import the dedicated excel exporter
            try:
                from excel_export import HighwaySegmentationExcelExporter
            except ImportError:
                messagebox.showerror("Export Error", "Excel export module not found. Please ensure excel_export.py is available.")
                return
            
            # Use complete JSON data to export ALL routes (not just selected route)
            json_data = {
                'analysis_metadata': self.json_results.get('analysis_metadata', {
                    'analysis_method': 'multi_route',
                    'timestamp': datetime.now().isoformat(),
                    'analysis_id': f"all_routes_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                }),
                'input_parameters': self.json_results.get('input_parameters', {}),
                'route_results': route_results  # ✅ Export ALL routes, not just selected
            }
            
            # Get file path for export
            route_count = len(route_results)
            route_names = [r.get('route_info', {}).get('route_id', 'Unknown') for r in route_results]
            default_filename = "highway_segmentation_export.xlsx"
            
            # Determine initial directory - default to Results/ folder with fallback to last directory
            initial_dir = "Results"
            if hasattr(self.parent_app, '_last_file_directory') and self.parent_app._last_file_directory:
                initial_dir = self.parent_app._last_file_directory
            elif not os.path.exists("Results"):
                initial_dir = "."
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialfile=default_filename,
                initialdir=initial_dir,
                title=f"Export Analysis to Excel ({route_count} routes)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Store selected directory for future use
            self.parent_app._last_file_directory = os.path.dirname(file_path)
            
            # Get original data path if available (use first route or fallback search)
            original_csv_path = None
            input_file_info = self.json_results.get('analysis_metadata', {}).get('input_file_info', {})
            stored_path = input_file_info.get('data_file_path')
            stored_name = input_file_info.get('data_file_name')
            
            # Use the same search logic as in load_original_data
            if stored_path and Path(stored_path).exists():
                original_csv_path = stored_path
            elif stored_name:
                # Try fallback locations
                for path in [Path('data') / stored_name, Path('Results') / stored_name, stored_name]:
                    if path.exists():
                        original_csv_path = str(path)
                        break
            
            # Create exporter and export
            exporter = HighwaySegmentationExcelExporter(json_data, original_csv_path)
            success, error_message = exporter.export_to_excel(file_path)
            
            if success:
                # Enhanced success message with route count
                route_list = ", ".join(route_names)
                result = messagebox.askyesno("Export Success", 
                    f"Successfully saved:\\n{file_path}\\n\\n" +
                    f"📊 Exported {route_count} routes: {route_list}\\n" +
                    f"📋 10 comprehensive data tabs created\\n\\n" +
                    "Would you like to open the file now?")
                
                if result:  # User clicked Yes
                    try:
                        import subprocess
                        import platform
                        
                        # Open file with default application based on OS
                        if platform.system() == "Windows":
                            os.startfile(file_path)
                        elif platform.system() == "Darwin":  # macOS
                            subprocess.call(["open", file_path])
                        else:  # Linux
                            subprocess.call(["xdg-open", file_path])
                            
                    except Exception as e:
                        messagebox.showwarning("Open File Error", 
                            f"File saved successfully but could not open automatically:\\n{str(e)}")
            else:
                messagebox.showerror("Export Error", error_message)
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export to Excel:\\n{str(e)}")


def show_enhanced_visualization(parent_app, json_results_path=None, json_results_data=None):
    """
    Show enhanced paned window visualization with optimization results.
    
    Args:
        parent_app: Main application instance
        json_results_path: Path to JSON results file (optional)
        json_results_data: Direct JSON results data (optional)
    """
    try:
        # Load JSON results data
        
        # Load JSON results if path provided
        if json_results_path and Path(json_results_path).exists():
            print(f"[FILE] Loading results from: {json_results_path}")
            with open(json_results_path, 'r') as f:
                json_data = json.load(f)
        elif json_results_data:
            json_data = json_results_data
            # Using provided JSON results data
        else:
            json_data = None
            print("[WARN] No JSON results provided, showing data visualization only")
        
        # Get original data from parent app
        original_data = None
        
        # Extracting original data from parent app...
        if hasattr(parent_app, 'data') and parent_app.data is not None:
            if hasattr(parent_app.data, 'route_data'):
                # RouteAnalysis object
                original_data = parent_app.data.route_data
                # Found RouteAnalysis data
            else:
                # Direct DataFrame
                original_data = parent_app.data
                # Found DataFrame data
        else:
            messagebox.showerror("Data Error", 
                "No data loaded in application.\n"
                "Please load a CSV file before opening visualization.")
            return None
        
        # VALIDATION LAYER 1: UI Controls Must Exist
        if not hasattr(parent_app, 'x_column') or not hasattr(parent_app, 'y_column'):
            missing = []
            if not hasattr(parent_app, 'x_column'): missing.append('X-axis column selector')
            if not hasattr(parent_app, 'y_column'): missing.append('Y-axis column selector')
            messagebox.showerror("Configuration Error", 
                f"Application missing required controls:\n{', '.join(missing)}\n\n"
                "Please restart the application.")
            return None
        
        # VALIDATION LAYER 2: Column Values Must Be Selected
        x_col = parent_app.x_column.get()
        y_col = parent_app.y_column.get()
        
        if not x_col or not y_col:
            messagebox.showerror("Column Selection Error",
                "Please select both X and Y axis columns.\n\n"
                f"Current selection:\n"
                f"• X-axis: '{x_col}'\n"
                f"• Y-axis: '{y_col}'")
            return None
        
        # VALIDATION LAYER 3: Columns Must Exist in Data  
        missing_cols = []
        if x_col not in original_data.columns: missing_cols.append(f"'{x_col}'")
        if y_col not in original_data.columns: missing_cols.append(f"'{y_col}'") 
        
        if missing_cols:
            available = "', '".join(original_data.columns[:8])  # Show first 8 columns
            more_msg = f" (and {len(original_data.columns)-8} more)" if len(original_data.columns) > 8 else ""
            messagebox.showerror("Column Not Found",
                f"Selected columns not found in loaded data:\n{', '.join(missing_cols)}\n\n"
                f"Available columns: '{available}'{more_msg}")
            return None
        
        # VALIDATION LAYER 4: Columns Must Be Numeric
        for col_name, col_purpose in [(x_col, 'X-axis'), (y_col, 'Y-axis')]:
            col_data = original_data[col_name]
            
            if not pd.api.types.is_numeric_dtype(col_data):
                sample_values = list(col_data.dropna().head(3))
                messagebox.showerror("Data Type Error",
                    f"{col_purpose} column '{col_name}' contains non-numeric data.\n"
                    f"Visualization requires numeric columns for analysis.\n\n"
                    f"Sample values: {sample_values}")
                return None
        
        # Create and show enhanced visualization
        # Creating enhanced visualization window...
        viz_window = EnhancedVisualizationWindow(
            parent_app=parent_app,
            json_results_data=json_data,
            original_data=original_data,
            x_column=x_col,
            y_column=y_col
        )
        
        # Enhanced visualization opened successfully
        return viz_window
        
    except Exception as e:
        print(f"[ERROR] Error opening enhanced visualization: {e}")
        return None