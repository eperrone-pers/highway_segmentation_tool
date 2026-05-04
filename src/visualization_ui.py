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
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector
from logger import create_logger
import json
import os
from pathlib import Path
from datetime import datetime
from matplotlib.ticker import MaxNLocator

from route_utils import normalize_route_column_selection
from visualization.utils import safe_print as _safe_print, default_colors
from visualization.results_binding import (
    resolve_routes,
    original_data_path_from_results,
    find_existing_original_data_file,
    group_original_data_by_route,
)
from visualization.pareto import prepare_pareto_series


# Pleasant color scheme - updated for better contrast
COLORS = default_colors()


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

        # Zoom state (reset on route change)
        self._seg_x_zoom_enabled = False
        self._seg_default_xlim = None
        self._seg_default_ylim = None
        self._pareto_default_xlim = None
        self._pareto_default_ylim = None
        self._current_seg_x = None
        self._current_seg_y = None
        
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
        # Get route column name from parent app if available
        route_column = normalize_route_column_selection(
            self.parent_app.route_column.get() if hasattr(self.parent_app, 'route_column') else None
        )

        self.routes = resolve_routes(self.json_results, self.original_data, route_column)
            

        
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
        if self.is_multi_objective:
            left_bottom_bar = ttk.Frame(self.left_frame)
            left_bottom_bar.pack(side='bottom', fill='x')

            left_toolbar_container = ttk.Frame(left_bottom_bar)
            left_toolbar_container.pack(side='left', fill='x', expand=True)
            toolbar_left = NavigationToolbar2Tk(self.canvas_left, left_toolbar_container)
            toolbar_left.update()

            left_controls_container = ttk.Frame(left_bottom_bar)
            left_controls_container.pack(side='right')
            self.reset_pareto_zoom_button = ttk.Button(
                left_controls_container,
                text="Reset Pareto Zoom",
                command=self.reset_pareto_zoom,
            )
            self.reset_pareto_zoom_button.pack(side='right', padx=(6, 0), pady=2)

            self.canvas_left.get_tk_widget().pack(side='top', fill='both', expand=True)
        else:
            self.canvas_left.get_tk_widget().pack(fill='both', expand=True)
        
        # Connect click events for Pareto point selection
        self.canvas_left.mpl_connect('pick_event', self.on_pareto_pick)
        self.canvas_left.mpl_connect('button_press_event', self.on_pareto_click)
        
        # RIGHT PANE - Segmentation Graph  
        right_frame = ttk.LabelFrame(main_paned, text="📊 Highway Segmentation Analysis", padding=5)
        main_paned.add(right_frame, weight=1)  # Pane for segmentation display
        
        # Create right figure (Segmentation) with tight layout  
        self.fig_right = Figure(figsize=(7, 6), dpi=100, tight_layout=True)
        self.ax_right = self.fig_right.add_subplot(111)

        # Keep paging controls in sync with any toolbar-driven x-limit changes.
        try:
            self._seg_xlim_callback_cid = self.ax_right.callbacks.connect(
                'xlim_changed',
                lambda _ax: self._update_segmentation_paging_controls(),
            )
        except Exception:
            self._seg_xlim_callback_cid = None

        # Container to place paging arrows on either side of the segmentation canvas.
        # The arrows only appear when the x-axis is zoomed in.
        seg_plot_container = ttk.Frame(right_frame)
        seg_plot_container.pack(side='top', fill='both', expand=True)
        seg_plot_container.grid_rowconfigure(0, weight=1)
        seg_plot_container.grid_columnconfigure(1, weight=1)

        # Canvas and toolbar for right pane
        # IMPORTANT: canvas widget must be parented to seg_plot_container because we use
        # grid inside seg_plot_container. right_frame itself uses pack.
        self.canvas_right = FigureCanvasTkAgg(self.fig_right, seg_plot_container)

        self.seg_page_left_button = ttk.Button(
            seg_plot_container,
            text="◀",
            width=3,
            command=lambda: self.page_segmentation_x_window(direction=-1),
        )
        self.seg_page_left_button.grid(row=0, column=0, sticky='ns', padx=(0, 6), pady=6)

        self.canvas_right.get_tk_widget().grid(row=0, column=1, sticky='nsew')

        self.seg_page_right_button = ttk.Button(
            seg_plot_container,
            text="▶",
            width=3,
            command=lambda: self.page_segmentation_x_window(direction=1),
        )
        self.seg_page_right_button.grid(row=0, column=2, sticky='ns', padx=(6, 0), pady=6)

        # Hidden by default; shown when zoomed.
        try:
            self.seg_page_left_button.grid_remove()
            self.seg_page_right_button.grid_remove()
        except Exception:
            pass

        right_bottom_bar = ttk.Frame(right_frame)
        right_bottom_bar.pack(side='bottom', fill='x')

        right_toolbar_container = ttk.Frame(right_bottom_bar)
        right_toolbar_container.pack(side='left', fill='x', expand=True)
        toolbar_right = NavigationToolbar2Tk(self.canvas_right, right_toolbar_container)
        toolbar_right.update()

        right_controls_container = ttk.Frame(right_bottom_bar)
        right_controls_container.pack(side='right')

        self.seg_xzoom_button = ttk.Button(
            right_controls_container,
            text="X Zoom (Segmentation)",
            command=self.toggle_segmentation_x_zoom,
        )
        self.seg_xzoom_button.pack(side='left', padx=(0, 6), pady=2)

        self.reset_seg_zoom_button = ttk.Button(
            right_controls_container,
            text="Reset Seg Zoom",
            command=self.reset_segmentation_zoom,
        )
        self.reset_seg_zoom_button.pack(side='left', padx=(0, 0), pady=2)

        # X-only zoom selector for the segmentation axis (disabled by default)
        self._seg_span_selector = SpanSelector(
            self.ax_right,
            self._on_segmentation_xspan_selected,
            direction='horizontal',
            useblit=True,
            interactive=True,
            props=dict(alpha=0.20, facecolor=COLORS['original_edge']),
        )
        self._seg_span_selector.set_active(False)
        
        # Status message frame for original data loading issues
        self.status_frame = ttk.Frame(self.window)
        self.status_frame.pack(fill='x', padx=10, pady=(0,5))

        # Copy-friendly original data path display
        self.data_status_label = ttk.Label(self.status_frame, text="", foreground='red')
        self.data_status_label.pack(side='left', padx=(0, 8))

        self.data_path_var = tk.StringVar(value="")
        self.data_path_entry = ttk.Entry(self.status_frame, textvariable=self.data_path_var, state='readonly')
        self.data_path_entry.pack(side='left', fill='x', expand=True)
        
        # Selection tracking
        self.analysis_method = analysis_method
        self.selected_pareto_point = None
        self.pareto_points_data = []
        
        # Load original data from input file info
        self.load_original_data()
        
        _safe_print("Enhanced visualization interface ready")
        
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
        self.loaded_original_data_path = None
        
        if not self.json_results:
            return
            
        # Get file info from JSON schema
        data_file_path = original_data_path_from_results(self.json_results)
        data_file_name = (
            self.json_results.get('analysis_metadata', {}).get('input_file_info', {}).get('data_file_name')
            if isinstance(self.json_results.get('analysis_metadata', {}).get('input_file_info', {}), dict)
            else None
        )
        
        # Try to find the original data file.
        # Preference: only use the exact stored full path. Do not search for other
        # files with the same name in the project folders.
        file_to_load = None
        search_paths = []
        
        # Add absolute path if provided (only path we will attempt)
        if data_file_path:
            search_paths.append(data_file_path)

        # Search through all paths until we find the file
        for path in search_paths:
            existing = find_existing_original_data_file(path)
            if existing:
                file_to_load = existing
                _safe_print(f"[SUCCESS] Found original data file: {file_to_load}")
                break
                
        if file_to_load:
            try:
                # Read as strings first to preserve leading zeros and keep route identifiers categorical.
                # We'll convert X/Y columns to numeric later at plot time.
                self.original_data = pd.read_csv(file_to_load, dtype=str)

                # Get column names from JSON schema
                route_processing = self.json_results.get('input_parameters', {}).get('route_processing', {})
                route_column = route_processing.get('route_column')

                self.original_data_by_route = group_original_data_by_route(
                    self.original_data,
                    self.routes,
                    route_column,
                )
                        
                _safe_print(f"[SUCCESS] Loaded original data from {file_to_load}")
                self.loaded_original_data_path = str(Path(file_to_load).resolve())
                try:
                    self.data_status_label.config(text="Loaded original data:", foreground='green')
                    self.data_path_var.set(self.loaded_original_data_path)
                except Exception:
                    pass
                return
                
            except Exception as e:
                _safe_print(f"[ERROR] Failed to load original data: {e}")
                
        # Show error message if data not found
        missing_path_display = str(data_file_path or data_file_name or "")
        try:
            self.data_status_label.config(text="Original data file not found:", foreground='red')
            self.data_path_var.set(missing_path_display)
        except Exception:
            # Best-effort fallback
            try:
                self.data_status_label.config(text=f"Original data file not found: {data_file_name or 'Unknown file'}")
            except Exception:
                pass

        # Console output must remain ASCII-safe on Windows.
        _safe_print(f"[WARNING] Original data file not found: {missing_path_display or (data_file_name or 'Unknown file')}")
        
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
        # Route changed
        # Reset zoom state on route change (user preference)
        self._seg_x_zoom_enabled = False
        try:
            if hasattr(self, '_seg_span_selector'):
                self._seg_span_selector.set_active(False)
            if hasattr(self, 'seg_xzoom_button'):
                self.seg_xzoom_button.config(text="X Zoom (Segmentation)")
        except Exception:
            pass
        self.update_visualizations()

    def toggle_segmentation_x_zoom(self):
        """Toggle X-only zoom mode for the segmentation plot."""
        self._seg_x_zoom_enabled = not self._seg_x_zoom_enabled
        try:
            if hasattr(self, '_seg_span_selector'):
                self._seg_span_selector.set_active(self._seg_x_zoom_enabled)
            if hasattr(self, 'seg_xzoom_button'):
                self.seg_xzoom_button.config(
                    text=("X Zoom: ON" if self._seg_x_zoom_enabled else "X Zoom (Segmentation)")
                )
        except Exception:
            pass

    def _on_segmentation_xspan_selected(self, xmin, xmax):
        """Handle a user-dragged X span on the segmentation axis."""
        try:
            if xmin is None or xmax is None:
                return
            if xmax < xmin:
                xmin, xmax = xmax, xmin
            if abs(xmax - xmin) < 1e-12:
                return

            # Apply X zoom
            self.ax_right.set_xlim(xmin, xmax)

            self._autoscale_segmentation_y_to_visible(xmin, xmax)

            self.canvas_right.draw_idle()
            self._update_segmentation_paging_controls()
        except Exception as e:
            try:
                self.status_label.config(text=f"❌ X Zoom failed: {e}")
            except Exception:
                pass

    def reset_segmentation_zoom(self):
        """Reset segmentation plot limits to the defaults for the current route."""
        try:
            if self._seg_default_xlim is not None:
                self.ax_right.set_xlim(*self._seg_default_xlim)
            if self._seg_default_ylim is not None:
                self.ax_right.set_ylim(*self._seg_default_ylim)
            self.canvas_right.draw_idle()
            self._update_segmentation_paging_controls()
        except Exception as e:
            try:
                self.status_label.config(text=f"❌ Reset seg zoom failed: {e}")
            except Exception:
                pass

    def _autoscale_segmentation_y_to_visible(self, xmin: float, xmax: float) -> None:
        """Autoscale segmentation Y limits to points visible within [xmin, xmax]."""
        try:
            if self._current_seg_x is None or self._current_seg_y is None:
                return
            from visualization.autoscale import autoscale_y_limits, visible_y_values_in_x_window

            y_vis = visible_y_values_in_x_window(
                self._current_seg_x,
                self._current_seg_y,
                xmin=xmin,
                xmax=xmax,
            )
            if y_vis is None:
                return

            y_limits = autoscale_y_limits(y_vis, pad_fraction=0.05, min_pad=1.0)
            if y_limits is None:
                return

            self.ax_right.set_ylim(*y_limits)
        except Exception:
            return

    def _update_segmentation_paging_controls(self) -> None:
        """Show/hide the segmentation paging arrows depending on zoom state."""
        try:
            if not hasattr(self, 'seg_page_left_button') or not hasattr(self, 'seg_page_right_button'):
                return
            from visualization.zoom_decisions import should_show_segmentation_paging_arrows

            show = should_show_segmentation_paging_arrows(
                full_xlim=self._seg_default_xlim,
                cur_xlim=self.ax_right.get_xlim(),
            )
            if show:
                self.seg_page_left_button.grid()
                self.seg_page_right_button.grid()
            else:
                self.seg_page_left_button.grid_remove()
                self.seg_page_right_button.grid_remove()
        except Exception:
            return

    def page_segmentation_x_window(self, direction: int) -> None:
        """Page the segmentation x-window left/right by the current zoom span.

        direction: -1 for left, +1 for right.
        """
        try:
            from visualization.zoom_decisions import compute_paged_xlim

            paged = compute_paged_xlim(
                full_xlim=self._seg_default_xlim,
                cur_xlim=self.ax_right.get_xlim(),
                direction=direction,
            )
            if paged is None:
                self._update_segmentation_paging_controls()
                return

            new_xmin, new_xmax = paged
            self.ax_right.set_xlim(new_xmin, new_xmax)
            self._autoscale_segmentation_y_to_visible(new_xmin, new_xmax)
            self.canvas_right.draw_idle()
            self._update_segmentation_paging_controls()
        except Exception as e:
            try:
                self.status_label.config(text=f"❌ Paging failed: {e}")
            except Exception:
                pass

    def reset_pareto_zoom(self):
        """Reset Pareto plot limits to the defaults for the current route."""
        if not getattr(self, 'is_multi_objective', False):
            return
        try:
            if self._pareto_default_xlim is not None:
                self.ax_left.set_xlim(*self._pareto_default_xlim)
            if self._pareto_default_ylim is not None:
                self.ax_left.set_ylim(*self._pareto_default_ylim)
            self.canvas_left.draw_idle()
        except Exception as e:
            try:
                self.status_label.config(text=f"❌ Reset pareto zoom failed: {e}")
            except Exception:
                pass
        
    def update_visualizations(self):
        """Update both visualizations based on selected route and analysis method."""
        from route_utils import normalize_route_id

        route_id = normalize_route_id(self.route_var.get()) or str(self.route_var.get()).strip()

        try:
            # Get route results for this route
            route_results = self.get_route_results(route_id)
            if not route_results:
                # Avoid blank graphs: show explicit message
                if self.is_multi_objective:
                    self.ax_left.clear()
                    self.ax_left.text(0.5, 0.5, f"No route results found for '{route_id}'",
                                      transform=self.ax_left.transAxes, ha='center', va='center',
                                      fontsize=12, color=COLORS['text_secondary'])
                    self.ax_left.set_title("Pareto Front")

                self.ax_right.clear()
                self.ax_right.text(0.5, 0.5, f"No route results found for '{route_id}'",
                                   transform=self.ax_right.transAxes, ha='center', va='center',
                                   fontsize=12, color=COLORS['text_secondary'])
                self.ax_right.set_title("Segmentation")

                if self.is_multi_objective:
                    self.canvas_left.draw()
                self.canvas_right.draw()
                return

            # Get pareto points. Contract: properly saved results must include at least one.
            processing_results = route_results.get('processing_results', {}) or {}
            pareto_points = processing_results.get('pareto_points', [])
            if not pareto_points:
                error_msg = "Invalid/incompatible results JSON: missing processing_results.pareto_points"
                try:
                    self.status_label.config(text=f"❌ {error_msg}")
                except Exception:
                    pass

                if self.is_multi_objective:
                    self.ax_left.clear()
                    self.ax_left.text(0.5, 0.5, error_msg,
                                      transform=self.ax_left.transAxes, ha='center', va='center',
                                      fontsize=12, color=COLORS['mandatory_bp'])
                    self.ax_left.set_title(f"Pareto Analysis - {route_id}")

                self.ax_right.clear()
                self.ax_right.text(0.5, 0.5, error_msg,
                                   transform=self.ax_right.transAxes, ha='center', va='center',
                                   fontsize=12, color=COLORS['mandatory_bp'])
                self.ax_right.set_title(f"Highway Segmentation - {route_id}")

                if self.is_multi_objective:
                    self.canvas_left.draw()
                self.canvas_right.draw()
                return

            self.pareto_points_data = pareto_points

            # Auto-select point with highest X value BEFORE drawing graphs
            best_point = max(pareto_points, key=lambda p: (p.get('objective_values', [0]) or [0])[0])
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
                        pass
                    _safe_print(f"[ROUTE {route_id}] Hidden Pareto pane for single-objective (degenerate case)")

            # Update segmentation graph (RIGHT pane) with selected point
            self.update_segmentation_graph(route_id)

            # Update paging control visibility after plotting.
            self._update_segmentation_paging_controls()

            # Redraw canvases
            if self.is_multi_objective:
                self.canvas_left.draw()
            self.canvas_right.draw()

        except Exception as e:
            error_msg = f"Visualization error: {e}"
            try:
                self.status_label.config(text=f"❌ {error_msg}")
            except Exception:
                pass
            if self.is_multi_objective:
                self.ax_left.clear()
                self.ax_left.text(0.5, 0.5, error_msg,
                                  transform=self.ax_left.transAxes, ha='center', va='center',
                                  fontsize=12, color=COLORS['mandatory_bp'])
                self.ax_left.set_title("Pareto Front")
            self.ax_right.clear()
            self.ax_right.text(0.5, 0.5, error_msg,
                               transform=self.ax_right.transAxes, ha='center', va='center',
                               fontsize=12, color=COLORS['mandatory_bp'])
            self.ax_right.set_title("Segmentation")
            if self.is_multi_objective:
                try:
                    self.canvas_left.draw()
                except Exception:
                    pass
            try:
                self.canvas_right.draw()
            except Exception:
                pass
        
    def get_current_route_data(self, route_id):
        """Get original data for the specified route from loaded data."""
        from route_utils import normalize_route_id

        route_key = normalize_route_id(route_id) or str(route_id).strip()
        if hasattr(self, 'original_data_by_route') and route_key in self.original_data_by_route:
            return self.original_data_by_route[route_key]
        return None
        
    def get_route_results(self, route_id):
        """Get optimization results for the specified route using actual schema structure."""
        if not self.json_results or 'route_results' not in self.json_results:
            return None

        from route_utils import normalize_route_id

        route_key = normalize_route_id(route_id) or str(route_id).strip()
        for route_result in self.json_results['route_results']:
            candidate = route_result.get('route_info', {}).get('route_id')

            candidate_key = normalize_route_id(candidate) or str(candidate).strip()
            if candidate_key == route_key:
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
            
        series = prepare_pareto_series(self.json_results, pareto_points)

        # If objective_values are not usable, show a clear message instead of a blank plot.
        if not series.x_values or not series.y_values:
            self.ax_left.text(
                0.5,
                0.5,
                "No 2D objective_values available to plot\n(expected 2 objectives per pareto point)",
                transform=self.ax_left.transAxes,
                ha='center',
                va='center',
                fontsize=12,
                color=COLORS['text_secondary'],
            )
            self.ax_left.set_title(f"Pareto Analysis - {route_id}")
            return

        if series.warning:
            _safe_print(f"[WARN] {series.warning}")

        # Clear previous scatter plot references
        self.pareto_scatter_plots = {}
        self.point_id_map = {}  # Map from matplotlib artist to point_id for fast picker events

        # Plot all Pareto points with optimized selection handling
        for i, (x, y, point_id) in enumerate(zip(series.x_values, series.y_values, series.point_ids)):
            is_selected = (self.selected_pareto_point == point_id)

            color = COLORS['pareto_selected'] if is_selected else COLORS['pareto_normal']
            size = 100 if is_selected else 50  # Selected point is larger
            alpha = 0.9 if is_selected else 0.7
            edge_color = COLORS['pareto_border']
            edge_width = 2.5 if is_selected else 1.5  # Selected has thicker border

            scatter = self.ax_left.scatter(
                x,
                y,
                s=size,
                color=color,
                alpha=alpha,
                edgecolors=edge_color,
                linewidth=edge_width,
                picker=5,
                zorder=6 if is_selected else 5,
            )  # picker=5 means 5 pixel tolerance

            # Store scatter plot reference and coordinates for fast access
            self.pareto_scatter_plots[point_id] = {'scatter': scatter, 'x': x, 'y': y}
            self.point_id_map[scatter] = point_id  # Direct mapping for picker events

            # No text annotation needed - visual highlighting is sufficient

        # Set axis labels and title
        self.ax_left.set_xlabel(series.x_label)
        self.ax_left.set_ylabel(series.y_label)
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

        # Cache default limits (used by Reset Pareto Zoom); overwrite each redraw.
        try:
            self._pareto_default_xlim = self.ax_left.get_xlim()
            self._pareto_default_ylim = self.ax_left.get_ylim()
        except Exception:
            pass

            
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
        from visualization.segmentation_data import preprocess_gap_intervals

        return preprocess_gap_intervals(gap_segments)
        
    def _segments_outside_gaps(self, segments, gap_intervals):
        """Efficiently filter segments to exclude those overlapping with gaps.
        
        Args:
            segments: List of (start, end) segment tuples
            gap_intervals: Preprocessed sorted list of (start, end) gap tuples
            
        Returns:
            list: Segments that don't overlap with any gaps
        """
        from visualization.segmentation_data import segments_outside_gaps

        return segments_outside_gaps(segments, gap_intervals)
        
    def update_segmentation_graph(self, route_id):
        """Update RIGHT pane with segmentation graph for the SELECTED ROUTE only."""
        self.ax_right.clear()
        
        # Debug: Segmentation update (removed verbose logging)
        
        # Get original data and optimization results for this specific route
        from route_utils import normalize_route_id

        route_id = normalize_route_id(route_id) or str(route_id).strip()
        route_data = self.get_current_route_data(route_id)
        route_results = self.get_route_results(route_id)
        
        if not route_results:
            self.ax_right.text(0.5, 0.5, 'No optimization results available', 
                             transform=self.ax_right.transAxes, ha='center', va='center',
                             fontsize=12, color=COLORS['text_secondary'])
            self.ax_right.set_title(f"Segmentation - {route_id} (No Results)")
            return
            
        processing_results = route_results.get('processing_results', {}) or {}

        # Get pareto points and find selected point
        pareto_points = processing_results.get('pareto_points', [])
        if not pareto_points:
            self.ax_right.text(0.5, 0.5, 'Invalid/incompatible results JSON: missing pareto_points',
                             transform=self.ax_right.transAxes, ha='center', va='center',
                             fontsize=12, color=COLORS['mandatory_bp'])
            self.ax_right.set_title(f"Highway Segmentation - {route_id} (Invalid Results)")
            return
            
        # Find selected point (or use first if none selected)
        from visualization.pareto import choose_selected_pareto_point

        selected_point = choose_selected_pareto_point(
            pareto_points,
            getattr(self, 'selected_pareto_point', None),
        )
        if not selected_point:
            self.ax_right.text(0.5, 0.5, 'Invalid/incompatible results JSON: empty pareto point list',
                             transform=self.ax_right.transAxes, ha='center', va='center',
                             fontsize=12, color=COLORS['mandatory_bp'])
            self.ax_right.set_title(f"Highway Segmentation - {route_id} (Invalid Results)")
            return
            
        # Get segmentation data
        segmentation = selected_point.get('segmentation', {})
        breakpoints = segmentation.get('breakpoints', [])

        if not breakpoints:
            self.ax_right.text(0.5, 0.5, 'No breakpoints available in results JSON',
                             transform=self.ax_right.transAxes, ha='center', va='center',
                             fontsize=12, color=COLORS['text_secondary'])
            self.ax_right.set_title(f"Highway Segmentation - {route_id} (No Breakpoints)")
            return
        
        # Resolve column names from results JSON.
        # Strict mode: if missing, do NOT guess from the dataframe; show a clear warning.
        from visualization.results_binding import resolve_xy_columns

        xy = resolve_xy_columns(self.json_results)
        x_col = xy.x_col
        y_col = xy.y_col
        
        # Get mandatory breakpoints
        from visualization.breakpoints import extract_mandatory_breakpoints

        mandatory_breakpoints = extract_mandatory_breakpoints(route_results)

        # Always draw breakpoint lines from JSON when available, even if original points are missing.
        if breakpoints:
            from visualization.breakpoints import compute_breakpoint_line_specs

            specs = compute_breakpoint_line_specs(breakpoints, mandatory_breakpoints)
            for spec in specs:
                if spec.kind == 'mandatory':
                    self.ax_right.axvline(
                        x=spec.x,
                        color=COLORS['mandatory_bp'],
                        linestyle='--',
                        linewidth=1.2,
                        alpha=0.9,
                        zorder=3,
                        label=spec.label,
                    )
                else:
                    self.ax_right.axvline(
                        x=spec.x,
                        color=COLORS['analysis_bp'],
                        linestyle='--',
                        linewidth=0.8,
                        alpha=0.8,
                        zorder=3,
                        label=spec.label,
                    )

        # If x/y column info is missing, stop here (breakpoints already drawn).
        if xy.error_message:
            self.app.log_message(f"WARNING: {xy.error_message}")
            self.ax_right.text(
                0.02,
                0.98,
                '⚠️ Missing x/y column info in results JSON\nShowing breakpoints only',
                transform=self.ax_right.transAxes,
                fontsize=11,
                verticalalignment='top',
                color=COLORS['mandatory_bp'],
                weight='bold',
            )

            # Keep the view usable by setting x-limits from breakpoints.
            from visualization.breakpoints import xlim_from_breakpoints

            xlim = xlim_from_breakpoints(breakpoints)
            if xlim:
                self.ax_right.set_xlim(*xlim)

            self._current_seg_x = None
            self._current_seg_y = None

            from visualization.graph_styling import pretty_axis_label

            self.ax_right.set_xlabel(pretty_axis_label(x_col, default='X'))
            self.ax_right.set_ylabel(pretty_axis_label(y_col, default='Y'))
            self.ax_right.set_title(f"Highway Segmentation - {route_id}")
            from visualization.graph_styling import default_segmentation_axis_style

            style = default_segmentation_axis_style()
            self.ax_right.grid(True, alpha=style.grid_alpha, color=COLORS['grid'], zorder=1)

            self.ax_right.xaxis.set_major_locator(MaxNLocator(nbins=style.major_x_nbins, prune=style.major_x_prune))
            self.ax_right.yaxis.set_major_locator(MaxNLocator(nbins=style.major_y_nbins, prune=style.major_y_prune))
            self.ax_right.xaxis.set_minor_locator(MaxNLocator(nbins=style.minor_x_nbins))
            self.ax_right.yaxis.set_minor_locator(MaxNLocator(nbins=style.minor_y_nbins))

            handles, labels = self.ax_right.get_legend_handles_labels()
            from visualization.graph_styling import dedupe_legend_entries

            deduped_labels, deduped_handles = dedupe_legend_entries(labels, handles)
            if deduped_labels:
                self.ax_right.legend(deduped_handles, deduped_labels, loc='best', framealpha=0.9)

            from visualization.zoom_decisions import should_cache_default_limits

            if should_cache_default_limits(x_zoom_enabled=self._seg_x_zoom_enabled):
                try:
                    self._seg_default_xlim = self.ax_right.get_xlim()
                    self._seg_default_ylim = self.ax_right.get_ylim()
                except Exception:
                    pass

            return
        
        # Plot original input data points (Z-order: 2)
        from visualization.original_data_prep import prepare_numeric_xy_series

        prepared_series = prepare_numeric_xy_series(route_data, x_col=x_col, y_col=y_col)
        if prepared_series.error_message:
            self.app.log_message(f"WARNING: {prepared_series.error_message}")
        
        # Only plot original points when numeric preparation succeeded.
        route_data = prepared_series.prepared_df

        if (
            route_data is not None
            and not route_data.empty
            and prepared_series.x_data is not None
            and prepared_series.y_data is not None
        ):
                
            # Plot with improved contrast colors (light gray for original data)
            self.ax_right.scatter(route_data[x_col], route_data[y_col], 
                               alpha=0.8, s=25, color=COLORS['original_data'], 
                               edgecolors=COLORS['original_edge'], linewidth=0.5,
                               label='Original Data Points', zorder=2)
            
            x_data = prepared_series.x_data
            y_data = prepared_series.y_data

            # Cache current series for X-zoom autoscaling
            self._current_seg_x = x_data
            self._current_seg_y = y_data
            
            # Ensure route endpoints are included in mandatory breakpoints
            route_start = np.min(x_data)
            route_end = np.max(x_data)

            from visualization.breakpoints import add_endpoints_to_mandatory_breakpoints

            mandatory_breakpoints = add_endpoints_to_mandatory_breakpoints(
                mandatory_breakpoints,
                route_start,
                route_end,
            )
            
            # Get gap segments from JSON data for this specific route (for display info only)
            route_results = self.get_route_results(route_id)
            from visualization.gap_analysis_data import extract_gap_analysis, should_show_gap_info_once

            gap_info = extract_gap_analysis(route_results)
            gap_segments = gap_info.gap_segments

            # Only print gap info once per route to avoid repetition
            if not hasattr(self, '_gap_info_shown'):
                self._gap_info_shown = set()

            should_print, updated_shown = should_show_gap_info_once(
                route_id=str(route_id),
                total_gaps=gap_info.total_gaps,
                already_shown_routes=self._gap_info_shown,
            )
            self._gap_info_shown = updated_shown

            if should_print:
                _safe_print(f"[INFO] Route '{route_id}': {gap_info.total_gaps} data gaps in original data")
            
            # Efficiently filter segments to exclude gaps (single-pass processing)
            if breakpoints:
                from visualization.segmentation_data import compute_segment_average_lines

                avg_lines = compute_segment_average_lines(
                    x_data=x_data,
                    y_data=y_data,
                    breakpoints=breakpoints,
                    gap_segments=gap_segments,
                )
                for line in avg_lines:
                    # Draw horizontal segment average line with bolder blue
                    self.ax_right.plot(
                        [line.start_x, line.end_x],
                        [line.avg_y, line.avg_y],
                        color=COLORS['segment_avg'],
                        linewidth=3,
                        alpha=0.9,
                        zorder=4,
                        solid_capstyle='butt',
                        label=line.label,
                    )
                                             
        else:
            # No original points available for this route; still show breakpoints from JSON.
            self.ax_right.text(
                0.02,
                0.98,
                '⚠️ Original data points not available\nShowing breakpoints only',
                transform=self.ax_right.transAxes,
                fontsize=11,
                verticalalignment='top',
                color=COLORS['mandatory_bp'],
                weight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFF8E1', alpha=0.9, edgecolor=COLORS['mandatory_bp']),
            )

            # If we have breakpoints, set a reasonable x-range to keep the view usable.
            from visualization.breakpoints import xlim_from_breakpoints

            xlim = xlim_from_breakpoints(breakpoints)
            if xlim:
                self.ax_right.set_xlim(*xlim)

            # No points available; disable autoscale input but keep current Y as requested.
            self._current_seg_x = None
            self._current_seg_y = None
        
        # Set labels and title with pleasant styling
        from visualization.graph_styling import pretty_axis_label

        self.ax_right.set_xlabel(pretty_axis_label(x_col, default='X'))
        self.ax_right.set_ylabel(pretty_axis_label(y_col, default='Y'))
        self.ax_right.set_title(f"Highway Segmentation - {route_id}")
        from visualization.graph_styling import default_segmentation_axis_style

        style = default_segmentation_axis_style()
        self.ax_right.grid(True, alpha=style.grid_alpha, color=COLORS['grid'], zorder=1)  # Grid at lowest Z-order

        # Set automatic tick intervals for better readability
        self.ax_right.xaxis.set_major_locator(MaxNLocator(nbins=style.major_x_nbins, prune=style.major_x_prune))
        self.ax_right.yaxis.set_major_locator(MaxNLocator(nbins=style.major_y_nbins, prune=style.major_y_prune))

        # Add minor ticks for precision
        self.ax_right.xaxis.set_minor_locator(MaxNLocator(nbins=style.minor_x_nbins))
        self.ax_right.yaxis.set_minor_locator(MaxNLocator(nbins=style.minor_y_nbins))
        
        # Add legend (remove duplicates)
        handles, labels = self.ax_right.get_legend_handles_labels()
        from visualization.graph_styling import dedupe_legend_entries

        deduped_labels, deduped_handles = dedupe_legend_entries(labels, handles)
        if deduped_labels:
            self.ax_right.legend(deduped_handles, deduped_labels, loc='best', framealpha=0.9)

        # Cache default segmentation limits for reset.
        # Only update defaults when X-zoom is currently OFF (so reset returns to full view).
        from visualization.zoom_decisions import should_cache_default_limits

        if should_cache_default_limits(x_zoom_enabled=self._seg_x_zoom_enabled):
            try:
                self._seg_default_xlim = self.ax_right.get_xlim()
                self._seg_default_ylim = self.ax_right.get_ylim()
            except Exception:
                pass

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
                    "📋 10 comprehensive data tabs created\\n\\n" +
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
            _safe_print(f"[FILE] Loading results from: {json_results_path}")
            with open(json_results_path, 'r') as f:
                json_data = json.load(f)
        elif json_results_data:
            json_data = json_results_data
            # Using provided JSON results data
        else:
            json_data = None
            _safe_print("[WARN] No JSON results provided, showing data visualization only")
        
        # Get original data from parent app
        original_data = None
        
        # Extract original data from parent app if available, but do NOT require it.
        # When opening a results JSON, the visualization can load original data
        # from the stored file path in the JSON (or fall back to breakpoints-only).
        if hasattr(parent_app, 'data') and parent_app.data is not None:
            if hasattr(parent_app.data, 'route_data'):
                original_data = parent_app.data.route_data
            else:
                original_data = parent_app.data
        
        # Determine X/Y column mapping.
        # Prefer parent app selection, but fall back to JSON metadata when no CSV is loaded.
        x_col = None
        y_col = None

        if hasattr(parent_app, 'x_column') and hasattr(parent_app.x_column, 'get'):
            try:
                x_col = parent_app.x_column.get()
            except Exception:
                x_col = None
        if hasattr(parent_app, 'y_column') and hasattr(parent_app.y_column, 'get'):
            try:
                y_col = parent_app.y_column.get()
            except Exception:
                y_col = None

        if (not x_col or not y_col) and json_data:
            route_processing = json_data.get('input_parameters', {}).get('route_processing', {})
            x_col = x_col or route_processing.get('x_column')
            y_col = y_col or route_processing.get('y_column')

            if not x_col or not y_col:
                column_info = json_data.get('analysis_metadata', {}).get('input_file_info', {}).get('column_info', {})
                x_col = x_col or column_info.get('x_column')
                y_col = y_col or column_info.get('y_column')

        if not x_col or not y_col:
            messagebox.showerror(
                "Column Selection Error",
                "Could not determine X and Y axis columns.\n\n"
                "Select X/Y in the app, or open a results file that contains column metadata.",
            )
            return None
        
        # If original data is already loaded in the app, validate that X/Y exist and are numeric.
        # If not loaded, allow opening the visualization; it will try to load original data
        # from the JSON's stored file path and will fall back to breakpoints-only.
        if original_data is not None:
            missing_cols = []
            if x_col not in original_data.columns:
                missing_cols.append(f"'{x_col}'")
            if y_col not in original_data.columns:
                missing_cols.append(f"'{y_col}'")

            if missing_cols:
                available = "', '".join(original_data.columns[:8])  # Show first 8 columns
                more_msg = f" (and {len(original_data.columns)-8} more)" if len(original_data.columns) > 8 else ""
                messagebox.showerror(
                    "Column Not Found",
                    f"Selected columns not found in loaded data:\n{', '.join(missing_cols)}\n\n"
                    f"Available columns: '{available}'{more_msg}",
                )
                return None

            for col_name, col_purpose in [(x_col, 'X-axis'), (y_col, 'Y-axis')]:
                col_data = original_data[col_name]
                if not pd.api.types.is_numeric_dtype(col_data):
                    sample_values = list(col_data.dropna().head(3))
                    messagebox.showerror(
                        "Data Type Error",
                        f"{col_purpose} column '{col_name}' contains non-numeric data.\n"
                        f"Visualization requires numeric columns for analysis.\n\n"
                        f"Sample values: {sample_values}",
                    )
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
        _safe_print(f"[ERROR] Error opening enhanced visualization: {e}")
        return None