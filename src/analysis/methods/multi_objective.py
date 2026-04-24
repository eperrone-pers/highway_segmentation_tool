"""
Multi-Objective (NSGA-II) Analysis Method for Highway Segmentation GA

This module implements the NSGA-II (Non-dominated Sorting Genetic Algorithm II) approach
for multi-objective highway segmentation optimization, finding Pareto-optimal trade-offs
between data accuracy (deviation fitness) and segmentation simplicity (segment count).

Key Features:
- Non-dominated sorting with dominance hierarchy 
- Crowding distance for diversity maintenance
- Pareto front generation with multiple optimal solutions
- Trade-off analysis between competing objectives
- Configuration integration with MULTI_OBJECTIVE_NSGA2_PARAMETERS

Author: Highway Segmentation GA Team  
Phase: 1.95.4 - Multi-Objective Method Extraction
"""

import time
import random
from typing import Any, Dict, List, Optional, Callable, Tuple, Union
import numpy as np

from ..base import AnalysisMethodBase, AnalysisResult 
from ..utils.ga_utilities import (
    nsga2_tournament_selection, fast_non_dominated_sort, calculate_crowding_distance,
    crossover_with_retries, mutation_with_retries, analyze_population_diversity
)

# Import GA class and configuration
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from analysis.utils.genetic_algorithm import HighwaySegmentGA
from config import get_optimization_method
from logger import create_logger


class MultiObjectiveMethod(AnalysisMethodBase):
    """
    NSGA-II multi-objective genetic algorithm analysis method.
    
    Simultaneously optimizes two competing objectives:
    1. Data fitness (minimize deviation between actual data and segment averages)
    2. Segmentation simplicity (minimize number of segments)
    
    Returns a Pareto front of non-dominated solutions representing optimal trade-offs
    between data accuracy and complexity, allowing users to select solutions based
    on their specific requirements and constraints.
    """
    
    @property
    def method_name(self) -> str:
        """Human-readable method name for GUI display."""
        return "Multi-Objective NSGA-II"
    
    @property 
    def method_key(self) -> str:
        """Method key for result handling and export."""
        return "multi"
        
    def run_analysis(self, 
                    data: Any,
                    route_id: str,
                    x_column: str, 
                    y_column: str,
                    gap_threshold: float,
                    **kwargs) -> AnalysisResult:
        """
        Execute NSGA-II multi-objective optimization.
        
        Args:
            data: RouteAnalysis object with highway data
            route_id: Route identifier for this analysis
            x_column: Column name for x-axis values (e.g., 'milepoint')  
            y_column: Column name for y-axis values (optimization target)
            gap_threshold: Data gap detection threshold
            **kwargs: Method-specific parameters including:
                - min_length: Minimum segment length constraint
                - max_length: Maximum segment length constraint
                - population_size: Individuals per generation (default from config)
                - num_generations: Evolution iterations (default from config)
                - crossover_rate: Crossover probability (default from config)
                - mutation_rate: Mutation probability (default from config)
                - cache_clear_interval: Generations between cache clears
                - enable_performance_stats: Track detailed metrics
                - Segment-level caching: Always enabled for performance
                - log_callback: Progress logging function
                - stop_callback: User stop request function
                
        Returns:
            AnalysisResult with Pareto front in all_solutions and best compromise in best_solution
        """
        if not hasattr(data, 'route_data'):
            raise TypeError(
                "MultiObjectiveMethod.run_analysis expects a RouteAnalysis object (with .route_data). "
                "Use analyze_route_gaps(...) to build one from a DataFrame."
            )

        # Get method configuration and default parameters
        method_config = get_optimization_method('multi')
        if not method_config:
            raise ValueError("Multi-objective method configuration not found")
            
        # Extract default parameter values from config
        param_defaults = {param.name: param.default_value for param in method_config.parameters}
        
        # Extract method-specific parameters with proper config defaults
        min_length = kwargs.get('min_length', param_defaults['min_length'])
        max_length = kwargs.get('max_length', param_defaults['max_length'])
        population_size = kwargs.get('population_size', param_defaults['population_size'])
        num_generations = kwargs.get('num_generations', param_defaults['num_generations'])
        crossover_rate = kwargs.get('crossover_rate', param_defaults['crossover_rate'])
        mutation_rate = kwargs.get('mutation_rate', param_defaults['mutation_rate'])
        cache_clear_interval = kwargs.get('cache_clear_interval', param_defaults['cache_clear_interval'])
        enable_performance_stats = kwargs.get('enable_performance_stats', param_defaults['enable_performance_stats'])
        log_callback = kwargs.get('log_callback', None)
        stop_callback = kwargs.get('stop_callback', None)
        
        # Validate parameters
        self.validate_parameters(
            min_length=min_length,
            max_length=max_length,
            population_size=population_size,
            num_generations=num_generations,
            gap_threshold=gap_threshold
        )
        
        start_time = time.time()
        # gap_threshold now comes as direct parameter (framework level)
        # Segment caching always enabled for performance
        log_callback = kwargs.get('log_callback', None)
        stop_callback = kwargs.get('stop_callback', None)
        
        # Create logger instance
        logger = create_logger(callback=log_callback)
        log = logger.log
        
        log("Initializing NSGA-II multi-objective optimization...")
        log(f"Objectives: Minimize deviation (data fit) vs. Maximize average segment length")
        log(f"Parameters: {population_size} individuals, {num_generations} generations")
        
        # Initialize genetic algorithm (RouteAnalysis-only contract)
        ga = HighwaySegmentGA(data, x_column, y_column, min_length=min_length, max_length=max_length,
                            population_size=population_size, crossover_rate=crossover_rate, mutation_rate=mutation_rate, 
                            gap_threshold=gap_threshold)  # Pass explicit parameters
        
        # Enable segment caching for improved performance 
        ga.enable_segment_cache_mode(True)
        
        # Generate initial population
        log("Generating diverse initial population...")
        population = ga.generate_diverse_initial_population()
        
        # Validate and fix initial population
        population = [ga._enforce_constraints(chrom) if not ga.validate_chromosome(chrom) else chrom 
                     for chrom in population]
        
        log(f"[OK] Generated {len(population)} valid chromosomes")
        
        # Initialize tracking variables
        pareto_history = []
        generation_times = [] if enable_performance_stats else None
        diversity_history = [] if enable_performance_stats else None
        
        log("\\nStarting NSGA-II multi-objective evolution...")
        log("Progress: [" + "-" * 50 + "]")
        
        # Main NSGA-II evolution loop
        for generation in range(num_generations):
            generation_start = time.time()
            
            # Check for user stop request
            if stop_callback and stop_callback():
                log("\\nOptimization stopped by user request")
                break
            
            # Evaluate population with multi-objective fitness (done by ga.fast_non_dominated_sort)
            
            # NSGA-II core: Non-dominated sorting and crowding distance
            fronts, fitness_values = ga.fast_non_dominated_sort(population)
            
            # Calculate crowding distances for each front
            crowding_distances = {}
            for front_idx, front in enumerate(fronts):
                distances = ga.calculate_crowding_distance(front, fitness_values)
                for sol_idx, distance in zip(front, distances):
                    crowding_distances[sol_idx] = distance
            
            # Progress reporting
            if generation % 4 == 0:
                progress = int((generation / num_generations) * 50)
                progress_bar = "=" * progress + "-" * (50 - progress)
                log(f"Progress: [{progress_bar}] {generation}/{num_generations} generations")
            
            # Periodic detailed reporting
            if generation % 50 == 0 and generation > 0:
                pareto_front = fronts[0] if fronts else []
                if pareto_front:
                    best_deviation = -max(fitness_values[i][0] for i in pareto_front)  # Convert -deviation back to +deviation
                    best_avg_length = max(fitness_values[i][1] for i in pareto_front)  # Already positive avg_length
                    log(f"\nGen {generation}: Pareto front size = {len(pareto_front)}")
                    log(f"  Best deviation: {best_deviation:.6f}, Best avg segment length: {best_avg_length:.2f} miles")
                    
                    # Clean up diversity stats formatting
                    diversity_raw = analyze_population_diversity(population)
                    diversity_clean = {
                        'min_segments': int(diversity_raw['min_segments']),
                        'max_segments': int(diversity_raw['max_segments']),
                        'avg_segments': round(float(diversity_raw['avg_segments']), 2),
                        'std_segments': round(float(diversity_raw['std_segments']), 2),
                        'unique_segment_counts': int(diversity_raw['unique_segment_counts']),
                        'segment_range': int(diversity_raw['segment_range'])
                    }
                    log(f"  Population diversity (segment counts): {diversity_clean}")
            
            # Store Pareto front for history
            if fronts:
                current_pareto = [(population[i], fitness_values[i]) for i in fronts[0]]
                pareto_history.append(current_pareto)
            
            # Performance tracking
            if enable_performance_stats:
                generation_time = time.time() - generation_start
                generation_times.append(generation_time)
                diversity_stats = analyze_population_diversity(population)
                diversity_history.append(diversity_stats)
            
            # Create next generation using NSGA-II selection
            if generation < num_generations - 1:  # Skip on last generation
                # Tournament selection based on dominance and crowding distance
                mating_pool = nsga2_tournament_selection(
                    population, fronts, fitness_values, crowding_distances, population_size
                )
                
                # Generate offspring through crossover and mutation
                offspring = []
                for i in range(0, population_size, 2):
                    parent1 = mating_pool[i % len(mating_pool)]
                    parent2 = mating_pool[(i + 1) % len(mating_pool)]
                    
                    # Crossover
                    if random.random() < crossover_rate:
                        child1, child2 = crossover_with_retries(
                            parent1, parent2, ga.x_data, ga.mandatory_breakpoints, ga.validate_chromosome
                        )
                        if child1 and child2:
                            offspring.extend([child1, child2])
                        else:
                            offspring.extend([parent1, parent2])  # Fallback to parents
                    else:
                        offspring.extend([parent1, parent2])  # No crossover
                
                # Apply mutations
                for i in range(len(offspring)):
                    if random.random() < mutation_rate:
                        mutated = mutation_with_retries(
                            offspring[i], ga.x_data, ga.mandatory_breakpoints, ga.validate_chromosome
                        )
                        if mutated:
                            offspring[i] = mutated
                
                # Ensure all offspring are valid
                offspring = [ga._enforce_constraints(chrom) if not ga.validate_chromosome(chrom) else chrom 
                           for chrom in offspring]
                
                # Environmental selection: Combine population + offspring, select best
                combined_population = population + offspring  
                
                # Non-dominated sort on combined population  
                combined_fronts, combined_fitness = ga.fast_non_dominated_sort(combined_population)
                
                # Calculate crowding distances for combined population
                combined_crowding = {}
                for front_idx, front in enumerate(combined_fronts):
                    distances = ga.calculate_crowding_distance(front, combined_fitness)
                    for sol_idx, distance in zip(front, distances):
                        combined_crowding[sol_idx] = distance
                
                # Select next generation population
                next_population = []
                for front in combined_fronts:
                    if len(next_population) + len(front) <= population_size:
                        # Add entire front
                        next_population.extend([combined_population[i] for i in front])
                    else:
                        # Partial front selection by crowding distance
                        remaining = population_size - len(next_population)
                        front_with_crowding = [(i, combined_crowding[i]) for i in front]
                        front_with_crowding.sort(key=lambda x: x[1], reverse=True)  # Higher crowding = better
                        
                        for i in range(remaining):
                            next_population.append(combined_population[front_with_crowding[i][0]])
                        break
                
                population = next_population
            
            # Cache clearing for performance
            if cache_clear_interval and (generation + 1) % int(cache_clear_interval) == 0 and hasattr(ga, 'clear_cache'):
                ga.clear_cache()
                
        # Final progress update
        log("Progress: [" + "=" * 50 + "] " + f"{num_generations}/{num_generations} generations - COMPLETE! ({time.time() - start_time:.1f}s)")
        
        # Final evaluation and Pareto front extraction
        final_fronts, final_fitness_values = ga.fast_non_dominated_sort(population)
        pareto_front_indices = final_fronts[0] if final_fronts else []
        
        # Create detailed solution information
        all_solutions = []
        best_deviation_solution = None
        best_length_solution = None
        best_deviation_fitness = float('inf')
        best_segment_count = float('inf')  # Track best segment count (lower is better)
        best_avg_length = 0  # Track best average segment length (higher is better)
        
        for idx in pareto_front_indices:
            chromosome = population[idx]
            negative_deviation, avg_segment_length = final_fitness_values[idx]  # GA returns (-deviation, +avg_length)
            
            # Calculate segment statistics  
            segments = []
            for i in range(len(chromosome) - 1):
                start_mile = chromosome[i]
                end_mile = chromosome[i + 1]
                segments.append(end_mile - start_mile)
            
            calculated_avg_length = sum(segments) / len(segments) if segments else 0.0
            segment_count = len(segments)
            
            # Store raw GA values - let config handle visualization transforms
            solution_info = {
                'chromosome': chromosome,
                'fitness': [negative_deviation, avg_segment_length],  # Raw GA values
                'objective_values': [negative_deviation, avg_segment_length],  # Raw GA values for config transforms
                'deviation_fitness': negative_deviation,  # Raw negative deviation from GA
                'segment_fitness': avg_segment_length,    # Positive segment length from GA
                'num_segments': segment_count,
                'avg_segment_length': calculated_avg_length,  # Calculated positive value for stats
                'segment_lengths': segments
            }
            
            all_solutions.append(solution_info)
            
            # Track best solutions for each objective (using calculated positive values for meaningful comparison)  
            # Safety check: ensure negative_deviation is a number
            if isinstance(negative_deviation, (int, float)):
                positive_deviation = -negative_deviation  # Convert for meaningful comparison
            else:
                # Handle case where GA returns unexpected data type
                try:
                    positive_deviation = -float(negative_deviation)
                except (ValueError, TypeError):
                    print(f"🚨 Warning: Could not convert deviation {negative_deviation} to number, using absolute calculated value")
                    positive_deviation = sum(segments)**2 if segments else 0  # Fallback to basic deviation calculation
                    
            if positive_deviation < best_deviation_fitness:
                best_deviation_fitness = positive_deviation
                best_deviation_solution = solution_info
            
            if segment_count < best_segment_count:  # Lower segment count is better for simplicity
                best_segment_count = segment_count
                
            if avg_segment_length > best_avg_length:  # Higher average length is better
                best_avg_length = avg_segment_length
                best_length_solution = solution_info
        
        # Select best compromise solution (normalized trade-off)
        if all_solutions:
            # Find solution with best balance between low deviation and high average segment length
            dev_values = [sol['deviation_fitness'] for sol in all_solutions]
            length_values = [sol['avg_segment_length'] for sol in all_solutions]
            
            min_dev, max_dev = min(dev_values), max(dev_values)
            min_length, max_length = min(length_values), max(length_values)
            
            best_compromise = None
            best_compromise_score = float('inf')
            
            for solution in all_solutions:
                # Normalize deviation (lower is better) and segment length (higher is better)
                norm_dev = (solution['deviation_fitness'] - min_dev) / (max_dev - min_dev) if max_dev > min_dev else 0
                norm_length = 1 - (solution['avg_segment_length'] - min_length) / (max_length - min_length) if max_length > min_length else 0  # Invert for \"lower is better\"
                
                # Compromise score (equal weighting, both normalized to lower-is-better)
                compromise_score = norm_dev + norm_length
                
                if compromise_score < best_compromise_score:
                    best_compromise_score = compromise_score
                    best_compromise = solution
            
            # Use compromise as primary solution, fallback to best deviation
            primary_solution = best_compromise or best_deviation_solution or all_solutions[0]
        else:
            # Fallback: no Pareto solutions found
            log("Warning: No Pareto solutions found, using best population member")
            best_idx = min(range(len(final_fitness_values)), key=lambda i: final_fitness_values[i][0])
            chromosome = population[best_idx]
            deviation_fitness, segment_count = final_fitness_values[best_idx]
            
            primary_solution = {
                'chromosome': chromosome,
                'fitness': [deviation_fitness, segment_count],
                'deviation_fitness': deviation_fitness,
                'segment_fitness': segment_count, 
                'num_segments': segment_count,
                'avg_segment_length': sum(chromosome[i+1] - chromosome[i] for i in range(len(chromosome)-1)) / max(1, len(chromosome)-1)
            }
            all_solutions = [primary_solution]
        
        # Prepare optimization statistics
        optimization_stats = {
            'pareto_front_size': len(all_solutions),
            'best_deviation_fitness': best_deviation_fitness if best_deviation_fitness != float('inf') else None,
            'best_segment_count': best_segment_count if best_segment_count != float('inf') else None,
            'final_population_size': len(population),
            'generations_completed': num_generations,  # Use num_generations directly since we completed the full run
            'generations_run': num_generations,        # Add alias for compatibility
            'final_generation': num_generations,       # Add alias for compatibility
            'population_size': population_size,
        }
        
        if enable_performance_stats:
            optimization_stats.update({
                'generation_times': generation_times,
                'diversity_history': diversity_history,
                'average_generation_time': sum(generation_times) / len(generation_times) if generation_times else 0,
            })
        
        # Prepare input parameters record using configuration values
        # These parameters are preserved for accurate JSON export
        input_parameters = {
            'min_length': min_length,        # Configuration parameter value
            'max_length': max_length,        # Configuration parameter value
            'population_size': population_size,
            'num_generations': num_generations,
            'crossover_rate': crossover_rate,
            'mutation_rate': mutation_rate,
            'gap_threshold': gap_threshold,
            'cache_clear_interval': cache_clear_interval,
            'enable_performance_stats': enable_performance_stats
        }
        
        # Prepare data summary - consistent with other methods, use RouteAnalysis data_range for per-route bounds
        actual_data = data.route_data
        
        # Use data_range from RouteAnalysis if available (ensures consistency with mandatory breakpoints)
        if hasattr(ga, 'route_analysis') and ga.route_analysis and hasattr(ga.route_analysis, 'data_range'):
            data_range = ga.route_analysis.data_range
        else:
            # Fallback to direct calculation if RouteAnalysis not available
            data_range = {
                'x_min': float(actual_data[x_column].min()),
                'x_max': float(actual_data[x_column].max()),
                'y_min': float(actual_data[y_column].min()),
                'y_max': float(actual_data[y_column].max())
            }
        
        data_summary = {
            'total_data_points': len(actual_data),  # Fixed: was 'total_points'
            'data_range': data_range,  # Schema-compliant per-route data bounds for visualization
            'mandatory_breakpoints': list(ga.mandatory_breakpoints),
            # Add gap analysis information (generic to all methods)
            'gap_analysis': {
                'total_gaps': len(ga.route_analysis.gap_segments) if hasattr(ga, 'route_analysis') and ga.route_analysis else 0,
                'gap_segments': [{'start': gap[0], 'end': gap[1], 'length': gap[1] - gap[0]} for gap in ga.route_analysis.gap_segments] if hasattr(ga, 'route_analysis') and ga.route_analysis else [],
                'total_gap_length': ga.route_analysis.route_stats.get('gap_total_length', 0.0) if hasattr(ga, 'route_analysis') and ga.route_analysis else 0.0
            }
        }
        
        # Get route ID from data if available
        route_id = getattr(data, 'route_id', 'Unknown')
        
        log("\\n=== MULTI-OBJECTIVE RESULTS ===")
        log(f"Pareto front size: {len(all_solutions)}")
        if best_deviation_solution:
            log(f"Best deviation: {best_deviation_solution['deviation_fitness']:.6f} ({int(best_deviation_solution['num_segments'])} segments, {best_deviation_solution['avg_segment_length']:.2f} miles avg)")
        if best_length_solution:
            log(f"Best avg segment length: {best_length_solution['avg_segment_length']:.2f} miles ({int(best_length_solution['num_segments'])} segments, deviation: {best_length_solution['deviation_fitness']:.6f})")
        if primary_solution != best_deviation_solution and primary_solution != best_length_solution:
            log(f"Compromise solution: {primary_solution['deviation_fitness']:.6f} deviation, {int(primary_solution['num_segments'])} segments, {primary_solution['avg_segment_length']:.2f} miles avg")
        log(f"Total time: {time.time() - start_time:.1f} seconds")
        log("[OK] Multi-objective optimization complete!")
        
        # Create and return AnalysisResult
        return AnalysisResult(
            method_name=self.method_name,
            method_key=self.method_key,
            route_id=route_id,
            all_solutions=all_solutions,  # Complete Pareto front
            optimization_stats=optimization_stats,
            mandatory_breakpoints=sorted(list(ga.mandatory_breakpoints)),
            processing_time=time.time() - start_time,
            input_parameters=input_parameters,
            data_summary=data_summary
        )