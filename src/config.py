"""
Configuration Classes for Highway Segmentation Genetic Algorithm

This module centralizes all configuration constants to eliminate magic numbers
throughout the codebase and provide a single source of truth for all settings.

Author: Eric (Mott MacDonald)
Date: March 2026
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Any, List, Optional, Union, Type
from abc import ABC, abstractmethod
import tkinter as tk
import importlib


# ===== PARAMETER DEFINITION CLASSES FOR EXTENSIBLE FRAMEWORK =====
# These classes enable declarative parameter definitions for dynamic UI generation
# and consistent validation across all optimization methods.

@dataclass
class ParameterDefinition(ABC):
    """Base class for declarative parameter definitions."""
    
    # Parameter identification
    name: str                          # Parameter name (e.g., "population_size")
    display_name: str                  # Human-readable label (e.g., "Population Size")
    description: str                   # Tooltip/help text for users
    
    # UI organization
    group: str                         # Parameter group (e.g., "basic_ga", "constraint_params")
    order: int                         # Display order within group (lower = earlier)
    
    # Default and validation
    default_value: Any                 # Default parameter value
    required: bool = True              # Whether parameter is required
    
    @abstractmethod
    def create_widget(self, parent) -> tk.Widget:
        """Create appropriate tkinter widget for this parameter."""
        pass
    
    @abstractmethod
    def get_widget_value(self, widget: tk.Widget) -> Any:
        """Get current value from the widget."""
        pass
    
    @abstractmethod
    def set_widget_value(self, widget: tk.Widget, value: Any) -> None:
        """Set widget to specific value."""
        pass
    
    @abstractmethod
    def validate_value(self, value: Any) -> tuple[bool, str]:
        """Validate parameter value. Returns (is_valid, error_message)."""
        pass


@dataclass
class NumericParameter(ParameterDefinition):
    """Parameter definition for numeric values (int or float)."""
    
    # Numeric constraints
    min_value: Optional[float] = None  # Minimum allowed value
    max_value: Optional[float] = None  # Maximum allowed value
    step: float = 1.0                  # Input step size
    decimal_places: int = 0            # Number of decimal places (0 = integer)
    
    # UI configuration
    widget_width: int = 10             # Width of entry widget
    
    def create_widget(self, parent) -> tk.Entry:
        """Create numeric entry widget."""
        widget = tk.Entry(parent, width=self.widget_width)
        self.set_widget_value(widget, self.default_value)
        return widget
    
    def get_widget_value(self, widget: tk.Entry) -> Union[int, float]:
        """Get numeric value from entry widget."""
        try:
            value = float(widget.get())
            return int(value) if self.decimal_places == 0 else round(value, self.decimal_places)
        except ValueError:
            return self.default_value
    
    def set_widget_value(self, widget: tk.Entry, value: Union[int, float]) -> None:
        """Set entry widget to numeric value."""
        widget.delete(0, tk.END)
        if self.decimal_places == 0:
            widget.insert(0, str(int(value)))
        else:
            widget.insert(0, f"{value:.{self.decimal_places}f}")
    
    def validate_value(self, value: Any) -> tuple[bool, str]:
        """Validate numeric parameter."""
        try:
            num_value = float(value)
            
            # Check bounds
            if self.min_value is not None and num_value < self.min_value:
                return False, f"{self.display_name} must be >= {self.min_value}"
            if self.max_value is not None and num_value > self.max_value:
                return False, f"{self.display_name} must be <= {self.max_value}"
            
            # Check integer requirement
            if self.decimal_places == 0 and not float(num_value).is_integer():
                return False, f"{self.display_name} must be an integer"
            
            return True, ""
            
        except (ValueError, TypeError):
            return False, f"{self.display_name} must be a valid number"


@dataclass
class OptionalNumericParameter(ParameterDefinition):
    """Parameter definition for optional numeric values that can be None."""
    
    # Numeric constraints
    min_value: Optional[float] = None  # Minimum allowed value (when not None)
    max_value: Optional[float] = None  # Maximum allowed value (when not None)
    step: float = 1.0                  # Input step size
    decimal_places: int = 0            # Number of decimal places (0 = integer)
    none_text: str = "(None)"          # Text shown when value is None
    
    # UI configuration
    widget_width: int = 10             # Width of entry widget
    
    def create_widget(self, parent) -> tk.Entry:
        """Create numeric entry widget that supports None values."""
        widget = tk.Entry(parent, width=self.widget_width)
        self.set_widget_value(widget, self.default_value)
        return widget
    
    def get_widget_value(self, widget: tk.Entry) -> Union[int, float, None]:
        """Get numeric value from entry widget, supporting None."""
        text = widget.get().strip()
        if not text or text.lower() in ('none', '(none)', 'null', ''):
            return None
        try:
            value = float(text)
            return int(value) if self.decimal_places == 0 else round(value, self.decimal_places)
        except ValueError:
            return self.default_value
    
    def set_widget_value(self, widget: tk.Entry, value: Union[int, float, None]) -> None:
        """Set entry widget to numeric value or None."""
        widget.delete(0, tk.END)
        if value is None:
            widget.insert(0, self.none_text)
        elif self.decimal_places == 0:
            widget.insert(0, str(int(value)))
        else:
            widget.insert(0, f"{value:.{self.decimal_places}f}")
    
    def validate_value(self, value: Any) -> tuple[bool, str]:
        """Validate optional numeric parameter."""
        if value is None:
            return True, ""  # None is always valid for optional parameters
            
        try:
            num_value = float(value)
            
            # Check bounds
            if self.min_value is not None and num_value < self.min_value:
                return False, f"{self.display_name} must be >= {self.min_value} or None"
            if self.max_value is not None and num_value > self.max_value:
                return False, f"{self.display_name} must be <= {self.max_value} or None"
            
            # Check integer requirement
            if self.decimal_places == 0 and not float(num_value).is_integer():
                return False, f"{self.display_name} must be an integer or None"
            
            return True, ""
            
        except (ValueError, TypeError):
            return False, f"{self.display_name} must be a valid number or None"


@dataclass  
class SelectParameter(ParameterDefinition):
    """Parameter definition for selection from predefined options."""
    
    # Selection options
    options: List[tuple[str, Any]] = None    # List of (display_text, value) tuples
    
    def __post_init__(self):
        """Initialize options after instance creation."""
        if self.options is None:
            self.options = []
    
    def create_widget(self, parent) -> tk.StringVar:
        """Create combobox/dropdown widget."""
        # Note: This returns StringVar for now - actual combobox creation handled by UI builder
        widget_var = tk.StringVar(parent)
        # Find default display text
        default_display = next((display for display, val in self.options if val == self.default_value), 
                              self.options[0][0] if self.options else "")
        widget_var.set(default_display)
        return widget_var
    
    def get_widget_value(self, widget: tk.StringVar) -> Any:
        """Get selected value from combobox."""
        display_text = widget.get()
        # Find corresponding value
        for display, value in self.options:
            if display == display_text:
                return value
        return self.default_value
    
    def set_widget_value(self, widget: tk.StringVar, value: Any) -> None:
        """Set combobox to specific value."""
        # Find display text for value
        display_text = next((display for display, val in self.options if val == value), 
                           self.options[0][0] if self.options else "")
        widget.set(display_text)
    
    def validate_value(self, value: Any) -> tuple[bool, str]:
        """Validate selection parameter."""
        valid_values = [val for _, val in self.options]
        if value in valid_values:
            return True, ""
        return False, f"{self.display_name} must be one of: {', '.join(str(v) for v in valid_values)}"


@dataclass
class BoolParameter(ParameterDefinition):
    """Parameter definition for boolean (checkbox) values."""
    
    def create_widget(self, parent) -> tk.BooleanVar:
        """Create checkbox widget variable."""
        widget_var = tk.BooleanVar(parent)
        widget_var.set(self.default_value)
        return widget_var
    
    def get_widget_value(self, widget: tk.BooleanVar) -> bool:
        """Get boolean value from checkbox."""
        return widget.get()
    
    def set_widget_value(self, widget: tk.BooleanVar, value: bool) -> None:
        """Set checkbox to boolean value."""
        widget.set(bool(value))
    
    def validate_value(self, value: Any) -> tuple[bool, str]:
        """Validate boolean parameter."""
        if isinstance(value, bool):
            return True, ""
        return False, f"{self.display_name} must be True or False"


@dataclass
class TextParameter(ParameterDefinition):
    """Parameter definition for text/string values."""
    
    # Text constraints
    min_length: int = 0                # Minimum string length
    max_length: Optional[int] = None   # Maximum string length  
    allowed_chars: Optional[str] = None # Regex pattern for allowed characters
    
    # UI configuration
    widget_width: int = 30             # Width of entry widget
    multiline: bool = False            # Use Text widget instead of Entry
    
    def create_widget(self, parent) -> Union[tk.Entry, tk.Text]:
        """Create text entry widget."""
        if self.multiline:
            widget = tk.Text(parent, width=self.widget_width, height=3)
            widget.insert("1.0", str(self.default_value))
        else:
            widget = tk.Entry(parent, width=self.widget_width)
            widget.insert(0, str(self.default_value))
        return widget
    
    def get_widget_value(self, widget: Union[tk.Entry, tk.Text]) -> str:
        """Get text value from widget."""
        if isinstance(widget, tk.Text):
            return widget.get("1.0", tk.END).strip()
        else:
            return widget.get()
    
    def set_widget_value(self, widget: Union[tk.Entry, tk.Text], value: str) -> None:
        """Set widget to text value."""
        if isinstance(widget, tk.Text):
            widget.delete("1.0", tk.END)
            widget.insert("1.0", str(value))
        else:
            widget.delete(0, tk.END)
            widget.insert(0, str(value))
    
    def validate_value(self, value: Any) -> tuple[bool, str]:
        """Validate text parameter."""
        str_value = str(value)
        
        # Check length constraints
        if len(str_value) < self.min_length:
            return False, f"{self.display_name} must be at least {self.min_length} characters"
        if self.max_length and len(str_value) > self.max_length:
            return False, f"{self.display_name} must be at most {self.max_length} characters"
        
        # Check character pattern (if specified)
        if self.allowed_chars:
            import re
            if not re.match(self.allowed_chars, str_value):
                return False, f"{self.display_name} contains invalid characters"
        
        return True, ""


# ===== METHOD-SPECIFIC PARAMETER DEFINITIONS =====
# Each method defines its complete parameter list independently
# No shared parameters - each method owns all its parameters even if names are similar

SINGLE_OBJECTIVE_GA_PARAMETERS = [
    # Segment length constraints
    NumericParameter(
        name="min_length", display_name="Min Segment Length", 
        description="Minimum allowed segment length in miles",
        group="segment_constraints", order=1, default_value=0.5,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    NumericParameter(
        name="max_length", display_name="Max Segment Length",
        description="Maximum allowed segment length in miles", 
        group="segment_constraints", order=2, default_value=10.0,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    
    # Genetic Algorithm parameters
    NumericParameter(
        name="population_size", display_name="Population Size",
        description="Number of individuals in each generation",
        group="genetic_algorithm", order=1, default_value=100,
        min_value=10, max_value=1000, decimal_places=0
    ),
    NumericParameter(
        name="num_generations", display_name="Generations", 
        description="Number of evolutionary generations to run",
        group="genetic_algorithm", order=2, default_value=200,  # Single-objective default
        min_value=1, max_value=10000, decimal_places=0
    ),
    NumericParameter(
        name="crossover_rate", display_name="Crossover Rate",
        description="Probability of crossover operations (0.0-1.0)",
        group="genetic_algorithm", order=3, default_value=0.8,
        min_value=0.1, max_value=1.0, decimal_places=3
    ),
    NumericParameter(
        name="mutation_rate", display_name="Mutation Rate", 
        description="Probability of mutation operations (0.0-1.0)",
        group="genetic_algorithm", order=4, default_value=0.05,
        min_value=0.001, max_value=0.5, decimal_places=3
    ),
    NumericParameter(
        name="elite_ratio", display_name="Elite Ratio",
        description="Proportion of best individuals preserved each generation",
        group="genetic_algorithm", order=5, default_value=0.05,
        min_value=0.01, max_value=0.20, decimal_places=3
    ),
    
    # Performance settings
    NumericParameter(
        name="cache_clear_interval", display_name="Cache Clear Interval",
        description="Number of generations between cache clears",
        group="performance", order=1, default_value=50,
        min_value=1, max_value=1000, decimal_places=0
    ),
    BoolParameter(
        name="enable_performance_stats", display_name="Performance Statistics",
        description="Enable detailed performance tracking and reporting",
        group="performance", order=2, default_value=True

    )
]

MULTI_OBJECTIVE_NSGA2_PARAMETERS = [
    # Segment length constraints (same names but method-specific instances)
    NumericParameter(
        name="min_length", display_name="Min Segment Length",
        description="Minimum allowed segment length in miles", 
        group="segment_constraints", order=1, default_value=0.5,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    NumericParameter(
        name="max_length", display_name="Max Segment Length",
        description="Maximum allowed segment length in miles",
        group="segment_constraints", order=2, default_value=10.0,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    
    # Genetic Algorithm parameters (no elite_ratio for NSGA-II)
    NumericParameter(
        name="population_size", display_name="Population Size",
        description="Number of individuals in each generation",
        group="genetic_algorithm", order=1, default_value=100,
        min_value=10, max_value=1000, decimal_places=0
    ),
    NumericParameter(
        name="num_generations", display_name="Generations",
        description="Number of evolutionary generations to run", 
        group="genetic_algorithm", order=2, default_value=100,  # Multi-objective default (different!)
        min_value=1, max_value=10000, decimal_places=0
    ),
    NumericParameter(
        name="crossover_rate", display_name="Crossover Rate",
        description="Probability of crossover operations (0.0-1.0)",
        group="genetic_algorithm", order=3, default_value=0.8,
        min_value=0.1, max_value=1.0, decimal_places=3
    ),
    NumericParameter(
        name="mutation_rate", display_name="Mutation Rate",
        description="Probability of mutation operations (0.0-1.0)",
        group="genetic_algorithm", order=4, default_value=0.05,
        min_value=0.001, max_value=0.5, decimal_places=3
    ),
    
    # Performance settings
    NumericParameter(
        name="cache_clear_interval", display_name="Cache Clear Interval",
        description="Number of generations between cache clears",
        group="performance", order=1, default_value=50,
        min_value=1, max_value=1000, decimal_places=0
    ),
    BoolParameter(
        name="enable_performance_stats", display_name="Performance Statistics", 
        description="Enable detailed performance tracking and reporting",
        group="performance", order=2, default_value=True
    )
]

CONSTRAINED_SINGLE_OBJECTIVE_PARAMETERS = [
    # Segment length constraints  
    NumericParameter(
        name="min_length", display_name="Min Segment Length",
        description="Minimum allowed segment length in miles",
        group="segment_constraints", order=1, default_value=0.5,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    NumericParameter(
        name="max_length", display_name="Max Segment Length", 
        description="Maximum allowed segment length in miles",
        group="segment_constraints", order=2, default_value=10.0,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    
    # Genetic Algorithm parameters
    NumericParameter(
        name="population_size", display_name="Population Size",
        description="Number of individuals in each generation", 
        group="genetic_algorithm", order=1, default_value=100,
        min_value=10, max_value=1000, decimal_places=0
    ),
    NumericParameter(
        name="num_generations", display_name="Generations",
        description="Number of evolutionary generations to run",
        group="genetic_algorithm", order=2, default_value=150,  # Constrained default (different!)
        min_value=1, max_value=10000, decimal_places=0
    ),
    NumericParameter(
        name="crossover_rate", display_name="Crossover Rate",
        description="Probability of crossover operations (0.0-1.0)",
        group="genetic_algorithm", order=3, default_value=0.8,
        min_value=0.1, max_value=1.0, decimal_places=3
    ),
    NumericParameter(
        name="mutation_rate", display_name="Mutation Rate",
        description="Probability of mutation operations (0.0-1.0)",
        group="genetic_algorithm", order=4, default_value=0.05,
        min_value=0.001, max_value=0.5, decimal_places=3
    ),
    NumericParameter(
        name="elite_ratio", display_name="Elite Ratio", 
        description="Proportion of best individuals preserved each generation",
        group="genetic_algorithm", order=5, default_value=0.05,
        min_value=0.01, max_value=0.20, decimal_places=3
    ),
    
    # Constraint-specific parameters
    NumericParameter(
        name="target_avg_length", display_name="Target Avg Length",
        description="Target average segment length in miles",
        group="constraints", order=1, default_value=2.0,
        min_value=0.01, max_value=50.0, decimal_places=2
    ),
    NumericParameter(
        name="penalty_weight", display_name="Penalty Weight",
        description="Weight applied to constraint violation penalties",
        group="constraints", order=2, default_value=1000.0,
        min_value=0.0, max_value=100000.0, decimal_places=1
    ),
    NumericParameter(
        name="length_tolerance", display_name="Length Tolerance",
        description="Acceptable tolerance around target length",
        group="constraints", order=3, default_value=0.2,
        min_value=0.01, max_value=1.0, decimal_places=3
    ),
    
    # Performance settings
    NumericParameter(
        name="cache_clear_interval", display_name="Cache Clear Interval", 
        description="Number of generations between cache clears",
        group="performance", order=1, default_value=50,
        min_value=1, max_value=1000, decimal_places=0
    ),
    BoolParameter(
        name="enable_performance_stats", display_name="Performance Statistics",
        description="Enable detailed performance tracking and reporting",
        group="performance", order=2, default_value=True
    )
]

DEB_FEASIBILITY_CONSTRAINED_PARAMETERS = [
    # Segment length constraints
    NumericParameter(
        name="min_length", display_name="Min Segment Length",
        description="Minimum allowed segment length in miles",
        group="segment_constraints", order=1, default_value=0.5,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    NumericParameter(
        name="max_length", display_name="Max Segment Length",
        description="Maximum allowed segment length in miles",
        group="segment_constraints", order=2, default_value=10.0,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),

    # Genetic Algorithm parameters
    NumericParameter(
        name="population_size", display_name="Population Size",
        description="Number of individuals in each generation",
        group="genetic_algorithm", order=1, default_value=100,
        min_value=10, max_value=1000, decimal_places=0
    ),
    NumericParameter(
        name="num_generations", display_name="Generations",
        description="Number of evolutionary generations to run",
        group="genetic_algorithm", order=2, default_value=150,
        min_value=1, max_value=10000, decimal_places=0
    ),
    NumericParameter(
        name="crossover_rate", display_name="Crossover Rate",
        description="Probability of crossover operations (0.0-1.0)",
        group="genetic_algorithm", order=3, default_value=0.8,
        min_value=0.1, max_value=1.0, decimal_places=3
    ),
    NumericParameter(
        name="mutation_rate", display_name="Mutation Rate",
        description="Probability of mutation operations (0.0-1.0)",
        group="genetic_algorithm", order=4, default_value=0.05,
        min_value=0.001, max_value=0.5, decimal_places=3
    ),
    NumericParameter(
        name="elite_ratio", display_name="Elite Ratio",
        description="Proportion of best individuals preserved each generation",
        group="genetic_algorithm", order=5, default_value=0.05,
        min_value=0.01, max_value=0.20, decimal_places=3
    ),

    # Constraint parameters (no penalty weight)
    NumericParameter(
        name="target_avg_length", display_name="Target Avg Length",
        description="Target average segment length in miles",
        group="constraints", order=1, default_value=2.0,
        min_value=0.01, max_value=50.0, decimal_places=2
    ),
    NumericParameter(
        name="length_tolerance", display_name="Length Tolerance",
        description="Acceptable tolerance around target length (Deb feasibility band)",
        group="constraints", order=2, default_value=0.2,
        min_value=0.01, max_value=1.0, decimal_places=3
    ),

    # Performance settings
    NumericParameter(
        name="cache_clear_interval", display_name="Cache Clear Interval",
        description="Number of generations between cache clears",
        group="performance", order=1, default_value=50,
        min_value=1, max_value=1000, decimal_places=0
    ),
    BoolParameter(
        name="enable_performance_stats", display_name="Performance Statistics",
        description="Enable detailed performance tracking and reporting",
        group="performance", order=2, default_value=True
    )
]

AASHTO_CDA_PARAMETERS = [
    # Statistical Analysis Parameters
    NumericParameter(
        name="alpha", display_name="Significance Level",
        description="Statistical significance level for change point detection (lower = more conservative)",
        group="statistical_analysis", order=1, default_value=0.05,
        min_value=0.001, max_value=0.49, decimal_places=3
    ),
    SelectParameter(
        name="method", display_name="Error Estimation Method", 
        description="Method for estimating standard deviation of measurement error",
        group="statistical_analysis", order=2, default_value=2,
        options=[
            ("MAD with Normal Distribution", 1),
            ("Std Dev of Differences (Recommended)", 2), 
            ("Std Dev of Measurements", 3)
        ]
    ),
    BoolParameter(
        name="use_segment_length", display_name="Use Segment-Specific Length",
        description="Use individual segment lengths (recommended) vs. total data length in statistical calculations", 
        group="statistical_analysis", order=3, default_value=True  # GlobalLocal=1 in MATLAB (recommended)
    ),
    
    # Segmentation Constraints
    NumericParameter(
        name="min_segment_datapoints", display_name="Min Segment Datapoints",
        description="Minimum number of datapoints required per segment",
        group="segment_constraints", order=1, default_value=3,
        min_value=3, max_value=1000, decimal_places=0
    ),
    OptionalNumericParameter(
        name="max_segments", display_name="Max Segments", 
        description="Maximum number of segments allowed (None=no limit, algorithm may find fewer)",
        group="segment_constraints", order=2, default_value=None,
        min_value=2, max_value=10000, decimal_places=0
    ),
    NumericParameter(
        name="min_section_difference", display_name="Min Section Difference",
        description="Minimum difference in average values between adjacent segments (0=disabled)",
        group="segment_constraints", order=3, default_value=0.0,
        min_value=0.0, max_value=None, decimal_places=3
    ),
    
    # Processing Options
    BoolParameter(
        name="enable_diagnostic_output", display_name="Diagnostic Output",
        description="Enable detailed diagnostic information during processing",
        group="processing", order=1, default_value=False
    )
]


PELT_SEGMENTATION_PARAMETERS = [
    # Change point detection parameters
    SelectParameter(
        name="model",
        display_name="Cost Model",
        description="Cost function used by PELT (l2=mean shifts, l1=robust mean shifts, rbf=kernel).",
        group="change_point_detection",
        order=1,
        default_value="l2",
        options=[
            ("L2 (Mean Shifts)", "l2"),
            ("L1 (Robust Mean Shifts)", "l1"),
            ("RBF (Kernel)", "rbf"),
        ],
    ),
    NumericParameter(
        name="penalty",
        display_name="Penalty",
        description=(
            "Main sensitivity knob (higher=fewer breakpoints). "
            "Try a small grid like 6, 10, 14, 18 and pick the smallest penalty "
            "that avoids chattering."
        ),
        group="change_point_detection",
        order=2,
        default_value=12.0,
        min_value=0.1,
        max_value=5000.0,
        decimal_places=3,
    ),
    NumericParameter(
        name="jump",
        display_name="Jump",
        description="Subsample candidate change point locations (1=all points; higher=coarser/faster).",
        group="change_point_detection",
        order=3,
        default_value=1,
        min_value=1,
        max_value=50,
        decimal_places=0,
    ),

    # Smoothing parameters
    OptionalNumericParameter(
        name="smooth_window_miles",
        display_name="Smoothing Window (miles)",
        description=(
            "Optional smoothing window length in miles (None=off). "
            "For 0.1-mile spacing, 0.3–1.0 miles is a typical starting range."
        ),
        group="smoothing",
        order=1,
        default_value=None,
        min_value=0.0,
        max_value=5.0,
        decimal_places=3,
    ),
    SelectParameter(
        name="smoothing_method",
        display_name="Smoothing Method",
        description="Smoothing statistic (only used when smoothing window is enabled).",
        group="smoothing",
        order=2,
        default_value="mean",
        options=[
            ("Mean", "mean"),
            ("Median (robust to spikes)", "median"),
        ],
    ),

    # Segment constraints (use framework-style naming)
    NumericParameter(
        name="min_length",
        display_name="Min Segment Length",
        description=(
            "Minimum segment length in miles. Also enforces a minimum of 2 samples per segment internally."
        ),
        group="segment_constraints",
        order=1,
        default_value=0.5,
        min_value=0.0,
        max_value=100.0,
        decimal_places=3,
    ),
    NumericParameter(
        name="max_length",
        display_name="Max Segment Length",
        description=(
            "Maximum segment length in miles. PELT does not natively enforce a maximum; "
            "we post-process and split any overlong data segments while preserving gap segments."
        ),
        group="segment_constraints",
        order=2,
        default_value=5.0,
        min_value=0.0,
        max_value=100.0,
        decimal_places=3,
    ),

    # Processing options
    BoolParameter(
        name="enable_diagnostic_output",
        display_name="Diagnostic Output",
        description="Include additional per-section diagnostics in results (useful for debugging/tuning).",
        group="processing",
        order=1,
        default_value=False,
    ),
]


@dataclass
class AlgorithmConstants:
    """Internal algorithm constants - not user-configurable parameters."""
    
    # Algorithm implementation constants (not user-configurable)
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
    left_pane_width: int = 540  # Adjusted to fully show all buttons without cutting off
    main_canvas_width: int = 540
    entry_field_width_large: int = 35
    entry_field_width_medium: int = 30
    entry_field_width_small: int = 8
    
    # Text widget dimensions
    text_widget_height: int = 25
    text_widget_width: int = 60
    
    # Grid and spacing (reduced for more compact UI)
    standard_padding_x: Tuple[int, int] = (5, 5)
    standard_padding_y: Tuple[int, int] = (2, 0)  # Reduced from (5, 0)
    section_padding_y: Tuple[int, int] = (0, 5)  # Reduced from (0, 10)
    
    # Column spans for different sections
    standard_columnspan: int = 3
    title_columnspan: int = 3
    
    # File dialog settings
    csv_file_types: Tuple[Tuple[str, str], ...] = (("CSV files", "*.csv"),)  # For input data files
    results_file_types: Tuple[Tuple[str, str], ...] = (("JSON files", "*.json"),)  # For output results files


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
    selected_point_color: str = '#8B4A5C'  # Sophisticated burgundy instead of jarring red
    
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
    scatter_marker_size: int = 80  # scatter() uses s= (area in points²)
    selected_marker_size: int = 12  # plot() uses markersize= (diameter in points) - equivalent to ~113 points² area
    scatter_edge_width: float = 1.2
    selected_edge_width: int = 2
    
    # Edge colors for markers
    pareto_edge_color: str = '#2E5B8A'
    selected_edge_color: str = '#8B4A5C'  # Sophisticated burgundy instead of jarring red
    
    # Line and marker properties
    breakpoint_line_width: float = 2.0
    data_point_size: float = 1.0
    pareto_point_size: float = 50
    
    # Grid and axis properties
    grid_alpha: float = 0.3
    axis_label_fontsize: int = 12
    title_fontsize: int = 14


@dataclass
class ConstraintConfig:
    """Configuration for constraint validation and reporting."""
    
    # Reporting intervals
    constraint_report_interval: int = 10  # Every N generations
    performance_report_interval: int = 50  # Every N generations for detailed stats
    constraint_report_reset_interval: int = 50  # Reset crossover failures every N generations
    
    # Population diversity settings
    diversity_distribution: Dict[str, float] = None
    
    def __post_init__(self):
        """Initialize diversity distribution after instance creation."""
        if self.diversity_distribution is None:
            self.diversity_distribution = {
                'few_segments': 0.20,    # 20% with few segments (2-5)
                'medium_segments': 0.40,  # 40% with medium segments
                'many_segments': 0.20,    # 20% with many segments  
                'random': 0.20           # 20% completely random
            }


@dataclass
class CacheConfig:
    """Configuration for fitness caching and performance optimization."""
    
    # Cache sizes (number of entries)
    max_fitness_cache_size: int = 10000
    max_segment_cache_size: int = 5000
    
    # Memory management thresholds
    memory_warning_threshold_mb: float = 500.0  # Warn when cache exceeds this
    force_clear_threshold_mb: float = 1000.0    # Force clear when cache exceeds this
    
    # Performance monitoring
    cache_hit_rate_target: float = 0.7  # Target 70% hit rate
    cache_stats_report_interval: int = 100  # Report stats every N operations


@dataclass
class ConstrainedOptimizationConfig:
    """Configuration specific to constrained optimization method."""
    
    # Default constraint parameters
    target_avg_length_default: float = 2.0
    length_tolerance_default: float = 0.2
    penalty_weight_default: float = 1000.0
    
    # Convergence criteria
    convergence_stability_generations: int = 10  # Check stability over last N generations
    convergence_tolerance: float = 0.001  # Consider converged if change < this
    
    # Target calculation parameters
    mandatory_segment_threshold: float = 0.1  # Significant if > 10% of total distance


@dataclass
class ValidationConfig:
    """Configuration for parameter validation and bounds checking."""
    
    # File validation
    max_csv_file_size_mb: float = 100.0
    min_data_points: int = 10
    
    # Parameter bounds
    min_population_size: int = 10
    max_population_size: int = 1000
    min_generations: int = 5
    max_generations: int = 2000
    
    # Length constraint bounds  
    min_segment_length: float = 0.01  # 0.01 miles minimum
    max_segment_length: float = 100.0  # 100 miles maximum
    
    # Performance bounds
    max_timeout_ms: int = 30000  # 30 second maximum timeout


@dataclass
class ObjectivePlotConfig:
    """Configuration for plotting a specific objective in multi-objective visualizations.
    Convention: objective[0] = X axis, objective[1] = Y axis"""
    name: str                                # Display name for the objective
    description: str                         # Detailed description for tooltips  
    transform: Optional[str] = None          # Transformation to apply: "negate", "log", "sqrt", etc.
    reverse_scale: bool = False              # Whether to reverse the axis scale (high to low)

@dataclass
class OptimizationMethodConfig:
    """Configuration for a single optimization method - enables extensible method architecture."""
    method_key: str                          # Internal identifier (e.g., "single", "multi", "constrained")
    display_name: str                        # User-friendly name for dropdown
    description: str                         # Tooltip/help description for users
    parameters: List[ParameterDefinition]    # Complete parameter list for this method
    return_type: str                         # "single_objective" or "multi_objective" (controls visualization)

    # Dispatch mechanism: importable method class path
    # Example: "analysis.methods.aashto_cda.AashtoCdaMethod"
    method_class_path: str
    
    # Optional visualization configuration (backwards compatible)
    objective_names: Optional[List[str]] = None           # Names for objectives in plots (e.g., ["Data Fit", "Segment Count"])
    objective_descriptions: Optional[List[str]] = None    # Detailed descriptions for tooltips
    
    # Enhanced multi-objective plotting configuration  
    objective_plot_configs: Optional[List[ObjectivePlotConfig]] = None  # Per-objective plotting specifications
    

# ===== EXTENSIBLE OPTIMIZATION METHODS REGISTRY =====
# This registry makes adding new optimization methods a "5-minute change"
# Simply add parameter list above + OptimizationMethodConfig entry + implement runner function

OPTIMIZATION_METHODS = [
    OptimizationMethodConfig(
        method_key="single",
        display_name="Single-Objective GA",
        description="Traditional genetic algorithm focused on minimizing data deviation only. Fast convergence, single best solution.",
        parameters=SINGLE_OBJECTIVE_GA_PARAMETERS,
        return_type="single_objective",  # Shows segmentation graph only
        method_class_path="analysis.methods.single_objective.SingleObjectiveMethod",
    ),
    OptimizationMethodConfig(
        method_key="multi", 
        display_name="Multi-Objective NSGA-II",
        description="Pareto front optimization exploring trade-offs between total deviation and average segment length. Multiple optimal solutions.",
        parameters=MULTI_OBJECTIVE_NSGA2_PARAMETERS,
        return_type="multi_objective",  # Shows pareto front + segmentation graph
        method_class_path="analysis.methods.multi_objective.MultiObjectiveMethod",
        objective_names=["Total Deviation", "Average Segment Length"],
        objective_descriptions=[
            "Total deviation from target values (algorithm maximizes negative deviation for minimization)",
            "Average length of highway segments (algorithm maximizes positive length)"
        ],
        objective_plot_configs=[
            ObjectivePlotConfig(
                name="Total Deviation", 
                description="Total deviation - convert negative GA value to positive for minimization display",
                transform="negate"  # Convert GA's negative deviation to positive for plotting
            ),
            ObjectivePlotConfig(
                name="Average Segment Length",
                description="Average segment length - use positive GA value directly for maximization display"
                # No transform needed - GA returns positive values, plot shows maximization
            )
        ]
    ),
    OptimizationMethodConfig(
        method_key="constrained",
        display_name="Constrained Single-Objective", 
        description="Target-length optimization with penalty-based fitness for specific average segment length requirements.",
        parameters=CONSTRAINED_SINGLE_OBJECTIVE_PARAMETERS,
        return_type="single_objective",  # Shows segmentation graph only
        method_class_path="analysis.methods.constrained.ConstrainedMethod",
    ),
    OptimizationMethodConfig(
        method_key="constrained_deb",
        display_name="Constrained GA (Deb Feasibility)",
        description="Constrained single-objective GA using Deb feasibility rules (constraint domination) instead of penalty weights.",
        parameters=DEB_FEASIBILITY_CONSTRAINED_PARAMETERS,
        return_type="single_objective",
        method_class_path="analysis.methods.deb_feasibility_constrained.DebFeasibilityConstrainedMethod",
    ),
    OptimizationMethodConfig(
        method_key="aashto_cda",
        display_name="AASHTO CDA Statistical Analysis",
        description="Enhanced AASHTO Cumulative Difference Approach for deterministic statistical change point detection. Fast, statistically-justified segmentation without evolutionary computation.",
        parameters=AASHTO_CDA_PARAMETERS,
        return_type="single_objective",  # Shows segmentation graph only
        method_class_path="analysis.methods.aashto_cda.AashtoCdaMethod",
    ),
    OptimizationMethodConfig(
        method_key="pelt_segmentation",
        display_name="PELT Segmentation (ruptures)",
        description="Deterministic change-point detection using PELT (ruptures). Penalty controls sensitivity; supports optional smoothing and minimum segment length.",
        parameters=PELT_SEGMENTATION_PARAMETERS,
        return_type="single_objective",
        method_class_path="analysis.methods.pelt_segmentation.PeltSegmentationMethod",
    )
    # FUTURE METHODS - Easy to add with completely different parameter sets:
    #
    # OptimizationMethodConfig(
    #     method_key="deterministic",
    #     display_name="Deterministic Breakpoint Detection",
    #     description="Statistical analysis-based deterministic segmentation without evolutionary computation.",
    #     parameters=DETERMINISTIC_BREAKPOINT_PARAMETERS,  # No GA parameters at all!
    #     return_type="single_objective",  # Shows segmentation graph only
    #     method_class_path="analysis.methods.deterministic.DeterministicMethod",
    # ),
    #
    # OptimizationMethodConfig(
    #     method_key="machine_learning",
    #     display_name="ML-Based Segmentation", 
    #     description="Machine learning approach using trained models for pattern recognition.",
    #     parameters=ML_SEGMENTATION_PARAMETERS,  # Completely different parameter set!
    #     return_type="single_objective",  # Shows segmentation graph only
    #     method_class_path="analysis.methods.ml_segmentation.MlSegmentationMethod",
    # )
]

# Helper functions for method configuration management
def get_optimization_method(method_key: str) -> OptimizationMethodConfig:
    """Get optimization method configuration by key."""
    for method in OPTIMIZATION_METHODS:
        if method.method_key == method_key:
            return method
    raise ValueError(f"Unknown optimization method key: {method_key}")


def resolve_method_class(method_key: str) -> Type:
    """Resolve a configured analysis method class from `OptimizationMethodConfig.method_class_path`.

    Used for config-driven dispatch via an importable class path.
    """
    method_config = get_optimization_method(method_key)
    class_path = method_config.method_class_path
    if not class_path:
        raise ValueError(
            f"Method '{method_key}' is missing a valid method_class_path in OPTIMIZATION_METHODS"
        )

    if '.' not in class_path:
        raise ValueError(
            f"Invalid method_class_path for method '{method_key}': '{class_path}' (expected module.ClassName)"
        )

    module_path, class_name = class_path.rsplit('.', 1)
    try:
        module = importlib.import_module(module_path)
    except Exception as e:
        raise ImportError(
            f"Could not import module '{module_path}' for method '{method_key}' (method_class_path='{class_path}'): {e}"
        ) from e

    try:
        cls = getattr(module, class_name)
    except AttributeError as e:
        raise ImportError(
            f"Module '{module_path}' does not define class '{class_name}' for method '{method_key}' (method_class_path='{class_path}')"
        ) from e

    return cls


def validate_optimization_method_registry() -> None:
    """Validate that all configured methods have importable, compatible implementations.

    This is intended to run at application startup so configuration errors fail fast.
    """
    errors: List[str] = []
    try:
        from analysis.base import AnalysisMethodBase
    except Exception as e:
        raise ImportError(f"Could not import AnalysisMethodBase for validation: {e}") from e

    for method in OPTIMIZATION_METHODS:
        try:
            cls = resolve_method_class(method.method_key)
            if not isinstance(cls, type):
                raise TypeError(
                    f"Resolved object is not a class (got {type(cls).__name__})"
                )
            if not issubclass(cls, AnalysisMethodBase):
                raise TypeError(
                    f"{cls.__module__}.{cls.__name__} does not inherit from AnalysisMethodBase"
                )
        except Exception as e:
            errors.append(
                f"- method_key='{method.method_key}', display_name='{method.display_name}': {e}"
            )

    if errors:
        raise ValueError(
            "Optimization method registry validation failed. Fix OPTIMIZATION_METHODS in src/config.py:\n"
            + "\n".join(errors)
        )

def get_optimization_method_names() -> list:
    """Get list of all optimization method display names for dropdown."""
    return [method.display_name for method in OPTIMIZATION_METHODS]

def get_method_key_from_display_name(display_name: str) -> str:
    """Get method key from display name."""
    for method in OPTIMIZATION_METHODS:
        if method.display_name == display_name:
            return method.method_key
    raise ValueError(f"Unknown display name: {display_name}")

def get_default_method_key() -> str:
    """Get the default optimization method key."""
    return OPTIMIZATION_METHODS[0].method_key if OPTIMIZATION_METHODS else "single"

def get_method_parameters(method_key: str) -> List[ParameterDefinition]:
    """Get parameter list for a specific method."""
    method = get_optimization_method(method_key)
    return method.parameters

def get_parameter_groups(method_key: str) -> Dict[str, List[ParameterDefinition]]:
    """Get parameters organized by group for a specific method."""
    parameters = get_method_parameters(method_key)
    groups = {}
    for param in parameters:
        if param.group not in groups:
            groups[param.group] = []
        groups[param.group].append(param)
    
    # Sort parameters within each group by order
    for group_params in groups.values():
        group_params.sort(key=lambda p: p.order)
    
    return groups

def get_parameter_defaults(method_key: str) -> Dict[str, Any]:
    """Get dictionary of default parameter values for a method."""
    parameters = get_method_parameters(method_key)
    return {param.name: param.default_value for param in parameters}

def is_multi_objective_method(method_key: str) -> bool:
    """Check if method returns multi-objective results (controls visualization).
    
    Args:
        method_key: Method key string (e.g., "single", "multi", "constrained")
        
    Returns:
        bool: True if method has return_type == "multi_objective"
    """
    method = get_optimization_method(method_key)
    return method.return_type == "multi_objective"


# Removed get_method_config_by_analysis_method - no longer needed!
# JSON now stores method_key directly, eliminating the need for hard-coded mapping


# ===== LEGACY CONFIGURATION CLASSES =====
# These are kept for backward compatibility during transition
# The existing configuration classes remain unchanged for now


# ===== CONFIGURATION INSTANCES =====
# Single instances of each configuration class for global use
# These provide backward compatibility for existing code

# Core configuration instances
optimization_config = AlgorithmConstants()
ui_config = UIConfig()
plotting_config = PlottingConfig()
constraint_config = ConstraintConfig()
cache_config = CacheConfig()
constrained_optimization_config = ConstrainedOptimizationConfig()
validation_config = ValidationConfig()

# Helper function to get all config instances
def get_all_configs():
    """Get dictionary of all configuration instances."""
    return {
        'optimization': optimization_config,
        'ui': ui_config,
        'plotting': plotting_config,
        'constraint': constraint_config,
        'cache': cache_config,
        'constrained_optimization': constrained_optimization_config,
        'validation': validation_config
    }