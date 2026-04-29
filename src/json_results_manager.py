"""
JSON Results Manager for Highway Segmentation GA

This module provides JSON output capabilities for Highway Segmentation GA.
Implements the Phase 1 simplified JSON schema with essential features and extensibility
for future enhancements.

Key Features:
- Converts AnalysisResult dataclass to JSON schema format
- Cross-route aggregation for multi-route scenarios  
- Data traceability with column mapping
- Route processing context tracking
- Schema validation support

Author: Highway Segmentation GA Team
Phase: 1.95.2 - JSON Output Implementation
"""

import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path
from dataclasses import asdict

class SetEncoder(json.JSONEncoder):
    """Custom JSON encoder that converts sets to lists for serialization."""
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)

# Import analysis framework
try:
    from analysis.base import AnalysisResult
except ImportError:
    raise ImportError(
        "Cannot import AnalysisResult from 'analysis.base'. "
        "Ensure the project's 'src' directory is on PYTHONPATH/sys.path."
    )


class JsonResultsManager:
    """
    Manager class for converting optimization results to JSON format.
    
    This class takes AnalysisResult objects and converts them to the standardized
    JSON schema format. It handles both single-route and multi-route scenarios,
    providing essential metadata while preserving extensibility for future features.
    
    Usage:
        json_manager = JsonResultsManager()
        json_path = json_manager.save_analysis_results(analysis_results, "results.json")
    """
    
    def __init__(self, schema_version: str = "1.1.0"):
        """
        Initialize the JSON Results Manager.
        
        Args:
            schema_version: JSON schema version to use for output format
        """
        self.schema_version = schema_version
        self.schema_url = "https://json-schema.org/draft/2020-12/schema"
    
    def save_analysis_results(self, 
                            analysis_results: Union[AnalysisResult, List[AnalysisResult]], 
                            output_path: str,
                            input_file_info: Optional[Dict[str, Any]] = None,
                            route_processing_info: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert AnalysisResult(s) to JSON format and save to file.
        
        Args:
            analysis_results: Single AnalysisResult or list for multi-route
            output_path: Path where JSON file should be saved
            input_file_info: Optional metadata about input data file
            route_processing_info: Optional info about route processing configuration
            
        Returns:
            str: Path to saved JSON file
            
        Raises:
            ValueError: If analysis_results is empty or invalid
            IOError: If file cannot be written
        """
        # Convert single result to list for uniform processing
        if isinstance(analysis_results, AnalysisResult):
            results_list = [analysis_results]
        else:
            results_list = analysis_results
            
        if not results_list:
            raise ValueError("No analysis results provided")
        
        # Build JSON structure according to schema
        json_data = self._build_json_structure(results_list, input_file_info, route_processing_info)
        
        # Save to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, cls=SetEncoder)

        return str(output_path)
    
    def _build_json_structure(self, 
                            results_list: List[AnalysisResult],
                            input_file_info: Optional[Dict[str, Any]] = None,
                            route_processing_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build the complete JSON structure according to the schema.
        
        This is the core conversion method that maps AnalysisResult data to
        the JSON schema format we defined.
        """
        # Start with basic structure
        json_data = {
            "$schema": self.schema_url,
            "analysis_metadata": self._build_analysis_metadata(results_list, input_file_info),
            "input_parameters": self._build_input_parameters(results_list, route_processing_info),
            "route_results": self._build_route_results(results_list)
        }
        
        return json_data
    
    def _build_analysis_metadata(self, 
                               results_list: List[AnalysisResult], 
                               input_file_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build the analysis_metadata section of the JSON.
        
        This includes:
        - Analysis timestamp and basic identification
        - Software version information (optional)
        - Analysis method and status
        - Input file metadata and column mapping
        - Cross-route summary statistics
        """
        # Get basic info from first result (all should have same method/version)
        first_result = results_list[0]
        
        # Build metadata structure
        metadata = {
            "timestamp": first_result.timestamp if first_result.timestamp else datetime.now().isoformat(),
            "analysis_method": first_result.method_key,
            "analysis_status": "completed"  # Assume completed if we're saving results
        }
        
        # Add optional software version info if available
        if hasattr(first_result, 'analysis_version') and first_result.analysis_version:
            metadata["software_version"] = {
                "application": "Highway Segmentation",
                "version": first_result.analysis_version
            }
        
        # Build input file info section
        metadata["input_file_info"] = self._build_input_file_info(first_result, input_file_info)
        
        # Calculate and add analysis summary
        metadata["analysis_summary"] = self._calculate_analysis_summary(results_list)
        
        return metadata
    
    def _build_input_file_info(self, 
                             first_result: AnalysisResult, 
                             file_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build the input_file_info section with data traceability.
        
        This is essential for reproducing analyses - includes column mapping
        and basic file metadata.
        """
        # Start with provided file info or extract from data_summary
        input_file_info = {}
        
        if file_info:
            # Use provided file information
            input_file_info.update(file_info)
        
        # Extract data characteristics from AnalysisResult.data_summary
        if first_result.data_summary:
            data_summary = first_result.data_summary
            
            # Add total data points if available
            if 'total_data_points' in data_summary:
                input_file_info["total_data_rows"] = data_summary['total_data_points']
            
            # Add column information - this is critical for traceability
            if 'x_column' in data_summary:
                column_info = {
                    "x_column": data_summary['x_column'],
                    "y_column": data_summary.get('y_column', 'data_value')
                }
                
                # Add route column if this is multi-route data
                if 'route_column' in data_summary:
                    column_info["route_column"] = data_summary['route_column']
                    column_info["total_columns"] = 3
                else:
                    column_info["route_column"] = None
                    column_info["total_columns"] = 2
                
                input_file_info["column_info"] = column_info
        
        # Set defaults for required fields if not provided
        if "total_data_rows" not in input_file_info:
            input_file_info["total_data_rows"] = sum(
                result.data_summary.get('total_data_points', 0) 
                for result in [first_result]
            )
        
        if "total_routes_available" not in input_file_info:
            input_file_info["total_routes_available"] = 1  # Will be updated for multi-route
        
        return input_file_info
    
    def _build_input_parameters(self, 
                              results_list: List[AnalysisResult],
                              route_processing_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build the input_parameters section of the JSON.
        
        This includes:
        - Optimization method configuration  
        - Method parameters from AnalysisResult.input_parameters
        - Route processing configuration (essential for Phase 1)
        """
        first_result = results_list[0]

        # Build method configuration section (config-driven)
        method_key = first_result.method_key
        try:
            # Import locally to avoid circular import issues
            from config import get_optimization_method
            cfg = get_optimization_method(method_key)
        except Exception as e:
            raise ValueError(
                f"Unknown optimization method key {method_key!r}; cannot populate optimization_method_config"
            ) from e

        method_config = {
            "method_key": method_key,
            "display_name": getattr(cfg, 'display_name', first_result.method_name),
        }
        desc = getattr(cfg, 'description', None)
        if desc:
            method_config["description"] = desc
        
        # Build route processing configuration
        route_processing = self._build_route_processing_config(results_list, route_processing_info)

        # Schema note: input_parameters.method_parameters is an extensible map of primitive/object types
        # but does NOT permit null values. Use omission to represent "unset"/"unlimited".
        raw_method_parameters = first_result.input_parameters or {}
        method_parameters = {
            key: value
            for key, value in raw_method_parameters.items()
            if value is not None
        }
        
        return {
            "optimization_method_config": method_config,
            "method_parameters": method_parameters,
            "route_processing": route_processing
        }
    
    def _build_route_processing_config(self, 
                                     results_list: List[AnalysisResult],
                                     processing_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build route processing configuration section.
        
        This is critical for Phase 1 - includes the route filtering and processing
        context we agreed to implement.  
        """
        # Determine route mode based on number of results
        route_mode = "multi_route" if len(results_list) > 1 else "single_route"
        
        # Extract column information from first result
        first_result = results_list[0] 
        data_summary = first_result.data_summary or {}
        
        # Build base configuration
        config = {
            "route_mode": route_mode,
            "selected_routes": [result.route_id for result in results_list]
        }
        
        # Add column mapping (essential for traceability)
        # Use provided processing_info (actual column names) instead of broken fallbacks
        if processing_info:
            config["x_column"] = processing_info.get("x_column", "milepoint")
            config["y_column"] = processing_info.get("y_column", "structural_strength_ind")
            config["route_column"] = processing_info.get("route_column", None)
        else:
            # Fallback only when no processing_info provided (shouldn't happen with current architecture)
            config["x_column"] = data_summary.get("x_column", "milepoint")
            config["y_column"] = data_summary.get("y_column", "structural_strength_ind")
            config["route_column"] = data_summary.get("route_column", None)
        
        # Add route processing context (the fields we specifically wanted)
        if processing_info:
            # Use provided processing info
            config.update(processing_info)
        else:
            # Set reasonable defaults
            config["route_filtering_applied"] = len(results_list) > 1  # Assume filtering if multi-route
            config["total_routes_in_source"] = len(results_list)  # Will need to be updated by caller  
            config["total_routes_processed"] = len(results_list)
        
        return config
    
    def _build_route_results(self, results_list: List[AnalysisResult]) -> List[Dict[str, Any]]:
        """
        Build the route_results section of the JSON.
        
        This converts each AnalysisResult into the schema format with:
        - Route identification and processing context
        - Input data analysis summary 
        - Processing results with optimization outcomes
        """
        route_results = []
        
        for i, result in enumerate(results_list):
            route_data = {
                "route_info": self._build_route_info(result),
                "input_data_analysis": self._build_input_data_analysis(result),
                "processing_results": self._build_processing_results(result)
            }
            route_results.append(route_data)
        
        return route_results
    
    def _build_route_info(self, result: AnalysisResult) -> Dict[str, Any]:
        """Build route identification section."""
        return {
            "route_id": result.route_id
        }
    
    def _build_input_data_analysis(self, result: AnalysisResult) -> Dict[str, Any]:
        """
        Build input data analysis section from AnalysisResult.data_summary.
        
        Extracts available data characteristics - this provides context about
        the input data that was processed.
        """
        data_summary = result.data_summary or {}
        
        # Build data summary section
        analysis = {
            "data_summary": {
                "total_data_points": data_summary.get("total_data_points", 0)
            }
        }
        
        # Add data range if available
        if "data_range" in data_summary:
            analysis["data_summary"]["data_range"] = data_summary["data_range"]
        
        # Add gap analysis from data_summary (generic - applies to all methods)
        gap_info = {
            "total_gaps": 0,
            "gap_segments": [],
            "total_gap_length": 0.0
        }
        
        # Extract gap analysis from data_summary if available
        if "gap_analysis" in data_summary:
            gap_data = data_summary["gap_analysis"]
            gap_info.update({
                "total_gaps": gap_data.get("total_gaps", 0),
                "gap_segments": gap_data.get("gap_segments", []),
                "total_gap_length": gap_data.get("total_gap_length", 0.0)
            })
        
        # Build mandatory segments section
        mandatory_info = {
            "mandatory_breakpoints": result.mandatory_breakpoints,
            "analyzable_segments": [
                {
                    "start": result.mandatory_breakpoints[i],
                    "end": result.mandatory_breakpoints[i+1],
                    "length": result.mandatory_breakpoints[i+1] - result.mandatory_breakpoints[i],
                    "type": "data"
                }
                for i in range(len(result.mandatory_breakpoints) - 1)
            ] if len(result.mandatory_breakpoints) >= 2 else [],
            "total_analyzable_length": 0.0
        }
        
        # Calculate total length if possible
        if "data_range" in data_summary and "x_min" in data_summary["data_range"]:
            range_info = data_summary["data_range"]
            total_length = range_info.get("x_max", 0) - range_info.get("x_min", 0)
            mandatory_info["total_analyzable_length"] = round(total_length, 3)
        
        analysis["gap_analysis"] = gap_info
        analysis["mandatory_segments"] = mandatory_info
        
        return analysis
    
    def _build_processing_results(self, result: AnalysisResult) -> Dict[str, Any]:
        """
        Build processing results section with optimization outcomes.
        
        Uses unified pareto_points structure as required by schema for all methods.
        """
        # Unified structure: ALL methods return pareto_points array (schema compliant)
        if result.is_multi_objective():
            # Multi-objective: multiple Pareto solutions
            pareto_points = []
            for i, solution in enumerate(result.all_solutions):
                pareto_point = {
                    "point_id": i,
                    "objective_values": solution.get("objective_values", solution.get("fitness", [])),
                    "segmentation": self._extract_segmentation_info(solution)
                }
                pareto_points.append(pareto_point)
        else:
            # Single-objective or constrained: single pareto point (schema compliant)
            pareto_points = [{
                "point_id": 0,
                "objective_values": result.best_solution.get("objective_values", [result.get_best_fitness()]),
                "segmentation": self._extract_segmentation_info(result.best_solution)
            }]
        
        return {
            "pareto_points": pareto_points
        }
    
    def _extract_segmentation_info(self, solution: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract segmentation information from a solution.
        
        This formats the core optimization results (breakpoints, segments)
        in a consistent way regardless of the optimization method.
        """
        chromosome = solution.get("chromosome", [])
        
        segmentation = {
            "breakpoints": chromosome,
            "segment_count": len(chromosome) - 1 if len(chromosome) > 1 else 0,
        }
        
        # Calculate segment lengths if possible
        if len(chromosome) > 1:
            segment_lengths = []
            for i in range(len(chromosome) - 1):
                length = chromosome[i + 1] - chromosome[i]
                segment_lengths.append(round(length, 3))
            
            segmentation["segment_lengths"] = segment_lengths
            segmentation["total_length"] = round(sum(segment_lengths), 3)
            segmentation["average_segment_length"] = round(sum(segment_lengths) / len(segment_lengths), 3)
        
        return segmentation
    
    def _calculate_analysis_summary(self, results_list: List[AnalysisResult]) -> Dict[str, Any]:
        """
        Calculate cross-route analysis summary statistics.
        
        This implements the essential aggregation we agreed on:
        - total_processing_time
        - total_routes_processed  
        - total_length_processed
        """
        total_processing_time = sum(result.processing_time for result in results_list)
        total_routes_processed = len(results_list)
        
        # Calculate total length from data_summary if available
        total_length_processed = 0.0
        for result in results_list:
            if 'total_length' in result.data_summary:
                total_length_processed += result.data_summary['total_length']
            elif 'data_range' in result.data_summary:
                # Fallback: calculate from x_min/x_max
                range_info = result.data_summary['data_range']
                if 'x_max' in range_info and 'x_min' in range_info:
                    total_length_processed += range_info['x_max'] - range_info['x_min']
        
        return {
            "total_processing_time": round(total_processing_time, 3),
            "total_routes_processed": total_routes_processed,
            "total_length_processed": round(total_length_processed, 3)
        }


# Convenience function for single-result scenarios
def save_single_analysis_result(analysis_result: AnalysisResult, 
                              output_path: str,
                              **kwargs) -> str:
    """
    Convenience function to save a single AnalysisResult to JSON.
    
    Args:
        analysis_result: The AnalysisResult to save
        output_path: Where to save the JSON file
        **kwargs: Additional arguments passed to JsonResultsManager
        
    Returns:
        str: Path to saved file
    """
    json_manager = JsonResultsManager()
    return json_manager.save_analysis_results(analysis_result, output_path, **kwargs)