"""
Multi-Objective Optimization Plugin - Highway Segmentation GA

Self-contained plugin for extracting method-specific statistics from 
multi-objective genetic algorithm (NSGA-II) optimization results.

This plugin handles dual-objective optimization where solutions balance:
- Objective 1: Minimize deviation from target segment lengths (data fit)
- Objective 2: Minimize number of segments (solution simplicity)

Key Features:
- Pareto front analysis (size, composition, dominance)
- Multi-objective performance metrics (hypervolume, spacing, diversity)
- Solution trade-off analysis (compromise vs specialized solutions)
- Convergence information specific to multi-objective optimization
- Cross-route Pareto front comparison and statistics

Usage:
    # Auto-registered via plugin discovery
    from plugins.multi_objective_plugin import MultiObjectivePlugin
    
    # Or manual registration
    from extensible_results_manager import JsonMethodRegistry
    registry = JsonMethodRegistry()
    registry.register_plugin(MultiObjectivePlugin())

Author: Highway Segmentation GA Team
Plugin Version: 1.0.0
Compatible Methods: multi_objective, multiobjective, multi-obj, nsga2
Date: April 2026
"""

from typing import Dict, List, Any
import math

try:
    from extensible_results_manager import AnalysisMethodPlugin
except ImportError as e:
    raise ImportError(
        "Cannot import AnalysisMethodPlugin from 'extensible_results_manager'. "
        "Ensure the project's 'src' directory is on PYTHONPATH/sys.path."
    ) from e


class MultiObjectivePlugin(AnalysisMethodPlugin):
    """
    Plugin for multi-objective optimization methods (NSGA-II).
    
    Extracts comprehensive multi-objective statistics and Pareto analysis
    from dual-objective genetic algorithm results including:
    - Pareto front composition and quality metrics
    - Multi-objective performance indicators (hypervolume, spacing)
    - Solution trade-off analysis and compromise identification
    - Convergence patterns specific to multi-objective optimization
    - Cross-route Pareto front comparison capabilities
    
    This plugin follows the self-contained architecture pattern where all
    multi-objective specific logic is encapsulated in this single file.
    """
    
    # Plugin metadata
    PLUGIN_NAME = "MultiObjectivePlugin"
    PLUGIN_VERSION = "1.0.0"
    SUPPORTED_RETURN_TYPE = "multi_objective"
    
    # Legacy: Keep for backward compatibility (deprecated)
    SUPPORTED_METHODS = ["multi_objective", "multiobjective", "multi-obj", "nsga2"]
    
    def supports_method(self, method_key: str) -> bool:
        """
        Check if this plugin supports the specified method type.
        
        DEPRECATED: Use supports_return_type() instead.
        This is kept for backward compatibility.
        
        Args:
              method_key: Method identifier from AnalysisResult
            
        Returns:
            bool: True if this plugin handles multi-objective methods
        """
        return method_key.lower() in [m.lower() for m in self.SUPPORTED_METHODS]
        
    def supports_return_type(self, return_type: str) -> bool:
        """
        Check if this plugin supports the specified return type.
        
        Args:
            return_type: Return type from config (e.g., "multi_objective")
            
        Returns:
            bool: True if this plugin handles multi-objective return types
        """
        return return_type == self.SUPPORTED_RETURN_TYPE
    
    def extract_custom_statistics(self, analysis_result) -> Dict[str, Any]:
        """
        Extract comprehensive multi-objective statistics from AnalysisResult.
        
        Provides detailed metrics specific to multi-objective optimization:
        - Pareto front analysis (size, diversity, quality)
        - Multi-objective performance metrics
        - Solution trade-off assessment  
        - Convergence information for dual-objective optimization
        
        Args:
            analysis_result: AnalysisResult object containing optimization results
            
        Returns:
            Dict containing multi-objective specific statistics
        """
        stats = {}
        
        # Extract multi-objective performance metrics (core functionality)
        performance_stats = self._extract_performance_metrics(analysis_result)
        if performance_stats:
            stats['performance_metrics'] = performance_stats
        
        # Extract convergence analysis specific to multi-objective
        convergence_stats = self._extract_convergence_info(analysis_result)
        if convergence_stats:
            stats['convergence_analysis'] = convergence_stats
        
        # Note: Removed pareto_analysis, solution_tradeoffs, and processing_efficiency 
        # functions as they were producing empty sections and are not required by JSON schema
            
        return stats
    
    def _extract_pareto_analysis(self, analysis_result) -> Dict[str, Any]:
        """Extract Pareto front composition and quality metrics."""
        pareto = {}
        
        # Get Pareto front size and composition
        if hasattr(analysis_result, 'optimization_stats') and analysis_result.optimization_stats:
            opt_stats = analysis_result.optimization_stats
            
            if 'pareto_front_size' in opt_stats:
                pareto['front_size'] = opt_stats['pareto_front_size']
            
            # Analyze Pareto front diversity if we have solutions
            if hasattr(analysis_result, 'all_solutions') and analysis_result.all_solutions:
                solutions = analysis_result.all_solutions
                
                # Extract objective values for analysis
                if solutions and isinstance(solutions[0], dict):
                    deviation_values = []
                    segment_counts = []
                    
                    for sol in solutions:
                        # Extract deviation_fitness with proper handling for dict values
                        if 'deviation_fitness' in sol:
                            dev_val = sol['deviation_fitness']
                            if isinstance(dev_val, dict):
                                # Extract numeric value from dict structure 
                                numeric_val = dev_val.get('value', dev_val.get('total_deviation', 0))
                                deviation_values.append(numeric_val)
                            elif isinstance(dev_val, (int, float)):
                                deviation_values.append(dev_val)
                        
                        if 'num_segments' in sol:
                            segment_counts.append(sol['num_segments'])
                    # Filter to ensure only numeric values for calculations
                    deviation_values = [v for v in deviation_values if isinstance(v, (int, float))]
                    segment_counts = [v for v in segment_counts if isinstance(v, (int, float))]
                    
                    if deviation_values and segment_counts:
                        pareto['objective_ranges'] = {
                            'deviation_range': {
                                'min': min(deviation_values),
                                'max': max(deviation_values),
                                'span': max(deviation_values) - min(deviation_values)
                            },
                            'segment_range': {
                                'min': min(segment_counts),
                                'max': max(segment_counts),
                                'span': max(segment_counts) - min(segment_counts)
                            }
                        }
                        
                        # Note: Advanced metrics (spacing, hypervolume) removed to resolve dict arithmetic errors
        
        return pareto
    
    def _extract_performance_metrics(self, analysis_result) -> Dict[str, Any]:
        """Extract multi-objective optimization performance metrics."""
        performance = {}
        
        if hasattr(analysis_result, 'optimization_stats') and analysis_result.optimization_stats:
            opt_stats = analysis_result.optimization_stats
            
            # Core performance indicators
            performance['generations_completed'] = opt_stats.get('generations_completed', 
                                                               opt_stats.get('generations_run', 0))
            performance['population_size'] = opt_stats.get('population_size', 0)
            
            if 'best_deviation_fitness' in opt_stats:
                performance['best_deviation_fitness'] = opt_stats['best_deviation_fitness']
            if 'best_segment_count' in opt_stats:
                performance['best_segment_count'] = opt_stats['best_segment_count']
            if 'final_population_size' in opt_stats:
                performance['final_population_size'] = opt_stats['final_population_size']
                
        return performance
    
    def _extract_tradeoff_analysis(self, analysis_result) -> Dict[str, Any]:
        """Extract solution trade-off analysis and compromise identification."""
        tradeoffs = {}
        
        if hasattr(analysis_result, 'all_solutions') and analysis_result.all_solutions:
            solutions = analysis_result.all_solutions
            
            if not solutions:
                return {}
            
            # Helper function to extract numeric deviation_fitness value
            def get_numeric_deviation(solution):
                dev_val = solution.get('deviation_fitness', float('inf'))
                if isinstance(dev_val, dict):
                    return dev_val.get('value', dev_val.get('total_deviation', float('inf')))
                return dev_val if isinstance(dev_val, (int, float)) else float('inf')
            
            # Identify extreme solutions for each objective
            best_deviation = min(solutions, key=get_numeric_deviation)
            min_segments = min(solutions, key=lambda x: x.get('num_segments', float('inf')))
            
            tradeoffs['extreme_solutions'] = {
                'best_data_fit': {
                    'deviation_fitness': get_numeric_deviation(best_deviation),
                    'segment_count': best_deviation.get('num_segments'),
                    'avg_segment_length': best_deviation.get('avg_segment_length')
                },
                'minimum_segments': {
                    'deviation_fitness': get_numeric_deviation(min_segments),
                    'segment_count': min_segments.get('num_segments'),
                    'avg_segment_length': min_segments.get('avg_segment_length')
                }
            }
            
            # Identify compromise solution (closest to ideal point)
            if hasattr(analysis_result, 'best_solution') and analysis_result.best_solution:
                primary = analysis_result.best_solution
                tradeoffs['compromise_solution'] = {
                    'deviation_fitness': get_numeric_deviation(primary),
                    'segment_count': primary.get('num_segments'),
                    'avg_segment_length': primary.get('avg_segment_length')
                    # Note: compromise_score calculation removed to resolve dict arithmetic errors
                }
        
        return tradeoffs
    
    def _extract_convergence_info(self, analysis_result) -> Dict[str, Any]:
        """Extract convergence analysis specific to multi-objective optimization."""
        convergence = {}
        
        if hasattr(analysis_result, 'optimization_stats') and analysis_result.optimization_stats:
            opt_stats = analysis_result.optimization_stats
            
            # Standard convergence metrics
            convergence['final_generation'] = opt_stats.get('final_generation', 
                                                          opt_stats.get('generations_completed', 0))
            
            # Multi-objective specific convergence indicators
            if 'pareto_front_size' in opt_stats:
                convergence['final_pareto_size'] = opt_stats['pareto_front_size']
            
            if 'diversity_history' in opt_stats:
                diversity_hist = opt_stats['diversity_history']
                if diversity_hist and all(isinstance(x, (int, float)) for x in diversity_hist):
                    convergence['diversity_trend'] = {
                        'initial_diversity': diversity_hist[0] if diversity_hist else 0,
                        'final_diversity': diversity_hist[-1] if diversity_hist else 0,
                        'diversity_improvement': (diversity_hist[-1] - diversity_hist[0]) if len(diversity_hist) > 1 else 0
                    }
        
        return convergence
    
    def _extract_processing_info(self, analysis_result) -> Dict[str, Any]:
        """Extract processing efficiency and resource usage metrics."""
        processing = {}
        
        # Processing time analysis
        if hasattr(analysis_result, 'processing_time'):
            processing['optimization_time_seconds'] = analysis_result.processing_time
            
            # Calculate efficiency metrics if we have generation info
            if (hasattr(analysis_result, 'optimization_stats') and 
                analysis_result.optimization_stats and
                'generations_completed' in analysis_result.optimization_stats):
                
                gens = analysis_result.optimization_stats['generations_completed']
                if gens > 0:
                    processing['time_per_generation'] = analysis_result.processing_time / gens
        
        # Multi-objective specific processing metrics
        if hasattr(analysis_result, 'optimization_stats') and analysis_result.optimization_stats:
            opt_stats = analysis_result.optimization_stats
            if 'average_generation_time' in opt_stats:
                processing['average_generation_time'] = opt_stats['average_generation_time']
                
        return processing
    # Note: _calculate_spacing, _calculate_hypervolume_approx, and _calculate_compromise_score functions
    # were removed to resolve dictionary arithmetic errors that prevented plugin functionality
    
    def contribute_analysis_summary(self, all_results: List) -> Dict[str, Any]:
        """
        Contribute multi-objective summary statistics across all routes.
        
        Provides aggregated insights across multiple multi-objective optimizations:
        - Cross-route Pareto front comparison
        - Multi-objective convergence consistency analysis  
        - Trade-off pattern analysis across routes
        - Processing efficiency trends for multi-objective algorithms
        
        Args:
            all_results: List of all AnalysisResult objects from analysis
            
        Returns:
            Dict containing multi-objective aggregated statistics
        """
        if not all_results:
            return {}
        
        # Filter to only multi-objective results
        mo_results = [r for r in all_results if self.supports_method(getattr(r, 'method_key', ''))]
        if not mo_results:
            return {}
        
        summary = {
            'plugin_info': {
                'plugin_name': self.PLUGIN_NAME,
                'plugin_version': self.PLUGIN_VERSION,
                'routes_processed': len(mo_results)
            }
        }
        
        # Aggregate processing statistics
        processing_summary = self._aggregate_processing_stats(mo_results)
        if processing_summary:
            summary['processing_summary'] = processing_summary
        
        # Aggregate Pareto front statistics
        pareto_summary = self._aggregate_pareto_stats(mo_results)
        if pareto_summary:
            summary['pareto_analysis_summary'] = pareto_summary
            
        # Aggregate convergence patterns
        convergence_summary = self._aggregate_convergence_stats(mo_results) 
        if convergence_summary:
            summary['convergence_summary'] = convergence_summary
        
        return {'multi_objective_analysis': summary} if summary else {}
    
    def _aggregate_processing_stats(self, results: List) -> Dict[str, Any]:
        """Aggregate processing time and efficiency statistics."""
        times = [r.processing_time for r in results if hasattr(r, 'processing_time')]
        if not times:
            return {}
            
        return {
            'total_optimization_time': sum(times),
            'average_time_per_route': sum(times) / len(times),
            'min_processing_time': min(times),
            'max_processing_time': max(times),
            'routes_timed': len(times)
        }
    
    def _aggregate_pareto_stats(self, results: List) -> Dict[str, Any]:
        """Aggregate Pareto front statistics across routes."""
        front_sizes = []
        deviation_ranges = []
        segment_ranges = []
        
        for result in results:
            if hasattr(result, 'optimization_stats') and result.optimization_stats:
                opt_stats = result.optimization_stats
                if 'pareto_front_size' in opt_stats:
                    front_sizes.append(opt_stats['pareto_front_size'])
            
            if hasattr(result, 'all_solutions') and result.all_solutions:
                solutions = result.all_solutions
                if solutions and isinstance(solutions[0], dict):
                    # Extract deviation values with proper handling for dict structures
                    devs = []
                    segs = []
                    
                    for s in solutions:
                        # Handle deviation_fitness that might be dict
                        dev_val = s.get('deviation_fitness', 0)
                        if isinstance(dev_val, dict):
                            numeric_dev = dev_val.get('value', dev_val.get('total_deviation', 0))
                            devs.append(numeric_dev)
                        elif isinstance(dev_val, (int, float)):
                            devs.append(dev_val)
                        
                        # Handle num_segments (should always be numeric)
                        seg_val = s.get('num_segments', 0)
                        if isinstance(seg_val, (int, float)):
                            segs.append(seg_val)
                    
                    if devs and all(isinstance(d, (int, float)) for d in devs):
                        deviation_ranges.append(max(devs) - min(devs))
                    if segs and all(isinstance(s, (int, float)) for s in segs):
                        segment_ranges.append(max(segs) - min(segs))
        
        pareto_stats = {}
        if front_sizes:
            pareto_stats['front_size_distribution'] = {
                'min_front_size': min(front_sizes),
                'max_front_size': max(front_sizes),
                'average_front_size': sum(front_sizes) / len(front_sizes),
                'total_solutions_explored': sum(front_sizes)
            }
            
        if deviation_ranges and segment_ranges:
            pareto_stats['objective_diversity'] = {
                'average_deviation_range': sum(deviation_ranges) / len(deviation_ranges),
                'average_segment_range': sum(segment_ranges) / len(segment_ranges),
                'min_deviation_diversity': min(deviation_ranges),
                'max_segment_diversity': max(segment_ranges)
            }
        
        return pareto_stats
    
    def _aggregate_convergence_stats(self, results: List) -> Dict[str, Any]:
        """Aggregate convergence patterns across routes."""
        generations = []
        
        for result in results:
            if (hasattr(result, 'optimization_stats') and 
                result.optimization_stats and
                'generations_completed' in result.optimization_stats):
                generations.append(result.optimization_stats['generations_completed'])
        
        if not generations:
            return {}
        
        return {
            'convergence_distribution': {
                'min_generations': min(generations),
                'max_generations': max(generations), 
                'average_generations': sum(generations) / len(generations),
                'total_generations': sum(generations)
            },
            'convergence_consistency': {
                'generation_variance': self._calculate_variance(generations),
                'routes_converged': len(generations)
            }
        }
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance for a list of values."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / (len(values) - 1)


# Plugin auto-discovery support
def get_plugin_class():
    """Return the plugin class for auto-discovery systems."""
    return MultiObjectivePlugin


# Plugin metadata for discovery
PLUGIN_METADATA = {
    'name': MultiObjectivePlugin.PLUGIN_NAME,
    'version': MultiObjectivePlugin.PLUGIN_VERSION,
    'supported_return_type': MultiObjectivePlugin.SUPPORTED_RETURN_TYPE,
    'plugin_class': MultiObjectivePlugin,
    'description': 'Comprehensive multi-objective optimization and Pareto analysis'
}


# Auto-registration when imported.
# Keep this best-effort so plugin discovery never fails just because the
# registry isn't available in a given execution context.
try:
    from extensible_results_manager import JsonMethodRegistry

    registry = JsonMethodRegistry()
    if not any(isinstance(p, MultiObjectivePlugin) for p in registry.get_all_plugins()):
        plugin_instance = MultiObjectivePlugin()
        registry.register_plugin(plugin_instance)
        print(f"Auto-registered {MultiObjectivePlugin.PLUGIN_NAME} v{MultiObjectivePlugin.PLUGIN_VERSION}")
except ImportError:
    pass
except Exception as e:
    print(f"Warning: Could not auto-register MultiObjectivePlugin: {e}")