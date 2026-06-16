"""Shared genetic algorithm utilities for highway segmentation analysis.

Reusable GA operator functions shared across single-objective, multi-objective,
and constrained analysis methods. Extracted from GeneticAlgorithm so that each
method module can call these operators directly without instantiating the full
GeneticAlgorithm class.

Fitness sign convention: all functions in this module treat **higher fitness as
better** (maximization semantics). Callers that minimize a raw objective (e.g.,
deviation from mean) must negate it before passing fitness values here, or use a
transformed representation where the best solution has the largest value.
"""

import random
import bisect
import numpy as np
from typing import Callable, List, Tuple, Dict, Any, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config import optimization_config
from app_constants import AlgorithmConstants


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
    front_rank = {}
    for rank, front in enumerate(fronts):
        for idx in front:
            front_rank[idx] = rank

    parents = []
    for _ in range(num_parents):
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
    """Multi-attempt crossover that retries until a valid pair of children is produced.

    Performs physical-cut crossover (see ``perform_single_crossover``) and validates
    each attempt with a fast local segment check before falling back to the full
    ``validate_function``. Returns ``(None, None)`` after
    ``optimization_config.operator_max_retries`` failed attempts.

    When ``validate_function`` is a bound method of a ``GeneticAlgorithm`` instance,
    the fast validator uses the GA's ``min_length``/``max_length`` constraints
    directly instead of calling the full function, which avoids redundant traversal.

    Args:
        parent1: First parent chromosome (sorted list of breakpoint milepoints).
        parent2: Second parent chromosome (sorted list of breakpoint milepoints).
        x_data: Sorted array of all available x-values in the route data.
        mandatory_breakpoints: Breakpoints that must appear in every child;
            crossover operates only on the remaining optional breakpoints.
        validate_function: Callable with signature ``(chromosome: List[float]) -> bool``
            that returns ``True`` when the chromosome satisfies all constraints.

    Returns:
        Tuple of ``(child1, child2)`` on success, or ``(None, None)`` if every
        attempt produced an invalid chromosome.
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

        if fast_validate_physical_cut(child1_bps, cut_point) and fast_validate_physical_cut(child2_bps, cut_point):
            return child1_bps, child2_bps

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
    """Multi-attempt mutation that retries until a valid chromosome is produced.

    Chooses randomly among three mutation actions — add a breakpoint, remove one,
    or move one — and validates the result. When ``validate_function`` is bound to
    a ``GeneticAlgorithm`` instance the mutation is constraint-aware: it restricts
    candidate positions so that both adjacent segments satisfy ``min_length`` /
    ``max_length`` before the validator is even called. Falls back to
    ``perform_single_mutation`` otherwise.

    Returns ``None`` after ``optimization_config.operator_max_retries`` failed
    attempts; the caller is responsible for keeping the original chromosome.

    Args:
        chromosome: Chromosome to mutate (sorted list of breakpoint milepoints).
        x_data: Sorted array of all available x-values in the route data.
        mandatory_breakpoints: Breakpoints that must be preserved across the
            mutation; only optional breakpoints are added, removed, or moved.
        validate_function: Callable with signature ``(chromosome: List[float]) -> bool``
            that returns ``True`` when the chromosome satisfies all constraints.

    Returns:
        A valid mutated chromosome, or ``None`` if all attempts failed.
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
            return mutated

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
    
    if len(optional_breakpoints) <= 1:
        possible = [xp for xp in x_data 
                   if xp not in chrom_set and xp not in mandatory_set]
        if possible:
            new_bp = random.choice(possible)
            new_chrom = sorted(chromosome + [new_bp])
        else:
            return chromosome
    else:
        new_chrom = chromosome.copy()
        action = random.choice(['add', 'remove', 'move'])

        if action == 'add':
            new_chrom_set = set(new_chrom)
            possible = [xp for xp in x_data
                       if xp not in new_chrom_set and xp not in mandatory_set]
            if possible:
                bp = random.choice(possible)
                new_chrom.append(bp)
                new_chrom = sorted(new_chrom)

        elif action == 'remove':
            if optional_breakpoints:
                bp_to_remove = random.choice(optional_breakpoints)
                new_chrom.remove(bp_to_remove)
                
        elif action == 'move':
            if optional_breakpoints:
                bp_to_move = random.choice(optional_breakpoints)
                new_chrom.remove(bp_to_move)
                new_chrom_set = set(new_chrom)
                possible = [xp for xp in x_data
                           if xp not in new_chrom_set and xp not in mandatory_set]
                if possible:
                    new_bp = random.choice(possible)
                    new_chrom.append(new_bp)
                    new_chrom = sorted(new_chrom)
                else:
                    new_chrom.append(bp_to_move)  # restore if no valid replacement exists
                    new_chrom = sorted(new_chrom)
    
    return new_chrom


def fast_non_dominated_sort(population: List[List[float]],
                           multi_objective_fitness_function: callable) -> Tuple[List[List[int]], List[Tuple[float, float]]]:
    """NSGA-II fast non-dominated sorting.

    Evaluates every chromosome and partitions the population into Pareto fronts.
    Front 0 contains non-dominated solutions (no other solution is better in all
    objectives). Front 1 contains solutions dominated only by front 0, and so on.

    Dominance uses maximization semantics (see ``dominates``): a solution that is
    at least as good in every objective and strictly better in one dominates the other.

    Args:
        population: List of chromosomes (sorted breakpoint lists).
        multi_objective_fitness_function: Callable with signature
            ``(chromosome: List[float]) -> Tuple[float, float]`` that returns a
            two-element fitness tuple (higher values are better for both objectives).

    Returns:
        Tuple of ``(fronts, fitness_values)`` where ``fronts`` is a list of
        non-dominated fronts (each front is a list of chromosome indices into
        ``population``) and ``fitness_values`` is the evaluated fitness for every
        chromosome in ``population`` order.
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

    for obj_idx in range(2):
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


def tournament_select(
    population: List[List[float]],
    num_parents: int,
    comparator: Callable[[int, int], bool],
    tournament_size: int = AlgorithmConstants.tournament_size,
) -> List[List[float]]:
    """Tournament selection driven by a caller-supplied comparator.

    Args:
        population: Current population of chromosomes.
        num_parents: Number of parent chromosomes to select.
        comparator: ``comparator(i, j)`` returns True if candidate at index
            ``i`` is strictly better than the candidate at index ``j``.
            Callers bind their fitness/violation state in a closure.
        tournament_size: Number of candidates sampled per tournament.
            Clamped to ``[2, pop_size]`` to ensure competitive selection.

    Returns:
        List of selected parent chromosomes (length == num_parents).
    """
    parents: List[List[float]] = []
    pop_size = len(population)
    if pop_size == 0 or num_parents <= 0:
        return parents

    t_size = min(max(2, tournament_size), pop_size)

    for _ in range(num_parents):
        indices = random.sample(range(pop_size), k=t_size)
        winner = indices[0]
        for idx in indices[1:]:
            if comparator(idx, winner):
                winner = idx
        parents.append(population[winner])

    return parents


def calculate_gap_aware_target(
    mandatory_breakpoints: List[float],
    total_distance: float,
    target_avg_length: float,
    min_length: float,
    max_length: float,
    log: Callable[[str], None],
) -> int:
    """Calculate a realistic target segment count accounting for mandatory breakpoints.

    When mandatory breakpoints subdivide the route (e.g. data gaps or attribute
    boundaries), some segments are pre-determined. This function factors those
    in when deriving how many additional segments the GA should target, and logs
    advisory warnings when the requested average length is physically unreachable.

    Args:
        mandatory_breakpoints: Sorted list of mandatory breakpoint x-values
            (must include route start and end).
        total_distance: Full route length (last x − first x).
        target_avg_length: Desired average segment length.
        min_length: Minimum allowed segment length (for warning threshold).
        max_length: Maximum allowed segment length (for warning threshold).
        log: Callable used for progress/warning messages.

    Returns:
        int: Target segment count (always >= 2).
    """
    if len(mandatory_breakpoints) > 2:
        mandatory_distances = [
            mandatory_breakpoints[i + 1] - mandatory_breakpoints[i]
            for i in range(len(mandatory_breakpoints) - 1)
        ]
        mandatory_total_distance = float(sum(mandatory_distances))
        num_mandatory_segments = len(mandatory_distances)

        remaining_distance = float(total_distance - mandatory_total_distance)
        if remaining_distance > 0:
            total_segments_needed = float(total_distance / max(target_avg_length, 1e-9))
            target_regular_segments = max(0, int(round(total_segments_needed - num_mandatory_segments)))
            target_segments = num_mandatory_segments + target_regular_segments

            required_regular_avg = (
                remaining_distance / target_regular_segments
                if target_regular_segments > 0
                else target_avg_length
            )

            log("Gap-aware calculation:")
            log(f"  Mandatory segments: {num_mandatory_segments} covering {mandatory_total_distance:.2f} miles")
            log(f"  Remaining distance: {remaining_distance:.2f} miles for regular segments")
            log(f"  Target regular segments: {target_regular_segments}")
            log(f"  Required regular avg: {required_regular_avg:.3f} miles to achieve overall {target_avg_length:.2f}")

            if required_regular_avg > max_length * 0.9:
                log(
                    f"  WARNING: Required regular segment avg ({required_regular_avg:.2f}) is near "
                    f"max_length ({max_length:.2f})"
                )
            elif required_regular_avg < min_length * 1.1:
                log(
                    f"  WARNING: Required regular segment avg ({required_regular_avg:.2f}) is near "
                    f"min_length ({min_length:.2f})"
                )
        else:
            target_segments = num_mandatory_segments
            log(f"  All distance covered by mandatory segments: {num_mandatory_segments} segments")
    else:
        target_segments = max(2, int(round(total_distance / max(target_avg_length, 1e-9))))
        log(f"Simple calculation (no gaps): {target_segments} segments for {total_distance:.2f} miles")

    return max(2, int(target_segments))


def build_ga_data_summary(
    ga: Any,
    route_data: Any,
    x_column: str,
    y_column: str,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the standard data_summary dict used by all GA analysis methods.

    Args:
        ga: HighwaySegmentGA instance (post-run, has .route_analysis etc.).
        route_data: Route DataFrame (``data.route_data``).
        x_column: Name of the x-axis column.
        y_column: Name of the y-axis column.
        extra_fields: Optional additional key-value pairs merged into the
            top-level dict (e.g. ``{'target_segments_calculated': n}`` for
            constrained methods).

    Returns:
        data_summary dict ready for inclusion in AnalysisResult.
    """
    if hasattr(ga, 'route_analysis') and ga.route_analysis and hasattr(ga.route_analysis, 'data_range'):
        data_range = ga.route_analysis.data_range
    else:
        data_range = {
            'x_min': float(route_data[x_column].min()),
            'x_max': float(route_data[x_column].max()),
            'y_min': float(route_data[y_column].min()),
            'y_max': float(route_data[y_column].max()),
        }

    has_route_analysis = hasattr(ga, 'route_analysis') and ga.route_analysis
    data_summary: Dict[str, Any] = {
        'total_data_points': len(route_data),
        'data_range': data_range,
        'mandatory_breakpoints': list(ga.mandatory_breakpoints),
        'gap_analysis': {
            'total_gaps': len(ga.route_analysis.gap_segments) if has_route_analysis else 0,
            'gap_segments': [
                {'start': gap[0], 'end': gap[1], 'length': gap[1] - gap[0]}
                for gap in ga.route_analysis.gap_segments
            ] if has_route_analysis else [],
            'total_gap_length': ga.route_analysis.route_stats.get('gap_total_length', 0.0)
            if has_route_analysis else 0.0,
        },
    }

    if extra_fields:
        data_summary.update(extra_fields)

    return data_summary
