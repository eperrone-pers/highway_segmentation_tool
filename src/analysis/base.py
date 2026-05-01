"""
Analysis Base Classes and Interfaces

Defines the core interfaces and data structures for the extensible analysis framework.
All analysis methods must implement AnalysisMethodBase to ensure consistent behavior
and enable standardized result handling across the system.

Key Components:
- AnalysisResult: Standardized result structure for all analysis methods
- AnalysisMethodBase: Abstract base class defining the analysis method interface
- Parameter validation and method discovery contracts

This module establishes the contracts that enable:
- Consistent method calling patterns across all optimization types
- Standardized result structures for visualization and export
- Extensible plugin architecture for adding new analysis methods
- Type safety and validation for method parameters

Usage:
    class MyAnalysisMethod(AnalysisMethodBase):
        @property
        def method_name(self) -> str:
            return "My Custom Method"
            
        def run_analysis(self, data, x_column, y_column, **kwargs) -> AnalysisResult:
            # Implementation here
            return AnalysisResult(...)

Author: Highway Segmentation GA Team  
Phase: 1.95.1 - Common Analysis Interface Design
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Union, Tuple, TYPE_CHECKING, cast
import pandas as pd
import time
from datetime import datetime

# Import configuration functions for dynamic method checking
from config import is_multi_objective_method

if TYPE_CHECKING:
    # RouteAnalysis is the unified runtime input passed by the controller.
    from data_loader import RouteAnalysis


@dataclass
class AnalysisResult:
    """
    Standardized result structure for all highway segmentation analysis methods.
    
    This structure provides a unified interface for handling optimization results
    from any analysis method, enabling consistent visualization, export, and 
    further processing regardless of the underlying optimization approach.
    
    The design supports:
    - Single-objective methods (1 solution in all_solutions)
    - Multi-objective methods (multiple Pareto solutions in all_solutions)
    - Constrained methods (constraint achievement tracking)
    - Route identification for multi-route processing
    - Complete traceability with input parameters and processing metadata
    """
    
    # Core identification
    method_name: str                    # Human-readable method name ("Single-Objective GA")
    method_key: str                     # Method key (e.g., "single", "multi", "constrained", "aashto_cda")
    route_id: str                       # Route identifier for multi-route processing
    
    # All solutions found (single interface for single/multi-objective)
    all_solutions: List[Dict[str, Any]] # All solutions: [solution] for single, [pareto_front...] for multi
    
    @property
    def best_solution(self) -> Dict[str, Any]:
        """Backward compatibility property - returns first solution from all_solutions."""
        return self.all_solutions[0] if self.all_solutions else {}
    
    # Optimization metadata
    optimization_stats: Dict[str, Any] = field(default_factory=dict) # Performance metrics, convergence info
    mandatory_breakpoints: List[float] = field(default_factory=list) # Gap-created breakpoints
    processing_time: float = 0.0       # Total analysis time in seconds
    
    # Input context for reproducibility
    input_parameters: Dict[str, Any] = field(default_factory=dict) # All parameters used in analysis
    data_summary: Dict[str, Any] = field(default_factory=dict)     # Data characteristics (points, range, gaps)
    
    # Processing metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    analysis_version: str = "1.95.1"   # Version for compatibility tracking
    
    def get_solution_count(self) -> int:
        """Get number of solutions found (1 for single-obj, N for multi-obj)"""
        return len(self.all_solutions)
    
    def is_multi_objective(self) -> bool:
        """Check if this result represents a multi-objective optimization"""
        try:
            # Configuration-driven check: look up method by key and check return_type
            return is_multi_objective_method(self.method_key) and len(self.all_solutions) > 1
        except (ValueError, AttributeError):
            # Fallback for legacy or invalid method_key values
            return len(self.all_solutions) > 1
    
    def get_best_chromosome(self) -> List[float]:
        """Get the chromosome (breakpoints) of the primary solution"""
        return self.best_solution.get('chromosome', [])
    
    def get_best_fitness(self) -> Union[float, List[float]]:
        """Get fitness of primary solution (float for single-obj, list for multi-obj)"""
        return self.best_solution.get('fitness', 0.0)


class AnalysisMethodBase(ABC):
    """
    Abstract base class for all highway segmentation analysis methods.
    
    All analysis methods must implement this interface to ensure consistent
    behavior and enable the extensible plugin architecture. The interface
    provides standardized method calling, parameter validation, and result
    structures across all optimization approaches.
    
    Key Design Principles:
    - Consistent calling interface across all methods
    - Standardized result structures for uniform handling
    - Optional parameter validation with method-specific overrides
    - Support for progress callbacks and stop conditions
    - Complete input/output traceability for reproducibility
    
    Implementation Requirements:
    - Implement all abstract methods and properties
    - Return AnalysisResult from run_analysis()
    - Handle route_id parameter for multi-route processing
    - Preserve all mandatory breakpoints from input data
    - Provide comprehensive optimization statistics
    
    Example Implementation:
        class MyMethod(AnalysisMethodBase):
            @property
            def method_name(self) -> str:
                return "My Optimization Method"
            
            @property  
            def method_key(self) -> str:
                return "single"  # or "multi", "constrained", "aashto_cda"
                
            def run_analysis(self, data, x_column, y_column, **kwargs) -> AnalysisResult:
                # Your optimization implementation here
                return AnalysisResult(...)
    """
    
    @property
    @abstractmethod
    def method_name(self) -> str:
        """
        Human-readable method name for GUI display and result identification.
        
        Should be descriptive and unique across all methods.
        Examples: "Single-Objective GA", "Multi-Objective NSGA-II", "Constrained Single-Objective"
        
        Returns:
            str: Display name for the method
        """
        pass
    
    @property
    @abstractmethod
    def method_key(self) -> str:
        """
        Method key for result handling and export.
        
        Valid values:
        - "single": Single-objective GA
        - "multi": Multi-objective NSGA-II
        - "constrained": Constrained single-objective GA
        - "aashto_cda": Deterministic statistical CDA analysis
        
        Returns:
            str: Method key
        """
        pass
    
    @property  
    def supports_multi_route(self) -> bool:
        """
        Whether this method supports multi-route processing.
        Default implementation returns True. Override if method has limitations.
        
        Returns:
            bool: True if method can process multiple routes
        """
        return True
    
    @property
    def parameter_schema(self) -> Dict[str, Any]:
        """
        Schema defining expected parameters for this method.
        Override to provide method-specific parameter validation.
        
        Returns:
            dict: Parameter schema with types, defaults, and validation rules
        """
        return {
            'min_length': {'type': float, 'min': 0.1, 'required': True},
            'max_length': {'type': float, 'min': 1.0, 'required': True}, 
            'population_size': {'type': int, 'min': 10, 'default': 100},
            'num_generations': {'type': int, 'min': 1, 'default': 200},
            'gap_threshold': {'type': float, 'min': 0.0, 'default': 0.5}
        }
    
    @abstractmethod
    def run_analysis(
        self,
        data: "RouteAnalysis",
        route_id: str,
        x_column: str,
        y_column: str,
        gap_threshold: float,
        **kwargs,
    ) -> AnalysisResult:
        """
        Execute the core optimization analysis.
        
        This is the main method that performs the optimization and returns
        standardized results. All analysis methods must implement this with
        consistent parameter handling and result formatting.
        
        Unified Calling Convention (used by the controller in this repo):
            data: RouteAnalysis object (contains .route_data DataFrame and gap metadata)
            route_id: Route identifier for this analysis
            x_column: Name of milepoint/distance column
            y_column: Name of value/measurement column
            gap_threshold: Framework-level gap detection threshold (required, > 0)
            
        Common Method Parameters (via **kwargs):
            min_length: Minimum allowed segment length (typically required)
            max_length: Maximum allowed segment length (typically required)
            population_size: GA population size (default method-specific)
            num_generations: Number of GA generations (default method-specific)
            log_callback: Function for progress logging
            stop_callback: Function to check for user stop request
            mutation_rate: GA mutation probability
            crossover_rate: GA crossover probability
            
        Method-Specific Parameters:
            Single-objective: elite_ratio, cache_clear_interval
            Multi-objective: (uses NSGA-II defaults)  
            Constrained: target_avg_length, tolerance, penalty_weight
            
        Returns:
            AnalysisResult: Standardized result structure with:
                - method_name, method_key, route_id
                - best_solution (primary result)
                - all_solutions (single item for single-obj, multiple for multi-obj)
                - optimization_stats (performance metrics)
                - mandatory_breakpoints (gap-created breakpoints)
                - processing_time, input_parameters, data_summary
                - timestamp and version for traceability
                
        Raises:
            ValueError: Invalid parameters or data format
            RuntimeError: Optimization execution errors
        """
        pass
    
    def validate_parameters(self, **kwargs) -> Tuple[bool, str]:
        """
        Validate method-specific parameters before optimization.
        
        Override this method to provide custom parameter validation.
        Base implementation validates common GA parameters.
        
        Args:
            **kwargs: Parameters to validate using parameter_schema
            
        Returns:
            tuple: (is_valid, error_message)
                - is_valid: True if all parameters are valid
                - error_message: Description of validation error, or "Valid" if successful
        """
        schema = self.parameter_schema
        
        # Check required parameters
        for param, config in schema.items():
            if config.get('required', False) and param not in kwargs:
                return False, f"Required parameter '{param}' is missing"
        
        # Validate parameter types and ranges  
        for param, value in kwargs.items():
            if param in schema:
                config = schema[param]
                expected_type = config.get('type')
                
                # Type validation
                if expected_type and not isinstance(value, expected_type):
                    return False, f"Parameter '{param}' must be of type {expected_type.__name__}"
                
                # Range validation for numeric types
                if isinstance(value, (int, float)):
                    min_val = config.get('min')
                    max_val = config.get('max') 
                    
                    if min_val is not None and value < min_val:
                        return False, f"Parameter '{param}' must be >= {min_val}"
                    if max_val is not None and value > max_val:
                        return False, f"Parameter '{param}' must be <= {max_val}"
        
        return True, "Valid"
    
    def validate_data(self, data: pd.DataFrame, x_column: str, y_column: str) -> Tuple[bool, str]:
        """
        Validate input data format and completeness.
        
        Args:
            data: Input highway data
            x_column: Milepoint column name
            y_column: Value column name
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # Check data is not empty
        if data.empty:
            return False, "Input data is empty"
        
        # Check required columns exist
        if x_column not in data.columns:
            return False, f"Milepoint column '{x_column}' not found in data"
        if y_column not in data.columns:
            return False, f"Value column '{y_column}' not found in data"
        
        # Check for sufficient data points
        if len(data) < 3:
            return False, "Insufficient data points (minimum 3 required for segmentation)"
        
        # Check for numeric data types
        if not pd.api.types.is_numeric_dtype(data[x_column]):
            return False, f"Milepoint column '{x_column}' must contain numeric data"
        if not pd.api.types.is_numeric_dtype(data[y_column]):
            return False, f"Value column '{y_column}' must contain numeric data"
        
        # Check for null values
        if data[x_column].isna().any():
            return False, f"Milepoint column '{x_column}' contains null values"
        if data[y_column].isna().any():
            return False, f"Value column '{y_column}' contains null values"
        
        return True, "Valid"
    
    def prepare_data_summary(self, data: pd.DataFrame, x_column: str, y_column: str, **kwargs) -> Dict[str, Any]:
        """
        Generate summary statistics for the input data.
        
        Args:
            data: Input highway data
            x_column: Milepoint column name
            y_column: Value column name
            **kwargs: Additional parameters
            
        Returns:
            dict: Data summary statistics
        """
        # Use numeric Series reductions to avoid pandas ExtensionArray typing issues
        # (and to handle pd.NA safely when present).
        x_raw = cast(pd.Series, data[x_column])
        y_raw = cast(pd.Series, data[y_column])

        x_series = cast(pd.Series, pd.to_numeric(x_raw, errors="coerce"))
        y_series = cast(pd.Series, pd.to_numeric(y_raw, errors="coerce"))

        def _safe_float(value: Any) -> float:
            try:
                return float(value) if pd.notna(value) else float("nan")
            except Exception:
                return float("nan")

        x_min = x_series.min(skipna=True)
        x_max = x_series.max(skipna=True)
        y_mean = y_series.mean(skipna=True)
        y_std = y_series.std(skipna=True)
        y_min = y_series.min(skipna=True)
        y_max = y_series.max(skipna=True)
        
        return {
            'data_points': len(data),
            'milepoint_range': {
                'start': _safe_float(x_min),
                'end': _safe_float(x_max),
                'span': _safe_float(x_max - x_min) if pd.notna(x_min) and pd.notna(x_max) else float("nan"),
            },
            'value_statistics': {
                'mean': _safe_float(y_mean),
                'std': _safe_float(y_std),
                'min': _safe_float(y_min),
                'max': _safe_float(y_max),
            },
            'route_id': kwargs.get('route_id', 'single_route'),
            'columns_used': {
                'x_column': x_column,
                'y_column': y_column
            }
        }