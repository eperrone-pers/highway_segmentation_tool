"""Widget construction for EnhancedVisualizationWindow.

Separates Tkinter / matplotlib widget creation from visualization and
interaction logic, following the same UIBuilder pattern used by
gui_main.py / ui_builder.py.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from visualization_ui import EnhancedVisualizationWindow

from visualization.utils import safe_print as _safe_print, default_colors
from tooltip import attach_tooltip


class _QuietToolbar(NavigationToolbar2Tk):
    """Navigation toolbar with the built-in coordinate message suppressed.

    The segmentation pane has its own named coord_label that shows axis
    coordinates using actual column names.  The toolbar's raw (x, y) message
    would duplicate and conflict with that label, so we silence it here.
    """

    def set_message(self, s: str) -> None:
        pass

SECONDARY_NONE_SENTINEL = "(None)"

COLORS = default_colors()


class VisualizationUIBuilder:
    """Builds all Tkinter and matplotlib widgets for EnhancedVisualizationWindow."""

    def __init__(self, vis_window: "EnhancedVisualizationWindow") -> None:
        self.win = vis_window

    def build(self) -> None:
        """Create the complete enhanced paned-window interface."""
        self._build_control_bar()
        self._build_main_panes()
        self._build_status_bar()
        try:
            self.win.window.after(0, self.win._position_main_paned_sash_handle)
        except Exception:
            pass
        _safe_print("Enhanced visualization interface ready")

    # ------------------------------------------------------------------
    # Control bar (top row)
    # ------------------------------------------------------------------

    def _build_control_bar(self) -> None:
        """Create the top control bar: route selector, export, secondary-axis controls."""
        win = self.win

        control_frame = ttk.Frame(win.window)
        control_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(control_frame, text="Route:").pack(side='left', padx=(0, 5))

        win.route_var = tk.StringVar(value=win.routes[0])
        win.route_combo = ttk.Combobox(
            control_frame,
            textvariable=win.route_var,
            values=win.routes,
            state='normal',
            width=25,
        )
        win.route_combo.pack(side='left', padx=5)
        win.route_combo.bind('<KeyRelease>', win.on_route_keyrelease)
        win.route_combo.bind('<<ComboboxSelected>>', win.on_route_changed)
        attach_tooltip(win.route_combo, "Select which route to display. Type to filter available routes.")

        export_button = ttk.Button(
            control_frame, text="📊 Export to Excel", command=win._export_to_excel
        )
        export_button.pack(side='left', padx=(10, 4))
        attach_tooltip(export_button, "Export all route segments, breakpoints, and statistics to an Excel workbook.")

        csv_button = ttk.Button(
            control_frame, text="📄 Export Segments CSV", command=win._export_to_csv
        )
        csv_button.pack(side='left', padx=(0, 10))
        attach_tooltip(csv_button, "Export segment boundaries and statistics for all routes to a flat CSV (for GIS / PMS tools).")

        secondary_controls = ttk.Frame(control_frame)
        secondary_controls.pack(side='left', padx=(10, 0))

        win.secondary_column_var = tk.StringVar(value=SECONDARY_NONE_SENTINEL)
        win.secondary_color_var = tk.StringVar(value=win._secondary_color)

        ttk.Label(secondary_controls, text="Secondary Y:").pack(side='left', padx=(0, 5))
        win.secondary_column_combo = ttk.Combobox(
            secondary_controls,
            textvariable=win.secondary_column_var,
            values=[SECONDARY_NONE_SENTINEL],
            state='readonly',
            width=22,
        )
        win.secondary_column_combo.pack(side='left', padx=(0, 6))
        win.secondary_column_combo.bind(
            '<<ComboboxSelected>>', lambda _e: win._schedule_secondary_redraw()
        )
        attach_tooltip(win.secondary_column_combo,
                       "Overlay a second data column on a right Y-axis. "
                       "Useful for comparing two measurements on the same route.")

        win.secondary_color_button = ttk.Button(
            secondary_controls,
            text="Pick Color",
            command=win._choose_secondary_color,
        )
        win.secondary_color_button.pack(side='left', padx=(0, 6))
        attach_tooltip(win.secondary_color_button, "Choose the color for the secondary Y-axis series.")

        win.secondary_color_swatch = tk.Label(
            secondary_controls,
            width=2,
            relief='solid',
            borderwidth=1,
            bg=win.secondary_color_var.get(),
            cursor='hand2',
        )
        win.secondary_color_swatch.pack(side='left', padx=(0, 10), pady=2)
        win.secondary_color_swatch.bind('<Button-1>', lambda _e: win._choose_secondary_color())
        attach_tooltip(win.secondary_color_swatch, "Current color for the secondary series. Click to change.")

        ttk.Label(secondary_controls, text="Transparency:").pack(side='left', padx=(0, 4))
        win.secondary_alpha_var = tk.DoubleVar(value=win._secondary_points_alpha)
        win.secondary_alpha_scale = ttk.Scale(
            secondary_controls,
            from_=0.05,
            to=0.90,
            orient='horizontal',
            variable=win.secondary_alpha_var,
            command=win._on_secondary_alpha_changed,
            length=90,
        )
        win.secondary_alpha_scale.pack(side='left', padx=(0, 4))
        attach_tooltip(win.secondary_alpha_scale,
                       "Adjust the opacity of the secondary series points "
                       "(0.05 = nearly transparent, 0.90 = solid).")
        win.secondary_alpha_value_label = ttk.Label(
            secondary_controls, text=f"{win._secondary_points_alpha:.2f}"
        )
        win.secondary_alpha_value_label.pack(side='left', padx=(0, 8))

        opt_info = win.get_optimization_summary()
        win.opt_info_label = ttk.Label(control_frame, text=opt_info)
        win.opt_info_label.pack(side='left', padx=(10, 0))

        win.status_label = ttk.Label(control_frame, text="📈 Results loaded")
        win.status_label.pack(side='right', padx=10)

    # ------------------------------------------------------------------
    # Main paned window
    # ------------------------------------------------------------------

    def _build_main_panes(self) -> None:
        """Create the main PanedWindow and both panes."""
        win = self.win

        main_paned = tk.PanedWindow(win.window, orient='horizontal')
        try:
            main_paned.configure(
                showhandle=False,
                opaqueresize=False,
                sashwidth=10,
                sashpad=3,
                sashrelief='raised',
                cursor='sb_h_double_arrow',
                bg=COLORS['original_edge'],
            )
        except Exception:
            pass
        main_paned.pack(fill='both', expand=True, padx=10, pady=10)
        win.main_paned = main_paned

        analysis_method = win.json_results.get('analysis_metadata', {}).get('analysis_method')
        if not analysis_method:
            raise ValueError(
                "Results JSON is missing required analysis_metadata.analysis_method;"
                " cannot determine layout"
            )
        win.analysis_method = analysis_method

        self._build_pareto_pane(main_paned, analysis_method)
        self._build_segmentation_pane(main_paned)
        self._build_sash_grip(main_paned)

    def _build_pareto_pane(self, main_paned: tk.PanedWindow, analysis_method: str) -> None:
        """Create the left Pareto-front pane."""
        win = self.win
        from config import is_multi_objective_method

        win.left_frame = ttk.LabelFrame(main_paned, text="🎯 Pareto Front Analysis", padding=5)
        win.is_multi_objective = is_multi_objective_method(analysis_method)

        if win.is_multi_objective:
            try:
                main_paned.add(win.left_frame, stretch='always')
            except Exception:
                main_paned.add(win.left_frame)

        win.fig_left = Figure(figsize=(7, 6), dpi=100, tight_layout=False)
        win.ax_left = win.fig_left.add_subplot(111)
        win.canvas_left = FigureCanvasTkAgg(win.fig_left, win.left_frame)

        if win.is_multi_objective:
            left_bottom_bar = ttk.Frame(win.left_frame)
            left_bottom_bar.pack(side='bottom', fill='x')

            left_toolbar_container = ttk.Frame(left_bottom_bar)
            left_toolbar_container.pack(side='left', fill='x', expand=True)
            toolbar_left = NavigationToolbar2Tk(win.canvas_left, left_toolbar_container)
            toolbar_left.update()

            left_controls_container = ttk.Frame(left_bottom_bar)
            left_controls_container.pack(side='right')
            win.reset_pareto_zoom_button = ttk.Button(
                left_controls_container,
                text="Reset Pareto Zoom",
                command=win.reset_pareto_zoom,
            )
            win.reset_pareto_zoom_button.pack(side='right', padx=(6, 0), pady=2)
            attach_tooltip(win.reset_pareto_zoom_button,
                           "Restore the Pareto front plot to its original view, "
                           "showing all solutions in the trade-off space.")

            win.canvas_left.get_tk_widget().pack(side='top', fill='both', expand=True)
        else:
            win.canvas_left.get_tk_widget().pack(fill='both', expand=True)

        win.canvas_left.mpl_connect('pick_event', win.on_pareto_pick)
        win.canvas_left.mpl_connect('button_press_event', win.on_pareto_click)

    def _build_segmentation_pane(self, main_paned: tk.PanedWindow) -> None:
        """Create the right Segmentation pane with toolbar, paging buttons, and controls."""
        win = self.win

        right_frame = ttk.LabelFrame(
            main_paned, text="📊 Highway Segmentation Analysis", padding=5
        )
        try:
            main_paned.add(right_frame, stretch='always')
        except Exception:
            main_paned.add(right_frame)

        win.fig_right = Figure(figsize=(7, 6), dpi=100, tight_layout=False)
        win.ax_right = win.fig_right.add_subplot(111)

        try:
            win._seg_xlim_callback_cid = win.ax_right.callbacks.connect(
                'xlim_changed',
                lambda _ax: win._update_segmentation_paging_controls(),
            )
        except Exception:
            win._seg_xlim_callback_cid = None

        seg_plot_container = ttk.Frame(right_frame)
        seg_plot_container.pack(side='top', fill='both', expand=True)
        seg_plot_container.grid_rowconfigure(0, weight=1)
        seg_plot_container.grid_columnconfigure(1, weight=1)

        win.canvas_right = FigureCanvasTkAgg(win.fig_right, seg_plot_container)

        win._break_lane_hitboxes = []
        win._break_lane_labels = []
        win._break_lane_lane_labels = []
        win._break_lane_hover_after_id = None
        win._break_lane_hover_pending = None
        win._break_lane_hover_active_patch = None
        win._break_lane_tooltip_win = None
        win._break_lane_tooltip_label = None

        try:
            win._break_lane_motion_cid = win.canvas_right.mpl_connect(
                'motion_notify_event', win._on_segmentation_mouse_move
            )
            win._break_lane_leave_cid = win.canvas_right.mpl_connect(
                'figure_leave_event', win._hide_break_lane_tooltip
            )
            win._break_lane_draw_cid = win.canvas_right.mpl_connect(
                'draw_event', win._on_segmentation_draw
            )
        except Exception:
            win._break_lane_motion_cid = None
            win._break_lane_leave_cid = None
            win._break_lane_draw_cid = None

        win.seg_page_left_button = ttk.Button(
            seg_plot_container,
            text="◀",
            width=3,
            command=lambda: win.page_segmentation_x_window(direction=-1),
        )
        win.seg_page_left_button.grid(row=0, column=0, sticky='ns', padx=(0, 6), pady=6)

        win.canvas_right.get_tk_widget().grid(row=0, column=1, sticky='nsew')

        win.seg_page_right_button = ttk.Button(
            seg_plot_container,
            text="▶",
            width=3,
            command=lambda: win.page_segmentation_x_window(direction=1),
        )
        win.seg_page_right_button.grid(row=0, column=2, sticky='ns', padx=(6, 0), pady=6)

        try:
            win.seg_page_left_button.grid_remove()
            win.seg_page_right_button.grid_remove()
        except Exception:
            pass

        right_bottom_bar = ttk.Frame(right_frame)
        right_bottom_bar.pack(side='bottom', fill='x')

        right_toolbar_container = ttk.Frame(right_bottom_bar)
        right_toolbar_container.pack(side='left', fill='x', expand=True)
        toolbar_right = _QuietToolbar(win.canvas_right, right_toolbar_container)
        toolbar_right.update()

        right_controls_container = ttk.Frame(right_bottom_bar)
        right_controls_container.pack(side='right')

        win.coord_label = ttk.Label(
            right_controls_container,
            text="",
            width=38,
            anchor='e',
        )
        win.coord_label.pack(side='right', padx=(6, 0), pady=2)
        attach_tooltip(win.coord_label,
                       "Shows the axis coordinates under the cursor using the actual column names. "
                       "A ● indicator appears when the cursor snaps to a nearby data point.")

        win.seg_xzoom_button = ttk.Checkbutton(
            right_controls_container,
            text="X Zoom",
            variable=win._seg_xzoom_var,
            command=win.toggle_segmentation_x_zoom,
            takefocus=False,
        )
        try:
            win.seg_xzoom_button.configure(cursor='arrow')
        except Exception:
            pass
        win.seg_xzoom_button.pack(side='left', padx=(0, 6), pady=2)
        attach_tooltip(win.seg_xzoom_button,
                       "Enable drag-to-zoom on the X axis. "
                       "Click and drag on the plot to select a stationing range, "
                       "then use the arrow buttons to pan left or right.")

        win.reset_seg_zoom_button = ttk.Button(
            right_controls_container,
            text="Reset Seg Zoom",
            command=win.reset_segmentation_x_zoom,
        )
        win.reset_seg_zoom_button.pack(side='left', padx=(0, 0), pady=2)
        attach_tooltip(win.reset_seg_zoom_button,
                       "Restore the segmentation graph to its full stationing range.")

        win.break_lanes_button = ttk.Checkbutton(
            right_controls_container,
            text="Break Attributes",
            variable=win._show_break_lanes_var,
            command=win.update_visualizations,
            takefocus=False,
        )
        try:
            win.break_lanes_button.configure(cursor='arrow')
        except Exception:
            pass
        win._break_lanes_pack_opts = dict(side='left', padx=(8, 0), pady=2)
        attach_tooltip(win.break_lanes_button,
                       "Show or hide the colored lane bands below the plot. "
                       "Each band represents an attribute column (e.g. surface type, jurisdiction) "
                       "whose value changes force mandatory segment boundaries.")

        win.preprocessing_changes_button = ttk.Checkbutton(
            right_controls_container,
            text="Preprocessing",
            variable=win._show_preprocessing_changes_var,
            command=win.update_visualizations,
            takefocus=False,
        )
        try:
            win.preprocessing_changes_button.configure(cursor='arrow')
        except Exception:
            pass
        win._preprocessing_changes_pack_opts = dict(side='left', padx=(8, 0), pady=2)
        attach_tooltip(win.preprocessing_changes_button,
                       "Show or hide markers for data points that were modified or "
                       "removed during preprocessing (outlier detection, etc.).")

        try:
            win.break_lanes_button.pack_forget()
        except Exception:
            pass

        win._seg_span_selector = SpanSelector(
            win.ax_right,
            win._on_segmentation_xspan_selected,
            direction='horizontal',
            useblit=True,
            interactive=False,
            props=dict(
                alpha=0.18,
                facecolor=COLORS['original_edge'],
                edgecolor=COLORS['text_secondary'],
                linewidth=1.2,
            ),
        )
        win._seg_span_selector.set_active(False)


    def _build_sash_grip(self, main_paned: tk.PanedWindow) -> None:
        """Draw a custom centered three-dot grip overlay on the pane divider."""
        win = self.win
        try:
            win._sash_handle = tk.Canvas(
                main_paned,
                width=14,
                height=34,
                highlightthickness=0,
                bd=0,
                bg=COLORS['original_edge'],
                cursor='sb_h_double_arrow',
            )

            dot_color = COLORS['text_secondary']
            cx = 7
            r = 2
            for cy in (10, 17, 24):
                win._sash_handle.create_oval(
                    cx - r, cy - r, cx + r, cy + r, fill=dot_color, outline=dot_color
                )

            def _sash_local_xy(event):
                x = int(event.x_root - main_paned.winfo_rootx())
                y = int(event.y_root - main_paned.winfo_rooty())
                return x, y

            win._sash_handle.bind(
                '<ButtonPress-1>',
                lambda e: main_paned.sash_mark(0, *_sash_local_xy(e)),
            )
            win._sash_handle.bind(
                '<B1-Motion>',
                lambda e: (
                    main_paned.sash_dragto(0, *_sash_local_xy(e)),
                    win._position_main_paned_sash_handle(),
                ),
            )
            win._sash_handle.bind(
                '<ButtonRelease-1>',
                lambda _e: win._position_main_paned_sash_handle(),
            )
            main_paned.bind('<Configure>', lambda _e: win._position_main_paned_sash_handle())
            main_paned.bind('<B1-Motion>', lambda _e: win._position_main_paned_sash_handle())
            main_paned.bind(
                '<ButtonRelease-1>', lambda _e: win._position_main_paned_sash_handle()
            )
        except Exception:
            win._sash_handle = None

    # ------------------------------------------------------------------
    # Status bar + data initialisation
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        """Create the bottom status bar and trigger original-data loading."""
        win = self.win

        win.status_frame = ttk.Frame(win.window)
        win.status_frame.pack(fill='x', padx=10, pady=(0, 5))

        win.data_status_label = ttk.Label(win.status_frame, text="", foreground='red')
        win.data_status_label.pack(side='left', padx=(0, 8))

        win.data_path_var = tk.StringVar(value="")
        win.data_path_entry = ttk.Entry(
            win.status_frame, textvariable=win.data_path_var, state='readonly'
        )
        win.data_path_entry.pack(side='left', fill='x', expand=True)

        win.selected_pareto_point = None
        win.pareto_points_data = []

        win.load_original_data()
        win._refresh_secondary_column_options()
