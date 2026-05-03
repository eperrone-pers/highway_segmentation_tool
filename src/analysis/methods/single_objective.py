"""
Single-Objective Analysis Method for Highway Segmentation GA

Implements traditional single-objective genetic algorithm optimization focusing purely
on data accuracy (minimizing deviation between actual data and segment averages).

This method provides:
- Classical GA approach with single fitness objective
- Tournament selection with configurable pressure  
- Elite preservation ensuring best solutions survive
- Standard crossover and mutation operators
- Detailed performance tracking and statistics

Key characteristics:
- Maximum data accuracy without segment count constraints
- Faster convergence compared to multi-objective approaches
- Well-established algorithm with predictable behavior
- Suitable when segment count is not a primary concern

Version: 1.95.0 (Phase 1.95 Analysis Method Extraction)
"""

import time
import random
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

# Import base interface and utilities
from ..base import AnalysisMethodBase, AnalysisResult
from ..utils.ga_utilities import (
    crossover_with_retries,
    mutation_with_retries,
    analyze_population_diversity,
)
from ..utils.segment_metrics import average_length_excluding_gap_segments

# Import GA class and configuration
from ..utils.genetic_algorithm import HighwaySegmentGA
from config import get_optimization_method


class SingleObjectiveMethod(AnalysisMethodBase):
    """
    Single-objective genetic algorithm analysis method.
    
    Optimizes highway segmentation using a single fitness objective focused on
    maximizing data accuracy (minimizing deviation between actual data and segment averages).
    """
    
    @property
    def method_name(self) -> str:
        """Human-readable method name for GUI display."""
        return "Single-Objective GA"
    
    @property 
    def method_key(self) -> str:
        """Method key for result handling and export."""
        return "single"
        
    def run_analysis(self, 
                    data: Any,
                    route_id: str,
                    x_column: str, 
                    y_column: str,
                    gap_threshold: float,
                    **kwargs) -> AnalysisResult:
        """
        Execute single-objective genetic algorithm optimization.
        
        Args:
            data: DataFrame with highway data or RouteAnalysis object
            route_id: Route identifier for this analysis
            x_column: Column name for x-axis values (e.g., 'milepoint')  
            y_column: Column name for y-axis values (optimization target)
            gap_threshold: Data gap detection threshold
            **kwargs: Method-specific parameters including:
                - min_length: Minimum segment length constraint
                - max_length: Maximum segment length constraint
                - population_size: Individuals per generation (default from config)
                - num_generations: Evolution iterations (default from config)
                - elite_ratio: Elite preservation ratio (default: 0.05)
                - mutation_rate: Mutation probability (default from config)
                - crossover_rate: Crossover probability (default from config)
                - Segment-level caching: Always enabled for performance
                - enable_performance_stats: Track detailed stats (default: True)
                - log_callback: Progress logging function (optional)
                - stop_callback: Stop checking function (optional)
                
        Returns:
            AnalysisResult with optimization results and statistics
        """
        # Get configuration defaults for single-objective method
        method_config = get_optimization_method('single')
        param_defaults = {param.name: param.default_value for param in method_config.parameters}
        
        # Extract method-specific parameters with proper config defaults
        min_length = kwargs.get('min_length', param_defaults['min_length'])
        max_length = kwargs.get('max_length', param_defaults['max_length'])
        population_size = kwargs.get('population_size', param_defaults['population_size'])
        num_generations = kwargs.get('num_generations', param_defaults['num_generations'])
        elite_ratio = kwargs.get('elite_ratio', param_defaults['elite_ratio'])
        mutation_rate = kwargs.get('mutation_rate', param_defaults['mutation_rate'])
        crossover_rate = kwargs.get('crossover_rate', param_defaults['crossover_rate'])
        # gap_threshold now comes as direct parameter (framework level)
        # Segment caching always enabled for performance
        enable_performance_stats = kwargs.get('enable_performance_stats', param_defaults['enable_performance_stats'])
        log_callback = kwargs.get('log_callback', None)
        stop_callback = kwargs.get('stop_callback', None)

        # Logging controls (keep defaults quiet for GUI performance)
        log_elitism = bool(kwargs.get('log_elitism', False))
        elitism_log_interval = int(kwargs.get('elitism_log_interval', max(50, num_generations // 20)))
        log_constraint_stats = bool(kwargs.get('log_constraint_stats', False))
        constraint_stats_interval = int(kwargs.get('constraint_stats_interval', max(100, num_generations // 20)))
        
        # Validate parameters
        self.validate_parameters(
            min_length=min_length,
            max_length=max_length,
            population_size=population_size,
            num_generations=num_generations,
            gap_threshold=gap_threshold
        )
        if not hasattr(data, 'route_data'):
            raise TypeError(
                "SingleObjectiveMethod.run_analysis expects a RouteAnalysis object (with .route_data). "
                "Use analyze_route_gaps(...) to build one from a DataFrame."
            )
        
        start_time = time.time()
        
        # Setup logging
        def log(message):
            if log_callback:
                log_callback(message)
                
        log("Initializing single-objective genetic algorithm...")
        log(f"Objective: Maximize data fit (minimize deviation)")
        log(f"Parameters: {population_size} individuals, {num_generations} generations")
        
        # Initialize genetic algorithm
        ga = HighwaySegmentGA(data, x_column, y_column, min_length, max_length, 
                            population_size, mutation_rate=mutation_rate, 
                            crossover_rate=crossover_rate, gap_threshold=gap_threshold)
        
        # Enable segment caching for improved performance
        ga.enable_segment_cache_mode(True)
        
        # Generate initial population
        log("Generating diverse initial population...")
        population = ga.generate_diverse_initial_population()
        
        # Validate and fix initial population
        population = [ga._enforce_constraints(chrom) if not ga.validate_chromosome(chrom) else chrom 
                     for chrom in population]
        
        log(f"[OK] Generated {len(population)} valid chromosomes")
        
        # Initialize tracking
        best_fitness_history = []
        generation_times = [] if enable_performance_stats else None
        diversity_history = [] if enable_performance_stats else None
        
        log("\\nStarting single-objective evolution...")
        log("Progress: [" + "-" * 50 + "]")
        
        # Main evolution loop
        for gen in range(num_generations):
            # Check for stop request
            if stop_callback and stop_callback():
                log(f"\\n[STOPPED] Optimization stopped by user at generation {gen+1}")
                break

            gen_start_time = time.time()

            # Progress reporting
            progress_interval = max(1, num_generations // 50)
            if gen % progress_interval == 0 or gen == 0:
                progress = int((gen / num_generations) * 50)
                bar = "=" * progress + "-" * (50 - progress)
                log(f"\\rProgress: [{bar}] {gen}/{num_generations} generations")
            
            # Evaluate population fitness
            fitnesses = [ga.fitness(chromosome) for chromosome in population]
            best_fitness_history.append(max(fitnesses))
            
            # Detailed reporting every 50 generations
            if (gen + 1) % 50 == 0:
                best_idx = np.argmax(fitnesses)
                best_chromosome = population[best_idx]
                segment_count = len(best_chromosome) - 1
                diversity_stats = ga.analyze_population_diversity(population)
                
                # Average length excluding gap-only segments (method-owned export convention)
                avg_length = average_length_excluding_gap_segments(
                    best_chromosome,
                    getattr(data, 'gap_segments', []),
                )
                
                log(f"\\nGen {gen+1}: Best fitness = {fitnesses[best_idx]:.6f}")
                log(f"  Segments: {segment_count}")
                log(f"  Average length: {avg_length:.3f} miles")
                log(f"  Population fitness: avg={np.mean(fitnesses):.6f}, std={np.std(fitnesses):.6f}")
                log(f"  Diversity: {diversity_stats['unique_segment_counts']} types, "
                    f"Range: {diversity_stats['min_segments']}-{diversity_stats['max_segments']} segments")
            
            # Track performance stats
            if enable_performance_stats:
                generation_times.append(time.time() - gen_start_time)
                diversity_history.append(ga.analyze_population_diversity(population))
            
            # Report constraint statistics
            if log_constraint_stats and log_callback and (gen + 1) % constraint_stats_interval == 0:
                ga.report_constraint_statistics(gen + 1, log_callback)
            
            # ===== GENETIC OPERATIONS =====
            
            # Tournament selection for parents
            parents = self._select_parents_tournament(population, fitnesses, population_size // 2, ga)
            
            # Generate offspring through crossover
            offspring = []
            attempts = 0
            max_attempts = population_size * 2  # Prevent infinite loops
            
            while len(offspring) < population_size and attempts < max_attempts:
                attempts += 1
                p1, p2 = random.sample(parents, 2)
                
                # Apply crossover probabilistically
                if random.random() < ga.crossover_rate:
                    c1, c2 = crossover_with_retries(p1, p2, ga.x_data, ga.mandatory_breakpoints, 
                                                  ga.validate_chromosome)
                    if c1 is None:  # Crossover failed after retries
                        continue  # Try new parents
                else:
                    c1, c2 = p1[:], p2[:]  # Copy parents if no crossover
                    
                offspring.extend([c1, c2])
            
            # Truncate to correct size
            offspring = offspring[:population_size]
            
            # Apply mutations to offspring
            for i in range(len(offspring)):
                if random.random() < ga.mutation_rate:
                    mutated = mutation_with_retries(offspring[i], ga.x_data, ga.mandatory_breakpoints,
                                                  ga.validate_chromosome)
                    if mutated is not None:
                        offspring[i] = mutated
                    # If None, keep original offspring[i]
            
            # Validate offspring constraints
            offspring = [ga._enforce_constraints(chrom) if not ga.validate_chromosome(chrom) else chrom 
                        for chrom in offspring]
            
            # Evaluate offspring fitness
            offspring_fitnesses = [ga.fitness(chromosome) for chromosome in offspring]
            
            # Elitist selection: combine generations and select best
            elitism_callback = None
            if log_elitism and log_callback and ((gen + 1) % elitism_log_interval == 0 or gen == 0):
                elitism_callback = log

            population = ga.elitist_selection(
                population,
                fitnesses,
                offspring,
                offspring_fitnesses,
                elite_ratio,
                log_callback=elitism_callback,
            )
        
        # Final processing
        elapsed_time = time.time() - start_time
        
        # Final progress update
        progress = "=" * 50
        log(f"\\rProgress: [{progress}] {num_generations}/{num_generations} generations - COMPLETE! ({elapsed_time:.1f}s)")
        
        # Get final results
        final_fitnesses = [ga.fitness(chromosome) for chromosome in population]
        best_idx = np.argmax(final_fitnesses)
        best_chromosome = population[best_idx]
        best_fitness = final_fitnesses[best_idx]
        
        # Calculate final statistics
        segment_count = len(best_chromosome) + 1
        stats = ga.calculate_detailed_statistics(best_chromosome, data)
        avg_length = stats.avg_length if hasattr(stats, 'avg_length') else 0
        
        # Print summary
        log(f"\\n=== SINGLE-OBJECTIVE RESULTS ===")
        log(f"Best fitness: {best_fitness:.6f}")
        log(f"Segments: {segment_count}")
        log(f"Average length: {avg_length:.3f} miles")
        log(f"Total time: {elapsed_time:.1f} seconds")
        
        # Collect cache statistics
        cache_stats = self._collect_cache_stats(ga)
        
        # Prepare performance statistics
        performance_stats = None
        if enable_performance_stats and generation_times and diversity_history:
            performance_stats = {
                'average_generation_time': np.mean(generation_times),
                'total_generation_time': sum(generation_times),
                'diversity_history': diversity_history,
                'final_diversity': ga.analyze_population_diversity(population)
            }
        
        # Prepare optimization statistics with consistent field names
        optimization_stats = {
            'final_fitness': best_fitness,
            'fitness_history': best_fitness_history, 
            'generations_completed': num_generations,  # Use num_generations directly since we completed the full run
            'generations_run': num_generations,        # Add alias for compatibility
            'final_generation': num_generations,       # Add alias for compatibility  
            'population_size': population_size,
            'elite_ratio': elite_ratio,
            'mutation_rate': mutation_rate,
            'crossover_rate': crossover_rate,
            'cache_stats': cache_stats,
            'performance_stats': performance_stats
        }
        
        # Prepare input parameters summary
        input_parameters = {
            'population_size': population_size,
            'num_generations': num_generations,
            'min_length': min_length,
            'max_length': max_length,
            'elite_ratio': elite_ratio,
            'mutation_rate': mutation_rate,
            'crossover_rate': crossover_rate,
            'gap_threshold': gap_threshold
        }
        
        # Prepare data summary - use RouteAnalysis data_range for schema compliance
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
            'data_range': data_range,  # Schema-compliant data bounds for visualization
            'mandatory_breakpoints': list(ga.mandatory_breakpoints),
            # Add gap analysis information from route analysis (generic to all methods)
            'gap_analysis': {
                'total_gaps': len(ga.route_analysis.gap_segments) if hasattr(ga, 'route_analysis') and ga.route_analysis else 0,
                'gap_segments': [{'start': gap[0], 'end': gap[1], 'length': gap[1] - gap[0]} for gap in ga.route_analysis.gap_segments] if hasattr(ga, 'route_analysis') and ga.route_analysis else [],
                'total_gap_length': ga.route_analysis.route_stats.get('gap_total_length', 0.0) if hasattr(ga, 'route_analysis') and ga.route_analysis else 0.0
            }
        }
        
        # Get route ID from data if available
        route_id = getattr(data, 'route_id', 'Unknown')

        # Average length excluding gap-only segments (method-owned export convention)
        avg_length = average_length_excluding_gap_segments(
            best_chromosome,
            getattr(data, 'gap_segments', []),
        )

        # Method-owned segmentation payload for export (prevents exporter from imposing overall-mean semantics)
        segment_lengths = [best_chromosome[i + 1] - best_chromosome[i] for i in range(len(best_chromosome) - 1)]
        segmentation = {
            'breakpoints': best_chromosome,
            'segment_count': len(segment_lengths),
            'segment_lengths': segment_lengths,
            'total_length': (best_chromosome[-1] - best_chromosome[0]) if len(best_chromosome) >= 2 else 0.0,
            'average_segment_length': float(avg_length),
            'segment_details': [],
        }
        
        log("[OK] Single-objective optimization complete!")
        
        # Create and return AnalysisResult
        return AnalysisResult(
            method_name=self.method_name,
            method_key=self.method_key,
            route_id=route_id,
            all_solutions=[{
                'chromosome': best_chromosome,
                'fitness': best_fitness,
                'objective_values': [best_fitness, avg_length],  # Unified framework format: [fitness, avg_segment_length]
                'segment_count': segment_count,
                'num_segments': segment_count,  # Compatibility alias for controller
                'avg_length': avg_length,
                'avg_segment_length': avg_length,  # Compatibility alias for multi-objective consistency
                'segmentation': segmentation,
                'stats': stats
            }] + [{
                'chromosome': population[i],
                'fitness': final_fitnesses[i],
                'segment_count': len(population[i]) + 1
            } for i in range(1, len(population))],
            optimization_stats=optimization_stats,
            mandatory_breakpoints=sorted(list(ga.mandatory_breakpoints)),
            processing_time=elapsed_time,
            input_parameters=input_parameters,
            data_summary=data_summary,
            timestamp=datetime.now().isoformat(),
            analysis_version="1.95.0"
        )
    
    def _select_parents_tournament(self, population: List[List[float]], fitnesses: List[float], 
                                 num_parents: int, ga: HighwaySegmentGA) -> List[List[float]]:
        """
        Tournament selection for single-objective optimization.
        
        Args:
            population: Current population
            fitnesses: Fitness values 
            num_parents: Number of parents to select
            ga: GA instance for tournament size config
            
        Returns:
            Selected parent chromosomes
        """
        parents = []
        tournament_size = 3  # Standard tournament size

        population_size = len(population)
        if population_size == 0 or num_parents <= 0:
            return parents

        tournament_size = min(tournament_size, population_size)

        for _ in range(num_parents):
            tournament_indices = random.sample(range(population_size), k=tournament_size)
            best_idx = tournament_indices[0]
            best_fitness = fitnesses[best_idx]
            for idx in tournament_indices[1:]:
                if fitnesses[idx] > best_fitness:
                    best_idx = idx
                    best_fitness = fitnesses[idx]

            parents.append(population[best_idx])
            
        return parents
    
    def _collect_cache_stats(self, ga: HighwaySegmentGA) -> Optional[Dict[str, Any]]:
        """
        Collect caching statistics from GA instance.
        
        Args:
            ga: GA instance
            
        Returns:
            Cache statistics dictionary or None
        """
        cache_stats = None
        
        if hasattr(ga, 'enable_segment_caching') and ga.enable_segment_caching:
            # Hybrid caching is enabled
            all_stats = ga.get_cache_stats()
            segment_stats = ga.get_segment_cache_stats()
            cache_stats = {
                'cache_type': 'Hybrid caching (Chromosome + Segment)',
                'fitness_cache_size': all_stats.get('fitness_cache_size', 0),
                'multi_fitness_cache_size': all_stats.get('multi_fitness_cache_size', 0),
                'segment_cache_size': segment_stats.get('cache_size', 0),
                'hits': segment_stats.get('hits', 0),
                'misses': segment_stats.get('misses', 0),
                'total_calls': segment_stats.get('total_calls', 0),
                'hit_rate': segment_stats.get('hit_rate', 0.0)
            }
        else:
            # Standard chromosome caching
            if hasattr(ga, 'get_cache_stats'):
                chrom_stats = ga.get_cache_stats()
                cache_stats = {
                    'cache_type': 'Chromosome-level caching (Standard)',
                    'fitness_cache_size': chrom_stats.get('fitness_cache_size', 0),
                    'multi_fitness_cache_size': chrom_stats.get('multi_fitness_cache_size', 0)
                }
                
        return cache_stats