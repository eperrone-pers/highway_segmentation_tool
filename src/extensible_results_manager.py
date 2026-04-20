"""
Extensible Results Manager - Highway Segmentation GA

Modern, plugin-based results management system focused on JSON output with
method-specific extensibility. This is the future-focused replacement for 
legacy non-schema results outputs.

Key Features:
- JSON-first architecture with schema compliance
- Method plugin system for custom statistics
- Built-in support for AnalysisResult framework  
- Type-safe, modern Python design
- Extensible without core system modification
- Analysis-wide aggregation with method contributions

Architecture:
- ExtensibleJsonResultsManager: Core JSON generation with plugin support
- AnalysisMethodPlugin: Base class for method-specific extensions
- JsonMethodRegistry: Singleton registry for plugin management
- Built-in plugins for standard methods (single/multi/constrained)

Usage:
    # Standard usage
    manager = ExtensibleJsonResultsManager()
    output_path = manager.save_analysis_results(analysis_results, "results.json")
    
    # Custom method extension
    class MyMethodPlugin(AnalysisMethodPlugin):
        def supports_method(self, method_key: str) -> bool:
            return method_key == "my_custom_method"
        
        def extract_custom_statistics(self, result: AnalysisResult) -> Dict[str, Any]:
            return {"custom_metrics": {"efficiency": 0.92}}
    
    # Register and use
    JsonMethodRegistry().register_plugin(MyMethodPlugin())

Author: Highway Segmentation GA Team
Phase: 1.95.2 - Extensible JSON Results System
Date: April 2026
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import asdict

class SetEncoder(json.JSONEncoder):
    """Custom JSON encoder that converts sets to lists for serialization."""
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)

# Import analysis framework and base JSON manager
try:
    from analysis.base import AnalysisResult
    ANALYSIS_FRAMEWORK_AVAILABLE = True
except ImportError:
    print("Warning: AnalysisResult not available - analysis framework not found")
    ANALYSIS_FRAMEWORK_AVAILABLE = False

try:
    from json_results_manager import JsonResultsManager
    BASE_JSON_AVAILABLE = True
except ImportError:
    print("Warning: Base JsonResultsManager not available")
    BASE_JSON_AVAILABLE = False


# ===== METHOD PLUGIN SYSTEM =====

class AnalysisMethodPlugin(ABC):
    """
    Base class for method-specific JSON statistics contribution.
    
    This enables analysis methods to contribute specialized statistics and diagnostics
    to the JSON output beyond the standard schema. Each method can implement a plugin
    that extracts method-relevant insights from AnalysisResult objects.
    
    Design Benefits:
    - Methods become active participants in result generation
    - Extensible without modifying core JSON generation logic
    - Rich diagnostics specific to each optimization approach
    - Clean separation between core results and method specializations
    
    Plugin Lifecycle:
    1. supports_method() - Check if plugin handles this method type
    2. extract_custom_statistics() - Extract method-specific data from AnalysisResult
    3. enhance_route_results() - Add custom sections to individual route results
    4. contribute_analysis_summary() - Add to analysis-wide aggregated statistics
    """
    
    @abstractmethod
    def supports_method(self, method_key: str) -> bool:
        """
        Check if this plugin handles the specified method key.
        
        DEPRECATED: This method is deprecated. Use supports_return_type() instead.
        Will be called automatically by the registry using return_type lookup.
        
        Args:
            method_key: Method identifier (e.g., "single", "aashto_cda", "multi")
            
        Returns:
            bool: True if this plugin should process this method key
        """
        pass
    
    def supports_return_type(self, return_type: str) -> bool:
        """
        Check if this plugin handles the specified return type.
        
        This is the preferred method for plugin dispatch based on result structure
        rather than implementation details.
        
        Args:
            return_type: Return type from config (e.g., "single_objective", "multi_objective")
            
        Returns:
            bool: True if this plugin should process this return type
        """
        # Default implementation falls back to supports_method for backward compatibility
        # Plugins should override this method instead of supports_method
        return False
        
    def get_supported_return_type(self) -> str:
        """
        Get the return type this plugin supports.
        
        Returns:
            str: The return_type this plugin handles (e.g., "single_objective")
        
        Args:
            method_key: The method key from AnalysisResult (e.g., "single", "aashto_cda", "multi")
            
        Returns:
            bool: True if this plugin can process results from this method type
        """
        pass
    
    @abstractmethod
    def extract_custom_statistics(self, analysis_result: 'AnalysisResult') -> Dict[str, Any]:
        """
        Extract method-specific statistics from an AnalysisResult.
        
        This is where methods contribute their specialized insights:
        - Convergence analysis for single-objective methods
        - Pareto front analysis for multi-objective methods  
        - Constraint satisfaction metrics for constrained methods
        - Custom performance diagnostics and efficiency metrics
        
        Args:
            analysis_result: AnalysisResult object containing optimization results
            
        Returns:
            Dict containing method-specific statistics to add to JSON output.
            
            Example structure:
            {
                "convergence_analysis": {
                    "final_generation": 150,
                    "improvement_rate": 0.85,
                    "cache_efficiency": 0.73
                },
                "performance_metrics": {
                    "population_diversity": 0.92,
                    "selection_pressure": 1.2
                }
            }
        """
        pass
    
    def enhance_route_results(self, route_data: Dict[str, Any], analysis_result: 'AnalysisResult') -> Dict[str, Any]:
        """
        Enhance individual route results with method-specific sections.
        
        This allows methods to add specialized sections to each route's results.
        Default implementation adds custom statistics to a method_specific_statistics section.
        
        Args:
            route_data: Current route result dictionary being built
            analysis_result: AnalysisResult object for this route
            
        Returns:
            Enhanced route_data dictionary with method-specific additions
        """
        # Default implementation: add custom stats to dedicated section
        custom_stats = self.extract_custom_statistics(analysis_result)
        if custom_stats:
            if "method_specific_statistics" not in route_data:
                route_data["method_specific_statistics"] = {}
            route_data["method_specific_statistics"][analysis_result.method_key] = custom_stats
        
        return route_data
    
    def contribute_analysis_summary(self, all_results: List['AnalysisResult']) -> Dict[str, Any]:
        """
        Contribute to analysis-wide summary statistics.
        
        This allows methods to add aggregated statistics across all routes processed.
        For example, average convergence generation across routes, total Pareto points found,
        constraint violation rates, etc.
        
        Args:
            all_results: List of all AnalysisResult objects from the analysis
            
        Returns:
            Dict containing analysis-wide method-specific statistics
        """
        return {}


class JsonMethodRegistry:
    """
    Singleton registry for analysis method plugins.
    
    Provides a central location for registering and retrieving method-specific
    plugins that contribute custom statistics to JSON output.
    
    Features:
    - Singleton pattern ensures global plugin registry
    - Auto-initialization of built-in plugins
    - Type-safe plugin registration and retrieval
    - Method-based plugin lookup for efficient processing
    """
    
    _instance: Optional['JsonMethodRegistry'] = None
    
    def __new__(cls) -> 'JsonMethodRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.plugins: List[AnalysisMethodPlugin] = []
            cls._instance._initialize_builtin_plugins()
        return cls._instance
    
    def _initialize_builtin_plugins(self) -> None:
        """Initialize built-in plugins via plugin discovery system."""
        try:
            # Use plugin discovery to automatically load available plugins
            from plugins import discover_plugins
            discovered_plugins = discover_plugins()
            
            for plugin in discovered_plugins:
                self.register_plugin(plugin)
                
            print(f"Initialized {len(discovered_plugins)} plugins via discovery")
            
        except ImportError:
            print("Plugin discovery system not available - no plugins loaded")
        except Exception as e:
            print(f"Warning: Plugin discovery failed: {e}")
    
    def register_plugin(self, plugin: AnalysisMethodPlugin) -> None:
        """
        Register a method plugin for custom statistics contribution.
        
        Args:
            plugin: AnalysisMethodPlugin instance to register
            
        Raises:
            TypeError: If plugin doesn't inherit from AnalysisMethodPlugin
        """
        if not isinstance(plugin, AnalysisMethodPlugin):
            raise TypeError("Plugin must inherit from AnalysisMethodPlugin")
        
        self.plugins.append(plugin)
        print(f"Registered method plugin: {plugin.__class__.__name__}")
    
    def get_plugins_for_method(self, method_key: str) -> List[AnalysisMethodPlugin]:
        """
        Get all plugins that support the specified method type.
        
        This method now uses the config-based return_type dispatch approach.
        It looks up the return_type from the method key and finds plugins
        that support that return_type.
        
        Args:
            method_key: Method identifier (e.g., "single", "aashto_cda", "multi")
            
        Returns:
            List of plugins that support this method type
        """
        try:
            # Import here to avoid circular imports
            from config import get_optimization_method
            
            # Convert method key to return_type via config lookup
            method_config = get_optimization_method(method_key)
            return_type = method_config.return_type
            
            # Find plugins that support this return_type
            return [plugin for plugin in self.plugins if plugin.supports_return_type(return_type)]
            
        except (ValueError, ImportError) as e:
            # Fallback to old method for backward compatibility or if config lookup fails
            print(f"Warning: Config lookup failed for method '{method_key}', falling back to legacy dispatch: {e}")
            return [plugin for plugin in self.plugins if plugin.supports_method(method_key)]
    
    def get_all_plugins(self) -> List[AnalysisMethodPlugin]:
        """Get all registered plugins."""
        return self.plugins.copy()
    
    def clear_plugins(self) -> None:
        """Clear all registered plugins. Useful for testing."""
        self.plugins.clear()


# ===== EXTENSIBLE JSON RESULTS MANAGER =====

class ExtensibleJsonResultsManager:
    """
    Modern, extensible JSON results manager with method plugin support.
    
    This is the canonical results writer for schema-compliant JSON outputs.
    Built around JSON output with method-specific extensibility through plugins.
    
    Features:
    - Schema-compliant JSON output
    - Method plugin system for custom statistics
    - JSON output (schema-compliant)
    - Type-safe modern Python design
    - Built-in validation and error handling
    
    Architecture:
    - Uses base JsonResultsManager for core JSON structure
    - Enhances output with method-specific plugins
    - Provides unified interface for all analysis methods
    - Extensible without modifying core logic
    """
    
    def __init__(self, schema_version: str = "1.1.0"):
        """
        Initialize the extensible JSON results manager.
        
        Args:
            schema_version: JSON schema version to use for output format
        """
        self.schema_version = schema_version
        self.plugin_registry = JsonMethodRegistry()
        
        # Initialize base JSON manager if available
        if BASE_JSON_AVAILABLE:
            self.base_json_manager = JsonResultsManager(schema_version)
        else:
            print("Warning: Base JsonResultsManager not available - using fallback")
            self.base_json_manager = None
    
    def save_analysis_results(self, 
                            analysis_results: Union['AnalysisResult', List['AnalysisResult']], 
                            output_path: str,
                            input_file_info: Optional[Dict[str, Any]] = None,
                            route_processing_info: Optional[Dict[str, Any]] = None,
                            original_data_by_route: Optional[Dict[str, Any]] = None) -> str:
        """
        Save analysis results to JSON with method-specific extensions.
        
        This is the main entry point for saving results. It generates base JSON
        structure and enhances it with method-specific plugins.
        
        Args:
            analysis_results: Single AnalysisResult or list for multi-route
            output_path: Path where JSON file should be saved
            input_file_info: Optional metadata about input data file
            route_processing_info: Optional info about route processing configuration
            original_data_by_route: Optional original CSV data by route for segment statistics
            
        Returns:
            str: Path to saved JSON file
            
        Raises:
            ValueError: If analysis_results is empty or invalid
            IOError: If file cannot be written
        """
        # Normalize input to list
        if not ANALYSIS_FRAMEWORK_AVAILABLE:
            raise RuntimeError("AnalysisResult framework not available")
        
        if isinstance(analysis_results, list):
            results_list = analysis_results
        else:
            results_list = [analysis_results]
            
        if not results_list:
            raise ValueError("No analysis results provided")
        
        # Generate base JSON structure  
        json_data = self._generate_enhanced_json(results_list, input_file_info, route_processing_info, original_data_by_route)
        
        # Save to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, cls=SetEncoder)
        
        print(f"Enhanced JSON results saved to: {output_path}")
        return str(output_path)
    
    def _generate_enhanced_json(self, 
                              results_list: List['AnalysisResult'],
                              input_file_info: Optional[Dict[str, Any]] = None,
                              route_processing_info: Optional[Dict[str, Any]] = None,
                              original_data_by_route: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate JSON structure with base schema plus method-specific enhancements.
        
        This is the core logic that combines base JSON generation with plugin extensions.
        """
        # Start with base JSON generation
        if self.base_json_manager:
            # Check if base manager supports Y-value statistics parameters (newer version)
            if hasattr(self.base_json_manager, '_build_processing_results'):
                # Use our enhanced method instead of delegating
                json_data = self._build_complete_json_with_stats(
                    results_list, input_file_info, route_processing_info, original_data_by_route)
            else:
                # Fallback to base manager (no Y-statistics)
                json_data = self.base_json_manager._build_json_structure(
                    results_list, input_file_info, route_processing_info)
        else:
            # Fallback basic structure
            json_data = self._build_basic_json_structure(results_list, input_file_info, route_processing_info)
        
        # Enhance with method-specific plugins
        json_data = self._apply_method_plugins(json_data, results_list)
        
        return json_data
    
    def _build_complete_json_with_stats(self, 
                                      results_list: List['AnalysisResult'],
                                      input_file_info: Optional[Dict[str, Any]] = None,
                                      route_processing_info: Optional[Dict[str, Any]] = None,
                                      original_data_by_route: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build complete JSON structure with Y-value statistics support.
        
        This method builds the entire JSON structure using our enhanced processing
        logic that supports Y-value segment statistics.
        """
        # Build the JSON structure using the same pattern as JsonResultsManager but with our enhancements
        json_data = {
            "$schema": self.base_json_manager.schema_url,
            "analysis_metadata": self.base_json_manager._build_analysis_metadata(results_list, input_file_info),
            "input_parameters": self.base_json_manager._build_input_parameters(results_list, route_processing_info),
            "route_results": self._build_route_results_with_stats(results_list, original_data_by_route, route_processing_info)
        }
        
        return json_data
    
    def _build_route_results_with_stats(self, 
                                       results_list: List['AnalysisResult'], 
                                       original_data_by_route: Optional[Dict[str, Any]] = None,
                                       route_processing_info: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Build route results with enhanced Y-value statistics support.
        """
        route_results = []
        
        # Group results by route_id
        by_route = {}
        for result in results_list:
            if result.route_id not in by_route:
                by_route[result.route_id] = []
            by_route[result.route_id].append(result)
        
        # Process each route
        for route_id, route_results_list in by_route.items():
            route_result = {
                "route_info": self.base_json_manager._build_route_info(route_results_list[0]),
                "input_data_analysis": self.base_json_manager._build_input_data_analysis(route_results_list[0]),
                "processing_results": self._build_processing_results(
                    route_results_list[0], original_data_by_route, route_processing_info
                )
            }
            route_results.append(route_result)
        
        return route_results
    
    def _apply_method_plugins(self, json_data: Dict[str, Any], results_list: List['AnalysisResult']) -> Dict[str, Any]:
        """
        Apply method plugins to enhance JSON with custom statistics.
        
        Args:
            json_data: Base JSON structure to enhance
            results_list: List of analysis results
            
        Returns:
            Enhanced JSON data with method-specific additions
        """
        # Enhance individual route results
        if "route_results" in json_data:
            for i, route_data in enumerate(json_data["route_results"]):
                if i < len(results_list):
                    result = results_list[i] 
                    method_key = result.method_key
                    
                    # Apply all plugins that support this method
                    applicable_plugins = self.plugin_registry.get_plugins_for_method(method_key)
                    for plugin in applicable_plugins:
                        try:
                            route_data = plugin.enhance_route_results(route_data, result)
                        except Exception as e:
                            print(f"Warning: Plugin {plugin.__class__.__name__} failed for route {i}: {e}")
        
        # Enhance analysis summary with method contributions
        json_data = self._enhance_analysis_summary(json_data, results_list)
        
        return json_data
    
    def _enhance_analysis_summary(self, json_data: Dict[str, Any], results_list: List['AnalysisResult']) -> Dict[str, Any]:
        """
        Enhance analysis summary with method-specific aggregated statistics.
        
        Args:
            json_data: JSON data to enhance
            results_list: All analysis results
            
        Returns:
            Enhanced JSON with method-specific summary contributions
        """
        if "analysis_metadata" not in json_data:
            return json_data
            
        if "analysis_summary" not in json_data["analysis_metadata"]:
            return json_data
        
        # Collect method contributions to analysis summary
        method_aggregated_stats = {}
        
        # Group results by method type
        by_method = {}
        for result in results_list:
            method_key = result.method_key
            if method_key not in by_method:
                by_method[method_key] = []
            by_method[method_key].append(result)
        
        # Apply plugins for each method type
        for method_key, method_results in by_method.items():
            applicable_plugins = self.plugin_registry.get_plugins_for_method(method_key)
            for plugin in applicable_plugins:
                try:
                    method_stats = plugin.contribute_analysis_summary(method_results)
                    if method_stats:
                        method_aggregated_stats.update(method_stats)
                except Exception as e:
                    print(f"Warning: Plugin {plugin.__class__.__name__} failed for analysis summary: {e}")
        
        # Add method contributions to analysis summary if any were generated
        if method_aggregated_stats:
            json_data["method_specific_analysis_stats"] = method_aggregated_stats
        
        return json_data
    
    def _build_basic_json_structure(self, 
                                  results_list: List['AnalysisResult'],
                                  input_file_info: Optional[Dict[str, Any]] = None,
                                  route_processing_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fallback basic JSON structure when base JsonResultsManager is not available.
        """
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "analysis_metadata": {
                "timestamp": datetime.now().isoformat(),
                "analysis_method": results_list[0].method_key,
                "analysis_status": "completed",
                "input_file_info": input_file_info or {},
                "analysis_summary": {
                    "total_processing_time": sum(r.processing_time for r in results_list),
                    "total_routes_processed": len(results_list),
                    "total_length_processed": 0.0
                }
            },
            "input_parameters": {
                "optimization_method_config": {
                    "method_key": results_list[0].method_key,
                    "display_name": results_list[0].method_name
                },
                "method_parameters": results_list[0].input_parameters or {},
                "route_processing": route_processing_info or {}
            },
            "route_results": [
                {
                    "route_info": {
                        "route_id": result.route_id
                    },
                    "processing_results": self._build_processing_results(result, original_data_by_route, route_processing_info)
                }
                for i, result in enumerate(results_list)
            ]
        }
    
    def _calculate_segment_details(self, breakpoints, route_data, x_column, y_column, gap_segments, mandatory_breakpoints):
        """Calculate Y-value statistics for segments using proven visualization pattern.
        
        Args:
            breakpoints: List of breakpoint positions
            route_data: DataFrame with original route data
            x_column: Name of X coordinate column
            y_column: Name of Y value column  
            gap_segments: List of gap segment dictionaries
            mandatory_breakpoints: List of mandatory breakpoint positions
            
        Returns:
            List of segment detail dictionaries with Y-value statistics
        """
        import numpy as np
        
        if route_data is None or route_data.empty:
            # Return basic segment structure without Y-statistics if no data
            segment_details = []
            for i in range(len(breakpoints) - 1):
                segment_details.append({
                    "segment_index": i,
                    "start": breakpoints[i],
                    "end": breakpoints[i + 1],
                    "length": breakpoints[i + 1] - breakpoints[i],
                    "is_mandatory": breakpoints[i] in mandatory_breakpoints or breakpoints[i + 1] in mandatory_breakpoints,
                    "data_point_count": 0,
                    "y_value_min": None,
                    "y_value_max": None,
                    "y_value_avg": None,
                    "y_value_std": None
                })
            return segment_details
        
        try:
            # Extract data arrays (same pattern as visualization)
            x_data = route_data[x_column].values  
            y_data = route_data[y_column].values
            
            # Build gap intervals for filtering (simplified version)
            gap_intervals = []
            if gap_segments:
                for gap in gap_segments:
                    gap_intervals.append((gap['start'], gap['end']))
            
            segment_details = []
            for i in range(len(breakpoints) - 1):
                start_bp, end_bp = breakpoints[i], breakpoints[i + 1]
                
                # Same segment masking pattern as visualization lines 791-795
                segment_mask = (x_data >= start_bp) & (x_data <= end_bp)
                segment_y = y_data[segment_mask]
                
                # Calculate all statistics (enhanced beyond visualization)
                if len(segment_y) > 0:
                    details = {
                        "segment_index": i,
                        "start": float(start_bp),
                        "end": float(end_bp),
                        "length": float(end_bp - start_bp),
                        "is_mandatory": start_bp in mandatory_breakpoints or end_bp in mandatory_breakpoints,
                        "data_point_count": int(len(segment_y)),
                        "y_value_min": float(np.min(segment_y)),
                        "y_value_max": float(np.max(segment_y)),
                        "y_value_avg": float(np.mean(segment_y)),  # Same as visualization calculation
                        "y_value_std": float(np.std(segment_y)) if len(segment_y) > 1 else None
                    }
                else:
                    # No data points in segment (likely gap segment)
                    details = {
                        "segment_index": i,
                        "start": float(start_bp),
                        "end": float(end_bp),
                        "length": float(end_bp - start_bp),
                        "is_mandatory": start_bp in mandatory_breakpoints or end_bp in mandatory_breakpoints,
                        "data_point_count": 0,
                        "y_value_min": None,
                        "y_value_max": None,
                        "y_value_avg": None,
                        "y_value_std": None
                    }
                
                segment_details.append(details)
            
            return segment_details
            
        except Exception as e:
            # Fallback: return basic structure on any error
            print(f"Warning: Error calculating segment statistics: {e}")
            segment_details = []
            for i in range(len(breakpoints) - 1):
                segment_details.append({
                    "segment_index": i,
                    "start": breakpoints[i],
                    "end": breakpoints[i + 1], 
                    "length": breakpoints[i + 1] - breakpoints[i],
                    "is_mandatory": False,
                    "data_point_count": 0,
                    "y_value_min": None,
                    "y_value_max": None,
                    "y_value_avg": None,
                    "y_value_std": None
                })
            return segment_details

    def _build_processing_results(self, result, original_data_by_route=None, route_processing_info=None) -> Dict[str, Any]:
        """
        Build processing results section using unified pareto_points structure.
        
        For single-objective: converts best_solution to single pareto point
        For multi-objective: uses all_solutions as pareto points directly
        """
        
        # Import config system to detect multi-objective methods dynamically  
        from config import get_optimization_method, is_multi_objective_method
        
        # Check if this is a multi-objective method using dynamic config lookup
        is_multi_obj = is_multi_objective_method(result.method_key)
        
        if is_multi_obj and hasattr(result, 'all_solutions') and result.all_solutions:
            # Multi-objective: use ALL solutions from all_solutions (even if just 1!)
            pareto_points = []
            for i, solution in enumerate(result.all_solutions):
                point = {
                    "point_id": i,
                    "objective_values": solution.get('objective_values', [solution.get('fitness', 0.0)])
                }
                
                # Add segmentation info if available
                if 'segmentation' in solution:
                    point["segmentation"] = solution['segmentation']
                elif 'chromosome' in solution:
                    # Convert chromosome to segmentation format
                    breakpoints = solution['chromosome']
                    if isinstance(breakpoints, list) and len(breakpoints) >= 2:
                        segment_lengths = [breakpoints[i+1] - breakpoints[i] for i in range(len(breakpoints)-1)]
                        
                        # Calculate segment details with Y-value statistics
                        segment_details = []
                        if original_data_by_route and route_processing_info:
                            route_data = original_data_by_route.get(result.route_id)
                            x_column = route_processing_info.get('x_column', 'x')
                            y_column = route_processing_info.get('y_column', 'y')
                            gap_segments = result.data_summary.get('gap_analysis', {}).get('gap_segments', [])
                            mandatory_breakpoints = result.mandatory_breakpoints or []
                            
                            segment_details = self._calculate_segment_details(
                                breakpoints, route_data, x_column, y_column, gap_segments, mandatory_breakpoints
                            )
                        
                        point["segmentation"] = {
                            "breakpoints": breakpoints,
                            "segment_count": len(segment_lengths),
                            "segment_lengths": segment_lengths,
                            "total_length": breakpoints[-1] - breakpoints[0] if len(breakpoints) >= 2 else 0.0,
                            "average_segment_length": sum(segment_lengths) / len(segment_lengths) if segment_lengths else 0.0,
                            "segment_details": segment_details
                        }
                
                pareto_points.append(point)
            
            return {"pareto_points": pareto_points}
        else:
            # Single-objective: convert best_solution to single pareto point
            best_sol = result.best_solution
            pareto_point = {
                "point_id": 0,
                "objective_values": [best_sol.get('objective_value', best_sol.get('fitness', 0.0))]
            }
            
            # Add segmentation info
            if 'segmentation' in best_sol:
                pareto_point["segmentation"] = best_sol['segmentation']
            elif 'chromosome' in best_sol:
                # Convert chromosome to segmentation format
                breakpoints = best_sol['chromosome']
                if isinstance(breakpoints, list) and len(breakpoints) >= 2:
                    segment_lengths = [breakpoints[i+1] - breakpoints[i] for i in range(len(breakpoints)-1)]
                    
                    # Calculate segment details with Y-value statistics
                    segment_details = []
                    if original_data_by_route and route_processing_info:
                        route_data = original_data_by_route.get(result.route_id)
                        x_column = route_processing_info.get('x_column', 'x')
                        y_column = route_processing_info.get('y_column', 'y')
                        gap_segments = result.data_summary.get('gap_analysis', {}).get('gap_segments', [])
                        mandatory_breakpoints = result.mandatory_breakpoints or []
                        
                        segment_details = self._calculate_segment_details(
                            breakpoints, route_data, x_column, y_column, gap_segments, mandatory_breakpoints
                        )
                    
                    pareto_point["segmentation"] = {
                        "breakpoints": breakpoints,
                        "segment_count": len(segment_lengths),
                        "segment_lengths": segment_lengths,
                        "total_length": breakpoints[-1] - breakpoints[0] if len(breakpoints) >= 2 else 0.0,
                        "average_segment_length": sum(segment_lengths) / len(segment_lengths) if segment_lengths else 0.0,
                        "segment_details": segment_details
                    }
            
            return {"pareto_points": [pareto_point]}


# ===== CONVENIENCE FUNCTIONS =====

def save_analysis_results(analysis_results: Union['AnalysisResult', List['AnalysisResult']], 
                         output_path: str,
                         **kwargs) -> str:
    """
    Convenience function for saving analysis results with method extensions.
    
    Args:
        analysis_results: AnalysisResult(s) to save
        output_path: Where to save the JSON file
        **kwargs: Additional arguments for ExtensibleJsonResultsManager
        
    Returns:
        str: Path to saved file
    """
    manager = ExtensibleJsonResultsManager()
    return manager.save_analysis_results(analysis_results, output_path, **kwargs)


# Export main classes and functions
__all__ = [
    'AnalysisMethodPlugin',
    'JsonMethodRegistry', 
    'ExtensibleJsonResultsManager',
    'save_analysis_results'
]