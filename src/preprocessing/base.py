"""
Preprocessing Framework Base Classes

This module defines the core abstractions and data structures for the preprocessing
framework. All preprocessing methods must inherit from PreprocessingMethodBase and
use DataModificationContext for data modifications to ensure automatic logging.

Key Components:
- DataModification: Single modification record for audit trail
- DataModificationContext: Framework-controlled data modification API with auto-logging
- PreprocessingResult: Result container for preprocessing operations
- PreprocessingMethodBase: Abstract base class for all preprocessing methods
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime
import pandas as pd
from pandas.api.types import is_numeric_dtype

if TYPE_CHECKING:
    from data_loader import RouteAnalysis


@dataclass
class DataModification:
    """
    Single data modification record for audit trail.
    
    All data modifications must be logged using this structure to ensure
    full traceability and reproducibility of preprocessing operations.
    
    Attributes:
        modification_type: Type of modification performed
        x_value: X-axis location of modification
        original_y_value: Original Y value (None if point didn't exist)
        new_y_value: New Y value (None if point removed)
        reason: Optional explanation for the modification
        timestamp: ISO format timestamp (auto-generated if not provided)
    """
    modification_type: str              # "point_removed", "y_value_changed", "y_value_capped", "point_interpolated"
    x_value: float                      # X-axis location of modification
    original_y_value: Optional[float]   # Original Y value (None if point didn't exist)
    new_y_value: Optional[float]        # New Y value (None if point removed)
    reason: Optional[str] = None        # Optional explanation (e.g., "outlier beyond 1.5*IQR")
    timestamp: Optional[str] = None     # ISO format timestamp
    
    def __post_init__(self):
        """Auto-generate timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class DataModificationContext:
    """
    Framework-provided context for modifying route data with automatic logging.
    
    This is the ONLY sanctioned way to modify preprocessing data. All modifications
    are automatically logged with complete traceability.
    
    Usage Example:
        ```python
        ctx = DataModificationContext(route_analysis.route_data, x_column, y_column)
        
        # Remove outliers - automatically logged
        for x_val in outliers:
            ctx.remove_point(x_val, reason="outlier beyond 1.5*IQR")
        
        # Modify Y values - automatically logged
        for x_val, new_y in modifications:
            ctx.modify_y_value(x_val, new_y, reason="capped to upper fence")
        
        # Get modified data and complete log
        modified_df = ctx.get_modified_data()
        log = ctx.get_modification_log()
        ```
    
    Attributes:
        _df: Working copy of the dataframe being modified
        _x_column: Name of X-axis column
        _y_column: Name of Y-axis column
        _modifications: List of all modifications made
        _original_df: Preserved original dataframe for comparison
        _mandatory_breakpoints: Set of x-values that cannot be removed (gaps, route edges, attribute changes)
    """
    
    def __init__(self, df: pd.DataFrame, x_column: str, y_column: str, 
                 mandatory_breakpoints: Optional[List[float]] = None):
        """
        Initialize context with data to be modified.
        
        Args:
            df: DataFrame containing route data
            x_column: Name of X-axis column
            y_column: Name of Y-axis column
            mandatory_breakpoints: List of x-values that must not be removed (gaps, route boundaries, attribute changes)
        """
        self._df = df.copy()  # Work on a copy
        self._x_column = x_column
        self._y_column = y_column
        self._modifications: List[DataModification] = []
        self._original_df = df.copy()  # Preserve original for verification
        self._mandatory_breakpoints = set(mandatory_breakpoints or [])

        if y_column in self._df.columns and is_numeric_dtype(self._df[y_column]):
            self._df[y_column] = self._df[y_column].astype(float)
    
    def remove_point(self, x_value: float, reason: Optional[str] = None) -> None:
        """
        Remove a data point - automatically logs the modification.
        
        Args:
            x_value: X-coordinate of point to remove
            reason: Optional explanation (e.g., "outlier beyond 1.5*IQR upper fence")
        
        Raises:
            ValueError: If x_value not found in data or is a mandatory breakpoint
        """
        # Enforce framework constraint: mandatory breakpoints cannot be removed
        if x_value in self._mandatory_breakpoints:
            raise ValueError(
                f"Cannot remove point at x={x_value}: this is a mandatory breakpoint "
                f"(gap boundary, route edge, or attribute change). "
                f"Mandatory breakpoints must be preserved for segmentation."
            )
        
        # Find the point
        mask = self._df[self._x_column] == x_value
        if not mask.any():
            raise ValueError(f"Point at x={x_value} not found in data")
        
        # Get Y value before removal
        y_value = self._df.loc[mask, self._y_column].iloc[0]
        
        # Automatic logging
        self._modifications.append(DataModification(
            modification_type="point_removed",
            x_value=x_value,
            original_y_value=float(y_value),
            new_y_value=None,
            reason=reason
        ))
        
        # Remove from dataframe
        self._df = self._df[~mask].reset_index(drop=True)
    
    def modify_y_value(self, x_value: float, new_y_value: float, 
                       reason: Optional[str] = None, 
                       modification_type: str = "y_value_changed") -> None:
        """
        Modify Y value at specified X location - automatically logs the modification.
        
        Args:
            x_value: X-coordinate of point to modify
            new_y_value: New Y value
            reason: Optional explanation (e.g., "capped to IQR upper fence")
            modification_type: Type of modification ("y_value_changed", "y_value_capped", "point_interpolated")
        
        Raises:
            ValueError: If x_value not found in data
        """
        # Find the point
        mask = self._df[self._x_column] == x_value
        if not mask.any():
            raise ValueError(f"Point at x={x_value} not found in data")
        
        # Get original Y value
        old_y_value = self._df.loc[mask, self._y_column].iloc[0]
        
        # Automatic logging
        self._modifications.append(DataModification(
            modification_type=modification_type,
            x_value=x_value,
            original_y_value=float(old_y_value),
            new_y_value=float(new_y_value),
            reason=reason
        ))
        
        # Modify dataframe
        self._df.loc[mask, self._y_column] = new_y_value
    
    def get_modified_data(self) -> pd.DataFrame:
        """
        Return modified dataframe.
        
        Returns:
            pd.DataFrame: The modified dataframe with all changes applied
        """
        return self._df
    
    def get_modification_log(self) -> List[DataModification]:
        """
        Return complete log of all modifications.
        
        Returns:
            List[DataModification]: Complete list of all logged modifications
        """
        return self._modifications
    
    def get_original_data(self) -> pd.DataFrame:
        """
        Return original unmodified dataframe for comparison.
        
        Returns:
            pd.DataFrame: The original dataframe before any modifications
        """
        return self._original_df


@dataclass
class PreprocessingResult:
    """
    Result of a preprocessing operation.
    
    Contains the modified route analysis, complete modification log, metadata,
    and original values for comparison and visualization.
    
    Attributes:
        processed_route_analysis: Modified RouteAnalysis object
        modification_log: Complete log of all data modifications (auto-generated by DataModificationContext)
        preprocessing_metadata: Statistics, aggregated changes, method parameters, etc.
        original_y_values: Original Y values before preprocessing for comparison
        modifications_summary: Human-readable one-line summary of changes
    """
    processed_route_analysis: "RouteAnalysis"  # Modified route analysis
    modification_log: List[DataModification]    # **AUTOMATIC:** Generated by DataModificationContext
    preprocessing_metadata: Dict[str, Any]      # Stats, aggregated changes, etc.
    original_y_values: List[float]              # For comparison/visualization
    modifications_summary: str                  # Human-readable description


class PreprocessingMethodBase(ABC):
    """
    Abstract base class for all preprocessing methods.
    
    Mirrors AnalysisMethodBase to ensure consistent architecture across the system.
    Each method is a black box: it receives a RouteAnalysis and returns a modified
    RouteAnalysis. Internal algorithm complexity is up to the implementation.
    
    Implementation Requirements:
    - Implement all abstract properties and methods
    - Return PreprocessingResult from process()
    - **MUST use DataModificationContext for ALL data modifications**
    - Preserve mandatory breakpoints (gaps, attribute changes)
    - Provide comprehensive metadata for traceability
    
    Automatic Modification Logging:
    - Create DataModificationContext at start of process()
    - Use ONLY context methods to modify data:
      - `ctx.remove_point()` - removes point and auto-logs
      - `ctx.modify_y_value()` - changes Y value and auto-logs
      - `ctx.cap_y_value()` - caps outlier and auto-logs
      - `ctx.interpolate_y_value()` - interpolates and auto-logs
    - Get complete log at end: `modification_log=ctx.get_modification_log()`
    - Get modified DataFrame: `df_modified = ctx.get_modified_data()`
    
    Why Mandatory:
    - Ensures developers cannot forget to log modifications
    - Maintains consistent audit trail across all preprocessing methods
    - Automatic export to results JSON with full traceability
    - No manual tracking needed - framework handles it
    
    Example Implementation:
        ```python
        class MyPreprocessor(PreprocessingMethodBase):
            @property
            def preprocess_key(self) -> str:
                return "my_method"
            
            @property
            def preprocess_name(self) -> str:
                return "My Preprocessing Method"
            
            @property
            def description(self) -> str:
                return "Detailed description of what this method does."
            
            def process(self, route_analysis, x_column, y_column, log_callback=None, **parameters):
                # Create modification context
                ctx = DataModificationContext(route_analysis.route_data, x_column, y_column)
                
                # Your algorithm logic here
                outliers = detect_outliers(...)
                
                # Modify data using context (auto-logged)
                for x_val in outliers:
                    ctx.remove_point(x_val, reason="outlier detected")
                
                # Get modified data and log
                modified_df = ctx.get_modified_data()
                modifications = ctx.get_modification_log()
                
                # Build result
                return PreprocessingResult(
                    processed_route_analysis=...,
                    modification_log=modifications,
                    preprocessing_metadata={...},
                    original_y_values=...,
                    modifications_summary="Removed 5 outliers"
                )
        ```
    """
    
    @property
    @abstractmethod
    def preprocess_key(self) -> str:
        """
        Unique identifier for this preprocessing method.
        
        Used in configuration files and method resolution.
        Should be lowercase with underscores.
        
        Examples: "tukey_fences", "moving_average", "savitzky_golay"
        
        Returns:
            str: Method key (lowercase with underscores)
        """
        pass
    
    @property
    @abstractmethod
    def preprocess_name(self) -> str:
        """
        Human-readable method name for GUI display and logging.
        
        Examples: "Tukey Fences Outlier Detection", "Moving Average Smoothing"
        
        Returns:
            str: Display name for the method
        """
        pass
    
    @property
    def description(self) -> str:
        """
        Detailed description for tooltips and documentation.
        
        Returns:
            str: Method description (can be empty string)
        """
        return ""
    
    @abstractmethod
    def process(
        self,
        route_analysis: "RouteAnalysis",
        x_column: str,
        y_column: str,
        log_callback=None,
        **parameters
    ) -> PreprocessingResult:
        """
        Apply preprocessing to route data.

        This is the main method that performs the preprocessing operation.
        Must use DataModificationContext for all data modifications to ensure
        automatic logging.

        Args:
            route_analysis: RouteAnalysis object containing route data and metadata
            x_column: Name of X-axis column in route_data DataFrame
            y_column: Name of Y-axis column in route_data DataFrame
            log_callback: Optional callable for progress messages routed to the GUI
                right panel (or stdout in CLI/test contexts). Use like:
                ``log = log_callback or print; log("Processing segment 3/17...")``.
                Pass None when no progress output is needed.
            **parameters: Method-specific parameters (validated before this call)

        Returns:
            PreprocessingResult: Complete result with modified data and modification log

        Raises:
            ValueError: If parameters are invalid or processing fails
            RuntimeError: If mandatory breakpoints would be violated
        """
        pass


def create_processed_route_analysis(
    original: "RouteAnalysis",
    modified_df: pd.DataFrame,
    x_column: str,
    y_column: str
) -> "RouteAnalysis":
    """
    Helper to create processed RouteAnalysis preserving all metadata from original.
    
    This eliminates code duplication across preprocessing methods. Every preprocessing
    method needs to reconstruct a RouteAnalysis object after modifying the data,
    preserving all metadata from the original. This helper centralizes that logic.
    
    Automatically handles:
    - Copying all original metadata (gaps, breakpoints, attributes)
    - Recalculating data_range from modified DataFrame
    - Updating valid_x_values and route_stats
    - Handling optional fields (secondary attributes) safely with getattr()
    
    Args:
        original: Original RouteAnalysis object before preprocessing
        modified_df: Modified DataFrame after preprocessing operations
        x_column: Name of X-axis column in DataFrame
        y_column: Name of Y-axis column in DataFrame
    
    Returns:
        RouteAnalysis: New analysis object with modified data and preserved metadata
    
    Example:
        ```python
        ctx = DataModificationContext(route_analysis.route_data, x_column, y_column)
        # ... modify data ...
        modified_df = ctx.get_modified_data()
        
        # One-line reconstruction instead of 18 lines of boilerplate
        processed_analysis = create_processed_route_analysis(
            route_analysis, modified_df, x_column, y_column
        )
        ```
    """
    # Import here to avoid circular dependency
    from data_loader import RouteAnalysis

    route_start = float(modified_df[x_column].min())
    route_end = float(modified_df[x_column].max())
    gap_total_length = float(sum(end - start for start, end in (original.gap_segments or [])))
    
    return RouteAnalysis(
        route_id=original.route_id,
        route_data=modified_df,
        gap_segments=original.gap_segments,
        mandatory_breakpoints=original.mandatory_breakpoints,
        valid_x_values=modified_df[x_column].tolist(),
        data_range={
            'x_min': float(modified_df[x_column].min()),
            'x_max': float(modified_df[x_column].max()),
            'y_min': float(modified_df[y_column].min()),
            'y_max': float(modified_df[y_column].max()),
        },
        route_stats={
            **original.route_stats,
            'raw_points': len(modified_df),
            'total_points': len(modified_df),
            'valid_points': len(modified_df),
            'route_start': route_start,
            'route_end': route_end,
            'total_length': route_end - route_start,
            'gap_total_length': gap_total_length,
            'valid_length': (route_end - route_start) - gap_total_length,
        },
        must_break_columns_used=original.must_break_columns_used,
        attribute_breakpoints=original.attribute_breakpoints,
        attribute_break_events=original.attribute_break_events,
        secondary_break_columns_used=getattr(original, 'secondary_break_columns_used', None),
        secondary_attribute_breakpoints=getattr(original, 'secondary_attribute_breakpoints', None),
        secondary_attribute_break_events=getattr(original, 'secondary_attribute_break_events', None),
    )
