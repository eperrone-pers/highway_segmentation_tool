"""
Tukey Fences Outlier Detection Preprocessing Method

Implements outlier detection using the Interquartile Range (IQR) method,
also known as Tukey's Fences. Identifies outliers as values beyond 
[Q1 - k*IQR, Q3 + k*IQR] and handles them via remove, cap, or interpolate actions.

Reference: Tukey, J.W. (1977). Exploratory Data Analysis.
"""

from typing import TYPE_CHECKING
import numpy as np

from preprocessing.base import (
    PreprocessingMethodBase,
    PreprocessingResult,
    DataModificationContext,
)

if TYPE_CHECKING:
    from data_loader import RouteAnalysis


# Statistical constant: minimum points needed to calculate quartiles reliably
MIN_POINTS_FOR_IQR = 4


class TukeyFencesPreprocessor(PreprocessingMethodBase):
    """
    Outlier detection and handling using Tukey Fences (IQR method).
    
    Identifies outliers as values beyond [Q1 - k*IQR, Q3 + k*IQR]
    where k is typically 1.5 (outliers) or 3.0 (extreme outliers).
    
    The IQR (Interquartile Range) is Q3 - Q1, representing the spread
    of the middle 50% of data. Values beyond the fences are considered
    anomalous and can be removed, capped, or interpolated.
    
    Parameters:
        k_factor: Fence multiplier (1.5 = mild outliers, 3.0 = extreme)
        action: How to handle outliers ("remove", "cap", "interpolate")
    
    Parameters are defined declaratively in PREPROCESSING_METHODS registry
    and automatically generate UI widgets and validation.
    """
    
    @property
    def preprocess_key(self) -> str:
        """Unique identifier for this preprocessing method."""
        return "tukey_fences"
    
    @property
    def preprocess_name(self) -> str:
        """Human-readable name for GUI display."""
        return "Tukey Fences Outlier Detection"
    
    @property
    def description(self) -> str:
        """Detailed description for tooltips and help."""
        return (
            "Detects and handles outliers using the Interquartile Range (IQR) method. "
            "Values beyond Q1 - k*IQR or Q3 + k*IQR are considered outliers. "
            "Common k values: 1.5 (mild outliers), 3.0 (extreme outliers)."
        )
    
    def process(
        self,
        route_analysis: "RouteAnalysis",
        x_column: str,
        y_column: str,
        **parameters
    ) -> PreprocessingResult:
        """
        Apply Tukey Fences outlier detection to route data.
        
        Args:
            route_analysis: RouteAnalysis object with route data
            x_column: Name of X-axis column (e.g., "Milepoint")
            y_column: Name of Y-axis column (e.g., "IRI")
            **parameters: Method parameters (k_factor, action)
        
        Returns:
            PreprocessingResult with modified route analysis and complete modification log
        """
        # Extract parameters (with defaults)
        k_factor = parameters.get('k_factor', 1.5)
        action = parameters.get('action', 'remove')
        
        # Get data
        df = route_analysis.route_data
        y_values = df[y_column].values
        x_values = df[x_column].values
        original_y = y_values.copy()
        
        # Create modification context - REQUIRED for all data changes
        # This ensures automatic logging of all modifications
        # Pass mandatory breakpoints to prevent their accidental removal
        ctx = DataModificationContext(df, x_column, y_column, 
                                       route_analysis.mandatory_breakpoints)
        
        # Get mandatory breakpoints to process each segment independently
        # This is CRITICAL - different pavement types have different statistical properties
        mandatory_bps = sorted(list(route_analysis.mandatory_breakpoints or []))
        if not mandatory_bps:
            # No segments defined - fall back to global processing
            mandatory_bps = [float(x_values.min()), float(x_values.max())]
        
        total_outlier_count = 0
        
        # Process each analyzable segment independently
        for i in range(len(mandatory_bps) - 1):
            seg_start = mandatory_bps[i]
            seg_end = mandatory_bps[i + 1]
            
            # Get points in this segment
            seg_mask = (x_values >= seg_start) & (x_values <= seg_end)
            seg_y_values = y_values[seg_mask]
            seg_indices = np.where(seg_mask)[0]
            
            if len(seg_y_values) < MIN_POINTS_FOR_IQR:
                # Need at least MIN_POINTS_FOR_IQR points to calculate quartiles reliably
                continue
            
            # Calculate IQR bounds FOR THIS SEGMENT ONLY
            q1, q3 = np.percentile(seg_y_values, [25, 75])
            iqr = q3 - q1
            
            if iqr == 0:
                # All values identical in this segment - skip outlier detection
                continue
            
            lower_bound = q1 - k_factor * iqr
            upper_bound = q3 + k_factor * iqr
            
            # Identify outliers IN THIS SEGMENT
            outlier_mask = (seg_y_values < lower_bound) | (seg_y_values > upper_bound)
            segment_outlier_indices = seg_indices[outlier_mask]
            
            if len(segment_outlier_indices) == 0:
                continue
            
            # Apply action (each operation auto-logged by context)
            if action == 'remove':
                # Remove outlier points
                for idx in segment_outlier_indices:
                    reason = f"outlier beyond {k_factor}*IQR fence in segment [{seg_start:.1f}-{seg_end:.1f}]"
                    ctx.remove_point(x_values[idx], reason=reason)
                    total_outlier_count += 1
            
            elif action == 'cap':
                # Cap outliers to fence boundaries (segment-specific bounds)
                for idx in segment_outlier_indices:
                    new_y = lower_bound if y_values[idx] < lower_bound else upper_bound
                    bound_type = "lower" if y_values[idx] < lower_bound else "upper"
                    reason = f"segment [{seg_start:.1f}-{seg_end:.1f}] {bound_type} fence ({new_y:.1f})"
                    ctx.modify_y_value(
                        x_values[idx], 
                        new_y, 
                        reason=reason, 
                        modification_type="y_value_capped"
                    )
                    total_outlier_count += 1
            
            elif action == 'interpolate':
                # Replace outliers with interpolated values from neighbors
                for idx in segment_outlier_indices:
                    # Find neighboring indices WITHIN THIS SEGMENT
                    local_idx = np.where(seg_indices == idx)[0][0]
                    
                    # Skip interpolation at segment boundaries - can't get true neighbors
                    if local_idx == 0 or local_idx == len(seg_indices) - 1:
                        # Outlier at segment start/end - leave unchanged
                        # Can't interpolate without neighbors on both sides
                        continue
                    
                    # Normal case: interpolate between previous and next points
                    prev_idx = seg_indices[local_idx - 1]
                    next_idx = seg_indices[local_idx + 1]
                    
                    # Simple linear interpolation between neighbors
                    new_y = (y_values[prev_idx] + y_values[next_idx]) / 2
                    ctx.modify_y_value(
                        x_values[idx], 
                        new_y,
                        reason="interpolated from neighbors",
                        modification_type="point_interpolated"
                    )
                    total_outlier_count += 1
        
        # Get modified data and complete log from context
        df_processed = ctx.get_modified_data()
        modifications = ctx.get_modification_log()
        
        # Create new RouteAnalysis with processed data (preserves all metadata)
        from preprocessing.base import create_processed_route_analysis
        processed_analysis = create_processed_route_analysis(
            route_analysis, df_processed, x_column, y_column
        )
        
        # Build metadata for traceability
        metadata = {
            'method_key': self.preprocess_key,
            'method_name': self.preprocess_name,
            'k_factor': float(k_factor),
            'action': action,
            'outliers_detected': int(total_outlier_count),
            'points_before': len(route_analysis.route_data),
            'points_after': len(df_processed),
            'points_modified': total_outlier_count,
            'segments_processed': len(mandatory_bps) - 1,
        }
        
        # Human-readable summary
        summary = f"Tukey Fences (k={k_factor}): {action} {total_outlier_count} outlier{'s' if total_outlier_count != 1 else ''} across {len(mandatory_bps) - 1} segment{'s' if len(mandatory_bps) - 1 != 1 else ''}"
        
        # Return complete result
        return PreprocessingResult(
            processed_route_analysis=processed_analysis,
            modification_log=modifications,  # Automatically generated by context
            preprocessing_metadata=metadata,
            original_y_values=original_y.tolist(),
            modifications_summary=summary
        )
