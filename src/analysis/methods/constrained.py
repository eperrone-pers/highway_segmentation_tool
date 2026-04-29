"""
Constrained Single-Objective Analysis Method for Highway Segmentation GA

Implements constrained genetic algorithm optimization that balances data accuracy
with target average segment length requirements using penalty-based methods.

This method provides:
- Constraint-guided population initialization targeting desired segment lengths
- Penalty-based fitness combining deviation minimization with length constraints
- Gap-aware target calculation accounting for mandatory breakpoints
- Adaptive constraint tolerance with configurable penalty weights
- Length-aware genetic operators for constraint preservation

Key characteristics:
- Hybrid approach: constraint guidance + penalty enforcement
- Target-driven optimization for engineering requirements
- Comprehensive constraint violation tracking and reporting
- Suitable for design-driven segmentation with specific length requirements

Algorithm Flow:
1. Gap-aware target calculation considering mandatory breakpoints
2. Constraint-guided population initialization
3. Penalty-based fitness evaluation (deviation + length penalty)
4. Standard GA evolution with constraint-aware selection
5. Elite preservation of feasible solutions

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
    tournament_selection,
    crossover_with_retries,
    mutation_with_retries,
    analyze_population_diversity,
    batch_fitness_evaluation
)
from ..utils.segment_metrics import average_length_excluding_gap_segments

# Import GA class and configuration
from ..utils.genetic_algorithm import HighwaySegmentGA
from config import get_optimization_method


class ConstrainedMethod(AnalysisMethodBase):
    """
    Constrained single-objective genetic algorithm analysis method.
    
    This method implements a hybrid approach combining constraint-guided initialization
    with penalty-based fitness to find solutions near a target average segment length.
    """

    @property
    def method_name(self) -> str:
        return "Constrained Single-Objective GA"

    @property
    def method_key(self) -> str:
        return "constrained"

    @property
    def description(self) -> str:
        return ("Target-driven optimization balancing data accuracy with specific "
                "average segment length requirements using constraint penalties.")

    def run_analysis(
        self, 
        data, 
        route_id: str,
        x_column: str, 
        y_column: str,
        gap_threshold: float,
        **kwargs,
    ) -> AnalysisResult:
        """
        Execute constrained single-objective genetic algorithm analysis.
        
        Args:
            data: RouteAnalysis object or DataFrame with highway data
            route_id: Route identifier for this analysis
            x_column: Name of X-axis column (e.g., 'milepoint')
            y_column: Name of Y-axis column (e.g., strength indicator)
            gap_threshold: Data gap detection threshold
            **kwargs: Method-specific parameters including:
                - input_parameters: Optional parameter overrides dict
                - log_callback: Optional logging function for progress updates
                - stop_callback: Optional function to check if optimization should stop
                - min_length, max_length, target_avg_length, penalty_weight, etc.
                
        Returns:
            AnalysisResult with constrained optimization results
        """
        start_time = time.time()
        
        # Extract callback functions and parameters from kwargs
        input_parameters = kwargs.get('input_parameters', None)
        log_callback = kwargs.get('log_callback', None)
        stop_callback = kwargs.get('stop_callback', None)

        if not hasattr(data, 'route_data'):
            raise TypeError(
                "ConstrainedMethod.run_analysis expects a RouteAnalysis object (with .route_data). "
                "Use analyze_route_gaps(...) to build one from a DataFrame."
            )
        
        # Logging setup
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)
        
        # Get method configuration and merge with user parameters
        method_config = get_optimization_method('constrained')
        param_defaults = {param.name: param.default_value for param in method_config.parameters}
        
        # Merge parameters: defaults <- input_parameters <- kwargs
        parameters = param_defaults.copy()
        if input_parameters:
            parameters.update(input_parameters)
        # Add any additional kwargs (excluding callback functions)
        method_params = {k: v for k, v in kwargs.items() 
                        if k not in ['input_parameters', 'log_callback', 'stop_callback']}
        parameters.update(method_params)
        
        # Extract parameters with descriptive names
        min_length = parameters['min_length']
        max_length = parameters['max_length']
        # gap_threshold now comes as direct parameter (framework level)
        population_size = int(parameters['population_size'])
        num_generations = int(parameters['num_generations'])
        crossover_rate = parameters['crossover_rate']
        mutation_rate = parameters['mutation_rate']
        elite_ratio = parameters['elite_ratio']
        target_avg_length = parameters['target_avg_length']
        penalty_weight = parameters['penalty_weight']
        length_tolerance = parameters['length_tolerance']
        cache_clear_interval = int(parameters['cache_clear_interval'])
        enable_performance_stats = parameters['enable_performance_stats']
        # Segment caching always enabled for performance
        
        log(f"Initializing constrained single-objective GA...")
        log(f"Target: {target_avg_length:.2f} mile average segments (±{length_tolerance:.2f} tolerance)")
        log(f"Parameters: {population_size} individuals, {num_generations} generations")
        
        # Initialize genetic algorithm
        ga = HighwaySegmentGA(
            data, x_column, y_column,
            min_length=min_length,
            max_length=max_length,
            population_size=population_size,
            mutation_rate=mutation_rate,
            crossover_rate=crossover_rate,
            gap_threshold=gap_threshold
        )
        
        # Enable segment caching for improved performance
        ga.enable_segment_cache_mode(True)
        
        # ===== GAP-AWARE TARGET SEGMENT CALCULATION =====
        route_data = data.route_data
        total_distance = route_data[x_column].max() - route_data[x_column].min()
        mandatory_breakpoints = sorted(list(ga.mandatory_breakpoints))
        
        # Calculate realistic target segments considering gap constraints
        target_segments = self._calculate_gap_aware_target(
            mandatory_breakpoints, total_distance, target_avg_length, 
            min_length, max_length, log
        )
        
        # ===== POPULATION INITIALIZATION =====
        log("Generating diverse initial population...")
        population = ga.generate_diverse_initial_population()
        
        # Validate and enforce constraints on initial population
        population = [
            ga._enforce_constraints(chrom) if not ga.validate_chromosome(chrom) else chrom 
            for chrom in population
        ]
        
        log(f"[OK] Generated {len(population)} valid chromosomes")
        
        # ===== EVOLUTION LOOP =====
        log(f"\\nStarting constrained evolution...")
        log("Progress: [" + "-" * 50 + "]")
        
        best_fitness_history = []
        avg_length_history = []
        generation_times = []
        
        for generation in range(num_generations):
            # Check for early termination
            if stop_callback and stop_callback():
                log(f"\\n[STOPPED] Constrained optimization stopped by user at generation {generation+1}")
                break
            
            gen_start_time = time.time()
            
            # Update progress display
            progress_interval = max(1, num_generations // 50)
            if generation % progress_interval == 0:
                progress = int((generation / num_generations) * 50)
                bar = "=" * progress + "-" * (50 - progress)
                log(f"\\rProgress: [{bar}] {generation}/{num_generations} generations")
            
            # Evaluate population with constrained fitness
            fitness_data = [
                self._constrained_fitness(chrom, ga, target_avg_length, length_tolerance, penalty_weight)
                for chrom in population
            ]
            
            constrained_fitnesses = [f[0] for f in fitness_data]
            base_fitnesses = [f[1] for f in fitness_data]
            avg_lengths = [f[2] for f in fitness_data]
            length_deviations = [f[3] for f in fitness_data]
            
            # Track best solution
            best_idx = np.argmax(constrained_fitnesses)
            best_fitness_history.append(constrained_fitnesses[best_idx])
            avg_length_history.append(avg_lengths[best_idx])
            
            # Periodic detailed reporting
            if (generation + 1) % 50 == 0:
                diversity_stats = analyze_population_diversity(population)
                avg_length_pop = np.mean(avg_lengths)
                target_compliance = sum(1 for dev in length_deviations if dev <= length_tolerance) / len(length_deviations)
                
                log(f"\\nGen {generation+1}: Best constrained fitness = {constrained_fitnesses[best_idx]:.6f}")
                log(f"  Base fitness = {base_fitnesses[best_idx]:.6f}")
                log(f"  Length: {avg_lengths[best_idx]:.3f} miles (target: {target_avg_length:.3f}, dev: {length_deviations[best_idx]:.3f})")
                log(f"  Population avg length: {avg_length_pop:.3f}, compliance: {target_compliance:.1%}")
                log(f"  Diversity: {diversity_stats['unique_segment_counts']} types, Range: {diversity_stats['min_segments']}-{diversity_stats['max_segments']} segments")
            
            # Standard genetic algorithm operations with elitism
            parents = self._select_parents_tournament(population, constrained_fitnesses, population_size // 2)
            
            # Generate offspring through crossover
            offspring = []
            attempts = 0
            max_attempts = population_size * 10  # High guardrail; should not trigger in normal runs

            while len(offspring) < population_size and attempts < max_attempts:
                attempts += 1
                p1, p2 = random.sample(parents, 2)
                
                # Apply crossover probabilistically
                if random.random() < crossover_rate:
                    c1, c2 = crossover_with_retries(p1, p2, ga.x_data, ga.mandatory_breakpoints, 
                                                  ga.validate_chromosome)
                    if c1 is None:  # Crossover failed after retries
                        continue  # Try new parents
                else:
                    c1, c2 = p1[:], p2[:]  # Copy parents if no crossover
                    
                offspring.extend([c1, c2])

            if len(offspring) < population_size:
                log(
                    f"\n[WARNING] Offspring generation hit max attempts ({max_attempts}); "
                    f"padding with parent copies to reach population_size={population_size}" 
                )
                while len(offspring) < population_size:
                    offspring.append(random.choice(parents)[:])
            
            # Apply mutations to offspring
            for i in range(len(offspring)):
                if np.random.rand() < mutation_rate:
                    mutated = mutation_with_retries(offspring[i], ga.x_data, ga.mandatory_breakpoints,
                                                  ga.validate_chromosome)
                    if mutated is not None:
                        offspring[i] = mutated
            
            # Truncate offspring to correct size
            offspring = offspring[:population_size]
            
            # Evaluate offspring
            offspring_fitness_data = [
                self._constrained_fitness(chrom, ga, target_avg_length, length_tolerance, penalty_weight)
                for chrom in offspring
            ]
            offspring_constrained_fitnesses = [f[0] for f in offspring_fitness_data]
            
            # Elitist selection: preserve best solutions from both generations
            population = self._elitist_selection(
                population, constrained_fitnesses,
                offspring, offspring_constrained_fitnesses,
                elite_ratio
            )
            
            generation_times.append(time.time() - gen_start_time)
            
            # Cache management
            if (generation + 1) % cache_clear_interval == 0 and hasattr(ga, 'clear_cache'):
                ga.clear_cache()
        
        # Final progress update
        progress = "=" * 50
        elapsed_time = time.time() - start_time
        log(f"\\rProgress: [{progress}] {num_generations}/{num_generations} generations - COMPLETE! ({elapsed_time:.1f}s)")
        
        # ===== FINAL EVALUATION =====
        final_fitness_data = [
            self._constrained_fitness(chrom, ga, target_avg_length, length_tolerance, penalty_weight)
            for chrom in population
        ]
        
        final_constrained_fitnesses = [f[0] for f in final_fitness_data]
        final_base_fitnesses = [f[1] for f in final_fitness_data]
        final_avg_lengths = [f[2] for f in final_fitness_data]
        final_length_deviations = [f[3] for f in final_fitness_data]
        
        # Select best solution:
        # 1) Closest non-mandatory average length to target (min deviation)
        # 2) Tie-break by best base fitness (max data fit)
        best_idx = min(
            range(len(population)),
            key=lambda i: (final_length_deviations[i], -final_base_fitnesses[i])
        )
        best_chromosome = population[best_idx]
        
        # Create solution information
        segments = []
        for i in range(len(best_chromosome) - 1):
            start_point = best_chromosome[i]
            end_point = best_chromosome[i + 1]
            segments.append(end_point - start_point)
        
        best_solution = {
            'chromosome': best_chromosome,
            'fitness': final_constrained_fitnesses[best_idx],
            'objective_values': [final_constrained_fitnesses[best_idx], final_avg_lengths[best_idx]],  # Unified framework format: [fitness, avg_segment_length]
            'unconstrained_fitness': final_base_fitnesses[best_idx],
            'deviation_fitness': final_base_fitnesses[best_idx],
            'num_segments': len(best_chromosome) - 1,
            'avg_segment_length': final_avg_lengths[best_idx],
            'target_avg_length': target_avg_length,
            'length_deviation': final_length_deviations[best_idx],
            'segment_lengths': segments,
            'is_feasible': final_length_deviations[best_idx] <= length_tolerance
        }

        # Method-owned segmentation payload for export: average excludes gap-only segments.
        avg_excluding_gaps = average_length_excluding_gap_segments(
            best_chromosome,
            getattr(data, 'gap_segments', []),
        )
        best_solution['segmentation'] = {
            'breakpoints': best_chromosome,
            'segment_count': len(segments),
            'segment_lengths': segments,
            'total_length': (best_chromosome[-1] - best_chromosome[0]) if len(best_chromosome) >= 2 else 0.0,
            'average_segment_length': float(avg_excluding_gaps),
            'segment_details': [],
        }
        
        # Optimization statistics
        final_diversity = analyze_population_diversity(population)
        target_compliance = sum(1 for dev in final_length_deviations if dev <= length_tolerance) / len(final_length_deviations)
        
        optimization_stats = {
            'total_generations': len(best_fitness_history),
            'generations_completed': len(best_fitness_history),  # Add consistent field name
            'generations_run': len(best_fitness_history),        # Add alias for compatibility
            'final_generation': len(best_fitness_history),       # Add alias for compatibility
            'population_size': population_size,                  # Add consistent field
            'best_fitness_history': best_fitness_history,
            'avg_length_history': avg_length_history,
            'final_diversity': final_diversity,
            'target_compliance': target_compliance,
            'average_generation_time': np.mean(generation_times) if generation_times else 0,
            'constraint_violations': len(final_length_deviations) - sum(1 for dev in final_length_deviations if dev <= length_tolerance),
            'penalty_weight_used': penalty_weight,
            'tolerance_used': length_tolerance
        }
        
        # Data summary - consistent with other methods, use RouteAnalysis data_range for per-route bounds
        route_data = data.route_data
        
        # Use data_range from RouteAnalysis if available (ensures consistency with mandatory breakpoints)
        if hasattr(ga, 'route_analysis') and ga.route_analysis and hasattr(ga.route_analysis, 'data_range'):
            data_range = ga.route_analysis.data_range
        else:
            # Fallback to direct calculation if RouteAnalysis not available
            data_range = {
                'x_min': float(route_data[x_column].min()),
                'x_max': float(route_data[x_column].max()),
                'y_min': float(route_data[y_column].min()),
                'y_max': float(route_data[y_column].max())
            }
        
        data_summary = {
            'total_data_points': len(route_data),  # Fixed: was 'total_points'
            'data_range': data_range,  # Schema-compliant per-route data bounds for visualization
            'mandatory_breakpoints': list(ga.mandatory_breakpoints),
            'target_segments_calculated': target_segments,
            # Add gap analysis information (generic to all methods)
            'gap_analysis': {
                'total_gaps': len(ga.route_analysis.gap_segments) if hasattr(ga, 'route_analysis') and ga.route_analysis else 0,
                'gap_segments': [{'start': gap[0], 'end': gap[1], 'length': gap[1] - gap[0]} for gap in ga.route_analysis.gap_segments] if hasattr(ga, 'route_analysis') and ga.route_analysis else [],
                'total_gap_length': ga.route_analysis.route_stats.get('gap_total_length', 0.0) if hasattr(ga, 'route_analysis') and ga.route_analysis else 0.0
            }
        }
        
        # Final results reporting
        log("\\n=== CONSTRAINED SINGLE-OBJECTIVE RESULTS ===")
        log(f"Best constrained fitness: {best_solution['fitness']:.6f}")
        log(f"Base deviation fitness: {best_solution['unconstrained_fitness']:.6f}")
        log(f"Segments: {best_solution['num_segments']}")
        log(f"Average segment length: {best_solution['avg_segment_length']:.3f} miles (target: {target_avg_length:.3f})")
        log(f"Length deviation: {best_solution['length_deviation']:.3f} miles")
        log(f"Feasible solution: {'Yes' if best_solution['is_feasible'] else 'No'}")
        log(f"Population compliance: {target_compliance:.1%}")
        log(
            f"Selected solution (closest-to-target): avg_non_mandatory={best_solution['avg_segment_length']:.3f}, "
            f"target={target_avg_length:.3f}, dev={best_solution['length_deviation']:.3f}, "
            f"base_fitness={best_solution['unconstrained_fitness']:.6f}"
        )
        log(f"Total time: {elapsed_time:.1f} seconds")
        log("[OK] Constrained optimization complete!")
        
        # Get route ID from data if available
        route_id = getattr(data, 'route_id', 'Unknown')
        
        # Create and return AnalysisResult
        return AnalysisResult(
            method_name=self.method_name,
            method_key=self.method_key,
            route_id=route_id,
            all_solutions=[best_solution],  # Single solution
            optimization_stats=optimization_stats,
            mandatory_breakpoints=sorted(list(ga.mandatory_breakpoints)),
            processing_time=elapsed_time,
            input_parameters={**parameters, 'gap_threshold': gap_threshold},  # Include framework gap_threshold for export consistency
            data_summary=data_summary
        )
    
    def _calculate_gap_aware_target(self, mandatory_breakpoints, total_distance, 
                                   target_avg_length, min_length, max_length, log):
        """Calculate realistic target segments considering mandatory breakpoints."""
        
        if len(mandatory_breakpoints) > 2:  # More than just start/end points
            # Calculate distances of segments forced by mandatory breakpoints
            mandatory_distances = []
            for i in range(len(mandatory_breakpoints) - 1):
                mandatory_dist = mandatory_breakpoints[i + 1] - mandatory_breakpoints[i]
                mandatory_distances.append(mandatory_dist)
            
            mandatory_total_distance = sum(mandatory_distances)
            num_mandatory_segments = len(mandatory_distances)
            
            # Calculate what regular segments need to average
            remaining_distance = total_distance - mandatory_total_distance
            
            if remaining_distance > 0:
                total_segments_needed = total_distance / target_avg_length
                target_regular_segments = max(0, int(round(total_segments_needed - num_mandatory_segments)))
                target_segments = num_mandatory_segments + target_regular_segments
                
                if target_regular_segments > 0:
                    required_regular_avg = remaining_distance / target_regular_segments
                else:
                    required_regular_avg = target_avg_length
                
                log(f"Gap-aware calculation:")
                log(f"  Mandatory segments: {num_mandatory_segments} covering {mandatory_total_distance:.2f} miles")
                log(f"  Remaining distance: {remaining_distance:.2f} miles for regular segments")
                log(f"  Target regular segments: {target_regular_segments}")
                log(f"  Required regular avg: {required_regular_avg:.3f} miles to achieve overall {target_avg_length:.2f}")
                
                # Warn if target is unrealistic
                if required_regular_avg > max_length * 0.9:
                    log(f"  WARNING: Required regular segment avg ({required_regular_avg:.2f}) is near max_length ({max_length:.2f})")
                    log(f"           Target {target_avg_length:.2f} may be unrealistic with current gap pattern")
                elif required_regular_avg < min_length * 1.1:
                    log(f"  WARNING: Required regular segment avg ({required_regular_avg:.2f}) is near min_length ({min_length:.2f})")
                    log(f"           Consider lower target length")
            else:
                target_segments = num_mandatory_segments
                log(f"  All distance covered by mandatory segments: {num_mandatory_segments} segments")
        else:
            # Simple case: no significant mandatory breakpoints
            target_segments = max(2, int(round(total_distance / target_avg_length)))
            log(f"Simple calculation (no gaps): {target_segments} segments for {total_distance:.2f} miles")
        
        return max(2, target_segments)
    
    def _constrained_fitness(self, chromosome, ga, target_avg_length, tolerance, penalty_weight):
        """Calculate constrained fitness combining deviation minimization with length penalty."""
        
        # Base fitness: deviation minimization
        base_fitness = ga.fitness(chromosome)
        
        # Calculate current average segment length
        current_avg_length = ga._calculate_non_mandatory_avg_length(chromosome)
        
        # Calculate length deviation from target
        length_deviation = abs(current_avg_length - target_avg_length)
        
        if length_deviation <= tolerance:
            # Within tolerance - no penalty
            penalty = 0
        else:
            # Outside tolerance - apply penalty
            excess_deviation = length_deviation - tolerance
            penalty = penalty_weight * (excess_deviation ** 2)
        
        constrained_fitness = base_fitness - penalty
        return constrained_fitness, base_fitness, current_avg_length, length_deviation
    
    def _elitist_selection(self, population, fitness_values, offspring, offspring_fitness, elite_ratio):
        """Elitist selection preserving best solutions from both generations."""
        
        # Combine populations
        combined_population = population + offspring
        combined_fitness = fitness_values + offspring_fitness
        
        # Sort by fitness (higher is better)
        sorted_indices = np.argsort(combined_fitness)[::-1]
        
        # Select top individuals
        selected_size = len(population)
        selected_indices = sorted_indices[:selected_size]
        
        return [combined_population[i] for i in selected_indices]
    
    def _select_parents_tournament(self, population, fitnesses, num_parents):
        """
        Tournament selection for constrained optimization.
        
        Args:
            population: Current population
            fitnesses: Fitness values 
            num_parents: Number of parents to select
            
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