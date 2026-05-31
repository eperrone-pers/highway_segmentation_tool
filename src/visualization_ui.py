"""Enhanced paned-window visualization for Highway Segmentation results.

Integrates directly with the main application and shows a resizable two-pane view:
- Left pane: Pareto front (multi-objective) or fitness history
- Right pane: segmentation overlay on the original data signal

Supports interactive route selection, JSON-driven results, and optional original CSV data.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
import pandas as pd
import numpy as np
import logging
import json
import os
from pathlib import Path
from datetime import datetime
import warnings
from matplotlib.ticker import MaxNLocator
from matplotlib.patches import Rectangle
from matplotlib import transforms
from matplotlib import colors as mcolors
import bisect

from route_utils import normalize_route_column_selection, normalize_route_id
from visualization.utils import safe_print as _safe_print, default_colors
from visualization.results_binding import (
    resolve_routes,
    original_data_path_from_results,
    find_existing_original_data_file,
    group_original_data_by_route,
)
from visualization.pareto import prepare_pareto_series

logger = logging.getLogger(__name__)

# Matplotlib may emit this warning during draw/zoom when layout can't satisfy all decorations.
# It's noisy (not fatal) and can be triggered by draw paths outside our control (e.g. toolbar).
warnings.filterwarnings(
    "ignore",
    message=r"Tight layout not applied.*",
    category=UserWarning,
)


# Pleasant color scheme - updated for better contrast
COLORS = default_colors()


from visualization_ui_builder import SECONDARY_NONE_SENTINEL, VisualizationUIBuilder  # noqa: E402


class EnhancedVisualizationWindow:
    """Enhanced paned window visualization for optimization results."""

    def _contrast_text_color(self, fill_rgba) -> str:
        """Return a readable text color for a filled patch (white on dark, dark on light)."""
        try:
            r, g, b, _a = fill_rgba
            lum = 0.2126 * float(r) + 0.7152 * float(g) + 0.0722 * float(b)
            return "white" if lum < 0.55 else COLORS.get('pareto_border', COLORS['text_secondary'])
        except Exception:
            return COLORS.get('pareto_border', COLORS['text_secondary'])
    
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
            error_msg = f"Column mapping configuration is required but missing: x_column='{x_column}', y_column='{y_column}'"
            logger.error("EnhancedVisualizationWindow initialization failed: %s", error_msg)
            raise ValueError(f"Invalid column configuration: {error_msg}")
        
        self.parent_app = parent_app
        # Backward-compatible alias: existing visualization code uses self.app.*
        self.app = parent_app
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
        self._seg_xzoom_var = tk.BooleanVar(value=False)
        self._show_break_lanes_var = tk.BooleanVar(value=True)
        self._show_preprocessing_changes_var = tk.BooleanVar(value=False)
        self._seg_default_xlim = None
        self._seg_default_ylim = None
        self._seg_default_ylim_secondary = None
        self._pareto_default_xlim = None
        self._pareto_default_ylim = None
        self._current_seg_x = None
        self._current_seg_y = None
        self._current_seg_secondary_x = None
        self._current_seg_secondary_y = None
        self._last_seg_route_id = None

        # Hover highlight state (blit-based nearest-point ring)
        # _hover_seg_x/y are always the paired post-processing primary points used
        # for nearest-point snapping. Kept separate from _current_seg_x/y because
        # _current_seg_y is extended with preprocessing overlay y values for
        # autoscaling when the preprocessing panel is visible, making the arrays
        # different lengths and unusable for paired distance calculations.
        self._hover_seg_x = None
        self._hover_seg_y = None
        self._hover_bg = None
        self._hover_primary_ring = None
        self._hover_secondary_ring = None

        # Secondary Y-axis series state (one optional series)
        self._secondary_y_col = None
        self._secondary_color = COLORS.get('secondary_default', '#14B8A6')
        self._secondary_points_alpha = 0.25
        self._ax_right_secondary = None
        self._route_column_name = None

        # Debounce handle for secondary UI-driven redraws
        self._secondary_redraw_after_id = None

        # Noise suppression: avoid repeating console messages on redraw.
        self._pareto_hidden_logged = False
        
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
        VisualizationUIBuilder(self).build()

    def _position_main_paned_sash_handle(self) -> None:
        """Position the sash grip overlay over the paned divider."""

        try:
            if not hasattr(self, 'main_paned'):
                return
            if not hasattr(self, '_sash_handle') or self._sash_handle is None:
                return

            panes = []
            try:
                panes = list(self.main_paned.panes())
            except Exception:
                panes = []

            if not panes or len(panes) < 2:
                try:
                    self._sash_handle.place_forget()
                except Exception:
                    pass
                return

            if hasattr(self, 'left_frame') and str(self.left_frame) not in panes:
                try:
                    self._sash_handle.place_forget()
                except Exception:
                    pass
                return

            sx, _sy = self.main_paned.sash_coord(0)
            try:
                sash_w = int(self.main_paned.cget('sashwidth'))
            except Exception:
                sash_w = 10

            h = int(self.main_paned.winfo_height() or 0)
            if h <= 0:
                return

            self._sash_handle.update_idletasks()
            lw = int(self._sash_handle.winfo_reqwidth() or 0)
            lh = int(self._sash_handle.winfo_reqheight() or 0)

            x = int(sx + (sash_w / 2) - (lw / 2))
            y = int((h / 2) - (lh / 2))

            self._sash_handle.place(x=x, y=y)
        except Exception:
            return
        
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
                self._route_column_name = route_column

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

                # If the UI is already built, refresh secondary column options.
                try:
                    self._refresh_secondary_column_options()
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

        try:
            self._refresh_secondary_column_options()
        except Exception:
            pass


    def _infer_numeric_columns(self, df: pd.DataFrame) -> list[str]:
        """Best-effort inference of numeric columns from a dtype=str dataframe."""

        if df is None or df.empty:
            return []

        numeric_cols: list[str] = []
        total = len(df)

        # A column is considered numeric if numeric coercion yields a reasonable
        # fraction of valid values. This is intentionally permissive because the
        # CSV is loaded as dtype=str.
        for col in df.columns:
            try:
                coerced = pd.to_numeric(df[col], errors='coerce')
            except Exception:
                continue

            non_nan = int(coerced.notna().sum())
            if non_nan <= 0:
                continue

            if total <= 0:
                continue

            ratio = non_nan / total
            if ratio >= 0.60:
                numeric_cols.append(str(col))

        return numeric_cols


    def _refresh_secondary_column_options(self) -> None:
        """Refresh the secondary column dropdown from loaded original data."""

        if not hasattr(self, 'secondary_column_combo'):
            return

        if self.original_data is None or getattr(self.original_data, 'empty', True):
            self.secondary_column_combo.configure(values=[SECONDARY_NONE_SENTINEL])
            self.secondary_column_var.set(SECONDARY_NONE_SENTINEL)
            try:
                self.secondary_column_combo.configure(state='disabled')
            except Exception:
                pass
            return

        numeric_cols = self._infer_numeric_columns(self.original_data)

        excluded = {
            str(self.x_column) if self.x_column else None,
            str(self.y_column) if self.y_column else None,
            str(self._route_column_name) if self._route_column_name else None,
        }

        candidates = [c for c in numeric_cols if c not in excluded]
        candidates = sorted(set(candidates), key=lambda s: s.lower())

        values = [SECONDARY_NONE_SENTINEL] + candidates
        self.secondary_column_combo.configure(values=values)
        try:
            self.secondary_column_combo.configure(state='readonly')
        except Exception:
            pass

        current = self.secondary_column_var.get() or SECONDARY_NONE_SENTINEL
        if current not in values:
            self.secondary_column_var.set(SECONDARY_NONE_SENTINEL)

        # No explicit apply button; graph updates via live control changes.


    def _choose_secondary_color(self) -> None:
        """Open a color picker for the secondary series."""

        initial = self.secondary_color_var.get() or self._secondary_color
        chosen = colorchooser.askcolor(color=initial, parent=self.window)
        if not chosen or not chosen[1]:
            return

        self.secondary_color_var.set(chosen[1])
        try:
            if hasattr(self, 'secondary_color_swatch'):
                self.secondary_color_swatch.configure(bg=chosen[1])
        except Exception:
            pass

        # Live update
        self._schedule_secondary_redraw()


    def _on_secondary_alpha_changed(self, _value: str) -> None:
        """Handle alpha slider change (debounced redraw for responsiveness)."""

        try:
            alpha = float(self.secondary_alpha_var.get())
        except Exception:
            return

        alpha = max(0.0, min(1.0, alpha))
        try:
            self.secondary_alpha_value_label.configure(text=f"{alpha:.2f}")
        except Exception:
            pass

        self._schedule_secondary_redraw()


    def _schedule_secondary_redraw(self) -> None:
        """Debounce redraws from secondary controls to keep UI responsive."""

        try:
            if self._secondary_redraw_after_id is not None:
                self.window.after_cancel(self._secondary_redraw_after_id)
        except Exception:
            pass

        try:
            self._secondary_redraw_after_id = self.window.after(200, self._apply_secondary_series)
        except Exception:
            self._secondary_redraw_after_id = None


    def _apply_secondary_series(self) -> None:
        """Apply the selected secondary column/color and refresh the segmentation plot."""

        selected = (self.secondary_column_var.get() or SECONDARY_NONE_SENTINEL).strip()
        if selected == SECONDARY_NONE_SENTINEL:
            self._secondary_y_col = None
        else:
            self._secondary_y_col = selected

        color = (self.secondary_color_var.get() or '').strip()
        if color:
            self._secondary_color = color

        try:
            alpha = float(getattr(self, 'secondary_alpha_var', None).get())
            self._secondary_points_alpha = max(0.0, min(1.0, alpha))
        except Exception:
            # Keep last value
            pass

        try:
            route_id = self.route_var.get()
            self.update_segmentation_graph(route_id)
            self._draw_right_canvas(idle=True)
        except Exception as e:
            try:
                self.status_label.config(text=f"❌ Secondary plot update failed: {e}")
            except Exception:
                pass
        
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
            if hasattr(self, '_seg_xzoom_var'):
                self._seg_xzoom_var.set(False)
        except Exception:
            pass
        try:
            if hasattr(self, '_seg_span_selector'):
                self._seg_span_selector.set_active(False)
                # Clear any prior selection highlight
                try:
                    rect = getattr(self._seg_span_selector, 'rect', None)
                    if rect is not None:
                        rect.set_visible(False)
                except Exception:
                    pass
        except Exception:
            pass
        self.update_visualizations()

    def toggle_segmentation_x_zoom(self):
        """Toggle X-only zoom mode for the segmentation plot."""
        # When using a toggle-style control, treat the variable as source of truth.
        try:
            self._seg_x_zoom_enabled = bool(self._seg_xzoom_var.get())
        except Exception:
            self._seg_x_zoom_enabled = not self._seg_x_zoom_enabled
        try:
            if hasattr(self, '_seg_span_selector'):
                self._seg_span_selector.set_active(self._seg_x_zoom_enabled)

                # If toggling OFF, reset zoom and remove selection highlight.
                if not self._seg_x_zoom_enabled:
                    self._clear_segmentation_xzoom_highlight(force_draw=False)

                    # Reset to full view so paging/zoom highlight is cleared.
                    try:
                        self.reset_segmentation_zoom()
                    except Exception:
                        pass
                else:
                    # If toggling ON, allow selection rectangle to show when used.
                    try:
                        rect = getattr(self._seg_span_selector, 'rect', None)
                        if rect is not None:
                            rect.set_visible(True)
                    except Exception:
                        pass

        except Exception:
            pass

    def _clear_segmentation_xzoom_highlight(self, *, force_draw: bool = True) -> None:
        """Best-effort removal of the SpanSelector selection overlay.

        With blitting enabled, the selection rectangle can sometimes appear to
        "stick" unless we explicitly hide all selector artists and redraw.
        """

        try:
            selector = getattr(self, '_seg_span_selector', None)
            if selector is None:
                return

            # Common public attribute.
            rect = getattr(selector, 'rect', None)
            if rect is not None:
                try:
                    rect.set_visible(False)
                except Exception:
                    pass

            # Newer matplotlib versions may store artists differently.
            for attr_name in ('artists', '_artists', '_selection_artist', '_selection_patch'):
                artist_obj = getattr(selector, attr_name, None)
                if artist_obj is None:
                    continue
                try:
                    if isinstance(artist_obj, (list, tuple)):
                        for a in artist_obj:
                            try:
                                a.set_visible(False)
                            except Exception:
                                pass
                    else:
                        artist_obj.set_visible(False)
                except Exception:
                    pass

            # Some interactive selectors add handles.
            for attr_name in ('_handles', 'handles', '_edge_handles', '_center_handle'):
                handles = getattr(selector, attr_name, None)
                if handles is None:
                    continue
                try:
                    if isinstance(handles, (list, tuple)):
                        for h in handles:
                            try:
                                h.set_visible(False)
                            except Exception:
                                pass
                    else:
                        handles.set_visible(False)
                except Exception:
                    pass
        except Exception:
            return

        if force_draw:
            try:
                # Force a full redraw so any blitted overlay is cleared.
                self._draw_right_canvas()
            except Exception:
                try:
                    self._draw_right_canvas(idle=True)
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
            self._autoscale_secondary_y_to_visible(xmin, xmax)

            self._draw_right_canvas(idle=True)
            self._update_segmentation_paging_controls()
        except Exception as e:
            try:
                self.status_label.config(text=f"❌ X Zoom failed: {e}")
            except Exception:
                pass

    def reset_segmentation_x_zoom(self) -> None:
        """Reset X-zoom in the same way as unchecking the X Zoom checkbox.

        If X-zoom is currently enabled, we invoke the checkbox so the exact same
        command path runs (SpanSelector state, highlight clearing, etc.). If it
        is already disabled, fall back to a normal reset.
        """

        try:
            is_enabled = bool(getattr(self, '_seg_xzoom_var', None) and self._seg_xzoom_var.get())
        except Exception:
            is_enabled = bool(getattr(self, '_seg_x_zoom_enabled', False))

        if is_enabled:
            # Use the widget invocation when possible to guarantee identical behavior.
            try:
                if hasattr(self, 'seg_xzoom_button'):
                    self.seg_xzoom_button.invoke()
                    return
            except Exception:
                pass

            # Fallback: manually unset and run the toggle handler.
            try:
                if hasattr(self, '_seg_xzoom_var'):
                    self._seg_xzoom_var.set(False)
            except Exception:
                pass
            try:
                self.toggle_segmentation_x_zoom()
                return
            except Exception:
                pass

        # If already off, keep "reset zoom" semantics.
        self.reset_segmentation_zoom()

    def reset_segmentation_zoom(self):
        """Reset segmentation plot limits to the defaults for the current route."""
        try:
            # Resetting zoom should also exit X-zoom mode and clear any selection highlight.
            self._seg_x_zoom_enabled = False
            try:
                if hasattr(self, '_seg_xzoom_var'):
                    self._seg_xzoom_var.set(False)
            except Exception:
                pass

            try:
                if hasattr(self, '_seg_span_selector'):
                    self._seg_span_selector.set_active(False)
                    self._clear_segmentation_xzoom_highlight(force_draw=False)
            except Exception:
                pass

            if self._seg_default_xlim is not None:
                self.ax_right.set_xlim(*self._seg_default_xlim)
            if self._seg_default_ylim is not None:
                self.ax_right.set_ylim(*self._seg_default_ylim)
            if getattr(self, '_ax_right_secondary', None) is not None and self._seg_default_ylim_secondary is not None:
                try:
                    self._ax_right_secondary.set_ylim(*self._seg_default_ylim_secondary)
                except Exception:
                    pass

            # Keep the toggle label/appearance consistent.
            try:
                if hasattr(self, 'seg_xzoom_button'):
                    self.seg_xzoom_button.configure(text="X Zoom")
            except Exception:
                pass

            # Use a full draw to ensure any blitted selection overlay is cleared.
            try:
                self._draw_right_canvas()
            except Exception:
                self._draw_right_canvas(idle=True)
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

    def _autoscale_secondary_y_to_visible(self, xmin: float, xmax: float) -> None:
        """Autoscale secondary Y limits to points visible within [xmin, xmax]."""

        try:
            sec_ax = getattr(self, '_ax_right_secondary', None)
            if sec_ax is None:
                return
            if self._current_seg_secondary_x is None or self._current_seg_secondary_y is None:
                return

            from visualization.autoscale import autoscale_y_limits, visible_y_values_in_x_window

            y_vis = visible_y_values_in_x_window(
                self._current_seg_secondary_x,
                self._current_seg_secondary_y,
                xmin=xmin,
                xmax=xmax,
            )
            if y_vis is None:
                return

            y_limits = autoscale_y_limits(y_vis, pad_fraction=0.05, min_pad=1.0)
            if y_limits is None:
                return

            sec_ax.set_ylim(*y_limits)
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
            self._autoscale_secondary_y_to_visible(new_xmin, new_xmax)
            self._draw_right_canvas(idle=True)
            self._update_segmentation_paging_controls()
        except Exception as e:
            try:
                self.status_label.config(text=f"❌ Paging failed: {e}")
            except Exception:
                pass

    def _safe_canvas_draw(self, canvas, *, idle: bool = False) -> None:
        """Draw a matplotlib canvas while suppressing noisy tight_layout warnings."""
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"Tight layout not applied.*",
                    category=UserWarning,
                )
                if idle:
                    canvas.draw_idle()
                else:
                    canvas.draw()
        except Exception:
            # Never let draw failures crash the UI.
            try:
                if idle:
                    canvas.draw_idle()
                else:
                    canvas.draw()
            except Exception:
                pass

    def _draw_left_canvas(self, *, idle: bool = False) -> None:
        if getattr(self, 'canvas_left', None) is None:
            return
        self._safe_canvas_draw(self.canvas_left, idle=idle)

    def _draw_right_canvas(self, *, idle: bool = False) -> None:
        if getattr(self, 'canvas_right', None) is None:
            return
        self._safe_canvas_draw(self.canvas_right, idle=idle)

    # ------------------------------------------------------------------
    # Hover highlight: coordinate label + blit-based nearest-point ring
    # ------------------------------------------------------------------

    def _setup_hover_artists(self) -> None:
        """Create animated highlight ring artists on ax_right (and secondary axis if active).

        Called at the end of each full plot redraw so the artists survive ax_right.clear().
        The rings use animated=True so they are excluded from normal canvas draws and only
        appear during blit operations — this avoids any visual cost when the cursor is idle.
        """
        try:
            ring_kw = dict(
                marker='o', ms=11, mfc='none', mew=2,
                animated=True, zorder=10, ls='none', clip_on=True,
            )
            self._hover_primary_ring, = self.ax_right.plot(
                [], [], color=COLORS.get('segment_avg', '#2563EB'), **ring_kw
            )
            self._hover_secondary_ring = None
            ax2 = getattr(self, '_ax_right_secondary', None)
            if ax2 is not None:
                color2 = getattr(self, '_secondary_color', '#14B8A6')
                self._hover_secondary_ring, = ax2.plot([], [], color=color2, **ring_kw)
            self._hover_bg = None  # Invalidated; will be refreshed on next draw event
        except Exception:
            self._hover_primary_ring = None
            self._hover_secondary_ring = None
            self._hover_bg = None

    def _update_hover_highlight(self, event) -> None:
        """Update the coord label and blit-based highlight rings on mouse move.

        Primary series takes precedence when both are within the 8-pixel snap threshold.
        When snapped, the label shows exact data values; otherwise it shows cursor position.
        """
        try:
            coord_label = getattr(self, 'coord_label', None)

            # --- Clear and return when cursor is outside the plot axes ---
            if event is None or event.inaxes != self.ax_right or event.xdata is None or event.ydata is None:
                if coord_label is not None:
                    coord_label.config(text='')
                self._blit_rings(show_primary=False, show_secondary=False,
                                 px=0, py=0, sx=0, sy=0)
                return

            x_cursor = float(event.xdata)
            y_cursor = float(event.ydata)
            cursor_px = np.array([event.x, event.y])

            # --- Find nearest primary point (pixel distance) ---
            primary_snapped = False
            px, py = x_cursor, y_cursor
            # Use _hover_seg_x/y (always paired, post-processing) not _current_seg_x/y,
            # which may have its y extended with preprocessing overlay values for autoscaling.
            primary_x = getattr(self, '_hover_seg_x', None)
            primary_y = getattr(self, '_hover_seg_y', None)
            if primary_x is not None and primary_y is not None and len(primary_x) > 0:
                try:
                    pts = np.column_stack([primary_x, primary_y])
                    pts_disp = self.ax_right.transData.transform(pts)
                    dists = np.hypot(pts_disp[:, 0] - cursor_px[0], pts_disp[:, 1] - cursor_px[1])
                    idx = int(np.argmin(dists))
                    if dists[idx] <= 8.0:
                        primary_snapped = True
                        px, py = float(primary_x[idx]), float(primary_y[idx])
                except Exception:
                    pass

            # --- Find nearest secondary point (pixel distance on secondary axis) ---
            secondary_snapped = False
            sx, sy = x_cursor, y_cursor
            ax2 = getattr(self, '_ax_right_secondary', None)
            sec_x = getattr(self, '_current_seg_secondary_x', None)
            sec_y = getattr(self, '_current_seg_secondary_y', None)
            if ax2 is not None and sec_x is not None and sec_y is not None and len(sec_x) > 0:
                try:
                    pts2 = np.column_stack([sec_x, sec_y])
                    pts2_disp = ax2.transData.transform(pts2)
                    dists2 = np.hypot(pts2_disp[:, 0] - cursor_px[0], pts2_disp[:, 1] - cursor_px[1])
                    idx2 = int(np.argmin(dists2))
                    if dists2[idx2] <= 8.0:
                        secondary_snapped = True
                        sx, sy = float(sec_x[idx2]), float(sec_y[idx2])
                except Exception:
                    pass

            # --- Build coordinate label text ---
            # Only show the y value(s) for the series that is actually snapped.
            # When neither is snapped, show raw cursor position on the primary axis.
            if coord_label is not None:
                x_name = getattr(self, 'x_column', None) or 'X'
                y_name = getattr(self, 'y_column', None) or 'Y'
                sec_name = getattr(self, '_secondary_y_col', None)

                if primary_snapped and secondary_snapped and sec_name:
                    # Both snapped: primary takes precedence for x; show both y values.
                    text = (f"{x_name}: {px:.4f} ●   {y_name}: {py:.4f}"
                            f"   {sec_name}: {sy:.4f} ●")
                elif primary_snapped:
                    text = f"{x_name}: {px:.4f} ●   {y_name}: {py:.4f}"
                elif secondary_snapped and sec_name:
                    # Secondary only: show the secondary point's x and y — do NOT
                    # include the primary y since no primary point is highlighted.
                    text = f"{x_name}: {sx:.4f} ●   {sec_name}: {sy:.4f}"
                else:
                    # No snap: show raw cursor position on primary axis.
                    text = f"{x_name}: {x_cursor:.4f}   {y_name}: {y_cursor:.4f}"

                coord_label.config(text=text)

            # --- Blit the rings ---
            self._blit_rings(
                show_primary=primary_snapped, px=px, py=py,
                show_secondary=secondary_snapped, sx=sx, sy=sy,
            )
        except Exception:
            pass

    def _blit_rings(self, *, show_primary: bool, px: float, py: float,
                    show_secondary: bool, sx: float, sy: float) -> None:
        """Restore saved background and blit highlight rings in one pass."""
        try:
            bg = getattr(self, '_hover_bg', None)
            canvas = getattr(self, 'canvas_right', None)
            if bg is None or canvas is None:
                return

            primary_ring = getattr(self, '_hover_primary_ring', None)
            secondary_ring = getattr(self, '_hover_secondary_ring', None)

            if primary_ring is None and secondary_ring is None:
                return

            canvas.restore_region(bg)

            if primary_ring is not None:
                if show_primary:
                    primary_ring.set_data([px], [py])
                else:
                    primary_ring.set_data([], [])
                self.ax_right.draw_artist(primary_ring)

            ax2 = getattr(self, '_ax_right_secondary', None)
            if secondary_ring is not None and ax2 is not None:
                if show_secondary:
                    secondary_ring.set_data([sx], [sy])
                else:
                    secondary_ring.set_data([], [])
                ax2.draw_artist(secondary_ring)

            canvas.blit(self.ax_right.bbox)
        except Exception:
            pass

    def _ensure_break_lane_tooltip(self) -> None:
        """Ensure the Tkinter tooltip window exists (used for break-lane hover)."""
        try:
            win = getattr(self, '_break_lane_tooltip_win', None)
            if win is not None:
                try:
                    if bool(win.winfo_exists()):
                        return
                except Exception:
                    pass

            win = tk.Toplevel(self.window)
            win.withdraw()
            win.overrideredirect(True)
            try:
                win.attributes('-topmost', True)
            except Exception:
                pass

            label = tk.Label(
                win,
                text='',
                justify='left',
                bg='white',
                fg=COLORS.get('pareto_border', COLORS['text_secondary']),
                bd=1,
                relief='solid',
                padx=6,
                pady=3,
            )
            label.pack()

            self._break_lane_tooltip_win = win
            self._break_lane_tooltip_label = label
        except Exception:
            self._break_lane_tooltip_win = None
            self._break_lane_tooltip_label = None

    def _cancel_break_lane_hover(self) -> None:
        try:
            pending = getattr(self, '_break_lane_hover_after_id', None)
            if pending is not None and hasattr(self, 'window'):
                try:
                    self.window.after_cancel(pending)
                except Exception:
                    pass
        finally:
            self._break_lane_hover_after_id = None
            self._break_lane_hover_pending = None

    def _hide_break_lane_tooltip(self, _event=None) -> None:
        try:
            self._cancel_break_lane_hover()
            self._break_lane_hover_active_patch = None
            win = getattr(self, '_break_lane_tooltip_win', None)
            if win is not None:
                try:
                    win.withdraw()
                except Exception:
                    pass
        except Exception:
            return

    def _show_break_lane_tooltip(self) -> None:
        """Show tooltip for the currently pending hover target."""
        try:
            self._break_lane_hover_after_id = None
            pending = getattr(self, '_break_lane_hover_pending', None)
            if not pending:
                return

            active_key, col_name, value, x_root, y_root = pending

            self._ensure_break_lane_tooltip()
            win = getattr(self, '_break_lane_tooltip_win', None)
            label = getattr(self, '_break_lane_tooltip_label', None)
            if win is None or label is None:
                return

            v = (value or '').strip()
            if not v:
                v = '(blank)'

            label.configure(text=f"{col_name}: {v}")

            try:
                x = int(x_root) + 12 if x_root is not None else 0
                y = int(y_root) + 12 if y_root is not None else 0
                win.geometry(f"+{x}+{y}")
            except Exception:
                pass

            try:
                win.deiconify()
                win.lift()
            except Exception:
                pass

            self._break_lane_hover_active_patch = active_key
        except Exception:
            return

    def _on_segmentation_mouse_move(self, event) -> None:
        """Update coordinate label, highlight nearest data point, and show break-lane tooltips."""
        # Named coordinate display + blit highlight (independent of break-lane logic below)
        self._update_hover_highlight(event)

        try:
            if event is None or event.inaxes != self.ax_right:
                self._hide_break_lane_tooltip()
                return

            # Only active when lanes are enabled.
            try:
                if not bool(self._show_break_lanes_var.get()):
                    self._hide_break_lane_tooltip()
                    return
            except Exception:
                self._hide_break_lane_tooltip()
                return

            if getattr(event, 'x', None) is None or getattr(event, 'y', None) is None:
                self._hide_break_lane_tooltip()
                return

            hit_target = None
            try:
                overlay = getattr(self, '_break_lane_overlay_bounds', None)
                lanes = getattr(self, '_break_lane_hover_lanes', []) or []
                if overlay and lanes and event.xdata is not None:
                    inv = self.ax_right.transAxes.inverted()
                    _x_axes, y_axes = inv.transform((event.x, event.y))
                    bottom, top = overlay
                    if y_axes < bottom or y_axes > top:
                        hit_target = None
                    else:
                        x = float(event.xdata)
                        for lane in lanes:
                            if y_axes >= lane.get('y0', -1.0) and y_axes <= lane.get('y1', -1.0):
                                starts = lane.get('starts', [])
                                boxes = lane.get('boxes', [])
                                if not starts or not boxes:
                                    break
                                i = bisect.bisect_right(starts, x) - 1
                                if 0 <= i < len(boxes):
                                    s, e, v = boxes[i]
                                    if x >= s and x <= e:
                                        hit_target = ((int(lane.get('lane_idx', 0)), int(i)), lane.get('col', ''), v)
                                break
            except Exception:
                hit_target = None

            if hit_target is None:
                self._hide_break_lane_tooltip()
                return

            active_key, col_name, value = hit_target

            # Compute screen coords for a Tk tooltip without redrawing the plot.
            x_root = None
            y_root = None
            try:
                ge = getattr(event, 'guiEvent', None)
                if ge is not None and hasattr(ge, 'x_root') and hasattr(ge, 'y_root'):
                    x_root = ge.x_root
                    y_root = ge.y_root
            except Exception:
                pass
            if x_root is None or y_root is None:
                try:
                    widget = self.canvas_right.get_tk_widget()
                    x_root = int(widget.winfo_rootx()) + int(event.x)
                    y_root = int(widget.winfo_rooty()) + int(event.y)
                except Exception:
                    x_root = None
                    y_root = None

            # If we're already showing this same target, do nothing (avoids work).
            if active_key == getattr(self, '_break_lane_hover_active_patch', None):
                return

            # Debounce: wait briefly before showing (prevents flicker + busy cursor).
            self._cancel_break_lane_hover()
            self._break_lane_hover_pending = (active_key, col_name, value, x_root, y_root)
            try:
                if hasattr(self, 'window'):
                    self._break_lane_hover_after_id = self.window.after(150, self._show_break_lane_tooltip)
            except Exception:
                # Fallback: show immediately
                self._show_break_lane_tooltip()
        except Exception:
            return

    def _on_segmentation_draw(self, event) -> None:
        """After draw, decide which lane labels can fit (pixel-accurate), and save blit background."""
        try:
            if event is None or getattr(event, 'canvas', None) is None:
                return

            # Only update for our right canvas.
            if getattr(self, 'canvas_right', None) is None or event.canvas != self.canvas_right:
                return

            renderer = getattr(event, 'renderer', None)
            if renderer is None:
                return

            self._refresh_break_lane_labels(renderer)

            # Save clean background for hover-ring blitting.
            # Animated artists (rings) are excluded from the normal draw, so the
            # saved bitmap is the plot content without any hover overlay.
            try:
                self._hover_bg = self.canvas_right.copy_from_bbox(self.ax_right.bbox)
            except Exception:
                self._hover_bg = None
        except Exception:
            return

    def _refresh_break_lane_labels(self, renderer) -> None:
        """Refresh lane label positions/visibility using a renderer (zoom-aware)."""
        try:
            if renderer is None:
                return

            xlim = None
            try:
                xlim = self.ax_right.get_xlim()
            except Exception:
                xlim = None

            if xlim is None:
                return

            x0_view, x1_view = float(xlim[0]), float(xlim[1])
            xmin_view, xmax_view = (x0_view, x1_view) if x0_view <= x1_view else (x1_view, x0_view)
            view_width = max(0.0, float(xmax_view) - float(xmin_view))

            # Convert a small pixel padding into data units so padding stays consistent under zoom.
            ax_width_px = 0.0
            try:
                ax_width_px = float(getattr(getattr(self, 'ax_right', None), 'bbox', None).width)
            except Exception:
                ax_width_px = 0.0
            desired_pad_px = 6.0
            pad_from_px = (view_width * (desired_pad_px / max(ax_width_px, 1.0))) if view_width > 0 else 0.0

            # Refresh lane (attribute) labels anchored to the first box.
            lane_labels = getattr(self, '_break_lane_lane_labels', []) or []
            hover_lanes = getattr(self, '_break_lane_hover_lanes', []) or []
            fallback_color = COLORS.get('pareto_border', COLORS['text_secondary'])
            for item in lane_labels:
                if not isinstance(item, (list, tuple)) or len(item) not in (5, 6):
                    continue

                if len(item) == 6:
                    txt, start_x, end_x, y_axes, pad_data, lane_idx = item
                else:
                    txt, start_x, end_x, y_axes, pad_data = item
                    lane_idx = None
                try:
                    sx = float(start_x)
                    ex = float(end_x)
                    if ex < sx:
                        sx, ex = ex, sx

                    vx0 = max(sx, xmin_view)
                    vx1 = min(ex, xmax_view)
                    if vx1 <= vx0:
                        txt.set_visible(False)
                        continue

                    # Place at the left edge of the visible portion.
                    # Use a zoom-aware pad so the label doesn't drift too far right.
                    base_pad = max(0.0, float(pad_data))
                    cap_pad = view_width * 0.01
                    effective_pad = max(pad_from_px, min(base_pad, cap_pad))
                    x_pos = vx0 + effective_pad
                    if x_pos > vx1:
                        x_pos = vx0
                    try:
                        txt.set_position((x_pos, float(y_axes)))
                    except Exception:
                        pass

                    # Update color for contrast with the underlying box at x_pos.
                    try:
                        lane_info = None
                        if lane_idx is not None:
                            for lane in hover_lanes:
                                if int(lane.get('lane_idx', -1)) == int(lane_idx):
                                    lane_info = lane
                                    break

                        if lane_info is not None:
                            starts = lane_info.get('starts') or []
                            boxes = lane_info.get('boxes') or []
                            value_to_color = lane_info.get('value_to_color') or {}

                            i = bisect.bisect_right(starts, float(x_pos)) - 1
                            if 0 <= i < len(boxes):
                                s, e, v = boxes[i]
                                if float(s) <= float(x_pos) <= float(e):
                                    base = value_to_color.get(str(v).strip(), COLORS.get('original_data', '#DDDDDD'))
                                    fill = mcolors.to_rgba(base, alpha=0.90)
                                    txt.set_color(self._contrast_text_color(fill))
                                else:
                                    txt.set_color(fallback_color)
                            else:
                                txt.set_color(fallback_color)
                        else:
                            txt.set_color(fallback_color)
                    except Exception:
                        try:
                            txt.set_color(fallback_color)
                        except Exception:
                            pass

                    # Fit check based on visible width.
                    px0 = self.ax_right.transData.transform((vx0, 0))[0]
                    px1 = self.ax_right.transData.transform((vx1, 0))[0]
                    avail = abs(px1 - px0)

                    txt.set_visible(True)
                    bb = txt.get_window_extent(renderer=renderer)
                    needed = bb.width + 8

                    txt.set_visible(bool(avail >= max(30, needed)))
                except Exception:
                    try:
                        txt.set_visible(False)
                    except Exception:
                        pass

            labels = getattr(self, '_break_lane_labels', []) or []
            for item in labels:
                # Backward compatibility if any 3-tuples still exist.
                if not isinstance(item, (list, tuple)):
                    continue
                if len(item) == 4:
                    txt, start_x, end_x, y_axes = item
                elif len(item) == 3:
                    txt, start_x, end_x = item
                    y_axes = None
                else:
                    continue

                try:
                    sx = float(start_x)
                    ex = float(end_x)
                    if ex < sx:
                        sx, ex = ex, sx

                    vx0 = max(sx, xmin_view)
                    vx1 = min(ex, xmax_view)
                    if vx1 <= vx0:
                        txt.set_visible(False)
                        continue

                    x_mid_visible = (vx0 + vx1) / 2.0
                    if y_axes is not None:
                        try:
                            txt.set_position((x_mid_visible, float(y_axes)))
                        except Exception:
                            pass

                    px0 = self.ax_right.transData.transform((vx0, 0))[0]
                    px1 = self.ax_right.transData.transform((vx1, 0))[0]
                    avail = abs(px1 - px0)

                    txt.set_visible(True)
                    bb = txt.get_window_extent(renderer=renderer)
                    needed = bb.width + 8

                    show = (avail >= max(40, needed))
                    txt.set_visible(bool(show))
                except Exception:
                    try:
                        txt.set_visible(False)
                    except Exception:
                        pass
        except Exception:
            return

    def reset_pareto_zoom(self):
        """Reset Pareto plot limits to the defaults for the current route."""
        if not getattr(self, 'is_multi_objective', False):
            return
        try:
            if self._pareto_default_xlim is not None:
                self.ax_left.set_xlim(*self._pareto_default_xlim)
            if self._pareto_default_ylim is not None:
                self.ax_left.set_ylim(*self._pareto_default_ylim)
            self._draw_left_canvas(idle=True)
        except Exception as e:
            try:
                self.status_label.config(text=f"❌ Reset pareto zoom failed: {e}")
            except Exception:
                pass
        
    def update_visualizations(self):
        """Update both visualizations based on selected route and analysis method."""
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
                    self._draw_left_canvas()
                self._draw_right_canvas()
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
                    self._draw_left_canvas()
                self._draw_right_canvas()
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
                        if hasattr(self.main_paned, 'forget'):
                            self.main_paned.forget(self.left_frame)
                        else:
                            self.main_paned.remove(self.left_frame)
                    except (tk.TclError, ValueError):
                        pass
                    if not getattr(self, '_pareto_hidden_logged', False):
                        _safe_print(f"[ROUTE {route_id}] Hidden Pareto pane for single-objective (degenerate case)")
                        self._pareto_hidden_logged = True

            # Update segmentation graph (RIGHT pane) with selected point
            self.update_segmentation_graph(route_id)

            # Update paging control visibility after plotting.
            self._update_segmentation_paging_controls()

            # Redraw canvases
            if self.is_multi_objective:
                self._draw_left_canvas()
            self._draw_right_canvas()

            # Ensure lane labels are refreshed even when draw events are flaky.
            try:
                renderer = getattr(self.canvas_right, 'get_renderer', lambda: None)()
                self._refresh_break_lane_labels(renderer)
            except Exception:
                pass

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
                    self._draw_left_canvas()
                except Exception:
                    pass
            try:
                self._draw_right_canvas()
            except Exception:
                pass
        
    def get_current_route_data(self, route_id):
        """Get original data for the specified route from loaded data."""
        route_key = normalize_route_id(route_id) or str(route_id).strip()
        if hasattr(self, 'original_data_by_route') and route_key in self.original_data_by_route:
            return self.original_data_by_route[route_key]
        return None
        
    def get_route_results(self, route_id):
        """Get optimization results for the specified route using actual schema structure."""
        if not self.json_results or 'route_results' not in self.json_results:
            return None

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
            self._draw_left_canvas(idle=True)  # Non-blocking draw
            
            # Update segmentation immediately (synchronous for reliability)
            self.update_segmentation_graph(route_id)
            self._draw_right_canvas(idle=True)
            
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
            self._draw_left_canvas(idle=True)  # Non-blocking draw
            
            # Update segmentation graph immediately (synchronous for reliability)
            self.update_segmentation_graph(route_id)
            self._draw_right_canvas(idle=True)
            
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

        # Normalize early so we can compare to the previous route and decide
        # whether to preserve the current x-window (zoom/paging) on redraw.
        route_id = normalize_route_id(route_id) or str(route_id).strip()

        prev_xlim = None
        try:
            if getattr(self, '_last_seg_route_id', None) == route_id:
                prev_xlim = self.ax_right.get_xlim()
        except Exception:
            prev_xlim = None

        self._last_seg_route_id = route_id

        # Remove any previous secondary axis to avoid stacking multiple twinx axes.
        if getattr(self, '_ax_right_secondary', None) is not None:
            try:
                self._ax_right_secondary.remove()
            except Exception:
                pass
            self._ax_right_secondary = None

        # Clear cached secondary series for y-autoscale
        self._current_seg_secondary_x = None
        self._current_seg_secondary_y = None

        self.ax_right.clear()

        # Ensure we start each redraw in autoscale mode so switching routes
        # recomputes sane limits (especially after toolbar zoom / x-span zoom).
        try:
            self.ax_right.set_autoscale_on(True)
        except Exception:
            pass
        
        route_data = self.get_current_route_data(route_id)
        raw_route_data = route_data
        route_results = self.get_route_results(route_id)
        
        if not route_results:
            self.ax_right.text(0.5, 0.5, 'No optimization results available', 
                             transform=self.ax_right.transAxes, ha='center', va='center',
                             fontsize=12, color=COLORS['text_secondary'])
            self.ax_right.set_title(f"Segmentation - {route_id} (No Results)")
            return
            
        processing_results = route_results.get('processing_results', {}) or {}

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
        from visualization.breakpoints import (
            extract_attribute_breakpoints,
            extract_attribute_break_signatures,
            extract_gap_boundary_breakpoints,
            extract_mandatory_breakpoints,
        )

        from visualization.break_lanes import attribute_breakpoints_by_column, compute_lane_boxes

        mandatory_breakpoints = extract_mandatory_breakpoints(route_results)
        gap_breakpoints = extract_gap_boundary_breakpoints(route_results)
        attribute_breakpoints = extract_attribute_breakpoints(route_results)
        extract_attribute_break_signatures(route_results)

        preprocessed_gap_breakpoints = set()
        try:
            from visualization.gap_analysis_data import extract_gap_analysis

            gap_info = extract_gap_analysis(route_results)
            if (
                raw_route_data is not None
                and not raw_route_data.empty
                and x_col in raw_route_data.columns
                and gap_info.gap_segments
            ):
                raw_x_series = pd.to_numeric(raw_route_data[x_col], errors='coerce').dropna()
                if not raw_x_series.empty:
                    raw_x_values = raw_x_series.astype(float).tolist()
                    for seg in gap_info.gap_segments:
                        if not isinstance(seg, dict):
                            continue
                        try:
                            gap_start = float(seg.get('start'))
                            gap_end = float(seg.get('end'))
                        except (TypeError, ValueError):
                            continue

                        # If the original loaded data still has points inside the rendered
                        # gap interval, the gap was introduced by preprocessing removals.
                        if any(gap_start < x_value < gap_end for x_value in raw_x_values):
                            preprocessed_gap_breakpoints.add(gap_start)
                            preprocessed_gap_breakpoints.add(gap_end)
        except Exception:
            preprocessed_gap_breakpoints = set()

        # Keep artists so we can remove/redraw the lane overlay cleanly.
        if not hasattr(self, '_break_lane_artists'):
            self._break_lane_artists = []
        for a in getattr(self, '_break_lane_artists', []) or []:
            try:
                a.remove()
            except Exception:
                pass
        self._break_lane_artists = []

        # Reset lane interaction artifacts for this draw.
        self._break_lane_hitboxes = []
        self._break_lane_labels = []
        self._break_lane_lane_labels = []
        self._break_lane_hover_lanes = []
        self._break_lane_overlay_bounds = None
        self._hide_break_lane_tooltip()

        # Always draw breakpoint lines from JSON when available, even if original points are missing.
        if breakpoints:
            from visualization.breakpoints import compute_breakpoint_line_specs

            specs = compute_breakpoint_line_specs(
                breakpoints,
                mandatory_breakpoints,
                gap_breakpoints=gap_breakpoints,
                attribute_breakpoints=attribute_breakpoints,
                gap_label="Gap Breaks",
                attribute_label="Attribute Breaks",
            )

            attribute_labeled = False
            for spec in specs:
                if spec.kind in ('mandatory', 'mandatory_other'):
                    self.ax_right.axvline(
                        x=spec.x,
                        color=COLORS['mandatory_bp'],
                        linestyle='--',
                        linewidth=1.1,
                        alpha=0.9,
                        zorder=3,
                        label=spec.label,
                    )
                elif spec.kind == 'mandatory_gap':
                    is_preprocessed_gap = spec.x in preprocessed_gap_breakpoints
                    self.ax_right.axvline(
                        x=spec.x,
                        color=COLORS['mandatory_bp'],
                        linestyle='--' if is_preprocessed_gap else '-',
                        linewidth=1.1 if is_preprocessed_gap else 1.9,
                        alpha=0.95,
                        zorder=3,
                        label=spec.label,
                    )
                elif spec.kind == 'mandatory_attribute':
                    self.ax_right.axvline(
                        x=spec.x,
                        color=COLORS.get('pareto_normal', COLORS.get('segment_avg', COLORS['mandatory_bp'])),
                        linestyle='-',
                        linewidth=1.2,
                        alpha=0.9,
                        zorder=3,
                        label=(spec.label or ("Attribute Breaks" if not attribute_labeled else "")),
                    )
                    attribute_labeled = True
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

        # Break lanes overlay (per attribute) aligned to the x-axis.
        try:
            show_lanes = bool(self._show_break_lanes_var.get()) if hasattr(self, '_show_break_lanes_var') else False
        except Exception:
            show_lanes = False

        try:
            attr_block = None
            secondary_attr_block = None
            input_analysis = route_results.get('input_data_analysis') if isinstance(route_results, dict) else None
            if isinstance(input_analysis, dict):
                attr_block = input_analysis.get('attribute_break_analysis')
                secondary_attr_block = input_analysis.get('secondary_attribute_break_analysis')

            # Only show the lanes toggle when must-break columns exist (primary or secondary).
            try:
                cols_used_for_toggle = []
                if isinstance(attr_block, dict):
                    primary_cols = attr_block.get('columns_used')
                    if isinstance(primary_cols, list):
                        cols_used_for_toggle.extend(primary_cols)
                if isinstance(secondary_attr_block, dict):
                    secondary_cols = secondary_attr_block.get('columns_used')
                    if isinstance(secondary_cols, list):
                        cols_used_for_toggle.extend(secondary_cols)
                cols_used_for_toggle = [str(c).strip() for c in cols_used_for_toggle if str(c).strip()]

                toggle_visible = bool(cols_used_for_toggle)
                if hasattr(self, 'break_lanes_button'):
                    if toggle_visible:
                        # Show if currently hidden
                        if self.break_lanes_button.winfo_manager() != 'pack':
                            self.break_lanes_button.pack(**getattr(self, '_break_lanes_pack_opts', {}))
                    else:
                        # Hide and force off
                        try:
                            self._show_break_lanes_var.set(False)
                        except Exception:
                            pass
                        try:
                            self.break_lanes_button.pack_forget()
                        except Exception:
                            pass
            except Exception:
                pass

            # Control preprocessing changes toggle visibility based on whether preprocessing was used
            try:
                preprocessing_log = route_results.get('preprocessing_modification_log') if isinstance(route_results, dict) else None
                has_preprocessing = isinstance(preprocessing_log, list) and len(preprocessing_log) > 0
                
                if hasattr(self, 'preprocessing_changes_button'):
                    if has_preprocessing:
                        # Show if currently hidden
                        if self.preprocessing_changes_button.winfo_manager() != 'pack':
                            self.preprocessing_changes_button.pack(**getattr(self, '_preprocessing_changes_pack_opts', {}))
                    else:
                        # Hide and force off
                        try:
                            self._show_preprocessing_changes_var.set(False)
                        except Exception:
                            pass
                        try:
                            self.preprocessing_changes_button.pack_forget()
                        except Exception:
                            pass
            except Exception:
                pass

            if show_lanes and (isinstance(attr_block, dict) or isinstance(secondary_attr_block, dict)) and route_data is not None:
                # Collect columns from both primary and secondary attribute breaks
                cols_used = []
                bp_by_col = {}
                
                # Primary attribute breaks
                if isinstance(attr_block, dict):
                    primary_cols = attr_block.get('columns_used')
                    if isinstance(primary_cols, list):
                        cols_used.extend([str(c).strip() for c in primary_cols if str(c).strip()])
                    # Get breakpoints for primary columns
                    primary_bp = attribute_breakpoints_by_column(attr_block)
                    bp_by_col.update(primary_bp)
                
                # Secondary attribute breaks
                if isinstance(secondary_attr_block, dict):
                    secondary_cols = secondary_attr_block.get('columns_used')
                    if isinstance(secondary_cols, list):
                        cols_used.extend([str(c).strip() for c in secondary_cols if str(c).strip()])
                    # Get breakpoints for secondary columns
                    secondary_bp = attribute_breakpoints_by_column(secondary_attr_block)
                    bp_by_col.update(secondary_bp)

                # Prefer per-route x-range from results; fall back to dataframe.
                x_min = None
                x_max = None
                try:
                    ds = input_analysis.get('data_summary') if isinstance(input_analysis, dict) else None
                    dr = ds.get('data_range') if isinstance(ds, dict) else None
                    if isinstance(dr, dict):
                        x_min = float(dr.get('x_min'))
                        x_max = float(dr.get('x_max'))
                except Exception:
                    x_min = None
                    x_max = None

                if x_min is None or x_max is None:
                    try:
                        x_min = float(route_data[x_col].min())
                        x_max = float(route_data[x_col].max())
                    except Exception:
                        x_min = None
                        x_max = None

                if cols_used and x_min is not None and x_max is not None:
                    # bp_by_col already computed above from both primary and secondary blocks

                    total_height = 0.16
                    top = 0.995
                    bottom = top - total_height
                    lane_h = total_height / max(len(cols_used), 1)

                    # Cache overlay bounds for fast hover detection.
                    self._break_lane_overlay_bounds = (float(bottom), float(top))

                    trans = transforms.blended_transform_factory(self.ax_right.transData, self.ax_right.transAxes)
                    label_color = COLORS.get('pareto_border', COLORS['text_secondary'])

                    # Value color palette (re-use existing palette tokens).
                    # Colors are assigned per *attribute value* within a lane.
                    value_palette = [
                        COLORS.get('pareto_normal', COLORS.get('segment_avg', COLORS['analysis_bp'])),
                        COLORS.get('segment_avg', COLORS.get('pareto_normal', COLORS['analysis_bp'])),
                        COLORS.get('secondary_default', COLORS.get('analysis_bp', '#000000')),
                        COLORS.get('analysis_bp', COLORS.get('pareto_normal', '#000000')),
                        COLORS.get('pareto_border', COLORS.get('analysis_bp', '#000000')),
                        COLORS.get('original_edge', COLORS.get('analysis_bp', '#000000')),
                    ]

                    def _rgba(color: str, alpha: float):
                        return mcolors.to_rgba(color, alpha=max(0.0, min(1.0, alpha)))

                    def _value_text_color(fill_rgba) -> str:
                        return self._contrast_text_color(fill_rgba)

                    # Lane labels on the left (axes coords).
                    for lane_idx, col_name in enumerate(cols_used):
                        y0 = top - (lane_idx + 1) * lane_h
                        y1 = y0 + lane_h
                        y_mid = (y0 + y1) / 2.0

                        # Background band for visual separation
                        rect_bg = Rectangle(
                            (x_min, y0),
                            x_max - x_min,
                            lane_h,
                            transform=trans,
                            facecolor=COLORS['original_data'],
                            edgecolor=COLORS['grid'],
                            linewidth=0.6,
                            alpha=0.22,
                            zorder=4,
                            clip_on=False,
                        )
                        self.ax_right.add_patch(rect_bg)
                        self._break_lane_artists.append(rect_bg)

                        lane_bps = bp_by_col.get(col_name, [])
                        try:
                            x_vals = list(route_data[x_col].values)
                            attr_vals = list(route_data[col_name].values)
                        except Exception:
                            continue

                        boxes = compute_lane_boxes(
                            x_values=x_vals,
                            attribute_values=attr_vals,
                            lane_breakpoints=lane_bps,
                            x_min=float(x_min),
                            x_max=float(x_max),
                        )

                        # Stable value->color mapping per lane.
                        unique_vals = sorted({(bx.value or '').strip() for bx in boxes if (bx.value or '').strip()})
                        value_to_color = {
                            v: value_palette[i % len(value_palette)]
                            for i, v in enumerate(unique_vals)
                        }

                        # Build fast hover index for this lane (include value->color for contrast decisions).
                        try:
                            lane_boxes = [(float(bx.start_x), float(bx.end_x), str(bx.value) if bx.value is not None else "") for bx in boxes]
                            lane_boxes = [(s, e, v) for (s, e, v) in lane_boxes if e > s]
                            lane_starts = [s for (s, _e, _v) in lane_boxes]
                            self._break_lane_hover_lanes.append(
                                {
                                    'lane_idx': int(lane_idx),
                                    'y0': float(y0),
                                    'y1': float(y1),
                                    'col': str(col_name),
                                    'starts': lane_starts,
                                    'boxes': lane_boxes,
                                    'value_to_color': dict(value_to_color),
                                }
                            )
                        except Exception:
                            pass

                        # Attribute label: show for every lane.
                        # Anchor to the full x-range so it doesn't disappear when the first box is tiny.
                        try:
                            # Small left padding in data units.
                            pad = (float(x_max) - float(x_min)) * 0.005
                            x_label = float(x_min) + pad
                            # Vertically centered within the lane box strip.
                            y_label = y0 + 0.50 * lane_h

                            lane_label_color = label_color
                            try:
                                first_box = boxes[0] if boxes else None
                                if first_box is not None:
                                    fb_val = (first_box.value or '').strip()
                                    fb_base = value_to_color.get(fb_val, COLORS.get('original_data', '#DDDDDD'))
                                    fb_fill = _rgba(fb_base, 0.90)
                                    lane_label_color = self._contrast_text_color(fb_fill)
                            except Exception:
                                lane_label_color = label_color

                            lane_label = self.ax_right.text(
                                x_label,
                                y_label,
                                str(col_name),
                                transform=trans,
                                ha='left',
                                va='center',
                                fontsize=9,
                                color=lane_label_color,
                                alpha=1.0,
                                zorder=6,
                                clip_on=True,
                            )
                            self._break_lane_artists.append(lane_label)
                            try:
                                # Track the full lane span so the label stays visible on zoom.
                                self._break_lane_lane_labels.append(
                                    (lane_label, float(x_min), float(x_max), float(y_label), float(pad), int(lane_idx))
                                )
                            except Exception:
                                pass
                        except Exception:
                            pass

                        for b in boxes:
                            w = b.end_x - b.start_x
                            if w <= 0:
                                continue

                            raw_val = (b.value or '').strip()
                            base = value_to_color.get(raw_val, COLORS.get('original_data', '#DDDDDD'))
                            fill = _rgba(base, 0.90)
                            txt_color = _value_text_color(fill)

                            rect = Rectangle(
                                (b.start_x, y0 + 0.10 * lane_h),
                                w,
                                0.80 * lane_h,
                                transform=trans,
                                facecolor=fill,
                                edgecolor=base,
                                linewidth=1.0,
                                zorder=4.5,
                                clip_on=True,
                            )
                            self.ax_right.add_patch(rect)
                            self._break_lane_artists.append(rect)
                            self._break_lane_hitboxes.append((rect, col_name, b.value))

                            # Always create the text artist, but decide visibility after draw.
                            if b.value:
                                txt = self.ax_right.text(
                                    (b.start_x + b.end_x) / 2.0,
                                    y_mid,
                                    b.value,
                                    transform=trans,
                                    ha='center',
                                    va='center',
                                    fontsize=8,
                                    color=txt_color,
                                    alpha=1.0,
                                    zorder=5,
                                    clip_on=True,
                                )
                                txt.set_visible(True)
                                self._break_lane_artists.append(txt)
                                self._break_lane_labels.append((txt, b.start_x, b.end_x, y_mid))
        except Exception:
            pass

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
            self._hover_seg_x = None
            self._hover_seg_y = None

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
                leg = self.ax_right.legend(deduped_handles, deduped_labels, loc='best', framealpha=0.85)
                try:
                    leg.set_draggable(True)
                except Exception:
                    pass

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

        plotted_primary_points = False

        if (
            route_data is not None
            and not route_data.empty
            and prepared_series.x_data is not None
            and prepared_series.y_data is not None
        ):
            plotted_primary_points = True
                
            # Plot original points using the same hue as the segment average line,
            # but more transparent (consistent with secondary-series styling).
            self.ax_right.scatter(
                route_data[x_col],
                route_data[y_col],
                alpha=0.30,
                s=25,
                color=COLORS['segment_avg'],
                edgecolors='none',
                linewidth=0.0,
                label='Original Data Points',
                zorder=2,
            )
            
            # Preprocessing changes overlay - show original vs preprocessed points
            try:
                show_preprocessing = bool(self._show_preprocessing_changes_var.get()) if hasattr(self, '_show_preprocessing_changes_var') else False
            except Exception:
                show_preprocessing = False
            
            # Initialize preprocessing overlay variables
            original_filtered_x = []
            original_filtered_y = []
            preprocessed_data_x = []
            preprocessed_data_y = []
            
            if show_preprocessing:
                route_results = self.get_route_results(route_id)
                preprocessing_log = route_results.get('preprocessing_modification_log') if isinstance(route_results, dict) else None
                
                if isinstance(preprocessing_log, list) and preprocessing_log:
                    # Collect original data points (before preprocessing)
                    original_data_x = []
                    original_data_y = []
                    
                    # Collect preprocessed data points (after preprocessing) 
                    preprocessed_data_x = []
                    preprocessed_data_y = []
                    
                    for entry in preprocessing_log:
                        if not isinstance(entry, dict):
                            continue
                        
                        mod_type = entry.get('modification_type')
                        x_val = entry.get('x_value')
                        original_y = entry.get('original_y_value')
                        new_y = entry.get('new_y_value')
                        
                        try:
                            x_float = float(x_val)
                            
                            if mod_type == 'point_removed' and original_y is not None:
                                # Point was removed - only show original
                                original_data_x.append(x_float)
                                original_data_y.append(float(original_y))
                            elif mod_type in ('y_value_changed', 'y_value_capped', 'point_interpolated') and original_y is not None and new_y is not None:
                                # Point was modified - show both original and new
                                original_data_x.append(x_float)
                                original_data_y.append(float(original_y))
                                preprocessed_data_x.append(x_float)
                                preprocessed_data_y.append(float(new_y))
                        except (TypeError, ValueError):
                            continue
                    
                    # Show ALL outliers in the overlay without filtering
                    # If they're visible in the main plot, they must be visible in the overlay
                    # Otherwise it creates confusion where tall spikes don't have red markers
                    original_filtered_x = original_data_x
                    original_filtered_y = original_data_y
                    
                    # Plot original data points (distinctive red)
                    if original_filtered_x:
                        self.ax_right.scatter(
                            original_filtered_x,
                            original_filtered_y,
                            marker='o',
                            s=40,
                            color='#DC2626',
                            alpha=0.6,
                            edgecolors='#991B1B',
                            linewidths=0.5,
                            label='Original Data (Outliers)',
                            zorder=4,
                        )
                    
                    # Plot preprocessed data points (distinctive cyan)
                    if preprocessed_data_x:
                        self.ax_right.scatter(
                            preprocessed_data_x,
                            preprocessed_data_y,
                            marker='o',
                            s=40,
                            color='#06B6D4',
                            alpha=0.8,
                            edgecolors='#0891B2',
                            linewidths=0.5,
                            label='Preprocessed Data',
                            zorder=4.5,
                        )
            
            x_data = prepared_series.x_data
            y_data = prepared_series.y_data

            # Cache paired post-processing arrays for hover snapping.
            # Must be set BEFORE _current_seg_y is potentially extended with
            # preprocessing overlay values (which would make the arrays different lengths).
            self._hover_seg_x = x_data
            self._hover_seg_y = y_data

            # Cache current series for X-zoom autoscaling
            # Include preprocessing overlay points in y-data for proper autoscaling
            self._current_seg_x = x_data
            if show_preprocessing and (original_filtered_x or preprocessed_data_x):
                # Combine main data with preprocessing overlay for complete y-range
                all_y_values = list(y_data)
                if original_filtered_y:
                    all_y_values.extend(original_filtered_y)
                if preprocessed_data_y:
                    all_y_values.extend(preprocessed_data_y)
                self._current_seg_y = np.array(all_y_values)
            else:
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

            # Optional secondary Y-axis series
            secondary_col = getattr(self, '_secondary_y_col', None)
            if secondary_col:
                try:
                    secondary_prepared = prepare_numeric_xy_series(raw_route_data, x_col=x_col, y_col=secondary_col)
                    if secondary_prepared.prepared_df is not None and secondary_prepared.x_data is not None and secondary_prepared.y_data is not None:
                        sec_ax = self.ax_right.twinx()
                        self._ax_right_secondary = sec_ax

                        # Layering note:
                        # With twinx(), matplotlib may draw the secondary axes above the primary
                        # artists. But if we push the entire secondary axes behind the primary
                        # axes and keep the primary patch visible, the primary background can
                        # hide the secondary artists.
                        #
                        # Solution: keep primary axes above secondary, but make the primary
                        # patch transparent so secondary artists remain visible.
                        try:
                            sec_ax.set_zorder(0)
                            self.ax_right.set_zorder(1)
                            self.ax_right.patch.set_visible(False)
                            sec_ax.patch.set_visible(False)
                        except Exception:
                            pass

                        secondary_color = getattr(self, '_secondary_color', COLORS.get('secondary_default', '#14B8A6'))
                        secondary_alpha = float(getattr(self, '_secondary_points_alpha', 0.25) or 0.25)

                        # Cache current secondary series for zoom/paging y-autoscale
                        self._current_seg_secondary_x = secondary_prepared.x_data
                        self._current_seg_secondary_y = secondary_prepared.y_data

                        sec_ax.scatter(
                            secondary_prepared.prepared_df[x_col],
                            secondary_prepared.prepared_df[secondary_col],
                            alpha=secondary_alpha,
                            s=45,
                            color=secondary_color,
                            edgecolors='none',
                            label=f"{secondary_col} (Secondary)",
                            zorder=1,
                        )

                        from visualization.segmentation_data import compute_segment_average_lines

                        sec_avg_lines = compute_segment_average_lines(
                            x_data=secondary_prepared.x_data,
                            y_data=secondary_prepared.y_data,
                            breakpoints=breakpoints,
                            gap_segments=gap_segments,
                            label=f"{secondary_col} Segment Avg",
                        )

                        for line in sec_avg_lines:
                            sec_ax.plot(
                                [line.start_x, line.end_x],
                                [line.avg_y, line.avg_y],
                                color=secondary_color,
                                linewidth=2.5,
                                alpha=0.9,
                                zorder=2,
                                solid_capstyle='butt',
                                label=line.label,
                            )

                        # Force secondary axis to recompute its y-limits for this route.
                        try:
                            sec_ax.set_autoscale_on(True)
                            sec_ax.autoscale(enable=True, axis='y', tight=False)
                            sec_ax.autoscale_view(scalex=False, scaley=True)
                        except Exception:
                            pass

                        from visualization.graph_styling import pretty_axis_label

                        sec_ax.set_ylabel(pretty_axis_label(secondary_col, default='Secondary Y'))
                        try:
                            sec_ax.tick_params(axis='y', labelcolor=secondary_color)
                            sec_ax.spines['right'].set_color(secondary_color)
                            sec_ax.yaxis.label.set_color(secondary_color)
                        except Exception:
                            pass
                except Exception as e:
                    try:
                        self.app.log_message(f"WARNING: Secondary series plot failed: {e}")
                    except Exception:
                        pass
                                             
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
            self._hover_seg_x = None
            self._hover_seg_y = None
        
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
        if getattr(self, '_ax_right_secondary', None) is not None:
            try:
                sec_handles, sec_labels = self._ax_right_secondary.get_legend_handles_labels()
                handles = list(handles) + list(sec_handles)
                labels = list(labels) + list(sec_labels)
            except Exception:
                pass
        from visualization.graph_styling import dedupe_legend_entries

        deduped_labels, deduped_handles = dedupe_legend_entries(labels, handles)
        if deduped_labels:
            leg = self.ax_right.legend(deduped_handles, deduped_labels, loc='best', framealpha=0.85)
            try:
                leg.set_draggable(True)
            except Exception:
                pass

        # Deterministic full-view y-limits (avoid "sticky" limits when switching routes).
        full_primary_ylim = None
        if plotted_primary_points and self._current_seg_y is not None:
            try:
                from visualization.autoscale import autoscale_y_limits

                full_primary_ylim = autoscale_y_limits(self._current_seg_y, pad_fraction=0.05, min_pad=1.0)
                if full_primary_ylim is not None:
                    self.ax_right.set_ylim(*full_primary_ylim)
            except Exception:
                full_primary_ylim = None

        full_secondary_ylim = None
        if getattr(self, '_ax_right_secondary', None) is not None and self._current_seg_secondary_y is not None:
            try:
                from visualization.autoscale import autoscale_y_limits

                full_secondary_ylim = autoscale_y_limits(self._current_seg_secondary_y, pad_fraction=0.05, min_pad=1.0)
                if full_secondary_ylim is not None:
                    self._ax_right_secondary.set_ylim(*full_secondary_ylim)
            except Exception:
                full_secondary_ylim = None

        # Restore the previous x-window for same-route redraws (secondary control updates)
        # and rescale y-limits to the visible data.
        if prev_xlim is not None and plotted_primary_points:
            try:
                self.ax_right.set_xlim(*prev_xlim)
                xmin, xmax = self.ax_right.get_xlim()
                self._autoscale_segmentation_y_to_visible(xmin, xmax)
                self._autoscale_secondary_y_to_visible(xmin, xmax)
            except Exception:
                pass

        # Cache default segmentation limits for reset.
        # Only update defaults when X-zoom is currently OFF (so reset returns to full view).
        from visualization.zoom_decisions import should_cache_default_limits

        if should_cache_default_limits(x_zoom_enabled=self._seg_x_zoom_enabled):
            # Cache defaults only when we're in a full-view state.
            try:
                if plotted_primary_points and self._current_seg_x is not None and self._current_seg_x.size > 0:
                    full_xlim = (float(np.min(self._current_seg_x)), float(np.max(self._current_seg_x)))
                else:
                    full_xlim = None

                cur_xlim = self.ax_right.get_xlim()
                if full_xlim is None:
                    # Best-effort fallback
                    self._seg_default_xlim = cur_xlim
                    self._seg_default_ylim = self.ax_right.get_ylim()
                    self._seg_default_ylim_secondary = (
                        self._ax_right_secondary.get_ylim() if getattr(self, '_ax_right_secondary', None) is not None else None
                    )
                else:
                    from visualization.zoom_decisions import should_show_segmentation_paging_arrows

                    zoomed = should_show_segmentation_paging_arrows(full_xlim=full_xlim, cur_xlim=cur_xlim)
                    if not zoomed:
                        self._seg_default_xlim = full_xlim
                        self._seg_default_ylim = full_primary_ylim or self.ax_right.get_ylim()
                        self._seg_default_ylim_secondary = full_secondary_ylim
            except Exception:
                pass

        # (Re-)create animated hover ring artists after every full redraw.
        # ax_right.clear() removes all artists, so they must be rebuilt here.
        self._setup_hover_artists()

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