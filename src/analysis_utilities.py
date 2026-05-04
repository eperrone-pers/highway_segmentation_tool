"""
Highway Segmentation - Analysis Utilities

This module contains statistical analysis and calculation utilities for 
highway segmentation optimization results.

Functions:
- calculate_non_mandatory_segment_stats: Calculate statistics for segments without mandatory breakpoints
- print_optimization_summary: Print comprehensive NSGA-II optimization results
- print_single_objective_summary: Print single-objective optimization results  
- print_constrained_single_objective_summary: Print constrained optimization results

Author: Eric (Mott MacDonald)
Date: March 2026
"""

# Import dependencies for summary functions
import numpy as np
from logger import create_logger


def calculate_non_mandatory_segment_stats(chromosome, mandatory_breakpoints):
    """
    Calculate statistics for segments that don't have mandatory breakpoints at their boundaries.
    
    Args:
        chromosome: List of breakpoints defining segments
        mandatory_breakpoints: Set of mandatory breakpoints from data gaps
    
    Returns:
        dict: Statistics including count, total_length, avg_length for non-mandatory segments
    """
    if len(chromosome) < 2 or not mandatory_breakpoints:
        return {'count': 0, 'total_length': 0.0, 'avg_length': 0.0}
    
    non_mandatory_segments = []
    mandatory_set = set(mandatory_breakpoints)
    
    # Examine each segment
    for i, (start_bp, end_bp) in enumerate(zip(chromosome, chromosome[1:])):
        
        # Check if this segment has mandatory breakpoints at its boundaries
        # A segment is non-mandatory if neither start nor end is a mandatory breakpoint
        # (except for the very first and last breakpoints which are always mandatory)
        start_is_mandatory = start_bp in mandatory_set
        end_is_mandatory = end_bp in mandatory_set
        
        # Skip first and last segments since they always touch mandatory boundaries
        if i == 0 or i == len(chromosome) - 2:
            continue
            
        # This segment is non-mandatory if it doesn't have mandatory breakpoints at boundaries
        if not start_is_mandatory and not end_is_mandatory:
            segment_length = end_bp - start_bp
            non_mandatory_segments.append(segment_length)
    
    # Calculate statistics
    count = len(non_mandatory_segments)
    total_length = sum(non_mandatory_segments) if non_mandatory_segments else 0.0
    avg_length = total_length / count if count > 0 else 0.0
    
    return {
        'count': count,
        'total_length': total_length,
        'avg_length': avg_length
    }


# ===== SUMMARY AND REPORTING FUNCTIONS =====
# Functions for printing optimization results and performance summaries

def print_optimization_summary(pareto_front, fitness_values, generation_times, elapsed_time, enable_performance_stats=True, cache_stats=None):
    """
    Print a comprehensive summary of the optimization results
    """
    print(f"\n{'='*60}")
    print("OPTIMIZATION SUMMARY")
    print(f"{'='*60}")
    
    # Basic results
    pareto_fitness = [fitness_values[i] for i in pareto_front]
    print(f"[OK] Total runtime: {elapsed_time:.1f}s")
    print(f"[OK] Pareto front solutions: {len(pareto_front)}")
    
    if pareto_fitness:
        # Fitness statistics
        deviations = [f[0] for f in pareto_fitness]
        avg_lengths = [f[1] for f in pareto_fitness]
        
        print(f"[OK] Fitness range (deviation): {min(deviations):.3f} to {max(deviations):.3f}")
        print(f"[OK] Average segment length range: {min(avg_lengths):.3f} to {max(avg_lengths):.3f} miles")
        
        # Best solutions
        best_fitness_idx = pareto_front[np.argmin(deviations)]
        best_length_idx = pareto_front[np.argmin(avg_lengths)]
        
        print(f"\n[BEST] Best fitness solution: #{best_fitness_idx} (deviation: {min(deviations):.3f})")
        print(f"[BEST] Most compact solution: #{best_length_idx} (avg length: {min(avg_lengths):.3f} miles)")
    
    # Performance statistics
    if enable_performance_stats and generation_times:
        avg_gen_time = np.mean(generation_times)
        print("\n[PERF] Performance:")
        print(f"   Average generation time: {avg_gen_time:.3f}s")
        print(f"   Generations per second: {1.0/avg_gen_time:.1f}")
        
        if cache_stats:
            total_cache_hits = cache_stats['fitness_cache_size'] + cache_stats['multi_fitness_cache_size']
            print(f"   Cache efficiency: {total_cache_hits} evaluations avoided")
    
    print(f"{'='*60}\n")


def print_single_objective_summary(best_chromosome, best_fitness, fitness_history, elapsed_time, enable_performance_stats=True, diversity_stats=None, log_callback=None):
    """
    Print a comprehensive summary of single-objective optimization results
    """
    # Create logger instance for summary output
    logger = create_logger(callback=log_callback)
    log = logger.log
            
    log(f"\n{'='*60}")
    log("SINGLE-OBJECTIVE OPTIMIZATION SUMMARY")
    log(f"{'='*60}")
    
    # Basic results
    log(f"[OK] Total runtime: {elapsed_time:.1f}s")
    log(f"[OK] Best fitness achieved: {best_fitness:.6f}")
    log(f"[OK] Number of segments: {len(best_chromosome) - 1}")
    log(f"[OK] Total distance: {best_chromosome[-1] - best_chromosome[0]:.3f} miles")
    
    # Improvement tracking
    if len(fitness_history) > 1:
        improvement = fitness_history[-1] - fitness_history[0]
        log(f"[OK] Fitness improvement: {improvement:.6f} ({improvement/fitness_history[0]*100:+.1f}%)")
    
    # Segment analysis
    segment_lengths = [end_bp - start_bp for start_bp, end_bp in zip(best_chromosome, best_chromosome[1:])]
    log(f"[OK] Average segment length: {np.mean(segment_lengths):.3f} miles")
    log(f"[OK] Segment length range: {min(segment_lengths):.3f} - {max(segment_lengths):.3f} miles")
    
    # Performance statistics
    if enable_performance_stats and diversity_stats:
        log("\n[PERF] Performance:")
        log(f"   Final population diversity: {diversity_stats['unique_segment_counts']} different designs")
        log(f"   Segment count range: {diversity_stats['min_segments']} - {diversity_stats['max_segments']} (avg: {diversity_stats['avg_segments']:.1f})")
        
        if len(fitness_history) > 0:
            generations_per_second = len(fitness_history) / elapsed_time
            log(f"   Evolution rate: {generations_per_second:.1f} generations/second")
    
    print(f"{'='*60}\n")


def print_constrained_single_objective_summary(best_chromosome, best_constrained_fitness, best_unconstrained_fitness, 
                                             best_avg_length, target_avg_length, length_deviation, tolerance,
                                             fitness_history, length_history, elapsed_time, 
                                             enable_performance_stats, diversity_stats, log):
    """Print detailed summary for constrained single-objective optimization"""
    log("\n" + "=" * 60)
    log("CONSTRAINED SINGLE-OBJECTIVE OPTIMIZATION SUMMARY")
    log("=" * 60)
    
    # Basic solution info
    log("\nSolution Overview:")
    log(f"  Breakpoints: {len(best_chromosome)}")
    log(f"  Segments: {len(best_chromosome) - 1}")
    log(f"  Total length: {best_chromosome[-1] - best_chromosome[0]:.3f} miles")
    
    # Constraint satisfaction
    log("\nConstraint Performance:")
    log(f"  Target avg length: {target_avg_length:.3f} miles")
    log(f"  Achieved avg length: {best_avg_length:.3f} miles")
    log(f"  Length deviation: {length_deviation:.3f} miles")
    log(f"  Tolerance: {tolerance:.3f} miles")
    
    within_tolerance = length_deviation <= tolerance
    log(f"  Constraint satisfied: {'YES' if within_tolerance else 'NO'}")
    if not within_tolerance:
        excess = length_deviation - tolerance
        log(f"  Excess deviation: {excess:.3f} miles")
    
    # Fitness details
    log("\nFitness Details:")
    log(f"  Constrained fitness: {best_constrained_fitness:.6f}")
    log(f"  Base fitness (deviation): {best_unconstrained_fitness:.6f}")
    penalty = best_constrained_fitness - best_unconstrained_fitness
    log(f"  Length penalty: {-penalty:.6f}")
    
    # Performance statistics
    if enable_performance_stats and diversity_stats:
        log("\nPerformance Statistics:")
        log(f"  Evolution time: {elapsed_time:.2f} seconds")
        log(f"  Final diversity: {diversity_stats['unique_segment_counts']} segment count types")
        log(f"  Segment range: {diversity_stats['min_segments']}-{diversity_stats['max_segments']}")
        
        # Convergence analysis
        fitness_improvement = fitness_history[-1] - fitness_history[0] if len(fitness_history) > 0 else 0
        length_stability = np.std(length_history[-10:]) if len(length_history) >= 10 else float('inf')
        
        log(f"  Fitness improvement: {fitness_improvement:.6f}")
        log(f"  Length stability (last 10 gen): {length_stability:.6f}")
    
    log("\n" + "=" * 60)