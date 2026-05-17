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
from typing import Any

from ..base import AnalysisMethodBase, AnalysisResult
from ..utils.ga_utilities import (
    nsga2_tournament_selection, crossover_with_retries, mutation_with_retries, analyze_population_diversity
)
from ..utils.segment_metrics import average_length_excluding_gap_segments
from ..utils.genetic_algorithm import HighwaySegmentGA
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

        method_config = get_optimization_method('multi')
        if not method_config:
            raise ValueError("Multi-objective method configuration not found")

        param_defaults = {param.name: param.default_value for param in method_config.parameters}

        min_length = kwargs.get('min_length', param_defaults['min_length'])
        max_length = kwargs.get('max_length', param_defaults['max_length'])
        # Preserve constraint values; later compromise-scoring code computes min/max stats
        # and must not overwrite these configuration parameters.
        min_length_constraint = min_length
        max_length_constraint = max_length
        population_size = kwargs.get('population_size', param_defaults['population_size'])
        num_generations = kwargs.get('num_generations', param_defaults['num_generations'])
        crossover_rate = kwargs.get('crossover_rate', param_defaults['crossover_rate'])
        mutation_rate = kwargs.get('mutation_rate', param_defaults['mutation_rate'])
        cache_clear_interval = kwargs.get('cache_clear_interval', param_defaults['cache_clear_interval'])
        enable_performance_stats = kwargs.get('enable_performance_stats', param_defaults['enable_performance_stats'])
        log_callback = kwargs.get('log_callback', None)
        stop_callback = kwargs.get('stop_callback', None)
        
        self.validate_parameters(
            min_length=min_length,
            max_length=max_length,
            population_size=population_size,
            num_generations=num_generations,
            gap_threshold=gap_threshold
        )

        start_time = time.time()
        logger = create_logger(callback=log_callback)
        log = logger.log

        log("Initializing NSGA-II multi-objective optimization...")
        log("Objectives: Minimize deviation (data fit) vs. Maximize average segment length")
        log(f"Parameters: {population_size} individuals, {num_generations} generations")

        ga = HighwaySegmentGA(data, x_column, y_column, min_length=min_length, max_length=max_length,
                            population_size=population_size, crossover_rate=crossover_rate, mutation_rate=mutation_rate,
                            gap_threshold=gap_threshold)
        ga.enable_segment_cache_mode(True)

        log("Generating diverse initial population...")
        population = ga.generate_diverse_initial_population()
        population = [ga._enforce_constraints(chrom) if not ga.validate_chromosome(chrom) else chrom
                     for chrom in population]
        log(f"[OK] Generated {len(population)} valid chromosomes")

        pareto_history = []
        generation_times = [] if enable_performance_stats else None
        diversity_history = [] if enable_performance_stats else None

        log("\\nStarting NSGA-II multi-objective evolution...")
        log("Progress: [" + "-" * 50 + "]")
        
        # Main NSGA-II evolution loop
        for generation in range(num_generations):
            generation_start = time.time()
            
            if stop_callback and stop_callback():
                log("\\nOptimization stopped by user request")
                break

            # NSGA-II core: non-dominated sorting followed by crowding distance
            fronts, fitness_values = ga.fast_non_dominated_sort(population)
            crowding_distances = {}
            for front_idx, front in enumerate(fronts):
                distances = ga.calculate_crowding_distance(front, fitness_values)
                for sol_idx, distance in zip(front, distances):
                    crowding_distances[sol_idx] = distance
            
            if generation % 4 == 0:
                progress = int((generation / num_generations) * 50)
                progress_bar = "=" * progress + "-" * (50 - progress)
                log(f"Progress: [{progress_bar}] {generation}/{num_generations} generations")
            
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
            
            if fronts:
                current_pareto = [(population[i], fitness_values[i]) for i in fronts[0]]
                pareto_history.append(current_pareto)
            
            if enable_performance_stats:
                generation_time = time.time() - generation_start
                generation_times.append(generation_time)
                diversity_stats = analyze_population_diversity(population)
                diversity_history.append(diversity_stats)
            
            if generation < num_generations - 1:  # Skip selection on final generation
                mating_pool = nsga2_tournament_selection(
                    population, fronts, fitness_values, crowding_distances, population_size
                )
                
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
                        offspring.extend([parent1, parent2])

                for i in range(len(offspring)):
                    if random.random() < mutation_rate:
                        mutated = mutation_with_retries(
                            offspring[i], ga.x_data, ga.mandatory_breakpoints, ga.validate_chromosome
                        )
                        if mutated:
                            offspring[i] = mutated
                
                offspring = [ga._enforce_constraints(chrom) if not ga.validate_chromosome(chrom) else chrom
                           for chrom in offspring]

                # Environmental selection: combine parent + offspring populations, keep best
                combined_population = population + offspring
                combined_fronts, combined_fitness = ga.fast_non_dominated_sort(combined_population)
                combined_crowding = {}
                for front_idx, front in enumerate(combined_fronts):
                    distances = ga.calculate_crowding_distance(front, combined_fitness)
                    for sol_idx, distance in zip(front, distances):
                        combined_crowding[sol_idx] = distance
                
                next_population = []
                for front in combined_fronts:
                    if len(next_population) + len(front) <= population_size:
                        # Add entire front
                        next_population.extend([combined_population[i] for i in front])
                    else:
                        # Partial front: rank by crowding distance to preserve spread
                        remaining = population_size - len(next_population)
                        front_with_crowding = [(i, combined_crowding[i]) for i in front]
                        front_with_crowding.sort(key=lambda x: x[1], reverse=True)  # higher crowding distance = more diverse
                        
                        for i in range(remaining):
                            next_population.append(combined_population[front_with_crowding[i][0]])
                        break
                
                population = next_population
            
            if cache_clear_interval and (generation + 1) % int(cache_clear_interval) == 0 and hasattr(ga, 'clear_cache'):
                ga.clear_cache()
                
        # Final progress update
        log("Progress: [" + "=" * 50 + "] " + f"{num_generations}/{num_generations} generations - COMPLETE! ({time.time() - start_time:.1f}s)")
        
        final_fronts, final_fitness_values = ga.fast_non_dominated_sort(population)
        pareto_front_indices = final_fronts[0] if final_fronts else []
        
        all_solutions = []
        best_deviation_solution = None
        best_length_solution = None
        best_deviation_fitness = float('inf')
        best_segment_count = float('inf')  # Track best segment count (lower is better)
        best_avg_length = 0  # Track best average segment length (higher is better)
        
        for idx in pareto_front_indices:
            chromosome = population[idx]
            negative_deviation, avg_segment_length = final_fitness_values[idx]  # GA convention: (-deviation, +avg_length)
            segments = []
            for i in range(len(chromosome) - 1):
                start_mile = chromosome[i]
                end_mile = chromosome[i + 1]
                segments.append(end_mile - start_mile)
            
            # Method-owned export convention: average segment length excluding gap-only segments.
            calculated_avg_length = average_length_excluding_gap_segments(
                chromosome,
                getattr(data, 'gap_segments', []),
            )
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
                'segment_lengths': segments,
                'segmentation': {
                    'breakpoints': chromosome,
                    'segment_count': segment_count,
                    'segment_lengths': segments,
                    'total_length': (chromosome[-1] - chromosome[0]) if len(chromosome) >= 2 else 0.0,
                    'average_segment_length': float(calculated_avg_length),
                    'segment_details': [],
                },
            }
            
            all_solutions.append(solution_info)

            if isinstance(negative_deviation, (int, float)):
                positive_deviation = -negative_deviation  # Convert for meaningful comparison
            else:
                try:
                    positive_deviation = -float(negative_deviation)
                except (ValueError, TypeError):
                    print(f"Warning: Could not convert deviation {negative_deviation} to number, using fallback")
                    positive_deviation = sum(segments)**2 if segments else 0
                    
            if positive_deviation < best_deviation_fitness:
                best_deviation_fitness = positive_deviation
                best_deviation_solution = solution_info
            
            if segment_count < best_segment_count:  # Lower segment count is better for simplicity
                best_segment_count = segment_count
                
            if avg_segment_length > best_avg_length:  # Higher average length is better
                best_avg_length = avg_segment_length
                best_length_solution = solution_info
        
        if all_solutions:
            dev_values = [sol['deviation_fitness'] for sol in all_solutions]
            length_values = [sol['avg_segment_length'] for sol in all_solutions]
            
            min_dev, max_dev = min(dev_values), max(dev_values)
            min_avg_length, max_avg_length = min(length_values), max(length_values)
            
            best_compromise = None
            best_compromise_score = float('inf')
            
            for solution in all_solutions:
                # Normalize both objectives to [0,1] lower-is-better; equal weight compromise
                norm_dev = (solution['deviation_fitness'] - min_dev) / (max_dev - min_dev) if max_dev > min_dev else 0
                norm_length = 1 - (solution['avg_segment_length'] - min_avg_length) / (max_avg_length - min_avg_length) if max_avg_length > min_avg_length else 0

                compromise_score = norm_dev + norm_length
                
                if compromise_score < best_compromise_score:
                    best_compromise_score = compromise_score
                    best_compromise = solution
            
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
        
        input_parameters = {
            'min_length': min_length_constraint,
            'max_length': max_length_constraint,
            'population_size': population_size,
            'num_generations': num_generations,
            'crossover_rate': crossover_rate,
            'mutation_rate': mutation_rate,
            'gap_threshold': gap_threshold,
            'cache_clear_interval': cache_clear_interval,
            'enable_performance_stats': enable_performance_stats
        }
        
        actual_data = data.route_data

        if hasattr(ga, 'route_analysis') and ga.route_analysis and hasattr(ga.route_analysis, 'data_range'):
            data_range = ga.route_analysis.data_range
        else:
            data_range = {
                'x_min': float(actual_data[x_column].min()),
                'x_max': float(actual_data[x_column].max()),
                'y_min': float(actual_data[y_column].min()),
                'y_max': float(actual_data[y_column].max())
            }
        
        data_summary = {
            'total_data_points': len(actual_data),
            'data_range': data_range,
            'mandatory_breakpoints': list(ga.mandatory_breakpoints),
            'gap_analysis': {
                'total_gaps': len(ga.route_analysis.gap_segments) if hasattr(ga, 'route_analysis') and ga.route_analysis else 0,
                'gap_segments': [{'start': gap[0], 'end': gap[1], 'length': gap[1] - gap[0]} for gap in ga.route_analysis.gap_segments] if hasattr(ga, 'route_analysis') and ga.route_analysis else [],
                'total_gap_length': ga.route_analysis.route_stats.get('gap_total_length', 0.0) if hasattr(ga, 'route_analysis') and ga.route_analysis else 0.0
            }
        }

        # Optional: attribute-based must-break metadata for visualization/reporting
        try:
            from data_loader import build_attribute_break_analysis

            attr_block = build_attribute_break_analysis(ga.route_analysis)
            if attr_block:
                data_summary['attribute_break_analysis'] = attr_block
        except Exception:
            pass
        
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
        
        return AnalysisResult(
            method_name=self.method_name,
            method_key=self.method_key,
            route_id=route_id,
            all_solutions=all_solutions,
            optimization_stats=optimization_stats,
            mandatory_breakpoints=sorted(list(ga.mandatory_breakpoints)),
            processing_time=time.time() - start_time,
            input_parameters=input_parameters,
            data_summary=data_summary
        )