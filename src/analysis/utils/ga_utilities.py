"""
Shared Genetic Algorithm Utilities for Highway Segmentation Analysis

This module contains reusable GA functions extracted from the main genetic_algorithm.py
class for use across different analysis methods (single-objective, multi-objective, constrained).

Functions provided:
- Tournament selection (NSGA-II based)
- Crossover operations with retry mechanism
- Mutation operations with retry mechanism  
- Non-dominated sorting for multi-objective
- Crowding distance calculation
- Population diversity analysis
- Fitness evaluation helpers

Version: 1.95.0 (Phase 1.95 Analysis Method Extraction)
"""

import random
import bisect
import numpy as np
from typing import List, Tuple, Dict, Any, Optional

# Import from src level (relative to package structure)
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config import optimization_config


def tournament_selection(population: List[List[float]], 
                        fitness_values: List[Tuple[float, float]], 
                        tournament_size: int = None) -> List[List[float]]:
    """
    Simple tournament selection for single-objective optimization.
    
    Args:
        population: List of chromosomes (breakpoint lists)
        fitness_values: List of fitness values (single or multi-objective)
        tournament_size: Size of tournament (default from config)
        
    Returns:
        List of two selected parent chromosomes
    """
    if tournament_size is None:
        tournament_size = optimization_config.tournament_size
    
    parents = []
    for _ in range(2):  # Select 2 parents
        # Tournament selection
        tournament_indices = random.sample(range(len(population)), tournament_size)
        
        # Find best individual in tournament
        best_idx = tournament_indices[0]
        best_fitness = fitness_values[best_idx]
        
        for idx in tournament_indices[1:]:
            candidate_fitness = fitness_values[idx]
            # For single objective, compare directly; for multi-objective, use first value
            candidate_value = candidate_fitness[0] if isinstance(candidate_fitness, tuple) else candidate_fitness
            best_value = best_fitness[0] if isinstance(best_fitness, tuple) else best_fitness
            
            if candidate_value > best_value:  # Assuming maximization
                best_idx = idx
                best_fitness = candidate_fitness
        
        parents.append(population[best_idx])
    
    return parents


def nsga2_tournament_selection(population: List[List[float]], 
                              fronts: List[List[int]], 
                              fitness_values: List[Tuple[float, float]], 
                              crowding_distances: Dict[int, float], 
                              num_parents: int) -> List[List[float]]:
    """
    NSGA-II tournament selection based on Pareto dominance and crowding distance.
    
    Selection criteria (in order of priority):
    1. Pareto rank (lower is better - front 0 dominates front 1, etc.)
    2. Crowding distance (higher is better - more diversity)
    
    Args:
        population: List of chromosomes
        fronts: List of fronts from non-dominated sorting
        fitness_values: Fitness values for each individual
        crowding_distances: Dict mapping individual index to crowding distance
        num_parents: Number of parents to select
        
    Returns:
        List of selected parent chromosomes
    """
    # Create mapping from individual index to front rank
    front_rank = {}
    for rank, front in enumerate(fronts):
        for idx in front:
            front_rank[idx] = rank
    
    parents = []
    for _ in range(num_parents):
        # Tournament selection: pick 2 random individuals and compare
        candidates = random.sample(range(len(population)), k=2)
        winner = nsga2_compare(candidates[0], candidates[1], front_rank, crowding_distances)
        parents.append(population[winner])
    
    return parents


def nsga2_compare(idx1: int, idx2: int, front_rank: Dict[int, int], 
                 crowding_distances: Dict[int, float]) -> int:
    """
    Compare two individuals for NSGA-II tournament selection.
    
    Returns the index of the better individual based on:
    1. Pareto rank (lower is better)
    2. Crowding distance (higher is better for tie-breaking)
    
    Args:
        idx1, idx2: Indices of individuals to compare
        front_rank: Mapping of individual index to front rank
        crowding_distances: Mapping of individual index to crowding distance
        
    Returns:
        Index of the winning individual
    """
    rank1 = front_rank.get(idx1, float('inf'))
    rank2 = front_rank.get(idx2, float('inf'))
    
    # First criterion: Pareto rank (lower is better)
    if rank1 < rank2:
        return idx1
    elif rank2 < rank1:
        return idx2
    
    # Tie-breaking: Crowding distance (higher is better for diversity)
    dist1 = crowding_distances.get(idx1, 0)
    dist2 = crowding_distances.get(idx2, 0)
    
    return idx1 if dist1 > dist2 else idx2


def crossover_with_retries(parent1: List[float], parent2: List[float],
                          x_data: List[float], mandatory_breakpoints: List[float],
                          validate_function: callable) -> Tuple[Optional[List[float]], Optional[List[float]]]:
    """
    Multi-attempt crossover with retry mechanism.
    
    Args:
        parent1, parent2: Parent chromosomes (breakpoint lists)
        x_data: Available x-values for chromosome construction
        mandatory_breakpoints: Breakpoints that must be preserved
        validate_function: Function to validate chromosome constraints
        
    Returns:
        Tuple of (child1, child2) or (None, None) if all attempts failed
    """
    ga = getattr(validate_function, "__self__", None)
    mandatory_set = set(mandatory_breakpoints)

    def is_segment_valid(start_bp: float, end_bp: float) -> bool:
        length = end_bp - start_bp
        if length <= 0:
            return False
        if ga is None:
            return True  # can't validate locally without constraints
        if length < ga.min_length or length > ga.max_length:
            # Mandatory segments are warning-only
            if start_bp in mandatory_set and end_bp in mandatory_set:
                return True
            return False
        return True

    def fast_validate_physical_cut(child: List[float], cut_point: float) -> bool:
        if ga is None:
            return validate_function(child)

        if len(child) < 2:
            return False
        if child[0] != ga.x_data[0] or child[-1] != ga.x_data[-1]:
            return False
        if not mandatory_set.issubset(set(child)):
            return False

        # Only the boundary segment between last <= cut and first > cut can be newly invalid.
        insert_pos = bisect.bisect_right(child, cut_point)
        if insert_pos <= 0 or insert_pos >= len(child):
            return False
        left_bp = child[insert_pos - 1]
        right_bp = child[insert_pos]
        return is_segment_valid(left_bp, right_bp)

    # Precompute optional breakpoints union once per parent pair
    mandatory_set_local = mandatory_set
    p1_optional = [bp for bp in parent1 if bp not in mandatory_set_local]
    p2_optional = [bp for bp in parent2 if bp not in mandatory_set_local]
    all_optional = sorted(set(p1_optional + p2_optional))

    for attempt in range(optimization_config.operator_max_retries):
        cut_point = random.choice(all_optional) if all_optional else None
        child1_bps, child2_bps = perform_single_crossover(parent1, parent2, mandatory_breakpoints, cut_point=cut_point)

        if cut_point is None:
            # Only mandatory breakpoints exist; children are parents.
            if validate_function(child1_bps) and validate_function(child2_bps):
                return child1_bps, child2_bps
            continue

        # Fast local validation for physical-cut crossover
        if fast_validate_physical_cut(child1_bps, cut_point) and fast_validate_physical_cut(child2_bps, cut_point):
            return child1_bps, child2_bps  # Success!
    
    # All attempts failed
    return None, None


def perform_single_crossover(
    parent1: List[float],
    parent2: List[float],
    mandatory_breakpoints: List[float],
    *,
    cut_point: Optional[float] = None,
) -> Tuple[List[float], List[float]]:
    """
    Single-point crossover while preserving mandatory breakpoints.
    
    Args:
        parent1, parent2: Parent chromosomes
        mandatory_breakpoints: Breakpoints that must be preserved
        
    Returns:
        Tuple of (child1, child2) chromosomes
    """
    mandatory_set = set(mandatory_breakpoints)
    
    # Get non-mandatory breakpoints from each parent
    parent1_optional = [bp for bp in parent1 if bp not in mandatory_set]
    parent2_optional = [bp for bp in parent2 if bp not in mandatory_set]
    
    # Physical-cut crossover: choose a single cut milepoint from the union of optional breakpoints.
    # Child1 keeps parent1 optionals <= cut and parent2 optionals > cut (and vice versa for child2).
    # This recombines existing breakpoints only (does not introduce new breakpoints).
    all_optional = sorted(set(parent1_optional + parent2_optional))
    if not all_optional:
        return parent1[:], parent2[:]  # Only mandatory breakpoints exist

    if cut_point is None or cut_point not in all_optional:
        cut_point = random.choice(all_optional)

    p1_left = [bp for bp in parent1_optional if bp <= cut_point]
    p1_right = [bp for bp in parent1_optional if bp > cut_point]
    p2_left = [bp for bp in parent2_optional if bp <= cut_point]
    p2_right = [bp for bp in parent2_optional if bp > cut_point]

    child1_optional = p1_left + p2_right
    child2_optional = p2_left + p1_right

    child1 = sorted(set(mandatory_set).union(child1_optional))
    child2 = sorted(set(mandatory_set).union(child2_optional))
    return child1, child2


def mutation_with_retries(chromosome: List[float], x_data: List[float], 
                         mandatory_breakpoints: List[float],
                         validate_function: callable) -> Optional[List[float]]:
    """
    Multi-attempt mutation with retry mechanism.
    
    Args:
        chromosome: Chromosome to mutate (breakpoint list)
        x_data: Available x-values for mutation
        mandatory_breakpoints: Breakpoints that must be preserved 
        validate_function: Function to validate chromosome constraints
        
    Returns:
        Mutated chromosome or None if all attempts failed
    """
    ga = getattr(validate_function, "__self__", None)
    mandatory_set = set(mandatory_breakpoints)

    def constraint_aware_mutation_attempt(original: List[float]) -> List[float]:
        """Attempt a mutation that is likely to satisfy length constraints.

        Only used when `ga` is available (validate_function is bound to a GA instance).
        Does not introduce new breakpoints beyond existing `x_data` values.
        """
        if ga is None:
            return perform_single_mutation(original, x_data, mandatory_breakpoints)

        chrom = list(original)
        if len(chrom) < 2:
            return chrom

        # Work with a sorted chromosome.
        chrom.sort()
        chrom_set = set(chrom)

        optional_indices = [
            i for i, bp in enumerate(chrom)
            if bp not in mandatory_set
        ]

        # Helper: pick a new breakpoint from x_data within (lo, hi), excluding mandatory + existing.
        def pick_bp_in_range(lo: float, hi: float) -> Optional[float]:
            if lo >= hi:
                return None
            xs = getattr(ga, "sorted_x_data", None)
            if xs is None:
                xs = np.asarray(x_data)
            left = int(np.searchsorted(xs, lo, side="right"))
            right = int(np.searchsorted(xs, hi, side="left"))
            if right <= left:
                return None
            # Sample a few candidates to avoid building large lists.
            for _ in range(10):
                idx = random.randrange(left, right)
                bp = float(xs[idx])
                if bp in chrom_set or bp in mandatory_set:
                    continue
                return bp
            return None

        def segment_is_mandatory(a: float, b: float) -> bool:
            return a in mandatory_set and b in mandatory_set

        def segment_ok(a: float, b: float) -> bool:
            length = b - a
            if length <= 0:
                return False
            if length < ga.min_length or length > ga.max_length:
                return segment_is_mandatory(a, b)
            return True

        action = random.choice(["add", "remove", "move"])

        # If we don't have enough optional breakpoints, bias away from remove/move.
        if len(optional_indices) <= 1 and action in ("remove", "move"):
            action = "add"

        if action == "add":
            # Choose a segment to split.
            # Only segments with room for a new breakpoint are considered.
            candidate_segments = []
            for i in range(len(chrom) - 1):
                a, b = chrom[i], chrom[i + 1]
                lo = a + ga.min_length
                hi = b - ga.min_length
                if lo < hi:
                    candidate_segments.append((a, b))
            if not candidate_segments:
                return chrom

            a, b = random.choice(candidate_segments)
            new_bp = pick_bp_in_range(a + ga.min_length, b - ga.min_length)
            if new_bp is None:
                return chrom
            new_chrom = sorted(set(chrom + [new_bp]))
            return new_chrom

        if action == "remove":
            # Remove an optional breakpoint only if the merged segment remains valid.
            removable = []
            for i in optional_indices:
                if i <= 0 or i >= len(chrom) - 1:
                    continue
                a, b = chrom[i - 1], chrom[i + 1]
                if segment_ok(a, b):
                    removable.append(i)
            if not removable:
                return chrom
            i = random.choice(removable)
            new_chrom = chrom[:i] + chrom[i + 1 :]
            return new_chrom

        # action == "move"
        movable = [i for i in optional_indices if 0 < i < len(chrom) - 1]
        if not movable:
            return chrom

        i = random.choice(movable)
        bp_old = chrom[i]
        a, b = chrom[i - 1], chrom[i + 1]
        # Choose a new location that keeps both adjacent segments valid.
        lo = a + ga.min_length
        hi = b - ga.min_length
        new_bp = pick_bp_in_range(lo, hi)
        if new_bp is None:
            return chrom
        new_chrom = chrom[:]
        new_chrom[i] = new_bp
        new_chrom = sorted(set(new_chrom))
        # Avoid accidental no-op move if set dedup removed something.
        if new_bp == bp_old:
            return chrom
        return new_chrom

    def is_segment_valid(start_bp: float, end_bp: float) -> bool:
        length = end_bp - start_bp
        if length <= 0:
            return False
        if ga is None:
            return True
        if length < ga.min_length or length > ga.max_length:
            if start_bp in mandatory_set and end_bp in mandatory_set:
                return True
            return False
        return True

    def fast_validate_mutation(original: List[float], mutated: List[float]) -> bool:
        if ga is None:
            return validate_function(mutated)

        if len(mutated) < 2:
            return False
        if mutated[0] != ga.x_data[0] or mutated[-1] != ga.x_data[-1]:
            return False
        if not mandatory_set.issubset(set(mutated)):
            return False

        orig_set = set(original)
        mut_set = set(mutated)
        added = sorted(mut_set - orig_set)
        removed = sorted(orig_set - mut_set)

        # No change
        if not added and not removed:
            return True

        # Add: check split segment around inserted bp
        if len(added) == 1 and not removed:
            bp = added[0]
            i = bisect.bisect_left(mutated, bp)
            if i <= 0 or i >= len(mutated) - 1:
                return False
            return is_segment_valid(mutated[i - 1], mutated[i]) and is_segment_valid(mutated[i], mutated[i + 1])

        # Remove: check merged segment where breakpoint was removed
        if len(removed) == 1 and not added:
            bp = removed[0]
            i = bisect.bisect_left(original, bp)
            if i <= 0 or i >= len(original) - 1:
                return False
            return is_segment_valid(original[i - 1], original[i + 1])

        # Move: one removed, one added; check both neighborhoods
        if len(removed) == 1 and len(added) == 1:
            bp_old = removed[0]
            bp_new = added[0]

            i_old = bisect.bisect_left(original, bp_old)
            if i_old <= 0 or i_old >= len(original) - 1:
                return False
            ok_old = is_segment_valid(original[i_old - 1], original[i_old + 1])

            i_new = bisect.bisect_left(mutated, bp_new)
            if i_new <= 0 or i_new >= len(mutated) - 1:
                return False
            ok_new = is_segment_valid(mutated[i_new - 1], mutated[i_new]) and is_segment_valid(mutated[i_new], mutated[i_new + 1])

            return ok_old and ok_new

        # Unexpected multi-edit; fall back to full validation
        return validate_function(mutated)

    for attempt in range(optimization_config.operator_max_retries):
        mutated = constraint_aware_mutation_attempt(chromosome)

        if fast_validate_mutation(chromosome, mutated):
            return mutated  # Success!
    
    # All attempts failed
    return None


def perform_single_mutation(chromosome: List[float], x_data: List[float],
                           mandatory_breakpoints: List[float]) -> List[float]:
    """
    Single mutation attempt while preserving mandatory breakpoints.
    
    Args:
        chromosome: Chromosome to mutate
        x_data: Available x-values for mutation
        mandatory_breakpoints: Breakpoints that must be preserved
        
    Returns:
        Mutated chromosome
    """
    mandatory_set = set(mandatory_breakpoints)
    chrom_set = set(chromosome)
    optional_breakpoints = [bp for bp in chromosome if bp not in mandatory_set]
    
    if len(optional_breakpoints) <= 1:  # Not enough optional breakpoints to mutate
        # Add a new optional breakpoint instead
        possible = [xp for xp in x_data 
                   if xp not in chrom_set and xp not in mandatory_set]
        if possible:
            new_bp = random.choice(possible)
            new_chrom = sorted(chromosome + [new_bp])
        else:
            return chromosome  # Can't mutate
    else:
        new_chrom = chromosome.copy()
        action = random.choice(['add', 'remove', 'move'])
        
        if action == 'add':
            # Add a new optional breakpoint
            new_chrom_set = set(new_chrom)
            possible = [xp for xp in x_data 
                       if xp not in new_chrom_set and xp not in mandatory_set]
            if possible:
                bp = random.choice(possible)
                new_chrom.append(bp)
                new_chrom = sorted(new_chrom)
                
        elif action == 'remove':
            # Remove an optional breakpoint (never remove mandatory ones)
            if optional_breakpoints:
                bp_to_remove = random.choice(optional_breakpoints)
                new_chrom.remove(bp_to_remove)
                
        elif action == 'move':
            # Move an optional breakpoint
            if optional_breakpoints:
                bp_to_move = random.choice(optional_breakpoints)
                new_chrom.remove(bp_to_move)
                
                # Find new location
                new_chrom_set = set(new_chrom)
                possible = [xp for xp in x_data 
                           if xp not in new_chrom_set and xp not in mandatory_set]
                if possible:
                    new_bp = random.choice(possible)
                    new_chrom.append(new_bp)
                    new_chrom = sorted(new_chrom)
                else:
                    new_chrom.append(bp_to_move)  # Put it back if no alternatives
                    new_chrom = sorted(new_chrom)
    
    return new_chrom


def fast_non_dominated_sort(population: List[List[float]], 
                           multi_objective_fitness_function: callable) -> Tuple[List[List[int]], List[Tuple[float, float]]]:
    """
    NSGA-II Fast Non-dominated Sorting.
    
    Args:
        population: List of chromosomes
        multi_objective_fitness_function: Function to evaluate multi-objective fitness
        
    Returns:
        Tuple of (fronts, fitness_values) where fronts is list of fronts and 
        each front is a list of solution indices
    """
    fitness_values = [multi_objective_fitness_function(chrom) for chrom in population]
    
    fronts = [[]]
    dominated_solutions = [[] for _ in range(len(population))]
    domination_count = [0 for _ in range(len(population))]
    
    for i in range(len(population)):
        for j in range(i + 1, len(population)):
            if dominates(fitness_values[i], fitness_values[j]):
                dominated_solutions[i].append(j)
                domination_count[j] += 1
            elif dominates(fitness_values[j], fitness_values[i]):
                dominated_solutions[j].append(i)
                domination_count[i] += 1
        
        if domination_count[i] == 0:
            fronts[0].append(i)
    
    front_idx = 0
    while len(fronts[front_idx]) > 0:
        next_front = []
        for i in fronts[front_idx]:
            for j in dominated_solutions[i]:
                domination_count[j] -= 1
                if domination_count[j] == 0:
                    next_front.append(j)
        front_idx += 1
        fronts.append(next_front)
    
    return fronts[:-1], fitness_values  # Remove empty last front


def dominates(fitness1: Tuple[float, float], fitness2: Tuple[float, float]) -> bool:
    """
    Check if fitness1 dominates fitness2.
    For our objectives: both should be maximized.
    
    Args:
        fitness1, fitness2: Fitness tuples to compare
        
    Returns:
        True if fitness1 dominates fitness2
    """
    return (fitness1[0] >= fitness2[0] and fitness1[1] >= fitness2[1] and 
            (fitness1[0] > fitness2[0] or fitness1[1] > fitness2[1]))


def calculate_crowding_distance(front_indices: List[int], 
                               fitness_values: List[Tuple[float, float]]) -> List[float]:
    """
    Calculate crowding distance for solutions in a front.
    
    Args:
        front_indices: Indices of solutions in the front
        fitness_values: Fitness values for all solutions
        
    Returns:
        List of crowding distances for solutions in the front
    """
    distances = [0.0 for _ in range(len(front_indices))]
    
    if len(front_indices) <= optimization_config.min_front_size:
        return [float('inf')] * len(front_indices)
    
    # For each objective
    for obj_idx in range(2):  # We have 2 objectives
        # Sort by objective value
        sorted_indices = sorted(range(len(front_indices)), 
                              key=lambda i: fitness_values[front_indices[i]][obj_idx])
        
        # Set boundary points to infinity (EDGE PRESERVATION)
        distances[sorted_indices[0]] = float('inf')   # Best in this objective
        distances[sorted_indices[-1]] = float('inf')  # Worst in this objective
        
        # Calculate distances for intermediate solutions
        if len(front_indices) > 2:  # Only for non-trivial fronts
            obj_max = fitness_values[front_indices[sorted_indices[-1]]][obj_idx]
            obj_min = fitness_values[front_indices[sorted_indices[0]]][obj_idx]
            range_val = obj_max - obj_min
            
            if range_val > 0:  # Avoid division by zero
                for i in range(1, len(sorted_indices) - 1):
                    idx = sorted_indices[i]
                    next_fitness = fitness_values[front_indices[sorted_indices[i + 1]]][obj_idx]
                    prev_fitness = fitness_values[front_indices[sorted_indices[i - 1]]][obj_idx]
                    distances[idx] += (next_fitness - prev_fitness) / range_val
    
    return distances


def analyze_population_diversity(population: List[List[float]]) -> Dict[str, Any]:
    """
    Analyze diversity metrics of the current population.
    
    Args:
        population: List of chromosomes (breakpoint lists)
        
    Returns:
        Dictionary of diversity statistics
    """
    segment_counts = [len(chrom) - 1 for chrom in population]
    
    return {
        'min_segments': min(segment_counts),
        'max_segments': max(segment_counts),
        'avg_segments': np.mean(segment_counts),
        'std_segments': np.std(segment_counts),
        'unique_segment_counts': len(set(segment_counts)),
        'segment_range': max(segment_counts) - min(segment_counts)
    }


def batch_fitness_evaluation(population: List[List[float]],
                           fitness_function: callable) -> List[float]:
    """
    Evaluate fitness for entire population in batch.
    
    Args:
        population: List of chromosomes
        fitness_function: Function to evaluate single chromosome fitness
        
    Returns:
        List of fitness values
    """
    return [fitness_function(chrom) for chrom in population]


def batch_multi_objective_fitness(population: List[List[float]],
                                 multi_objective_fitness_function: callable) -> List[Tuple[float, float]]:
    """
    Evaluate multi-objective fitness for entire population in batch.
    
    Args:
        population: List of chromosomes
        multi_objective_fitness_function: Function to evaluate multi-objective fitness
        
    Returns:
        List of fitness tuples
    """
    return [multi_objective_fitness_function(chrom) for chrom in population]