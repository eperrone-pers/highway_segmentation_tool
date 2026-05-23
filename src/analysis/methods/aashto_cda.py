"""
AASHTO Enhanced Cumulative Difference Approach (CDA) for Pavement Data Segmentation

This module implements the Enhanced AASHTO Cumulative Difference Approach (CDA) 
for statistical change point detection in pavement data, providing deterministic 
segmentation without evolutionary computation.

Translation of MATLAB implementation to Python with numpy/scipy.

BSD 2-Clause License

Copyright (c) 2025, Samer Katicha

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
THE POSSIBILITY OF SUCH DAMAGE.

To cite the work:
Katicha, S., Flintsch, G. (2025), "Enhanced AASHTO Cumulative Difference
Approach (CDA) for Pavement Data Segmentation" Transportation Research
Record, Accepted.

Python translation notes:
- Converted from MATLAB 1-based to Python 0-based indexing
- Replaced MATLAB functions with numpy/scipy equivalents
- Maintained identical algorithm logic and statistical computations
"""

import numpy as np
from typing import Tuple, Optional
import math

from ..base import AnalysisMethodBase, AnalysisResult
from ..utils.segment_metrics import average_length_excluding_gap_segments
from config import get_optimization_method

try:
    from data_loader import build_attribute_break_analysis
except Exception:  # pragma: no cover
    build_attribute_break_analysis = None


def aashto_cda(y: np.ndarray,
               alpha: float = 0.05,
               num_sections: Optional[int] = None,
               min_segment_datapoints: int = 3,
               min_section_difference: float = 0.0,
               method: int = 2,
               global_local: bool = True,
               enable_diagnostic_output: bool = False,
               log=None) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Performs segmentation of data into uniform sections using Enhanced AASHTO CDA.
    
    Args:
        y: One-dimensional vector of data to be segmented
        alpha: Significance level (default=0.05, works for alpha < 0.5)
        num_sections: Maximum number of segments (default=length of y)
        min_segment_datapoints: Minimum number of datapoints per segment (default=3)
        min_section_difference: Minimum difference in average of adjacent segments (default=0)
        method: Method for estimating standard deviation of random error:
                1: MAD with normal distribution assumption
                2: Standard deviation of differences (recommended, default)
                other: Standard deviation of measurements
        global_local: If True, use segment-specific lengths (recommended, default)
                     If False, use total data length (not recommended)
        enable_diagnostic_output: If True, print verbose algorithm diagnostics to console
    
    Returns:
        uniform_sections: Segmented data values
        nodes: Identified breakpoints (0-based indices)
        section_start: Vector containing start indices of segments
        section_end: Vector containing end indices of segments
        mu: Mean value of each segment
    """
    _log = log or print
    y = np.asarray(y).flatten()
    n = len(y)

    if num_sections is None:
        num_sections = n

    x = np.arange(n)
    cy = np.cumsum(y)

    nodes = np.zeros(n, dtype=int)
    nodes[0] = 0      # first index (0-based)
    nodes[1] = n - 1  # last index (0-based)

    if method == 1:
        # MAD with normal distribution assumption
        diff_y = np.diff(y)
        sigma: float = float(
            1.4826 * np.median(np.abs(diff_y - np.median(diff_y))) / math.sqrt(2)
        )
    elif method == 2:
        # Standard deviation of differences (MATLAB-compatible default)
        diff_y = np.diff(y)
        if len(diff_y) >= 2:
            std_diff = float(np.std(diff_y, ddof=1))  # Use sample std (ddof=1) like MATLAB
        else:
            # Too few points for sample std; fall back to population std (or 0.0 for empty/singleton)
            std_diff = float(np.std(diff_y, ddof=0))

        sigma = float(std_diff / math.sqrt(2))
    else:
        # Standard deviation of measurements
        if len(y) >= 2:
            sigma = float(np.std(y, ddof=1))  # Use sample std like MATLAB
        else:
            sigma = float(np.std(y, ddof=0))
    
    i = 2  # Start with 2 nodes already defined (first and last)
    
    while i <= num_sections:
        try:
            location, change_point = find_change_point(
                cy, nodes[:i], x, float(sigma), alpha, min_segment_datapoints, global_local,
                enable_diagnostic_output, _log
            )
        except Exception:
            break
        
        if change_point == 0:
            break
            
        nodes[i] = location
        i += 1

        snodes = np.sort(nodes[:i])
        
        if np.all(np.diff(snodes) < (2 * min_segment_datapoints - 1)):
            break
    
    ii = i
    nodes = np.sort(nodes[:ii])

    # Interpolate uniform section values (matches MATLAB: uniform_sections = [u(1); u])
    cy_nodes = cy[nodes]
    uniform_sections = np.diff(np.interp(x, nodes, cy_nodes))
    uniform_sections = np.concatenate([[uniform_sections[0]], uniform_sections])

    # Section boundaries (MATLAB: Section_End=nodes(2:end), Section_Start=[1; Section_End(1:end-1)+1])
    section_end = nodes[1:].copy()
    section_start = np.concatenate([[0], section_end[:-1] + 1])

    mu = np.zeros(len(section_start))
    for i, _ in enumerate(section_start):
        mu[i] = np.mean(y[section_start[i]:section_end[i]+1])
    
    # Apply minimum section difference constraint if specified
    if enable_diagnostic_output:
        _log("\n--- Initial Segmentation ---")
        _log(f"Found {len(mu)} initial segments")
        _log(f"Segment means: {[round(m, 3) for m in mu]}")

    if min_section_difference > 0:
        if enable_diagnostic_output:
            _log(f"\n--- Merging Process (threshold={min_section_difference}) ---")
        iteration = 0
        while len(mu) > 1:
            mu_diff = np.abs(np.diff(mu))
            min_change = np.min(mu_diff)

            if enable_diagnostic_output:
                _log(f"Merge iteration {iteration}: min_diff={min_change:.3f} vs threshold={min_section_difference}")

            if min_change >= min_section_difference:
                if enable_diagnostic_output:
                    _log("STOP: All differences >= threshold")
                break

            min_id = np.argmin(mu_diff)
            if enable_diagnostic_output:
                _log(f"Merging segments {min_id} and {min_id+1}: {mu[min_id]:.3f} + {mu[min_id+1]:.3f}")

            # Merge adjacent segments (matches MATLAB logic exactly)
            section_start = np.delete(section_start, min_id + 1)
            section_end = np.delete(section_end, min_id)
            mu = np.delete(mu, min_id)
            mu[min_id] = np.mean(y[section_start[min_id]:section_end[min_id]+1])

            if enable_diagnostic_output:
                _log(f"  New mean: {mu[min_id]:.3f}, remaining segments: {len(mu)}")

            iteration += 1
            if iteration > 50:  # Safety cap against degenerate data
                if enable_diagnostic_output:
                    _log("ERROR: Too many merge iterations!")
                break

        # Recompute nodes and uniform sections after merging (matches MATLAB)
        nodes = np.concatenate([[0], section_end])
        cy_nodes = cy[nodes]
        uniform_sections = np.diff(np.interp(x, nodes, cy_nodes))
        uniform_sections = np.concatenate([[uniform_sections[0]], uniform_sections])

    if enable_diagnostic_output:
        _log("\n=== FINAL RESULTS ===")
        _log(f"Final segments: {len(mu)}")
        _log(f"Final means: {[round(m, 3) for m in mu]}")
        _log("Expected from MATLAB: 9 segments")
        _log(f"Match: {'YES' if len(mu) == 9 else 'NO'}")
        _log(f"RETURNING nodes: {nodes}")
        _log(f"Node count: {len(nodes)}")
    
    return uniform_sections, nodes, section_start, section_end, mu


def find_change_point(cy: np.ndarray,
                     nodes: np.ndarray,
                     x: np.ndarray,
                     sigma: float,
                     alpha: float,
                     min_segment_datapoints: int,
                     global_local: bool,
                     debug: bool = False,
                     log=None) -> Tuple[int, int]:
    """
    Test for significant change points in the cumulative signal across all sections.

    Uses a Bonferroni-adjusted significance threshold to control for multiple comparisons
    when testing across many segments simultaneously.

    Args:
        cy: Cumulative sum of measurements
        nodes: Locations of currently identified change points (0-based)
        x: Index vector
        sigma: Error standard deviation
        alpha: Significance level
        min_segment_datapoints: Minimum number of datapoints per segment
        global_local: Use segment-specific lengths (True) or total data length (False)
        debug: If True, emit diagnostic output for each change-point test
        log: Optional callable for output (defaults to print)

    Returns:
        location: Index of candidate change point (0-based)
        change_point_test: 1 if a significant change point was detected, 0 otherwise
    """
    nodes = np.sort(nodes)
    L = np.diff(nodes)

    m = np.zeros(len(L))
    id_array = np.zeros(len(L), dtype=int)

    cy_nodes = cy[nodes]
    cy_interp = np.interp(x, nodes, cy_nodes)

    # Bonferroni correction: divide alpha by number of segments and both tails
    alpha_adj = alpha / len(L) / 2
    log_val = math.log(alpha_adj)  
    th = math.sqrt(-0.5 * log_val)
    
    change_point_test = 0

    for i, (start_idx, end_idx) in enumerate(zip(nodes, nodes[1:])):
        cda = cy[start_idx:end_idx+1] - cy_interp[start_idx:end_idx+1]

        abs_cda = np.abs(cda)
        sorted_indices = np.argsort(abs_cda)[::-1]
        sorted_values = abs_cda[sorted_indices]

        # Select the highest-CDA candidate that respects min_segment_datapoints from both ends
        for j, candidate_idx in enumerate(sorted_indices):
            
            # MATLAB: if min(abs(ID(j)-[1; nodes(i+1) - nodes(i) + 1]))>(min_length - 1)
            # In 0-based Python: check distance to segment boundaries
            segment_length = end_idx - start_idx + 1  
            if min(abs(candidate_idx - 0), abs(candidate_idx - (segment_length - 1))) >= (min_segment_datapoints - 1):
                id_array[i] = candidate_idx
                m[i] = sorted_values[j]
                break
    
    if global_local:
        test_stats = np.divide(m, sigma * np.sqrt(np.maximum(L, 1)),
                              out=np.zeros_like(m), where=(sigma * np.sqrt(np.maximum(L, 1)) != 0))
        M_idx = np.argmax(test_stats)
        M = test_stats[M_idx]
    else:
        test_stats = m / (sigma * math.sqrt(len(cy)))
        M_idx = np.argmax(test_stats)
        M = test_stats[M_idx]

    _log = log or print
    location = id_array[M_idx] + np.sum(L[:M_idx])

    if debug:
        _log(f"    Max test stat: M={M:.6f} at location {location} (segment {M_idx})")

    # Test significance
    if M > th:
        change_point_test = 1
        if debug:
            _log(f"    SIGNIFICANT: {M:.6f} > {th:.6f}")
    else:
        if debug:
            _log(f"    NOT SIGNIFICANT: {M:.6f} <= {th:.6f}")
    
    return int(location), change_point_test


class AashtoCdaMethod(AnalysisMethodBase):
    """
    AASHTO Enhanced Cumulative Difference Approach analysis method.
    
    Implements deterministic statistical change point detection for highway
    pavement segmentation without requiring evolutionary computation.
    """
    
    def __init__(self):
        super().__init__()
    
    @property
    def method_name(self) -> str:
        """Human-readable method name for GUI display."""
        return "AASHTO CDA Statistical Analysis"
    
    @property
    def method_key(self) -> str:
        """Method key for result handling and export."""
        return "aashto_cda"
    
    def _create_analyzable_segments(self, route_analysis):
        """Build the analyzable-segments list from RouteAnalysis mandatory breakpoints."""
        segments = []

        mandatory_points = sorted(list(route_analysis.mandatory_breakpoints))
        gap_set = set(route_analysis.gap_segments)

        for start, end in zip(mandatory_points, mandatory_points[1:]):
            length = end - start

            is_gap = any(abs(start - gap[0]) < 0.001 and abs(end - gap[1]) < 0.001
                        for gap in gap_set)
            segment_type = "gap" if is_gap else "data"
            
            segments.append({
                "start": start,
                "end": end, 
                "length": length,
                "type": segment_type
            })
            
        return segments
    
    def run_analysis(self, 
                    data,  # RouteAnalysis object
                    route_id: str,
                    x_column: str,
                    y_column: str,
                    gap_threshold: float,
                    **kwargs) -> AnalysisResult:
        """
        Run AASHTO CDA analysis using RouteAnalysis segmentable sections architecture.
        
        CORRECTED ARCHITECTURE: Like GA methods, CDA now processes segmentable sections
        between mandatory breakpoints independently, then unions results (not single-pass).
        
        Args:
            data: RouteAnalysis object (required)
            route_id: Route identifier for this analysis
            x_column: Name of distance column (in RouteAnalysis.route_data)
            y_column: Name of measurement column (in RouteAnalysis.route_data)
            gap_threshold: Data gap detection threshold
            **kwargs: Method-specific parameters including:
                - alpha: Significance level for change point detection (default: 0.05)
                - method: Error estimation method (1=MAD+normal, 2=diff std dev, 3=measurement std dev) (default: 2)
                - use_segment_length: Use segment-specific lengths in calculations (default: True)
                - min_segment_datapoints: Minimum number of datapoints per segment (default: 1)
                - max_segments: Maximum segments per segmentable section (default: 1000)
                - min_section_difference: Minimum difference between adjacent sections (default: 0.0)
                - enable_diagnostic_output: Enable detailed diagnostics (default: False)
            min_section_difference: Minimum difference between adjacent segment means
            gap_threshold: Data gap detection threshold
            enable_diagnostic_output: Enable detailed diagnostic information
            **kwargs: Additional parameters (ignored)
            
        Returns:
            AnalysisResult with breakpoints and segment information
        """
        if not hasattr(data, 'route_data'):
            raise TypeError(
                "AashtoCdaMethod.run_analysis expects a RouteAnalysis object (with .route_data). "
                "Use analyze_route_gaps(...) to build one from a DataFrame."
            )

        try:
            # Extract method defaults strictly from method configuration
            method_config = get_optimization_method('aashto_cda')
            if not method_config:
                raise ValueError("AASHTO CDA method configuration not found")

            param_defaults = {param.name: param.default_value for param in method_config.parameters}

            log_callback = kwargs.get('log_callback', None)
            log = log_callback or print

            # Extract method-specific parameters with config defaults (no hardcoded literals)
            alpha = kwargs.get('alpha', param_defaults['alpha'])
            method = kwargs.get('method', param_defaults['method'])
            use_segment_length = kwargs.get('use_segment_length', param_defaults['use_segment_length'])
            min_segment_datapoints = kwargs.get('min_segment_datapoints', param_defaults['min_segment_datapoints'])
            max_segments = kwargs.get('max_segments', param_defaults['max_segments'])
            min_section_difference = kwargs.get('min_section_difference', param_defaults['min_section_difference'])
            enable_diagnostic_output = kwargs.get('enable_diagnostic_output', param_defaults['enable_diagnostic_output'])

            # Validate alpha based on algorithm constraints (documentation: alpha < 0.5)
            if not isinstance(alpha, (int, float)) or not (0.0 < float(alpha) < 0.5):
                raise ValueError(f"alpha must be between 0 and 0.5 (exclusive), got: {alpha}")
            
            # RouteAnalysis-only contract
            route_analysis = data
            route_data = route_analysis.route_data
            if x_column not in route_data.columns:
                raise ValueError(
                    f"x_column={x_column!r} not found in RouteAnalysis.route_data columns: {list(route_data.columns)!r}"
                )
            if y_column not in route_data.columns:
                raise ValueError(
                    f"y_column={y_column!r} not found in RouteAnalysis.route_data columns: {list(route_data.columns)!r}"
                )

            # Ensure we are working with numeric numpy arrays for comparisons/searchsorted.
            # RouteAnalysis data should already have numeric X/Y in normal GUI flows,
            # but this keeps direct/integration usages safe and keeps Pylance happy.
            try:
                x_values = np.asarray(route_data[x_column].to_numpy(), dtype=float)
                y_values = np.asarray(route_data[y_column].to_numpy(), dtype=float)
            except Exception as e:
                raise ValueError(
                    f"AASHTO CDA requires numeric columns for x_column={x_column!r}, y_column={y_column!r}. "
                    f"Could not convert to float arrays: {e}"
                ) from e
            mandatory_breakpoints = sorted(route_analysis.mandatory_breakpoints)
            
            # Validate min_segment_datapoints parameter (sample-std safe)
            if not isinstance(min_segment_datapoints, int) or min_segment_datapoints < 3:
                raise ValueError(f"min_segment_datapoints must be an integer >= 3, got: {min_segment_datapoints}")
            
            # Process each segmentable section independently (CORRECT ARCHITECTURE)
            all_breakpoints = list(mandatory_breakpoints)  # Start with mandatory breakpoints
            section_diagnostics = []
            
            if enable_diagnostic_output:
                log(f"\n=== AASHTO CDA Analysis: {route_id} ===")
                log(f"Total mandatory breakpoints: {len(mandatory_breakpoints)}")
                log(f"Segmentable sections to process: {len(mandatory_breakpoints) - 1}")
            
            # Process each segmentable section between mandatory breakpoints
            for section_idx, (section_start_mile, section_end_mile) in enumerate(zip(mandatory_breakpoints, mandatory_breakpoints[1:])):
                
                # Extract data for this segmentable section
                section_mask = (x_values >= section_start_mile) & (x_values <= section_end_mile)
                section_x = x_values[section_mask]
                section_y = y_values[section_mask]
                
                if len(section_y) < 2:
                    # Skip sections with insufficient data
                    if enable_diagnostic_output:
                        log(f"  Section {section_idx + 1}: [{section_start_mile:.3f} to {section_end_mile:.3f}] - SKIPPED (insufficient data: {len(section_y)} points)")
                    continue

                section_length = section_end_mile - section_start_mile
                if enable_diagnostic_output:
                    log(f"  Section {section_idx + 1}: [{section_start_mile:.3f} to {section_end_mile:.3f}] - length: {section_length:.3f} miles, points: {len(section_y)}")

                # Run AASHTO CDA on this segmentable section only
                try:
                    uniform_sections, cda_nodes, section_start_indices, section_end_indices, mu = aashto_cda(
                        section_y,
                        alpha=alpha,
                        num_sections=max_segments,
                        min_segment_datapoints=min_segment_datapoints,
                        min_section_difference=min_section_difference,
                        method=method,
                        global_local=use_segment_length,
                        enable_diagnostic_output=enable_diagnostic_output,
                        log=log,
                    )

                    # Convert section-relative indices to absolute mile positions
                    section_cda_miles = section_x[cda_nodes]
                    if enable_diagnostic_output:
                        log(f"    -> CDA algorithm returned {len(cda_nodes)} nodes: {cda_nodes}")
                        log(f"    -> Converted to mile positions: {section_cda_miles}")
                        log(f"    -> Section bounds: {section_start_mile} to {section_end_mile}")

                    internal_breakpoints = [bp for bp in section_cda_miles
                                          if section_start_mile < bp < section_end_mile]

                    # Add internal breakpoints (exclude section boundaries already in mandatory_breakpoints)
                    all_breakpoints.extend(internal_breakpoints)

                    # Store section diagnostics
                    if enable_diagnostic_output:
                        section_diagnostics.append({
                            'section_index': section_idx,
                            'section_bounds': [section_start_mile, section_end_mile],
                            'section_length': section_length,
                            'datapoints': len(section_y),
                            'cda_breakpoints_found': len(internal_breakpoints),
                            'internal_breakpoints': internal_breakpoints
                        })
                        log(f"    -> CDA found {len(internal_breakpoints)} internal breakpoints")

                except Exception as section_error:
                    if enable_diagnostic_output:
                        log(f"    -> ERROR in section {section_idx + 1}: {section_error}")
                    continue

            all_breakpoints = np.unique(np.array(all_breakpoints))
            all_breakpoints = np.sort(all_breakpoints)

            if enable_diagnostic_output:
                log("\n=== FINAL BREAKPOINT COLLECTION ===")
                log(f"Total breakpoints collected: {len(all_breakpoints)}")
                log(f"All breakpoints: {all_breakpoints.tolist()}")
            
            # Calculate final segment statistics using all breakpoints
            segment_stats = []
            for start_mile, end_mile in zip(all_breakpoints, all_breakpoints[1:]):
                
                # Find corresponding data indices
                start_idx = np.searchsorted(x_values, start_mile, side='left')
                end_idx = np.searchsorted(x_values, end_mile, side='right') - 1
                
                # Calculate segment statistics
                segment_length = end_mile - start_mile  
                if start_idx <= end_idx < len(y_values):
                    mean_value = np.mean(y_values[start_idx:end_idx+1])
                else:
                    mean_value = 0.0
                
                segment_stats.append({
                    'start_mile': start_mile,
                    'end_mile': end_mile,
                    'length': segment_length,
                    'mean_value': mean_value,
                    'start_index': int(start_idx),
                    'end_index': int(end_idx),
                    'source': 'segmented_cda'  # Indicates proper segmented processing
                })
            
            # Prepare diagnostic information if requested  
            diagnostics = {}
            if enable_diagnostic_output:
                log(f"Final result: {len(segment_stats)} segments from {len(all_breakpoints)} breakpoints")
                
                # Calculate average datapoint spacing for diagnostics
                avg_spacing = (x_values[-1] - x_values[0]) / len(x_values) if len(x_values) > 1 else 0.0
                
                diagnostics = {
                    'algorithm': 'AASHTO Enhanced CDA with RouteAnalysis Segmented Processing',
                    'architecture': 'segmented_processing',  # Correct architecture
                    'parameters': {
                        'alpha': alpha,
                        'method': method,
                        'use_segment_length': use_segment_length,
                        'min_segment_datapoints': min_segment_datapoints,
                        'max_segments_per_section': max_segments,
                        'min_section_difference': min_section_difference
                    },
                    'processing_summary': {
                        'route_id': route_id,
                        'num_datapoints': len(y_values),
                        'total_distance': x_values[-1] - x_values[0],
                        'avg_datapoint_spacing': avg_spacing,
                        'segmentable_sections_processed': len(mandatory_breakpoints) - 1,
                        'mandatory_breakpoints': len(mandatory_breakpoints),
                        'internal_breakpoints_found': len(all_breakpoints) - len(mandatory_breakpoints), 
                        'final_segments': len(segment_stats)
                    },
                    'section_details': section_diagnostics
                }
            
            # Return AnalysisResult
            breakpoints_list = all_breakpoints.tolist()
            segment_lengths = [breakpoints_list[i + 1] - breakpoints_list[i] for i in range(len(breakpoints_list) - 1)]
            avg_excluding_gaps = average_length_excluding_gap_segments(
                breakpoints_list,
                getattr(route_analysis, 'gap_segments', []),
            )

            data_summary = {
                'total_data_points': len(route_analysis.route_data),
                'data_range': {
                    'x_min': route_analysis.data_range['x_min'],
                    'x_max': route_analysis.data_range['x_max'],
                    'y_min': route_analysis.data_range['y_min'],
                    'y_max': route_analysis.data_range['y_max']
                },
                # Transform RouteAnalysis gap data to JSON format
                'gap_analysis': {
                    'total_gaps': len(route_analysis.gap_segments),
                    'gap_segments': [
                        {
                            'start': gap[0],
                            'end': gap[1],
                            'length': gap[1] - gap[0]
                        } for gap in route_analysis.gap_segments
                    ],
                    'total_gap_length': sum(gap[1] - gap[0] for gap in route_analysis.gap_segments)
                },
                'mandatory_segments': {
                    'mandatory_breakpoints': sorted(list(route_analysis.mandatory_breakpoints)),
                    'analyzable_segments': self._create_analyzable_segments(route_analysis),
                    'total_analyzable_length': route_analysis.route_stats.get('total_analyzable_length', 0.0)
                }
            }

            # Optional: attribute-based must-break metadata for visualization/reporting
            try:
                if build_attribute_break_analysis is not None:
                    attr_block = build_attribute_break_analysis(route_analysis)
                    if attr_block:
                        data_summary['attribute_break_analysis'] = attr_block
            except Exception:
                pass

            return AnalysisResult(
                method_name=self.method_name,
                method_key=self.method_key,
                route_id=route_id,
                all_solutions=[{
                    'chromosome': breakpoints_list,  # Use interface-compliant key name
                    'fitness': 0.0,  # CDA is deterministic
                    'total_deviation': 0.0,  # Not applicable for CDA
                    'avg_segment_length': float(avg_excluding_gaps),
                    'num_segments': len(segment_stats),
                    'segmentation': {
                        'breakpoints': breakpoints_list,
                        'segment_count': len(segment_lengths),
                        'segment_lengths': segment_lengths,
                        'total_length': (breakpoints_list[-1] - breakpoints_list[0]) if len(breakpoints_list) >= 2 else 0.0,
                        'average_segment_length': float(avg_excluding_gaps),
                        'segment_details': [],
                    },
                }],
                mandatory_breakpoints=list(mandatory_breakpoints),
                optimization_stats=diagnostics,
                input_parameters={
                    'alpha': alpha,
                    'method': method,
                    'use_segment_length': use_segment_length,
                    'min_segment_datapoints': min_segment_datapoints,
                    'max_segments': max_segments,
                    'min_section_difference': min_section_difference,
                    'gap_threshold': gap_threshold  # Framework parameter for export consistency
                },
                data_summary=data_summary
            )
            
        except Exception as e:
            # Return error result
            return AnalysisResult(
                method_name=self.method_name,
                method_key=self.method_key,
                route_id=route_id,
                all_solutions=[],
                optimization_stats={'error': str(e), 'error_type': type(e).__name__}
            )