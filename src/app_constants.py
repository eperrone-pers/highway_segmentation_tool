"""
Application-wide configuration constants for Highway Segmentation GA.

Contains frozen dataclasses for algorithm tuning, UI layout, plotting,
caching, and validation. None of these classes have external dependencies
beyond the stdlib — import anywhere without circular-import risk.

All names are re-exported from config.py for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class AlgorithmConstants:
    """Internal algorithm constants — not user-configurable parameters."""

    init_population_max_retries: int = 10
    operator_max_retries: int = 4
    tournament_size: int = 3
    elitism_logging_frequency: int = 20
    min_front_size: int = 2


@dataclass
class UIConfig:
    """Configuration for GUI layout and appearance."""

    # Main window dimensions
    window_width: int = 1100
    window_height: int = 700
    main_padding: str = "10"

    # Layout dimensions
    left_pane_width: int = 540
    main_canvas_width: int = 540
    entry_field_width_large: int = 35
    entry_field_width_medium: int = 30
    entry_field_width_small: int = 8

    # Text widget dimensions
    text_widget_height: int = 25
    text_widget_width: int = 60

    # Grid and spacing
    standard_padding_x: Tuple[int, int] = (5, 5)
    standard_padding_y: Tuple[int, int] = (2, 0)
    section_padding_y: Tuple[int, int] = (0, 5)

    # Column spans
    standard_columnspan: int = 3
    title_columnspan: int = 3

    # File dialog settings
    csv_file_types: Tuple[Tuple[str, str], ...] = (("CSV files", "*.csv"),)
    results_file_types: Tuple[Tuple[str, str], ...] = (("JSON files", "*.json"),)


@dataclass
class PlottingConfig:
    """Configuration for matplotlib plotting and visualization."""

    # Figure dimensions and DPI
    figure_width: float = 12.0
    figure_height: float = 8.0
    figure_dpi: int = 100
    save_dpi: int = 300

    # Button positioning [left, bottom, width, height]
    export_button_position: Tuple[float, float, float, float] = (0.85, 0.02, 0.13, 0.04)
    subplot_bottom_margin: float = 0.12

    # Color schemes
    mandatory_breakpoint_color: str = 'red'
    regular_breakpoint_color: str = 'blue'
    data_point_color: str = 'black'
    pareto_front_color: str = 'red'

    # Data visualization colors
    original_data_color: str = '#7FB3D3'
    segment_line_color: str = '#1E40AF'
    pareto_scatter_color: str = '#1E40AF'
    selected_point_color: str = '#8B4A5C'

    # Transparency and styling
    data_alpha: float = 0.6
    segment_line_alpha: float = 0.8
    breakpoint_alpha: float = 0.8
    scatter_alpha: float = 0.7
    selected_alpha: float = 0.9
    grid_alpha: float = 0.3

    # Line and marker properties
    data_marker_size: int = 4
    segment_line_width: float = 2.5
    mandatory_line_width: int = 2
    regular_line_width: int = 1
    scatter_marker_size: int = 80
    selected_marker_size: int = 12
    scatter_edge_width: float = 1.2
    selected_edge_width: int = 2

    # Edge colors for markers
    pareto_edge_color: str = '#2E5B8A'
    selected_edge_color: str = '#8B4A5C'

    # Line and marker properties
    breakpoint_line_width: float = 2.0
    data_point_size: float = 1.0
    pareto_point_size: float = 50

    # Grid and axis properties
    axis_label_fontsize: int = 12
    title_fontsize: int = 14


@dataclass
class ConstraintConfig:
    """Configuration for constraint validation and reporting."""

    constraint_report_interval: int = 10
    performance_report_interval: int = 50
    constraint_report_reset_interval: int = 50

    diversity_distribution: Optional[Dict[str, float]] = None

    def __post_init__(self):
        if self.diversity_distribution is None:
            self.diversity_distribution = {
                'few_segments': 0.20,
                'medium_segments': 0.40,
                'many_segments': 0.20,
                'random': 0.20,
            }


@dataclass
class CacheConfig:
    """Configuration for fitness caching and performance optimization."""

    max_fitness_cache_size: int = 10000
    max_segment_cache_size: int = 5000
    memory_warning_threshold_mb: float = 500.0
    force_clear_threshold_mb: float = 1000.0
    cache_hit_rate_target: float = 0.7
    cache_stats_report_interval: int = 100


@dataclass
class ConstrainedOptimizationConfig:
    """Configuration specific to the constrained optimization method."""

    target_avg_length_default: float = 2.0
    length_tolerance_default: float = 0.2
    penalty_weight_default: float = 1000.0
    convergence_stability_generations: int = 10
    convergence_tolerance: float = 0.001
    mandatory_segment_threshold: float = 0.1


@dataclass
class ValidationConfig:
    """Configuration for parameter validation and bounds checking."""

    max_csv_file_size_mb: float = 100.0
    min_data_points: int = 10
    min_population_size: int = 10
    max_population_size: int = 1000
    min_generations: int = 5
    max_generations: int = 2000
    min_segment_length: float = 0.01
    max_segment_length: float = 100.0
    max_timeout_ms: int = 30000
    large_table_row_threshold: int = 100_000


# ---------------------------------------------------------------------------
# Module-level singletons — imported by name throughout the codebase.
# ---------------------------------------------------------------------------

optimization_config = AlgorithmConstants()
ui_config = UIConfig()
plotting_config = PlottingConfig()
constraint_config = ConstraintConfig()
cache_config = CacheConfig()
constrained_optimization_config = ConstrainedOptimizationConfig()
validation_config = ValidationConfig()
