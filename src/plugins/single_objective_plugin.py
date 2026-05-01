"""
Single-Objective Optimization Plugin - Highway Segmentation GA

Self-contained plugin for extracting method-specific statistics from 
single-objective genetic algorithm optimization results.

This plugin demonstrates the extensible architecture pattern where each
optimization method is completely self-contained with its own:
- Custom statistics extraction logic
- Method-specific data processing  
- Analysis summary contributions
- Independent testing and validation

Key Features:
- Basic performance metrics (fitness, generations, population size)
- Solution quality assessment (segment count, total length)
- Convergence information (final generation, improvement tracking)
- Cross-route aggregation and summary statistics
- Processing time and efficiency metrics

Usage:
    # Auto-registered via plugin discovery
    from plugins.single_objective_plugin import SingleObjectivePlugin
    
    # Or manual registration
    from extensible_results_manager import JsonMethodRegistry
    registry = JsonMethodRegistry()
    registry.register_plugin(SingleObjectivePlugin())

Author: Highway Segmentation GA Team
Plugin Version: 1.0.0
Compatible Methods: single_objective, singleobjective, single-obj
Date: April 2026
"""

from typing import Dict, List, Any

try:
    from extensible_results_manager import AnalysisMethodPlugin
except ImportError as e:
    raise ImportError(
        "Cannot import AnalysisMethodPlugin from 'extensible_results_manager'. "
        "Ensure the project's 'src' directory is on PYTHONPATH/sys.path."
    ) from e


class SingleObjectivePlugin(AnalysisMethodPlugin):
    """
    Plugin for single-objective optimization methods.
    
    Extracts comprehensive performance statistics and convergence information
    from single-objective genetic algorithm results including:
    - Optimization performance metrics
    - Solution quality assessment 
    - Convergence analysis
    - Processing efficiency statistics
    - Cross-route aggregation capabilities
    
    This plugin follows the self-contained architecture pattern where all
    single-objective specific logic is encapsulated in this single file.
    """
    
    # Plugin metadata
    PLUGIN_NAME = "SingleObjectivePlugin"
    PLUGIN_VERSION = "1.0.0"
    SUPPORTED_RETURN_TYPE = "single_objective"
    
    # Legacy: Keep for backward compatibility (deprecated)
    SUPPORTED_METHODS = ["single_objective", "singleobjective", "single-obj", "constrained"]
    
    def supports_method(self, method_key: str) -> bool:
        """
        Check if this plugin supports the specified method type.
        
        DEPRECATED: Use supports_return_type() instead.
        This is kept for backward compatibility.
        
        Args:
            method_key: Method identifier from AnalysisResult
            
        Returns:
            bool: True if this plugin handles single-objective methods
        """
        return method_key.lower() in [m.lower() for m in self.SUPPORTED_METHODS]
        
    def supports_return_type(self, return_type: str) -> bool:
        """
        Check if this plugin supports the specified return type.
        
        Args:
            return_type: Return type from config (e.g., "single_objective")
            
        Returns:
            bool: True if this plugin handles single-objective return types
        """
        return return_type == self.SUPPORTED_RETURN_TYPE
    
    def extract_custom_statistics(self, analysis_result) -> Dict[str, Any]:
        """
        Extract comprehensive single-objective statistics from AnalysisResult.
        
        Provides detailed metrics specific to single-objective optimization:
        - Performance metrics (fitness, convergence, efficiency)
        - Solution quality (segment analysis, constraint satisfaction)
        - Processing statistics (timing, resource usage)
        - Method-specific diagnostics
        
        Args:
            analysis_result: AnalysisResult object containing optimization results
            
        Returns:
            Dict containing single-objective specific statistics
        """


        stats = {}
        
        # Extract optimization performance metrics
        performance_stats = self._extract_performance_metrics(analysis_result)
        if performance_stats:
            stats['performance_metrics'] = performance_stats
        
        # Extract solution quality assessment
        solution_stats = self._extract_solution_quality(analysis_result)  
        if solution_stats:
            stats['solution_quality'] = solution_stats
        
        # Extract convergence analysis
        convergence_stats = self._extract_convergence_info(analysis_result)
        if convergence_stats:
            stats['convergence_analysis'] = convergence_stats
        
        # Extract processing efficiency metrics
        processing_stats = self._extract_processing_info(analysis_result)
        if processing_stats:
            stats['processing_efficiency'] = processing_stats
            
        return stats
    
    def _extract_performance_metrics(self, analysis_result) -> Dict[str, Any]:
        """Extract basic optimization performance metrics."""
        performance = {}
        
        if hasattr(analysis_result, 'optimization_stats') and analysis_result.optimization_stats:
            opt_stats = analysis_result.optimization_stats
            
            # Core performance indicators
            if 'final_fitness' in opt_stats or 'best_fitness' in opt_stats:
                performance['best_fitness'] = opt_stats.get('final_fitness', opt_stats.get('best_fitness'))
            if 'generations_run' in opt_stats or 'generations_completed' in opt_stats:
                performance['generations_completed'] = opt_stats.get('generations_run', opt_stats.get('generations_completed'))
            if 'population_size' in opt_stats:
                performance['population_size'] = opt_stats['population_size']
            if 'total_evaluations' in opt_stats:
                performance['total_evaluations'] = opt_stats['total_evaluations']
                
        return performance
    
    def _extract_solution_quality(self, analysis_result) -> Dict[str, Any]:
        """Extract solution quality and constraint satisfaction metrics."""
        quality = {}
        
        if hasattr(analysis_result, 'best_solution') and analysis_result.best_solution:
            best_sol = analysis_result.best_solution
            
            # Basic solution characteristics
            if 'segments' in best_sol and best_sol['segments']:
                segments = best_sol['segments']
                quality['segment_count'] = len(segments)
                
                # Segment length analysis
                if all('length' in seg for seg in segments):
                    lengths = [seg['length'] for seg in segments]
                    quality['segment_length_stats'] = {
                        'min_length': min(lengths),
                        'max_length': max(lengths), 
                        'avg_length': sum(lengths) / len(lengths),
                        'total_length': sum(lengths)
                    }
            
            # Fitness and constraint satisfaction
            if 'fitness' in best_sol:
                quality['solution_fitness'] = best_sol['fitness']
            if 'constraint_violations' in best_sol:
                quality['constraint_violations'] = best_sol['constraint_violations']
            if 'feasible' in best_sol:
                quality['is_feasible'] = best_sol['feasible']
                
        return quality
    
    def _extract_convergence_info(self, analysis_result) -> Dict[str, Any]:
        """Extract convergence analysis and improvement tracking."""
        convergence = {}
        
        if hasattr(analysis_result, 'optimization_stats') and analysis_result.optimization_stats:
            opt_stats = analysis_result.optimization_stats
            
            # Convergence indicators with fallbacks
            if 'final_generation' in opt_stats or 'generations_completed' in opt_stats:
                convergence['final_generation'] = opt_stats.get('final_generation', opt_stats.get('generations_completed'))
            if 'improvement_generations' in opt_stats:
                convergence['generations_with_improvement'] = opt_stats['improvement_generations']
            if 'stagnation_count' in opt_stats:
                convergence['stagnation_generations'] = opt_stats['stagnation_count']
            if 'early_termination' in opt_stats:
                convergence['early_termination'] = opt_stats['early_termination']
            if 'convergence_reason' in opt_stats:
                convergence['termination_reason'] = opt_stats['convergence_reason']
                
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
                'generations_run' in analysis_result.optimization_stats):
                
                gens = analysis_result.optimization_stats['generations_run']
                if gens > 0:
                    processing['time_per_generation'] = analysis_result.processing_time / gens
        
        # Memory and cache usage (if available)
        if hasattr(analysis_result, 'optimization_stats') and analysis_result.optimization_stats:
            opt_stats = analysis_result.optimization_stats
            if 'cache_hits' in opt_stats:
                processing['cache_hits'] = opt_stats['cache_hits']
            if 'cache_misses' in opt_stats:
                processing['cache_misses'] = opt_stats['cache_misses']
            if 'memory_usage_mb' in opt_stats:
                processing['peak_memory_mb'] = opt_stats['memory_usage_mb']
                
        return processing
    
    def contribute_analysis_summary(self, all_results: List) -> Dict[str, Any]:
        """
        Contribute single-objective summary statistics across all routes.
        
        Provides aggregated insights across multiple single-objective optimizations:
        - Cross-route performance comparison
        - Convergence consistency analysis  
        - Solution quality distribution
        - Processing efficiency trends
        
        Args:
            all_results: List of all AnalysisResult objects from analysis
            
        Returns:
            Dict containing single-objective aggregated statistics
        """
        if not all_results:
            return {}
        
        # Filter to only single-objective results
        so_results = [r for r in all_results if self.supports_method(getattr(r, 'method_key', ''))]
        if not so_results:
            return {}
        
        summary = {
            'plugin_info': {
                'plugin_name': self.PLUGIN_NAME,
                'plugin_version': self.PLUGIN_VERSION,
                'routes_processed': len(so_results)
            }
        }
        
        # Aggregate processing statistics
        processing_summary = self._aggregate_processing_stats(so_results)
        if processing_summary:
            summary['processing_summary'] = processing_summary
        
        # Aggregate solution quality metrics
        quality_summary = self._aggregate_quality_stats(so_results)
        if quality_summary:
            summary['solution_quality_summary'] = quality_summary
            
        # Aggregate convergence patterns
        convergence_summary = self._aggregate_convergence_stats(so_results) 
        if convergence_summary:
            summary['convergence_summary'] = convergence_summary
        
        return {'single_objective_analysis': summary} if summary else {}
    
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
    
    def _aggregate_quality_stats(self, results: List) -> Dict[str, Any]:
        """Aggregate solution quality metrics across routes."""
        segment_counts = []
        fitness_values = []
        
        for result in results:
            if hasattr(result, 'best_solution') and result.best_solution:
                best_sol = result.best_solution
                if 'segments' in best_sol and best_sol['segments']:
                    segment_counts.append(len(best_sol['segments']))
                if 'fitness' in best_sol:
                    fitness_values.append(best_sol['fitness'])
        
        quality_stats = {}
        if segment_counts:
            quality_stats['segment_distribution'] = {
                'min_segments': min(segment_counts),
                'max_segments': max(segment_counts),
                'average_segments': sum(segment_counts) / len(segment_counts),
                'total_segments_generated': sum(segment_counts)
            }
            
        if fitness_values:
            quality_stats['fitness_distribution'] = {
                'best_fitness_overall': min(fitness_values),  # Assuming minimization
                'worst_fitness': max(fitness_values),
                'average_fitness': sum(fitness_values) / len(fitness_values),
                'fitness_variance': self._calculate_variance(fitness_values)
            }
        
        return quality_stats
    
    def _aggregate_convergence_stats(self, results: List) -> Dict[str, Any]:
        """Aggregate convergence patterns across routes."""
        generations = []
        
        for result in results:
            if (hasattr(result, 'optimization_stats') and 
                result.optimization_stats and
                'generations_run' in result.optimization_stats):
                generations.append(result.optimization_stats['generations_run'])
        
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
    return SingleObjectivePlugin


# Plugin metadata for discovery
PLUGIN_METADATA = {
    'name': SingleObjectivePlugin.PLUGIN_NAME,
    'version': SingleObjectivePlugin.PLUGIN_VERSION,
    'supported_return_type': SingleObjectivePlugin.SUPPORTED_RETURN_TYPE,
    'plugin_class': SingleObjectivePlugin,
    'description': 'Comprehensive single-objective optimization statistics extraction'
}


# Auto-registration when imported.
# Keep this best-effort so plugin discovery never fails just because the
# registry isn't available in a given execution context.
try:
    from extensible_results_manager import JsonMethodRegistry

    registry = JsonMethodRegistry()
    if not any(isinstance(p, SingleObjectivePlugin) for p in registry.get_all_plugins()):
        plugin_instance = SingleObjectivePlugin()
        registry.register_plugin(plugin_instance)
        print(f"Auto-registered {SingleObjectivePlugin.PLUGIN_NAME} v{SingleObjectivePlugin.PLUGIN_VERSION}")
except ImportError:
    pass
except Exception as e:
    print(f"Warning: Could not auto-register SingleObjectivePlugin: {e}")