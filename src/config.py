"""
Configuration Classes for Highway Segmentation Genetic Algorithm

This module centralizes all configuration constants to eliminate magic numbers
throughout the codebase and provide a single source of truth for all settings.

Author: Eric (Mott MacDonald)
Date: March 2026
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Type
import importlib


# ===== PARAMETER DEFINITION CLASSES FOR EXTENSIBLE FRAMEWORK =====
# Moved to parameter_definitions.py; re-exported here for backward compatibility.
from parameter_definitions import (  # noqa: E402
    ParameterDefinition,  # noqa: F401
    NumericParameter,  # noqa: F401
    OptionalNumericParameter,  # noqa: F401
    SelectParameter,  # noqa: F401
    ColumnSelectParameter,  # noqa: F401
    MultiColumnSelectParameter,  # noqa: F401
    BoolParameter,  # noqa: F401
    TextParameter,  # noqa: F401
)


# ===== METHOD-SPECIFIC PARAMETER DEFINITIONS =====
# Each method defines its complete parameter list independently
# No shared parameters - each method owns all its parameters even if names are similar

SINGLE_OBJECTIVE_GA_PARAMETERS = [
    # Segment length constraints
    NumericParameter(
        name="min_length", display_name="Min Segment Length", 
        description="Minimum allowed segment length in miles",
        group="04_segment_constraints", order=1, default_value=0.5,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    NumericParameter(
        name="max_length", display_name="Max Segment Length",
        description="Maximum allowed segment length in miles", 
        group="04_segment_constraints", order=2, default_value=10.0,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    
    # Genetic Algorithm parameters
    NumericParameter(
        name="population_size", display_name="Population Size",
        description="Number of individuals in each generation",
        group="05_genetic_algorithm", order=1, default_value=100,
        min_value=10, max_value=1000, decimal_places=0
    ),
    NumericParameter(
        name="num_generations", display_name="Generations", 
        description="Number of evolutionary generations to run",
        group="05_genetic_algorithm", order=2, default_value=200,  # Single-objective default
        min_value=1, max_value=10000, decimal_places=0
    ),
    NumericParameter(
        name="crossover_rate", display_name="Crossover Rate",
        description="Probability of crossover operations (0.0-1.0)",
        group="05_genetic_algorithm", order=3, default_value=0.8,
        min_value=0.1, max_value=1.0, decimal_places=3
    ),
    NumericParameter(
        name="mutation_rate", display_name="Mutation Rate", 
        description="Probability of mutation operations (0.0-1.0)",
        group="05_genetic_algorithm", order=4, default_value=0.05,
        min_value=0.001, max_value=0.5, decimal_places=3
    ),
    NumericParameter(
        name="elite_ratio", display_name="Elite Ratio",
        description="Proportion of best individuals preserved each generation",
        group="05_genetic_algorithm", order=5, default_value=0.05,
        min_value=0.01, max_value=0.20, decimal_places=3
    ),
    
    # Performance settings
    NumericParameter(
        name="cache_clear_interval", display_name="Cache Clear Interval",
        description="Number of generations between cache clears",
        group="08_performance", order=1, default_value=50,
        min_value=1, max_value=1000, decimal_places=0
    ),
    BoolParameter(
        name="enable_performance_stats", display_name="Performance Statistics",
        description="Enable detailed performance tracking and reporting",
        group="08_performance", order=2, default_value=True

    )
]

MULTI_OBJECTIVE_NSGA2_PARAMETERS = [
    # Segment length constraints (same names but method-specific instances)
    NumericParameter(
        name="min_length", display_name="Min Segment Length",
        description="Minimum allowed segment length in miles", 
        group="04_segment_constraints", order=1, default_value=0.5,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    NumericParameter(
        name="max_length", display_name="Max Segment Length",
        description="Maximum allowed segment length in miles",
        group="04_segment_constraints", order=2, default_value=10.0,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    
    # Genetic Algorithm parameters (no elite_ratio for NSGA-II)
    NumericParameter(
        name="population_size", display_name="Population Size",
        description="Number of individuals in each generation",
        group="05_genetic_algorithm", order=1, default_value=100,
        min_value=10, max_value=1000, decimal_places=0
    ),
    NumericParameter(
        name="num_generations", display_name="Generations",
        description="Number of evolutionary generations to run", 
        group="05_genetic_algorithm", order=2, default_value=100,  # Multi-objective default (different!)
        min_value=1, max_value=10000, decimal_places=0
    ),
    NumericParameter(
        name="crossover_rate", display_name="Crossover Rate",
        description="Probability of crossover operations (0.0-1.0)",
        group="05_genetic_algorithm", order=3, default_value=0.8,
        min_value=0.1, max_value=1.0, decimal_places=3
    ),
    NumericParameter(
        name="mutation_rate", display_name="Mutation Rate",
        description="Probability of mutation operations (0.0-1.0)",
        group="05_genetic_algorithm", order=4, default_value=0.05,
        min_value=0.001, max_value=0.5, decimal_places=3
    ),
    
    # Performance settings
    NumericParameter(
        name="cache_clear_interval", display_name="Cache Clear Interval",
        description="Number of generations between cache clears",
        group="08_performance", order=1, default_value=50,
        min_value=1, max_value=1000, decimal_places=0
    ),
    BoolParameter(
        name="enable_performance_stats", display_name="Performance Statistics", 
        description="Enable detailed performance tracking and reporting",
        group="08_performance", order=2, default_value=True
    )
]

CONSTRAINED_SINGLE_OBJECTIVE_PARAMETERS = [
    # Segment length constraints  
    NumericParameter(
        name="min_length", display_name="Min Segment Length",
        description="Minimum allowed segment length in miles",
        group="04_segment_constraints", order=1, default_value=0.5,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    NumericParameter(
        name="max_length", display_name="Max Segment Length", 
        description="Maximum allowed segment length in miles",
        group="04_segment_constraints", order=2, default_value=10.0,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    
    # Genetic Algorithm parameters
    NumericParameter(
        name="population_size", display_name="Population Size",
        description="Number of individuals in each generation", 
        group="05_genetic_algorithm", order=1, default_value=100,
        min_value=10, max_value=1000, decimal_places=0
    ),
    NumericParameter(
        name="num_generations", display_name="Generations",
        description="Number of evolutionary generations to run",
        group="05_genetic_algorithm", order=2, default_value=150,  # Constrained default (different!)
        min_value=1, max_value=10000, decimal_places=0
    ),
    NumericParameter(
        name="crossover_rate", display_name="Crossover Rate",
        description="Probability of crossover operations (0.0-1.0)",
        group="05_genetic_algorithm", order=3, default_value=0.8,
        min_value=0.1, max_value=1.0, decimal_places=3
    ),
    NumericParameter(
        name="mutation_rate", display_name="Mutation Rate",
        description="Probability of mutation operations (0.0-1.0)",
        group="05_genetic_algorithm", order=4, default_value=0.05,
        min_value=0.001, max_value=0.5, decimal_places=3
    ),
    NumericParameter(
        name="elite_ratio", display_name="Elite Ratio", 
        description="Proportion of best individuals preserved each generation",
        group="05_genetic_algorithm", order=5, default_value=0.05,
        min_value=0.01, max_value=0.20, decimal_places=3
    ),
    
    # Constraint-specific parameters
    NumericParameter(
        name="target_avg_length", display_name="Target Avg Length",
        description="Target average segment length in miles",
        group="06_constraints", order=1, default_value=2.0,
        min_value=0.01, max_value=50.0, decimal_places=2
    ),
    NumericParameter(
        name="penalty_weight", display_name="Penalty Weight",
        description="Weight applied to constraint violation penalties",
        group="06_constraints", order=2, default_value=1000.0,
        min_value=0.0, max_value=100000.0, decimal_places=1
    ),
    NumericParameter(
        name="length_tolerance", display_name="Length Tolerance",
        description="Acceptable tolerance around target length",
        group="06_constraints", order=3, default_value=0.2,
        min_value=0.01, max_value=1.0, decimal_places=3
    ),
    
    # Performance settings
    NumericParameter(
        name="cache_clear_interval", display_name="Cache Clear Interval", 
        description="Number of generations between cache clears",
        group="08_performance", order=1, default_value=50,
        min_value=1, max_value=1000, decimal_places=0
    ),
    BoolParameter(
        name="enable_performance_stats", display_name="Performance Statistics",
        description="Enable detailed performance tracking and reporting",
        group="08_performance", order=2, default_value=True
    )
]

DEB_FEASIBILITY_CONSTRAINED_PARAMETERS = [
    # Segment length constraints
    NumericParameter(
        name="min_length", display_name="Min Segment Length",
        description="Minimum allowed segment length in miles",
        group="04_segment_constraints", order=1, default_value=0.5,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),
    NumericParameter(
        name="max_length", display_name="Max Segment Length",
        description="Maximum allowed segment length in miles",
        group="04_segment_constraints", order=2, default_value=10.0,
        min_value=0.01, max_value=100.0, decimal_places=2
    ),

    # Genetic Algorithm parameters
    NumericParameter(
        name="population_size", display_name="Population Size",
        description="Number of individuals in each generation",
        group="05_genetic_algorithm", order=1, default_value=100,
        min_value=10, max_value=1000, decimal_places=0
    ),
    NumericParameter(
        name="num_generations", display_name="Generations",
        description="Number of evolutionary generations to run",
        group="05_genetic_algorithm", order=2, default_value=150,
        min_value=1, max_value=10000, decimal_places=0
    ),
    NumericParameter(
        name="crossover_rate", display_name="Crossover Rate",
        description="Probability of crossover operations (0.0-1.0)",
        group="05_genetic_algorithm", order=3, default_value=0.8,
        min_value=0.1, max_value=1.0, decimal_places=3
    ),
    NumericParameter(
        name="mutation_rate", display_name="Mutation Rate",
        description="Probability of mutation operations (0.0-1.0)",
        group="05_genetic_algorithm", order=4, default_value=0.05,
        min_value=0.001, max_value=0.5, decimal_places=3
    ),
    NumericParameter(
        name="elite_ratio", display_name="Elite Ratio",
        description="Proportion of best individuals preserved each generation",
        group="05_genetic_algorithm", order=5, default_value=0.05,
        min_value=0.01, max_value=0.20, decimal_places=3
    ),

    # Constraint parameters (no penalty weight)
    NumericParameter(
        name="target_avg_length", display_name="Target Avg Length",
        description="Target average segment length in miles",
        group="06_constraints", order=1, default_value=2.0,
        min_value=0.01, max_value=50.0, decimal_places=2
    ),
    NumericParameter(
        name="length_tolerance", display_name="Length Tolerance",
        description="Acceptable tolerance around target length (Deb feasibility band)",
        group="06_constraints", order=2, default_value=0.2,
        min_value=0.01, max_value=1.0, decimal_places=3
    ),

    # Performance settings
    NumericParameter(
        name="cache_clear_interval", display_name="Cache Clear Interval",
        description="Number of generations between cache clears",
        group="08_performance", order=1, default_value=50,
        min_value=1, max_value=1000, decimal_places=0
    ),
    BoolParameter(
        name="enable_performance_stats", display_name="Performance Statistics",
        description="Enable detailed performance tracking and reporting",
        group="08_performance", order=2, default_value=True
    )
]

AASHTO_CDA_PARAMETERS = [
    # Statistical Analysis Parameters
    NumericParameter(
        name="alpha", display_name="Significance Level",
        description="Statistical significance level for change point detection (lower = more conservative)",
        group="01_statistical_analysis", order=1, default_value=0.05,
        min_value=0.001, max_value=0.49, decimal_places=3
    ),
    SelectParameter(
        name="method", display_name="Error Estimation Method", 
        description="Method for estimating standard deviation of measurement error",
        group="01_statistical_analysis", order=2, default_value=2,
        options=[
            ("MAD with Normal Distribution", 1),
            ("Std Dev of Differences (Recommended)", 2), 
            ("Std Dev of Measurements", 3)
        ]
    ),
    BoolParameter(
        name="use_segment_length", display_name="Use Segment-Specific Length",
        description="Use individual segment lengths (recommended) vs. total data length in statistical calculations", 
        group="01_statistical_analysis", order=3, default_value=True  # GlobalLocal=1 in MATLAB (recommended)
    ),
    
    # Segmentation Constraints
    NumericParameter(
        name="min_segment_datapoints", display_name="Min Segment Datapoints",
        description="Minimum number of datapoints required per segment",
        group="04_segment_constraints", order=1, default_value=3,
        min_value=3, max_value=1000, decimal_places=0
    ),
    OptionalNumericParameter(
        name="max_segments", display_name="Max Segments", 
        description="Maximum number of segments allowed (None=no limit, algorithm may find fewer)",
        group="04_segment_constraints", order=2, default_value=None,
        min_value=2, max_value=10000, decimal_places=0
    ),
    NumericParameter(
        name="min_section_difference", display_name="Min Section Difference",
        description="Minimum difference in average values between adjacent segments (0=disabled)",
        group="04_segment_constraints", order=3, default_value=0.0,
        min_value=0.0, max_value=None, decimal_places=3
    ),
    
    # Processing Options
    BoolParameter(
        name="enable_diagnostic_output", display_name="Diagnostic Output",
        description="Enable detailed diagnostic information during processing",
        group="07_processing", order=1, default_value=False
    )
]


PELT_SEGMENTATION_PARAMETERS = [
    # Change point detection parameters
    SelectParameter(
        name="model",
        display_name="Cost Model",
        description="Cost function used by PELT (l2=mean shifts, l1=robust mean shifts, rbf=kernel).",
        group="02_change_point_detection",
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
        group="02_change_point_detection",
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
        group="02_change_point_detection",
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
        group="03_smoothing",
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
        group="03_smoothing",
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
        group="04_segment_constraints",
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
        group="04_segment_constraints",
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
        group="07_processing",
        order=1,
        default_value=False,
    ),
]


# ===== ALGORITHM AND UI CONSTANTS =====
# Moved to app_constants.py; re-exported here for backward compatibility.
from app_constants import (  # noqa: E402
    AlgorithmConstants,  # noqa: F401
    UIConfig,  # noqa: F401
    PlottingConfig,  # noqa: F401
    ConstraintConfig,  # noqa: F401
    CacheConfig,  # noqa: F401
    ConstrainedOptimizationConfig,  # noqa: F401
    ValidationConfig,  # noqa: F401
    optimization_config,  # noqa: F401
    ui_config,  # noqa: F401
    plotting_config,  # noqa: F401
    constraint_config,  # noqa: F401
    cache_config,  # noqa: F401
    constrained_optimization_config,  # noqa: F401
    validation_config,  # noqa: F401
)


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
    # To add a new method: define its parameter list above, add an OptimizationMethodConfig
    # entry here, and implement the corresponding AnalysisMethodBase subclass.
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


# ===== PREPROCESSING METHODS REGISTRY =====
# Parallel to OPTIMIZATION_METHODS - provides extensible preprocessing framework
# Adding a new preprocessing method: 1) Implement PreprocessingMethodBase, 2) Add entry below

@dataclass
class PreprocessingMethodConfig:
    """
    Configuration for a single preprocessing method - mirrors OptimizationMethodConfig pattern.
    
    Enables extensible preprocessing architecture where new methods can be added
    by implementing PreprocessingMethodBase and adding a registry entry.
    """
    method_key: str                          # Internal identifier (e.g., "tukey_fences", "moving_average")
    display_name: str                        # User-friendly name for GUI dropdown
    description: str                         # Detailed description for tooltips/help
    parameters: List[ParameterDefinition]    # Complete parameter list for this method
    method_class_path: str                   # Import path (e.g., "preprocessing.methods.tukey_fences.TukeyFencesPreprocessor")


@dataclass
class PreprocessingRunConfig:
    """
    Configuration for preprocessing pipeline execution.
    
    Defines which preprocessing methods to apply at each phase (pre-gap, primary, secondary)
    along with their parameters. All phases are optional.
    
    Design Note: User can select the same method multiple times with different parameters.
    Example: Tukey Fences at primary (k=1.5, aggressive) AND secondary (k=3.0, conservative)
    """
    # Pre-gap preprocessing (before gap detection)
    pre_gap_method: Optional[str] = None              # Method key or None
    pre_gap_parameters: Optional[Dict[str, Any]] = None  # Method parameters
    
    # Primary preprocessing (after gaps and first attribute breaks)
    primary_method: Optional[str] = None              # Method key or None
    primary_parameters: Optional[Dict[str, Any]] = None  # Method parameters
    
    # Secondary preprocessing (after all attribute breaks)
    secondary_method: Optional[str] = None            # Method key or None
    secondary_parameters: Optional[Dict[str, Any]] = None  # Method parameters
    
    # Master enable flag
    enabled: bool = False                             # True if any preprocessing configured
    
    def __post_init__(self):
        """Initialize empty parameter dicts if None."""
        if self.pre_gap_parameters is None:
            self.pre_gap_parameters = {}
        if self.primary_parameters is None:
            self.primary_parameters = {}
        if self.secondary_parameters is None:
            self.secondary_parameters = {}


# Preprocessing methods registry - currently empty, methods will be added as framework develops
# Future methods: Tukey Fences, Moving Average, Savitzky-Golay, etc.
PREPROCESSING_METHODS: List[PreprocessingMethodConfig] = [
    PreprocessingMethodConfig(
        method_key="tukey_fences",
        display_name="Tukey Fences Outlier Detection",
        description="IQR-based outlier detection with configurable thresholds and actions",
        parameters=[
            NumericParameter(
                name="k_factor",
                display_name="K Factor",
                description="IQR multiplier for fence bounds (1.5=mild outliers, 3.0=extreme outliers)",
                group="01_detection",
                order=1,
                default_value=1.5,
                min_value=0.5,
                max_value=5.0,
                decimal_places=1,
                widget_width=10
            ),
            SelectParameter(
                name="action",
                display_name="Outlier Action",
                description="How to handle detected outliers",
                group="02_handling",
                order=2,
                default_value="remove",
                options=[
                    ("Remove", "remove"),
                    ("Cap to Fence", "cap"),
                    ("Interpolate", "interpolate")
                ]
            ),
        ],
        method_class_path="preprocessing.methods.tukey_fences.TukeyFencesPreprocessor"
    ),
]


def get_preprocessing_method(method_key: str) -> PreprocessingMethodConfig:
    """
    Get preprocessing method configuration by key.
    
    Args:
        method_key: Method identifier (e.g., "tukey_fences")
        
    Returns:
        PreprocessingMethodConfig for the specified method
        
    Raises:
        ValueError: If method_key not found in registry
    """
    for method in PREPROCESSING_METHODS:
        if method.method_key == method_key:
            return method
    raise ValueError(f"Unknown preprocessing method key: {method_key}")


def resolve_preprocessing_class(method_key: str) -> Type:
    """
    Resolve preprocessing method class from method_class_path.
    
    Parallel to resolve_method_class() for analysis methods.
    Dynamically imports and returns the preprocessing method class.
    
    Args:
        method_key: Method identifier
        
    Returns:
        Type: The preprocessing method class (must inherit from PreprocessingMethodBase)
        
    Raises:
        ValueError: If method not found or class_path invalid
        ImportError: If module or class cannot be imported
    """
    method_config = get_preprocessing_method(method_key)
    class_path = method_config.method_class_path
    
    if not class_path:
        raise ValueError(
            f"Preprocessing method '{method_key}' is missing method_class_path in PREPROCESSING_METHODS"
        )
    
    if '.' not in class_path:
        raise ValueError(
            f"Invalid method_class_path for preprocessing method '{method_key}': '{class_path}' "
            "(expected module.ClassName)"
        )
    
    module_path, class_name = class_path.rsplit('.', 1)
    
    try:
        module = importlib.import_module(module_path)
    except Exception as e:
        raise ImportError(
            f"Could not import module '{module_path}' for preprocessing method '{method_key}' "
            f"(method_class_path='{class_path}'): {e}"
        ) from e
    
    try:
        cls = getattr(module, class_name)
    except AttributeError as e:
        raise ImportError(
            f"Module '{module_path}' does not define class '{class_name}' "
            f"for preprocessing method '{method_key}' (method_class_path='{class_path}')"
        ) from e
    
    return cls


def validate_preprocessing_method_registry() -> None:
    """
    Validate that all preprocessing methods have importable, compatible implementations.
    
    Parallel to validate_optimization_method_registry(). Runs at application startup
    to ensure configuration errors fail fast.
    
    Raises:
        ValueError: If any method fails validation (collected errors)
        ImportError: If PreprocessingMethodBase cannot be imported
    """
    errors: List[str] = []
    
    try:
        from preprocessing.base import PreprocessingMethodBase
    except Exception as e:
        raise ImportError(
            f"Could not import PreprocessingMethodBase for validation: {e}"
        ) from e
    
    for method in PREPROCESSING_METHODS:
        try:
            cls = resolve_preprocessing_class(method.method_key)
            
            if not isinstance(cls, type):
                raise TypeError(
                    f"Resolved object is not a class (got {type(cls).__name__})"
                )
            
            if not issubclass(cls, PreprocessingMethodBase):
                raise TypeError(
                    f"{cls.__module__}.{cls.__name__} does not inherit from PreprocessingMethodBase"
                )
                
        except Exception as e:
            errors.append(
                f"- method_key='{method.method_key}', display_name='{method.display_name}': {e}"
            )
    
    if errors:
        raise ValueError(
            "Preprocessing method registry validation failed. Fix PREPROCESSING_METHODS in src/config.py:\n"
            + "\n".join(errors)
        )


def get_preprocessing_method_names() -> List[str]:
    """
    Get list of preprocessing method display names for GUI dropdown.
    
    Returns:
        List of display names (e.g., ["Tukey Fences Outlier Detection", "Moving Average"])
    """
    return [method.display_name for method in PREPROCESSING_METHODS]


def get_preprocessing_method_key_from_display_name(display_name: str) -> str:
    """
    Get method key from display name.
    
    Args:
        display_name: Human-readable method name
        
    Returns:
        Method key (e.g., "tukey_fences")
        
    Raises:
        ValueError: If display_name not found
    """
    for method in PREPROCESSING_METHODS:
        if method.display_name == display_name:
            return method.method_key
    raise ValueError(f"Unknown preprocessing method display name: {display_name}")


def get_preprocessing_parameters(method_key: str) -> List[ParameterDefinition]:
    """
    Get parameter list for a preprocessing method.
    
    Args:
        method_key: Method identifier
        
    Returns:
        List of ParameterDefinition objects for the method
    """
    method = get_preprocessing_method(method_key)
    return method.parameters


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
