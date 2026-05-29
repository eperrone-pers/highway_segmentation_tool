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
        log_callback=None,
        **parameters
    ) -> PreprocessingResult:
        """
        Apply Tukey Fences outlier detection to route data.

        Args:
            route_analysis: RouteAnalysis object with route data
            x_column: Name of X-axis column (e.g., "Milepoint")
            y_column: Name of Y-axis column (e.g., "IRI")
            log_callback: Optional callable for progress messages. Use like:
                ``log = log_callback or print; log("Processing...")``.
            **parameters: Method parameters (k_factor, action)

        Returns:
            PreprocessingResult with modified route analysis and complete modification log
        """
        log = log_callback or print

        # Extract parameters (with defaults)
        k_factor = parameters.get('k_factor', 1.5)
        action = parameters.get('action', 'remove')
        
        # Get data
        df = route_analysis.route_data
        original_y = df[y_column].values.copy()
        
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
            mandatory_bps = [float(df[x_column].min()), float(df[x_column].max())]

        log(
            f"Tukey Fences start for route {route_analysis.route_id}: "
            f"k_factor={k_factor}, action={action}, points={len(df)}, "
            f"segments={len(mandatory_bps) - 1}"
        )
        
        total_outlier_count = 0
        
        # Process each analyzable segment independently
        for i in range(len(mandatory_bps) - 1):
            seg_start = mandatory_bps[i]
            seg_end = mandatory_bps[i + 1]

            current_df = ctx.get_modified_data().sort_values(x_column).reset_index(drop=True)
            current_x_values = current_df[x_column].to_numpy()
            current_y_values = current_df[y_column].to_numpy()
            is_last_segment = i == len(mandatory_bps) - 2
            
            # Use half-open intervals so shared breakpoint rows belong to exactly one segment.
            if is_last_segment:
                seg_mask = (current_x_values >= seg_start) & (current_x_values <= seg_end)
            else:
                seg_mask = (current_x_values >= seg_start) & (current_x_values < seg_end)

            seg_x_values = current_x_values[seg_mask]
            seg_y_values = current_y_values[seg_mask]
            
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
            segment_outlier_x_values = seg_x_values[outlier_mask]
            segment_outlier_y_values = seg_y_values[outlier_mask]
            
            if len(segment_outlier_x_values) == 0:
                continue
            
            # Apply action (each operation auto-logged by context)
            if action == 'remove':
                # Remove outlier points
                for x_val in segment_outlier_x_values:
                    if float(x_val) in (route_analysis.mandatory_breakpoints or set()):
                        continue
                    reason = f"outlier beyond {k_factor}*IQR fence in segment [{seg_start:.1f}-{seg_end:.1f}]"
                    ctx.remove_point(float(x_val), reason=reason)
                    total_outlier_count += 1
            
            elif action == 'cap':
                # Cap outliers to fence boundaries (segment-specific bounds)
                for x_val, y_val in zip(segment_outlier_x_values, segment_outlier_y_values):
                    new_y = lower_bound if y_val < lower_bound else upper_bound
                    bound_type = "lower" if y_val < lower_bound else "upper"
                    reason = f"segment [{seg_start:.1f}-{seg_end:.1f}] {bound_type} fence ({new_y:.1f})"
                    ctx.modify_y_value(
                        float(x_val), 
                        float(new_y), 
                        reason=reason, 
                        modification_type="y_value_capped"
                    )
                    total_outlier_count += 1
            
            elif action == 'interpolate':
                # Replace outliers with interpolated values from neighbors
                outlier_positions = np.where(outlier_mask)[0]
                for local_idx in outlier_positions:
                    
                    # Skip interpolation at segment boundaries - can't get true neighbors
                    if local_idx == 0 or local_idx == len(seg_x_values) - 1:
                        # Outlier at segment start/end - leave unchanged
                        # Can't interpolate without neighbors on both sides
                        continue
                    
                    # Normal case: interpolate between previous and next points
                    x_val = seg_x_values[local_idx]
                    prev_y = seg_y_values[local_idx - 1]
                    next_y = seg_y_values[local_idx + 1]
                    
                    # Simple linear interpolation between neighbors
                    new_y = (prev_y + next_y) / 2
                    ctx.modify_y_value(
                        float(x_val), 
                        float(new_y),
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

        log(
            f"Tukey Fences complete for route {route_analysis.route_id}: "
            f"modified={len(modifications)}, outliers_handled={total_outlier_count}, "
            f"points_before={len(route_analysis.route_data)}, points_after={len(df_processed)}"
        )
        
        # Return complete result
        return PreprocessingResult(
            processed_route_analysis=processed_analysis,
            modification_log=modifications,  # Automatically generated by context
            preprocessing_metadata=metadata,
            original_y_values=original_y.tolist(),
            modifications_summary=summary
        )
