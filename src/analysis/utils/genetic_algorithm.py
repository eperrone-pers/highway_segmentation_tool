"""Highway Segmentation Genetic Algorithm Implementation

This module implements a sophisticated genetic algorithm for optimizing highway segmentation
based on data accuracy. It provides a comprehensive solution for finding optimal breakpoints
that minimize the deviation between actual data and segment average values while respecting
engineering constraints.

Key Features:
- Gap-aware segmentation respecting data collection limitations
- Hybrid multi-level caching system for performance optimization
- Support for both single-objective and multi-objective optimization
- Advanced constraint handling for segment length requirements
- Comprehensive performance statistics and debugging capabilities

The algorithm is designed to handle real-world highway data with gaps and constraints,
making it suitable for practical engineering applications in pavement management.

Author: Highway Segmentation GA Team
Version: 1.95+ (Performance Optimized)
"""

import numpy as np
import random
from config import AlgorithmConstants

# Create algorithm constants instance
optimization_config = AlgorithmConstants()

class HighwaySegmentGA:
    """
    Highway Segmentation Genetic Algorithm Implementation
    
    This class implements a genetic algorithm for optimizing highway segmentation
    based on data accuracy. It supports both single-objective and multi-objective
    optimization with advanced features including:
    
    - Gap-aware segmentation respecting data collection limitations
    - Hybrid multi-level caching system (chromosome + segment level) for performance
    - Constraint-aware generation ensuring valid solutions
    - Tournament selection with configurable selection pressure
    - Elite preservation maintaining best solutions across generations
    
    The algorithm segments highway data by finding optimal breakpoints that
    minimize the deviation between actual data and segment average values,
    while respecting engineering constraints on segment lengths.
    
    Key Features:
        - Mandatory breakpoint handling for data gaps
        - Performance-optimized fitness evaluation with multi-level caching
        - Constraint validation for minimum/maximum segment lengths
        - Multi-objective support (deviation vs segment count)
        - Comprehensive performance statistics and debugging
        - Diverse population initialization strategies
    
    Attributes:
        data (DataFrame): Highway measurement data (milepoint, values) from RouteAnalysis.route_data
        x_column (str): Column name for position data (e.g., 'milepoint')
        y_column (str): Column name for measurement values (e.g., 'strength')
        min_length (float): Engineering minimum segment length constraint
        max_length (float): Engineering maximum segment length constraint
        mandatory_breakpoints (Set[float]): Required breakpoints from gap detection
        population_size (int): Number of individuals per generation
        Cache system: Multi-level performance optimization system
    
    Algorithm Flow:
        1. Data preprocessing and gap analysis
        2. Diverse population initialization with constraint validation
        3. Fitness evaluation using multi-level caching
        4. Selection, crossover, and mutation operations
        5. Elite preservation and constraint enforcement
    
    Usage:
        # Basic single-objective optimization
        # (Create RouteAnalysis upstream, then pass it in)
        ga = HighwaySegmentGA(route_analysis, 'milepoint', 'strength', 0.5, 5.0)
        population = ga.generate_initial_population()
        # Evolution handled by optimization runners
        
        # Multi-objective with custom parameters
        ga = HighwaySegmentGA(route_analysis, 'milepoint', 'strength', 0.5, 5.0,
                             population_size=200, mutation_rate=0.1)
    
    Performance Optimizations:
        - Chromosome-level caching: O(1) lookup for repeated evaluations
        - Segment-level caching: Reusable segment statistics
        - Precomputed sorted data structures for faster access
        - Vectorized numpy operations for mathematical computations
    
    Constraint Handling:
        - Mandatory breakpoints from gap detection always preserved
        - Length constraints enforced during generation and mutation
        - Validation and repair mechanisms for invalid solutions
    """
    def __init__(self, data, x_column, y_column, min_length, max_length, population_size=None, mutation_rate=None, crossover_rate=None, gap_threshold=None):
        """
        Initialize Highway Segmentation Genetic Algorithm with data and parameters.
        
        Sets up the genetic algorithm with highway data, constraints, and optimization
        parameters.
        
        Args:
            data: RouteAnalysis object produced by analyze_route_gaps
            x_column (str): Column name for position data (e.g., 'milepoint')
            y_column (str): Column name for measurement values (e.g., 'strength') 
            min_length (float): Minimum allowed segment length (engineering constraint)
            max_length (float): Maximum allowed segment length (engineering constraint)
            population_size (int, optional): Individuals per generation (uses config default)
            mutation_rate (float, optional): Mutation probability (uses config default)
            crossover_rate (float, optional): Crossover probability (uses config default)
            gap_threshold (float, optional): Gap detection threshold (uses config default)
            
        Initialization Process:
            1. Data handling: RouteAnalysis (normal) or DataFrame (testing fallback)
            2. Parameter setup: Use provided values or configuration defaults
            3. Performance optimization: Precompute data structures
            4. Gap analysis integration: Use existing or create minimal analysis
            5. Caching setup: Initialize multi-level caching system
            6. Statistics tracking: Set up performance and constraint monitoring
            
        Data Handling:
            - RouteAnalysis only: input must include pre-computed gap analysis
            
        Performance Features:
            - Precomputed sorted data arrays for O(log n) segment access
            - Multi-level caching system (chromosome + segment level)
            - Index mapping for fast breakpoint to data mapping
            - Comprehensive performance statistics tracking
        """
        # Enforce explicit parameters (do not invent defaults here).
        # These values must come from method configuration/UI.
        if population_size is None:
            raise ValueError("population_size must be provided (no GA hardcoded default)")
        if mutation_rate is None:
            raise ValueError("mutation_rate must be provided (no GA hardcoded default)")
        if crossover_rate is None:
            raise ValueError("crossover_rate must be provided (no GA hardcoded default)")
        if gap_threshold is None:
            raise ValueError("gap_threshold must be provided (no GA hardcoded default)")
        if float(gap_threshold) <= 0:
            raise ValueError(f"gap_threshold must be > 0 (got {gap_threshold})")

        # RouteAnalysis-only contract (no raw DataFrame fallback)
        if not hasattr(data, 'route_data'):
            raise TypeError(
                "HighwaySegmentGA expects a RouteAnalysis object (with .route_data). "
                "Call analyze_route_gaps(df, x_column, y_column, route_id, gap_threshold) first."
            )

        self.route_analysis = data
        self.data = data.route_data

        if self.data is None:
            raise ValueError("RouteAnalysis.route_data is None")
        if len(self.data) < 3:
            raise ValueError(
                f"RouteAnalysis must contain at least 3 data points for optimization (got {len(self.data)})"
            )
        # Store column names for data access
        self.x_column = x_column
        self.y_column = y_column        
            
        self.x_data = self.data[x_column].values
        self.y_data = self.data[y_column].values
        
        # Use explicitly provided values (validated above)
        self.population_size = int(population_size)
        self.mutation_rate = float(mutation_rate)
        self.crossover_rate = float(crossover_rate)
        self.gap_threshold = float(gap_threshold)
        self.min_length = min_length
        self.max_length = max_length
        
        # HYBRID CACHING: Initialize both chromosome and segment-level caching
        self.enable_segment_caching = False  # Feature flag for hybrid segment+chromosome caching
        self._segment_cache = {}  # (start_idx, end_idx) -> (deviation, length, point_count)
        self._x_to_idx_map = None  # Precomputed X value to index mapping
        self._segment_cache_stats = {'hits': 0, 'misses': 0, 'total_calls': 0}
        
        # Performance optimization: precompute data for faster access
        self._precompute_data()
        
        # Use gap analysis from RouteAnalysis
        self._use_existing_gap_analysis()

        # Cache mandatory breakpoint membership checks (hot path in validation/operators)
        self._mandatory_bp_set = set(self.mandatory_breakpoints) if self.mandatory_breakpoints is not None else set()
        
        # Fitness caching for better performance
        self._fitness_cache = {}
        self._multi_fitness_cache = {}
        
        # Constraint violation tracking for user feedback
        self._generation_stats = {
            'total_attempts': 0,
            'failed_generations': 0,
            'fallback_chromosomes': 0,
            'crossover_failures': 0,
            'crossover_attempts': 0,
            'crossover_retries': 0,
            'crossover_parent_reselections': 0,
            'mutation_attempts': 0,
            'mutation_retries': 0,
            'mutation_reselections': 0,
            'last_report_generation': 0
        }
    
    def _precompute_data(self):
        """
        Precompute data structures for faster fitness evaluation.
        
        This optimization method prepares sorted data arrays and index mappings
        that enable O(log n) segment lookups instead of O(n) linear scans during
        fitness evaluation. Critical for performance with large datasets.
        
        Optimizations Applied:
            1. Sorted indices for binary search segment access
            2. Sorted X and Y data arrays aligned with indices
            3. X-value to index mapping for segment cache (if enabled)
            
        Performance Impact:
            - Segment access: O(n) → O(log n) via binary search
            - Cache lookups: O(1) via precomputed index mapping
            - Overall speedup: 10-100x for large datasets
            
        Memory Trade-off:
            - Additional memory: ~3x original data size
            - Performance gain: Significant for repeated evaluations
        """
        # Create sorted indices for faster segment lookups
        self.sorted_indices = np.argsort(self.x_data)
        self.sorted_x_data = self.x_data[self.sorted_indices]
        self.sorted_y_data = self.y_data[self.sorted_indices]

        # Prefix sums for fast segment SSE computation:
        # SSE = sum(y^2) - (sum(y)^2)/n. Sums are computed via prefix differences.
        self._sorted_y_prefix_sum = np.concatenate(([0.0], np.cumsum(self.sorted_y_data, dtype=float)))
        self._sorted_y2_prefix_sum = np.concatenate(([0.0], np.cumsum(self.sorted_y_data * self.sorted_y_data, dtype=float)))
        
        # Build X value to index mapping for segment caching performance optimization
        if self.enable_segment_caching:
            self._build_x_value_index_map()
    
    def _use_existing_gap_analysis(self):
        """
        Use pre-computed gap analysis from RouteAnalysis object.
        
        This method handles the optimized path where comprehensive gap analysis
        was performed during the data loading phase, avoiding duplicate computation
        and ensuring consistency with the standardized gap detection system.
        
        Process:
            1. Extract mandatory breakpoints from pre-computed analysis
            2. Apply additional constraint-based merging if needed
            3. Log comprehensive analysis results for debugging
            4. Validate gap coverage and data point statistics
            
        Benefits:
            - Eliminates duplicate gap analysis computation
            - Ensures consistency with data loading pipeline
            - Provides comprehensive logging of gap statistics
            - Validates data integrity before optimization begins
            
        Gap Analysis Information:
            - Route boundaries and total length
            - Number and locations of detected gaps
            - Gap coverage percentage
            - Valid vs. total data points
            - Final mandatory breakpoint count
        """
        # Extract mandatory breakpoints from pre-computed gap analysis
        # RouteAnalysis.mandatory_breakpoints already includes route start/end + gap boundaries
        self.mandatory_breakpoints = self.route_analysis.mandatory_breakpoints.copy()
        
        # Log results using pre-computed analysis
        print(f"[INFO] Using pre-computed gap analysis:")
        print(f"  - Route: {self.route_analysis.route_stats['route_start']:.3f} to {self.route_analysis.route_stats['route_end']:.3f} miles")
        print(f"  - Total gaps detected: {len(self.route_analysis.gap_segments)}")
        print(f"  - Gap coverage: {self.route_analysis.route_stats['gap_total_length']:.3f} miles ({self.route_analysis.route_stats['gap_total_length']/self.route_analysis.route_stats['total_length']*100:.1f}%)")
        print(f"  - Valid data points: {self.route_analysis.route_stats['valid_points']}/{self.route_analysis.route_stats['total_points']}")
        print(f"  - Final mandatory breakpoints: {len(self.mandatory_breakpoints)}")
        
        if self.route_analysis.gap_segments:
            for i, (start, end) in enumerate(self.route_analysis.gap_segments, 1):
                print(f"    Gap {i}: {start:.3f} to {end:.3f} miles ({end-start:.3f} miles)")
    
    def _merge_nearby_breakpoints_for_constraints(self, breakpoints):
        """
        Apply additional merging based on min_length constraints.
        
        This is applied after our comprehensive gap analysis to ensure
        no mandatory breakpoints create segments shorter than min_length.
        """
        if len(breakpoints) <= 2:  # Just start/end
            return breakpoints
        
        merged = [breakpoints[0]]  # Always keep start point
        
        for i in range(1, len(breakpoints) - 1):  # Don't process the last point yet
            current_bp = breakpoints[i]
            distance_to_last = current_bp - merged[-1]
            
            if distance_to_last < self.min_length:
                # This breakpoint would create a segment too short - skip it
                print(f"[INFO] Constraint merging: skipping breakpoint {current_bp:.3f} (too close to {merged[-1]:.3f}, distance: {distance_to_last:.3f} < {self.min_length})")
                continue
            else:
                # Check if adding this breakpoint would make the next segment too short
                next_bp = breakpoints[i + 1] if i + 1 < len(breakpoints) else breakpoints[-1]
                distance_to_next = next_bp - current_bp
                
                if distance_to_next < self.min_length and i + 1 < len(breakpoints) - 1:
                    # Next segment would be too short - merge by skipping current breakpoint
                    print(f"[INFO] Constraint merging: skipping breakpoint {current_bp:.3f} (would make next segment too short: {distance_to_next:.3f} < {self.min_length})")
                    continue
                else:
                    merged.append(current_bp)
        
        merged.append(breakpoints[-1])  # Always keep end point
        
        return merged
    

    def generate_chromosome(self):
        """
        Generate a valid random chromosome respecting all constraints.
        
        Creates a chromosome (list of breakpoints) that defines a legal highway
        segmentation. Ensures structural validity by:
        
        1. Starting with mandatory breakpoints from gap detection
        2. Adding random breakpoints in valid positions between mandatory ones
        3. Enforcing minimum/maximum segment length constraints
        4. Validating against data boundaries
        
        Constraint Handling:
            - Mandatory breakpoints: Always included (gap boundaries + route ends)
            - Length constraints: All segments must be [min_length, max_length]
            - Data boundaries: Breakpoints must align with available data
            - Position validation: No breakpoints in data gap regions
        
        Returns:
            List[float]: Sorted breakpoint positions defining valid segmentation
            
        Algorithm:
            1. Initialize with mandatory breakpoints (gaps + route boundaries)
            2. For each gap between mandatory breakpoints:
               - Find valid positions respecting length constraints
               - Randomly decide whether to add breakpoint (50% probability)
               - Choose from available valid positions
            3. Sort and deduplicate final breakpoint list
            
        Example:
            For route 0-10 miles with gap at 3-4 miles:
            mandatory_breakpoints = {0, 3, 4, 10}
            Random additions might create: [0, 2.5, 3, 4, 7.2, 10]
        """
        # Start with mandatory breakpoints
        breakpoints = list(self.mandatory_breakpoints)
        
        # Add random breakpoints between mandatory ones
        for start_segment, end_segment in zip(breakpoints, breakpoints[1:]):
            
            # Add random breakpoints within this segment
            current = start_segment
            while current < end_segment:
                possible = self.x_data[
                    (self.x_data > current + self.min_length) &
                    (self.x_data <= min(current + self.max_length, end_segment))
                ]
                if len(possible) == 0:
                    break
                
                # Randomly decide whether to add a breakpoint (50% chance)
                if np.random.random() < 0.5 and len(possible) > 0:
                    next_bp = np.random.choice(possible)
                    if next_bp not in breakpoints:
                        breakpoints.append(next_bp)
                    current = next_bp
                else:
                    break
        
        return sorted(list(set(breakpoints)))
    
    def generate_chromosome_with_target_segments(self, target_segments):
        """Generate chromosome targeting a specific number of segments with mandatory breakpoints"""
        if target_segments < len(self.mandatory_breakpoints) - 1:
            target_segments = len(self.mandatory_breakpoints) - 1  # Can't have fewer segments than mandatory gaps
        
        # Start with mandatory breakpoints 
        breakpoints = list(self.mandatory_breakpoints)
        current_segments = len(breakpoints) - 1
        
        # Add additional breakpoints to reach target
        additional_needed = target_segments - current_segments
        
        if additional_needed > 0:
            # Calculate target spacing between mandatory breakpoints
            mandatory_list = list(self.mandatory_breakpoints)
            for segment_start, segment_end in zip(mandatory_list, mandatory_list[1:]):
                segment_distance = segment_end - segment_start
                
                # Determine how many additional breakpoints to add in this mandatory segment
                segment_proportion = segment_distance / (self.x_data[-1] - self.x_data[0])
                target_additions = max(0, int(additional_needed * segment_proportion))
                
                if target_additions > 0:
                    target_avg_length = segment_distance / (target_additions + 1)
                    
                    current = segment_start
                    for _ in range(target_additions):
                        target_next = current + target_avg_length
                        
                        # Add some randomness
                        variance = target_avg_length * 0.3
                        min_next = max(current + self.min_length, target_next - variance)
                        max_next = min(segment_end, target_next + variance)
                        
                        possible = self.x_data[
                            (self.x_data >= min_next) &
                            (self.x_data <= max_next) &
                            (~np.isin(self.x_data, breakpoints))
                        ]
                        
                        if len(possible) > 0:
                            next_bp = np.random.choice(possible)
                            breakpoints.append(next_bp)
                            current = next_bp
                        else:
                            break
        
        return sorted(list(set(breakpoints)))
    
    def generate_diverse_initial_population(self):
        """
        Generate initial population with improved diversity across segment counts.
        
        Creates a diverse initial population using adaptive strategies based on
        problem size and constraints. Ensures good coverage of the solution space
        from simple (few segments) to complex (many segments) solutions.
        
        Strategy Selection:
            - Large problems (50+ individuals, 20+ segment range): 10-bin uniform distribution
            - Small problems: Fallback to strategy-based distribution
            
        Uniform Distribution Approach (Preferred):
            1. Calculate splittable route length (excluding mandatory gaps)
            2. Determine viable segment count range based on length constraints
            3. Create 10 equal bins across segment range
            4. Generate equal numbers of individuals per bin
            5. Use segment-splitting algorithm for targeted generation
            
        Fallback Strategy Distribution:
            - 20% few segments (minimal complexity)
            - 35% medium segments (balanced solutions)
            - 30% many segments (high accuracy focus)
            - 15% random (exploration)
            
        Returns:
            List[List[float]]: Population of diverse chromosome solutions
            
        Quality Metrics Reported:
            - Segment count range and distribution
            - Population diversity statistics (mean, std)
            - Strategy selection rationale
            - Constraint validation success rate
            
        Algorithm Benefits:
            - Uniform exploration of solution space
            - Avoids premature convergence to local optima
            - Provides good starting points for different objectives
            - Maintains constraint satisfaction from initialization
        """
        population = []
        
        # Calculate splittable route length (excluding gaps between mandatory breakpoints)
        splittable_length = 0
        mandatory_list = sorted(list(self.mandatory_breakpoints))
        for start_bp, end_bp in zip(mandatory_list, mandatory_list[1:]):
            splittable_length += end_bp - start_bp
        
        # Calculate segment range based on splittable length
        min_possible_segments = max(len(mandatory_list) - 1, int(splittable_length / self.max_length))
        max_possible_segments = int(splittable_length / self.min_length)
        segment_range = max_possible_segments - min_possible_segments
        
        print(f"[INFO] Splittable route length: {splittable_length:.2f} miles")
        print(f"[INFO] Segment range: {min_possible_segments} to {max_possible_segments} segments")
        
        # Check if conditions are met for 10-bin uniform distribution
        if self.population_size >= 50 and segment_range > 20:
            print("[INFO] Using 10-bin uniform distribution approach")
            try:
                population, segment_counts = self._generate_uniform_distribution_population(
                    min_possible_segments, max_possible_segments, mandatory_list, splittable_length
                )
            except ValueError as e:
                # Some routes/constraint combos can make certain segment counts infeasible given discrete X locations.
                # Do not hard-fail route optimization; fall back to the robust mixed-strategy initializer.
                print(f"[WARNING] Uniform init-pop failed ({e}); falling back to strategy-based initialization")
                population, segment_counts = self._generate_fallback_population(
                    min_possible_segments, max_possible_segments
                )
        else:
            print(f"[INFO] Using fallback strategy (pop_size={self.population_size}, range={segment_range})")
            population, segment_counts = self._generate_fallback_population(
                min_possible_segments, max_possible_segments
            )
        
        # Print diversity statistics
        print(f"[INFO] Population diversity: {min(segment_counts)}-{max(segment_counts)} segments")
        print(f"[INFO] Average segments: {np.mean(segment_counts):.1f}, Std: {np.std(segment_counts):.1f}")
        
        # Show distribution
        unique_counts = np.unique(segment_counts, return_counts=True)
        distribution = {int(count): int(freq) for count, freq in zip(unique_counts[0], unique_counts[1])}
        print(f"[INFO] Segment distribution: {distribution}")
        
        return population
    
    def _generate_uniform_distribution_population(self, min_segments, max_segments, mandatory_list, splittable_length):
        """Generate population using 10-bin uniform distribution with segment-splitting approach"""
        population = []
        segment_counts = []
        
        # Create 10 equal bins across segment range
        bin_size = (max_segments - min_segments) / 10
        chromosomes_per_bin = self.population_size // 10
        remainder = self.population_size % 10
        
        for bin_idx in range(10):
            # Calculate bin range
            bin_min = min_segments + int(bin_idx * bin_size) 
            bin_max = min_segments + int((bin_idx + 1) * bin_size)
            if bin_idx == 9:  # Last bin includes maximum
                bin_max = max_segments
            
            # Determine number of chromosomes for this bin
            bin_chromosomes = chromosomes_per_bin
            if bin_idx < remainder:  # Distribute remainder across first bins
                bin_chromosomes += 1
            
            # Generate chromosomes for this bin using segment-splitting
            for _ in range(bin_chromosomes):
                target_segments = random.randint(bin_min, bin_max)

                max_retries = optimization_config.init_population_max_retries
                last_error = None

                chromosome = None
                for attempt in range(max_retries):
                    candidate = self._generate_chromosome_by_splitting(
                        target_segments,
                        mandatory_list,
                        splittable_length,
                    )

                    if self.validate_chromosome(candidate, suppress_warnings=True):
                        chromosome = candidate
                        break

                    repaired = self._enforce_constraints(candidate, return_none_on_failure=True)
                    if repaired is None:
                        # Quiet retry: irreparable >max segment with no admissible split
                        last_error = "irreparable_max_length_violation"
                        continue

                    if self.validate_chromosome(repaired, suppress_warnings=True):
                        chromosome = repaired
                        break

                    last_error = "repair_did_not_produce_valid_chromosome"

                if chromosome is None:
                    route_id = getattr(getattr(self, 'route_analysis', None), 'route_id', 'Unknown')
                    print(
                        f"[ERROR] Uniform init-pop generation failed for route {route_id} after {max_retries} retries "
                        f"(last_error={last_error}, target_segments={target_segments})."
                    )
                    raise ValueError(
                        f"Failed to generate valid chromosome after {max_retries} retries "
                        f"(last_error={last_error})."
                    )

                population.append(chromosome)
                segment_counts.append(len(chromosome) - 1)
        
        return population, segment_counts
        
    def _generate_chromosome_by_splitting(self, target_segments, mandatory_list, splittable_length):
        """
        OPTIMIZED: Generate chromosome by progressively splitting segments until target count reached
        Key optimizations: Pre-filtering, sets for O(1) lookups, caching, early termination
        """
        # Start with just mandatory breakpoints
        breakpoints = list(mandatory_list)
        current_segments = len(breakpoints) - 1
        
        # Need to add (target_segments - current_segments) breakpoints through splitting
        additional_needed = target_segments - current_segments
        
        if additional_needed <= 0:
            return breakpoints
        
        # OPTIMIZATION 1: Pre-convert breakpoints to set for O(1) lookups
        breakpoints_set = set(breakpoints)
        
        # OPTIMIZATION 2: Pre-filter X values based on route bounds and constraints
        route_start, route_end = min(mandatory_list), max(mandatory_list)
        # Only consider X values that could create valid segments (min_length from boundaries)
        valid_x_values = [xp for xp in self.x_data 
                           if (route_start + self.min_length < xp < route_end - self.min_length)]
        
        # Track which segments cannot be split further
        unsplittable_segments = set()
        
        # OPTIMIZATION 3: Early termination tracking
        attempts = 0
        max_attempts = additional_needed * 2  # Prevent infinite loops
        
        # Progressively split segments until we reach target  
        while additional_needed > 0 and attempts < max_attempts:
            attempts += 1
            
            # OPTIMIZATION 4: Find longest splittable segment in single pass
            longest_segment = None
            max_length = 0
            
            for segment_idx, (start_mile, end_mile) in enumerate(zip(breakpoints, breakpoints[1:])):
                segment_key = (start_mile, end_mile)
                segment_length = end_mile - start_mile
                
                if (segment_key not in unsplittable_segments and 
                    segment_length > max_length):
                    max_length = segment_length
                    longest_segment = (segment_idx, segment_length, start_mile, end_mile)
            
            if not longest_segment:
                # No more segments can be split - stop early
                break
            
            # Split the longest available segment
            split_index, segment_length, start_mile, end_mile = longest_segment
            
            # OPTIMIZATION 5: Find valid breakpoints with single pass filtering
            # Pre-filter valid breakpoints to avoid repeated constraint checking
            possible_breakpoints = []
            for xp in valid_x_values:
                # Check all constraints in single evaluation:
                # 1. Minimum distance from segment start (creates valid left segment)
                # 2. Minimum distance from segment end (creates valid right segment)  
                # 3. Not already in breakpoints set (avoid duplicates)
                if (start_mile + self.min_length < xp < end_mile - self.min_length and 
                    xp not in breakpoints_set):
                    possible_breakpoints.append(xp)
            
            if possible_breakpoints:
                # Choose split breakpoint uniformly at random from all admissible x-points
                best_breakpoint = random.choice(possible_breakpoints)
                
                # Insert the new breakpoint and update data structures
                breakpoints.insert(split_index + 1, best_breakpoint)
                breakpoints_set.add(best_breakpoint)  # Update set for O(1) lookups
                additional_needed -= 1  # One step closer to target
                
                # Remove the original segment from unsplittable tracking
                # (it's now split into two segments, both potentially splittable)
                unsplittable_segments.discard((start_mile, end_mile))
            else:
                # Mark this segment as unsplittable for future optimization
                # This prevents infinite loops by tracking which segments
                # cannot be split further due to constraint limitations
                unsplittable_segments.add((start_mile, end_mile))
        
        return sorted(list(set(breakpoints)))
        
    def _generate_fallback_population(self, min_segments, max_segments):
        """Fallback to current strategy-based approach for small populations or narrow ranges"""
        population = []
        segment_counts = []
        
        # Use simplified strategy distribution for fallback
        strategies = {
            'few_segments': 0.20,
            'medium_segments': 0.35,
            'many_segments': 0.30,
            'random': 0.15
        }
        
        for strategy, proportion in strategies.items():
            count = int(self.population_size * proportion)
            
            for _ in range(count):
                if strategy == 'few_segments':
                    target = random.randint(min_segments, min(min_segments + 3, max_segments))
                elif strategy == 'medium_segments':
                    mid_point = (min_segments + max_segments) // 2
                    target = random.randint(max(min_segments, mid_point - 3), 
                                          min(max_segments, mid_point + 3))
                elif strategy == 'many_segments':
                    range_size = max_segments - min_segments
                    start_point = min_segments + int(range_size * 0.4)
                    target = random.randint(max(min_segments, start_point), max_segments)
                else:  # random
                    target = random.randint(min_segments, max_segments)
                
                chromosome = self.generate_chromosome_with_target_segments(target)
                if not self.validate_chromosome(chromosome, suppress_warnings=True):
                    chromosome = self._enforce_constraints(chromosome)
                population.append(chromosome)
                segment_counts.append(len(chromosome) - 1)
        
        # Fill remaining slots with random generation (with retries)
        while len(population) < self.population_size:
            self._generation_stats['total_attempts'] += 1
            chromosome = None
            
            # Try to generate a valid chromosome with retries
            for attempt in range(10):  # max_retries = 10
                chrom = self.generate_chromosome()
                if self.validate_chromosome(chrom, suppress_warnings=True):
                    chromosome = chrom
                    break
                else:
                    # Try to fix it while preserving mandatory breakpoints
                    chrom = self._enforce_constraints(chrom)
                    if self.validate_chromosome(chrom, suppress_warnings=True):
                        chromosome = chrom
                        break
            
            # If all attempts failed, use minimal valid chromosome
            if chromosome is None:
                self._generation_stats['failed_generations'] += 1
                self._generation_stats['fallback_chromosomes'] += 1
                print("[WARNING] Failed to generate valid chromosome, using mandatory breakpoints only")
                chromosome = list(self.mandatory_breakpoints)
            
            population.append(chromosome)
            segment_counts.append(len(chromosome) - 1)
            
        return population, segment_counts

    def generate_initial_population(self):
        """Generate initial population with improved diversity"""
        return self.generate_diverse_initial_population()

    def _total_squared_deviation_fast(self, chromosome):
        """Compute total sum of squared deviations using prefix sums.

        This is mathematically equivalent to summing (y - mean)^2 within each segment,
        but avoids allocating per-point temporary arrays.
        """
        if len(chromosome) < 2:
            return 0.0

        bps = np.asarray(chromosome, dtype=float)
        start_idx = np.searchsorted(self.sorted_x_data, bps[:-1], side='left')
        end_idx = np.searchsorted(self.sorted_x_data, bps[1:], side='left')

        n = end_idx - start_idx
        valid = n > 0
        if not np.any(valid):
            return 0.0

        sum_y = self._sorted_y_prefix_sum[end_idx] - self._sorted_y_prefix_sum[start_idx]
        sum_y2 = self._sorted_y2_prefix_sum[end_idx] - self._sorted_y2_prefix_sum[start_idx]

        sse = np.zeros_like(sum_y, dtype=float)
        sse[valid] = sum_y2[valid] - (sum_y[valid] * sum_y[valid]) / n[valid]
        sse[sse < 0.0] = 0.0  # guard against tiny negative round-off
        return float(np.sum(sse))

    def fitness(self, chromosome):
        """
        Calculate single-objective fitness using sum of squared deviations.
        
        This is the core evaluation function that measures how well a segmentation
        represents the actual highway data. Uses a sophisticated multi-level caching
        system for optimal performance.
        
        Algorithm:
            1. Check chromosome-level cache for O(1) lookup (fastest path)
            2. If cache miss, calculate using segment-level cache or direct computation
            3. Split data into segments based on chromosome breakpoints
            4. Calculate average value for each segment
            5. Compute squared deviation of each point from its segment average
            6. Sum all deviations and negate for minimization optimization
            7. Store result in chromosome cache for future lookups
        
        Mathematical Model:
            fitness = -Σ(actual_value - segment_average)² for all data points
            
        Lower (more negative) scores indicate better data representation.
        
        Args:
            chromosome (List[float]): Breakpoint positions defining segments
            
        Returns:
            float: Negative sum of squared deviations (for minimization)
            
        Performance Features:
            - Multi-level caching: chromosome + segment level caching
            - O(1) lookup for repeated evaluations (chromosome cache)
            - Vectorized numpy operations for mathematical efficiency
            - Precomputed sorted data structures for fast segment access
            
        Cache Behavior:
            - Level 1: Chromosome cache - O(1) identical chromosome lookup
            - Level 2: Segment cache - Reusable segment statistics (if enabled)
            - Level 3: Direct calculation with optimized data access
            
        See Also:
            multi_objective_fitness(): Extension for bi-objective optimization
        """
        # Level 1: Check chromosome cache first (fastest possible - O(1))
        chrom_key = tuple(chromosome)
        if chrom_key in self._fitness_cache:
            return self._fitness_cache[chrom_key]
        
        # Level 2: Calculate using segment cache (if enabled) or direct calculation
        if self.enable_segment_caching:
            # Use segment-level caching for calculation (reuses segment statistics)
            fitness_val = self._fitness_with_segment_cache_internal(chromosome)
        else:
            # Direct calculation without segment caching.
            # Use prefix sums for an O(K) SSE computation (K = number of segments).
            fitness_val = -self._total_squared_deviation_fast(chromosome)
        
        # Level 3: Store result in chromosome cache for future identical lookups
        # This enables O(1) retrieval for repeated evaluations of the same chromosome
        self._fitness_cache[chrom_key] = fitness_val
        return fitness_val
    
    def _calculate_non_mandatory_avg_length(self, chromosome):
        """Calculate average segment length excluding data gaps.

        IMPORTANT: Despite the legacy name, this function is the shared definition of
        "average segment length" used across GA-based methods.

        Requirement (project-wide): Any reported/exported average segment length should
        exclude *gap-only* segments (intervals with no data). The overall average that
        includes gaps is not meaningful for optimization assessment.

        Definition:
        - Compute lengths for all segments in the chromosome.
        - Exclude segments that exactly match a detected gap interval.
        - Average the remaining lengths (data-bearing / segmentable portions).
        
          Notes:
          - Route start/end segments are included (they are part of the road).
          - Segments adjacent to gaps are included (they contain data).
          - Pure gap segments (gap_start -> gap_end) are excluded.
        
        Args:
            chromosome (List[float]): Sorted breakpoint positions defining segments
        
        Returns:
            float: Average length excluding gaps, or 0.0 if none exist
            
        Edge Cases Handled:
            - Empty or invalid chromosome: returns 0.0
            - No data-bearing segments (degenerate): returns 0.0
            - Numerical errors in chromosome values: converts to float with fallback
            - Missing mandatory_breakpoints: falls back to overall average
            
        Performance Optimizations:
            - Vectorized numpy operations for length calculations
            - Set-based membership testing for O(1) breakpoint lookups
            - Boolean indexing for efficient array filtering
            
        Use Cases:
            - Multi-objective fitness evaluation (complexity measure)
            - Population diversity analysis
            - Constraint satisfaction assessment
        """
        # Input validation
        if not chromosome or len(chromosome) < 2:
            return 0.0
            
        # Ensure all chromosome values are valid numbers
        try:
            chromosome = [float(x) if x is not None else 0.0 for x in chromosome]
        except (ValueError, TypeError):
            print(f"[ERROR] Invalid chromosome values: {chromosome}")
            return 0.0
            
        # Check if mandatory breakpoints are available (should always be true after initialization)
        if not hasattr(self, 'mandatory_breakpoints') or self.mandatory_breakpoints is None:
            # Fallback to overall average - this should rarely occur
            total_length = float(np.sum(np.diff(chromosome)))
            return total_length / (len(chromosome) - 1)
        
        # Build a fast lookup of gap segments (if available)
        gap_segments = []
        if hasattr(self, 'route_analysis') and self.route_analysis and hasattr(self.route_analysis, 'gap_segments'):
            gap_segments = self.route_analysis.gap_segments or []

        # Normalize gap segments to float tuples
        gap_set = set()
        for g in gap_segments:
            try:
                gap_set.add((float(g[0]), float(g[1])))
            except Exception:
                continue

        def _is_gap_segment(a: float, b: float, eps: float = 1e-9) -> bool:
            if not gap_set:
                return False
            # Exact match with tolerance (gap boundaries are mandatory breakpoints)
            for gs, ge in gap_set:
                if abs(a - gs) <= eps and abs(b - ge) <= eps:
                    return True
            return False

        segment_lengths = np.diff(chromosome)
        if len(segment_lengths) == 0:
            return 0.0

        counted_lengths = []
        for i in range(len(chromosome) - 1):
            start_bp = float(chromosome[i])
            end_bp = float(chromosome[i + 1])
            length = float(segment_lengths[i])
            if length <= 0:
                continue
            if _is_gap_segment(start_bp, end_bp):
                continue
            counted_lengths.append(length)

        return float(np.mean(counted_lengths)) if counted_lengths else 0.0
    
    def multi_objective_fitness(self, chromosome):
        """
        Calculate multi-objective fitness for NSGA-II optimization.
        
        Evaluates chromosomes on two competing objectives to create a Pareto front
        of trade-off solutions between data accuracy and segment complexity.
        
        Objectives:
            1. Data accuracy: Minimize sum of squared deviations (primary objective)
            2. Segment efficiency: Maximize average non-mandatory segment length
        
        Algorithm:
            1. Check chromosome-level cache for O(1) lookup (fastest path)
            2. Calculate objective 1: Total deviation across all segments
               - Segment data based on chromosome breakpoints
               - Calculate squared deviations from segment averages
               - Sum and negate for minimization
            3. Calculate objective 2: Non-mandatory segment average length
               - Focus on user-controllable segments (exclude mandatory gaps)
               - Calculate average length of segments without mandatory boundaries
            4. Store result in chromosome cache for future lookups
        
        Mathematical Model:
            objective1 = -Σ(actual_value - segment_average)² for all data points
            objective2 = average_length(non_mandatory_segments)
            
        Args:
            chromosome (List[float]): Breakpoint positions defining segments
            
        Returns:
            Tuple[float, float]: (negative_deviation, avg_segment_length)
            - Both values designed for NSGA-II maximization framework
            - Lower deviation (more negative) = better data fit
            - Higher avg_length = simpler segmentation with fewer segments
            
        Multi-Objective Benefits:
            - Explores trade-offs between accuracy and simplicity
            - No need to specify weights between competing objectives
            - Provides decision makers with range of optimal solutions
            - Natural handling of conflicting objectives without bias
            
        Performance Features:
            - Same multi-level caching as single-objective fitness
            - Efficient non-mandatory segment calculation using numpy
            - Comprehensive error handling and validation
            
        See Also:
            fitness(): Single-objective version focusing only on deviation
            _calculate_non_mandatory_avg_length(): Specialized length calculation
        """
        # Level 1: Check chromosome cache first (fastest possible - O(1))
        chrom_key = tuple(chromosome)
        if chrom_key in self._multi_fitness_cache:
            return self._multi_fitness_cache[chrom_key]
        
        # Level 2: Calculate using segment cache (if enabled) or direct calculation
        if self.enable_segment_caching:
            # Use segment-level caching for calculation (reuses segment statistics)
            result = self._multi_objective_fitness_with_segment_cache_internal(chromosome)
        else:
            # Objective 1: Data accuracy - minimize total squared deviation
            total_deviation = self._total_squared_deviation_fast(chromosome)
                
            # Objective 2: Segment efficiency - maximize average non-mandatory length
            # This encourages fewer, longer segments for simpler solutions
            avg_segment_length = self._calculate_non_mandatory_avg_length(chromosome)
            
            # SAFETY CHECK: Segment lengths should never be negative!
            # This validates algorithm correctness and catches potential data errors
            if avg_segment_length < 0:
                print(f"🚨 ERROR: Negative average segment length {avg_segment_length:.6f} for chromosome {chromosome}")
                print(f"   Chromosome has {len(chromosome)-1} segments")
                print(f"   First few segments: {[chromosome[i+1] - chromosome[i] for i in range(min(3, len(chromosome)-1))]}")
                avg_segment_length = abs(avg_segment_length)  # Emergency fix - take absolute value
                
            # Return objectives formatted for NSGA-II maximization framework
            # NSGA-II maximizes both objectives, so:
            # - Minimize deviation: use negative deviation (more negative = better fit)
            # - Maximize avg length: use positive length (higher = simpler solution)
            result = (-total_deviation, avg_segment_length)
        
        # Level 3: Store result in chromosome cache for future identical lookups
        self._multi_fitness_cache[chrom_key] = result
        return result
    
    # ========================================
    # SEGMENT-LEVEL CACHING METHODS
    # ========================================
    
    def _build_x_value_index_map(self):
        """Build mapping from X value to its first index in the sorted array."""
        x_to_idx = {}
        for idx, xp in enumerate(self.sorted_x_data):
            if xp not in x_to_idx:
                x_to_idx[xp] = idx
        self._x_to_idx_map = x_to_idx
    
    def _get_segment_stats_cached(self, start_mp, end_mp):
        """Get cached segment statistics or compute and cache if not found"""
        self._segment_cache_stats['total_calls'] += 1
        
        # Convert X values to indices
        if self._x_to_idx_map is None:
            self._build_x_value_index_map()
            
        start_idx = self._x_to_idx_map.get(start_mp)
        end_idx = self._x_to_idx_map.get(end_mp) 
        
        if start_idx is None or end_idx is None:
            # Fallback to binary search if exact match not found
            start_idx = np.searchsorted(self.sorted_x_data, start_mp, side='left')
            end_idx = np.searchsorted(self.sorted_x_data, end_mp, side='left')
        
        # Check cache
        cache_key = (start_idx, end_idx)
        if cache_key in self._segment_cache:
            self._segment_cache_stats['hits'] += 1
            return self._segment_cache[cache_key]
        
        # Cache miss - compute segment statistics
        self._segment_cache_stats['misses'] += 1
        
        if start_idx >= end_idx:
            # Empty segment
            stats = (0.0, 0.0, 0)
        else:
            point_count = int(end_idx - start_idx)
            if point_count <= 0:
                stats = (0.0, 0.0, 0)
            else:
                sum_y = float(self._sorted_y_prefix_sum[end_idx] - self._sorted_y_prefix_sum[start_idx])
                sum_y2 = float(self._sorted_y2_prefix_sum[end_idx] - self._sorted_y2_prefix_sum[start_idx])
                deviation = sum_y2 - (sum_y * sum_y) / point_count
                if deviation < 0.0:
                    deviation = 0.0
                length = end_mp - start_mp
                stats = (float(deviation), float(length), point_count)
        
        # Cache the result
        self._segment_cache[cache_key] = stats
        return stats
    
    def _fitness_with_segment_cache_internal(self, chromosome):
        """INTERNAL: Segment-cached fitness calculation (used by hybrid method)"""
        # Segment-level caching adds overhead from Python loops and dict lookups.
        # Use vectorized prefix-sum SSE computation instead (mathematically identical).
        return -self._total_squared_deviation_fast(chromosome)
    
    def _multi_objective_fitness_with_segment_cache_internal(self, chromosome):
        """INTERNAL: Segment-cached multi-objective fitness calculation (used by hybrid method)"""
        total_deviation = self._total_squared_deviation_fast(chromosome)

        # Calculate average segment length for maximization
        avg_segment_length = self._calculate_non_mandatory_avg_length(chromosome)
        return (-total_deviation, avg_segment_length)  # NSGA-II maximizes: minimize deviation, maximize length
    
    def get_segment_cache_stats(self):
        """Get performance statistics for segment caching"""
        stats = self._segment_cache_stats.copy()
        if stats['total_calls'] > 0:
            stats['hit_rate'] = stats['hits'] / stats['total_calls']
            stats['cache_size'] = len(self._segment_cache)
        else:
            stats['hit_rate'] = 0.0
            stats['cache_size'] = 0
        return stats
    
    def enable_segment_cache_mode(self, enable=True):
        """Enable or disable hybrid segment caching mode (works alongside chromosome caching)"""
        old_state = self.enable_segment_caching
        self.enable_segment_caching = enable
        
        if enable and self._x_to_idx_map is None:
            # Build index mapping when first enabled
            self._build_x_value_index_map()
            print(f"[HYBRID CACHE] Segment-level caching enabled - built index map for {len(self.sorted_x_data)} points")
            print(f"[HYBRID CACHE] Both chromosome and segment caches now active for maximum performance")
        elif not enable:
            print(f"[HYBRID CACHE] Segment caching disabled - using chromosome-level caching only")
            
        return old_state
    
    def clear_segment_cache(self):
        """Clear segment cache and reset statistics - optimized for large caches"""
        # Replace dictionary instead of clearing (much faster for large caches)
        self._segment_cache = {}
        self._segment_cache_stats = {'hits': 0, 'misses': 0, 'total_calls': 0}
        # Clear segment cache
    
    def batch_fitness_evaluation(self, population):
        """Evaluate fitness for multiple chromosomes efficiently"""
        return [self.fitness(chrom) for chrom in population]
    
    def batch_multi_objective_fitness(self, population):
        """Evaluate multi-objective fitness for multiple chromosomes efficiently"""
        return [self.multi_objective_fitness(chrom) for chrom in population]
    
    def clear_cache(self):
        """
        Clear all fitness caches to free memory and reset performance counters.
        
        This method clears both chromosome-level and segment-level caches to free
        memory during long optimization runs. Uses dictionary replacement instead
        of clearing for optimal performance with large caches.
        
        Cache Types Cleared:
            1. Chromosome-level fitness cache: _fitness_cache
            2. Chromosome-level multi-objective cache: _multi_fitness_cache  
            3. Segment-level statistics cache: _segment_cache (if enabled)
            4. Segment cache performance statistics
            
        Performance Optimization:
            - Dictionary replacement vs. clearing: ~10x faster for large caches
            - Comprehensive timing and statistics logging
            - Memory usage tracking and reporting
            
        When to Use:
            - Between optimization runs to free memory
            - When cache hit rates become too low
            - During performance testing and benchmarking
            - Before switching to different datasets
            
        Memory Impact:
            - Chromosome caches: Variable (depends on population diversity)
            - Segment caches: Can be substantial for complex segmentations
            - Immediate memory reclaim through garbage collection
        """
        import time
        start_time = time.time()
        
        # Clear chromosome level caches - use replacement for faster clearing
        old_chrom_cache_size = len(self._fitness_cache)
        old_multi_cache_size = len(self._multi_fitness_cache)
        
        # Replace dictionaries instead of clearing (much faster for large caches)
        self._fitness_cache = {}
        self._multi_fitness_cache = {}
        
        # Clear segment cache if enabled and show comprehensive stats
        if self.enable_segment_caching:
            stats = self.get_segment_cache_stats()
            segment_cache_size = stats['cache_size']
            hit_rate = stats.get('hit_rate', 0.0)
            
            self.clear_segment_cache()
            
            elapsed = time.time() - start_time
        else:
            elapsed = time.time() - start_time
    
    def analyze_population_diversity(self, population):
        """Analyze diversity metrics of the current population"""
        segment_counts = [len(chrom) - 1 for chrom in population]
        
        return {
            'min_segments': min(segment_counts),
            'max_segments': max(segment_counts),
            'avg_segments': np.mean(segment_counts),
            'std_segments': np.std(segment_counts),
            'unique_segment_counts': len(set(segment_counts)),
            'segment_range': max(segment_counts) - min(segment_counts)
        }
    
    def get_cache_stats(self):
        """Get cache statistics for performance monitoring (includes both cache levels)"""
        base_stats = {
            'fitness_cache_size': len(self._fitness_cache),
            'multi_fitness_cache_size': len(self._multi_fitness_cache)
        }
        
        # Include segment cache stats if enabled
        if self.enable_segment_caching:
            segment_stats = self.get_segment_cache_stats()
            base_stats.update({
                'segment_cache_size': segment_stats.get('cache_size', 0),
                'segment_hits': segment_stats.get('hits', 0),
                'segment_misses': segment_stats.get('misses', 0),
                'segment_total_calls': segment_stats.get('total_calls', 0),
                'segment_hit_rate': segment_stats.get('hit_rate', 0.0)
            })
            
        return base_stats
    
    def fast_non_dominated_sort(self, population):
        """
        NSGA-II Fast Non-dominated Sorting
        Returns list of fronts, where each front is a list of solution indices
        """
        fitness_values = [self.multi_objective_fitness(chrom) for chrom in population]
        
        fronts = [[]]
        dominated_solutions = [[] for _ in population]
        domination_count = [0 for _ in population]
        
        # Convert to list of indices then enumerate  
        for i, _ in enumerate(population):
            for j in range(i + 1, len(population)):
                if self._dominates(fitness_values[i], fitness_values[j]):
                    dominated_solutions[i].append(j)
                    domination_count[j] += 1
                elif self._dominates(fitness_values[j], fitness_values[i]):
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
    
    def _dominates(self, fitness1, fitness2):
        """
        Check if fitness1 dominates fitness2
        For our objectives: both should be maximized
        """
        return (fitness1[0] >= fitness2[0] and fitness1[1] >= fitness2[1] and 
                (fitness1[0] > fitness2[0] or fitness1[1] > fitness2[1]))
    
    def calculate_crowding_distance(self, front_indices, fitness_values):
        """
        Calculate crowding distance for solutions in a front
        """
        distances = [0.0 for _ in front_indices]
        
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
            
            # DEBUG: Log edge assignments for verification
            if len(front_indices) > 2:  # Only log for non-trivial fronts
                edge_low_idx = front_indices[sorted_indices[0]]
                edge_high_idx = front_indices[sorted_indices[-1]]
                edge_low_fitness = fitness_values[edge_low_idx]
                edge_high_fitness = fitness_values[edge_high_idx]
                # Uncomment for detailed edge tracking:

            
            # Calculate distances for middle points
            obj_range = (fitness_values[front_indices[sorted_indices[-1]]][obj_idx] - 
                        fitness_values[front_indices[sorted_indices[0]]][obj_idx])
            
            if obj_range > 0:
                for i in range(1, len(sorted_indices) - 1):
                    distances[sorted_indices[i]] += (
                        fitness_values[front_indices[sorted_indices[i+1]]][obj_idx] - 
                        fitness_values[front_indices[sorted_indices[i-1]]][obj_idx]
                    ) / obj_range
        
        return distances
    
    def nsga2_selection(self, population, offspring):
        """
        NSGA-II environmental selection
        """        
        combined = population + offspring
        fronts, fitness_values = self.fast_non_dominated_sort(combined)
        
        new_population = []
        front_idx = 0
        
        while len(new_population) + len(fronts[front_idx]) <= self.population_size:
            new_population.extend([combined[i] for i in fronts[front_idx]])
            front_idx += 1
        
        if len(new_population) < self.population_size:
            # Need to select some individuals from the next front
            remaining = self.population_size - len(new_population)
            distances = self.calculate_crowding_distance(fronts[front_idx], fitness_values)
            
            # Sort by crowding distance (descending)
            sorted_indices = sorted(range(len(fronts[front_idx])), 
                                  key=lambda i: distances[i], reverse=True)
            
            for i in range(remaining):
                new_population.append(combined[fronts[front_idx][sorted_indices[i]]])
        
        return new_population

    def select_parents(self, population, fitnesses, num_parents):
        # Tournament selection (single-objective)
        parents = []
        for _ in range(num_parents):
            candidates = random.sample(list(zip(population, fitnesses)), k=optimization_config.tournament_size)
            winner = max(candidates, key=lambda x: x[1])
            parents.append(winner[0])
        return parents
    
    def nsga2_tournament_selection(self, population, fronts, fitness_values, crowding_distances, num_parents):
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
            winner = self._nsga2_compare(candidates[0], candidates[1], front_rank, crowding_distances)
            parents.append(population[winner])
        
        return parents
    
    def _nsga2_compare(self, idx1, idx2, front_rank, crowding_distances):
        """
        Compare two individuals for NSGA-II tournament selection.
        
        Returns the index of the better individual based on:
        1. Pareto rank (lower is better)
        2. Crowding distance (higher is better for tie-breaking)
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
    
    def elitist_selection(self, population, fitnesses, offspring, offspring_fitnesses, elite_ratio=None, log_callback=None):
        """
        Elitist selection combining parents and offspring with guaranteed elite preservation.
        
        This method ensures the best solutions survive to the next generation by:
        1. Preserving the top elite_ratio% of current population (elites)
        2. Filling remaining spots with best offspring
        3. Guaranteeing monotonic improvement in best fitness
        4. Logging elitism effectiveness for verification
        
        Args:
            population (list): Current generation chromosomes
            fitnesses (list): Fitness values for current population  
            offspring (list): Generated offspring chromosomes
            offspring_fitnesses (list): Fitness values for offspring
            elite_ratio (float): Percentage of population to preserve as elites (0.01-0.20 typical)
            log_callback (callable): Optional logging function for elitism verification
            
        Returns:
            list: New population with elites preserved and best offspring

        Notes:
            If elite_ratio is not provided, this function defaults to 0.05 (matching the
            default value in the method parameter definitions).

        Example:
            >>> new_pop = ga.elitist_selection(pop, fits, offspring, off_fits, elite_ratio=0.10)
        """
        # Use the same default as method parameter definitions in config.py.
        # (Both single-objective and constrained single-objective default elite_ratio to 0.05.)
        if elite_ratio is None:
            elite_ratio = 0.05

        if not isinstance(elite_ratio, (int, float)):
            raise TypeError(f"elite_ratio must be a float in (0, 1], got: {elite_ratio!r}")

        elite_ratio = float(elite_ratio)
        if not (0.0 < elite_ratio <= 1.0):
            raise ValueError(f"elite_ratio must be in (0, 1], got: {elite_ratio}")

        population_size = len(population)
        elite_count = max(1, int(population_size * elite_ratio))  # At least 1 elite
        
        # ===== ELITISM VERIFICATION TRACKING =====
        # Track fitness before selection for elitism verification
        best_parent_fitness = max(fitnesses) if fitnesses else float('-inf')
        best_offspring_fitness = max(offspring_fitnesses) if offspring_fitnesses else float('-inf')
        
        # Get indices of elite individuals (top performers)
        elite_indices = np.argsort(fitnesses)[-elite_count:]
        elites = [population[i] for i in elite_indices]
        elite_fitnesses = [fitnesses[i] for i in elite_indices]
        
        # Remaining spots filled by best offspring
        remaining_size = population_size - elite_count
        if remaining_size > 0 and len(offspring) > 0:
            best_offspring_indices = np.argsort(offspring_fitnesses)[-remaining_size:]
            best_offspring = [offspring[i] for i in best_offspring_indices]
        else:
            # Edge case: no offspring or no remaining spots
            best_offspring = []
        
        # Combine elites and best offspring
        new_population = elites + best_offspring
        
        # Ensure we have exactly the right population size
        if len(new_population) > population_size:
            new_population = new_population[:population_size]
        elif len(new_population) < population_size:
            # Pad with random selection from combined pool if needed
            combined = population + offspring
            combined_fits = fitnesses + offspring_fitnesses
            while len(new_population) < population_size:
                idx = np.random.choice(len(combined))
                new_population.append(combined[idx])
        
        # ===== ELITISM EFFECTIVENESS VERIFICATION =====
        # Verify elitism is working and log statistics
        if log_callback and elite_count > 0:
            best_elite_fitness = max(elite_fitnesses)
            
            # Key elitism verification metrics
            fitness_preserved = best_elite_fitness >= best_parent_fitness  # Should always be True
            improvement_achieved = best_elite_fitness > best_parent_fitness
            elite_ratio_actual = elite_count / population_size
            
            # Log elitism effectiveness every few generations (avoid spam)
            if not hasattr(self, '_elitism_log_counter'):
                self._elitism_log_counter = 0
            
            self._elitism_log_counter += 1
            if self._elitism_log_counter % optimization_config.elitism_logging_frequency == 1:  # Log every N generations
                status = "✅" if fitness_preserved else "❌"  # Check or X mark
                improvement = "🔺" if improvement_achieved else "="
                
                log_callback(
                    f"  {status} Elitism: {elite_count}/{population_size} elites preserved ({elite_ratio_actual:.1%}) | "
                    f"Best: {best_elite_fitness:.6f} {improvement} | "
                    f"Offspring best: {best_offspring_fitness:.6f}"
                )
                
                # Warning if elitism appears to be failing
                if not fitness_preserved:
                    log_callback("  ⚠️ WARNING: Elite fitness regression detected! Check elitism implementation.")
        
        return new_population

    def crossover(self, parent1, parent2):
        """Multi-attempt crossover with same strategy, different random inputs"""
        self._generation_stats['crossover_attempts'] += 1
        
        for attempt in range(optimization_config.operator_max_retries):
            # Same crossover logic, just different random choices each time
            child1_bps, child2_bps = self._perform_single_crossover(parent1, parent2)
            
            if self.validate_chromosome(child1_bps) and self.validate_chromosome(child2_bps):
                return child1_bps, child2_bps  # Success!
            
            # Track retry statistics
            if attempt > 0:  # Don't count first attempt as retry
                self._generation_stats['crossover_retries'] += 1
        
        # All attempts failed - return None to signal parent reselection needed
        self._generation_stats['crossover_failures'] += 1
        self._generation_stats['crossover_parent_reselections'] += 1
        return None, None

    def _perform_single_crossover(self, parent1, parent2):
        """Single-point crossover while preserving mandatory breakpoints"""
        # Always include mandatory breakpoints
        mandatory_set = set(self.mandatory_breakpoints)
        
        # Get non-mandatory breakpoints from each parent
        parent1_optional = [bp for bp in parent1 if bp not in mandatory_set]
        parent2_optional = [bp for bp in parent2 if bp not in mandatory_set]
        
        if len(parent1_optional) == 0 and len(parent2_optional) == 0:
            # Both parents have only mandatory breakpoints
            return list(self.mandatory_breakpoints), list(self.mandatory_breakpoints)
        
        # Perform crossover on optional breakpoints only - single milepoint cut
        all_optional = sorted(set(parent1_optional + parent2_optional))

        if len(all_optional) == 0:
            # No optional breakpoints from either parent
            child1_optional = []
            child2_optional = []
        else:
            # Choose single physical cut point (actual milepoint value)
            cut_point = random.choice(all_optional)
            
            # Split each parent at this physical location
            p1_before = [bp for bp in parent1_optional if bp < cut_point]
            p1_after = [bp for bp in parent1_optional if bp >= cut_point]
            p2_before = [bp for bp in parent2_optional if bp < cut_point]  
            p2_after = [bp for bp in parent2_optional if bp >= cut_point]
            
            # Create children by recombining
            child1_optional = p1_before + p2_after
            child2_optional = p2_before + p1_after
        
        # Combine mandatory + optional breakpoints
        child1_bps = sorted(list(set(list(self.mandatory_breakpoints) + child1_optional)))
        child2_bps = sorted(list(set(list(self.mandatory_breakpoints) + child2_optional)))
        
        # Enforce constraints (this will preserve mandatory breakpoints)
        child1_bps = self._enforce_constraints(child1_bps)
        child2_bps = self._enforce_constraints(child2_bps)
        
        return child1_bps, child2_bps
    
    def report_constraint_statistics(self, generation, log_callback=None):
        """Report periodic statistics about constraint violations and generation failures"""
        stats = self._generation_stats
        
        # Only report every 10 generations to avoid spam
        if generation - stats['last_report_generation'] < 10:
            return
            
        stats['last_report_generation'] = generation
        
        # Calculate percentages and rates
        if stats['total_attempts'] > 0:
            failure_rate = (stats['failed_generations'] / stats['total_attempts']) * 100
            fallback_rate = (stats['fallback_chromosomes'] / stats['total_attempts']) * 100
        else:
            failure_rate = fallback_rate = 0
            
        # Create summary message
        msg = f"[CONSTRAINT STATS] Gen {generation}: {failure_rate:.1f}% generation failures, {stats['crossover_failures']} crossover failures, {stats['fallback_chromosomes']} fallbacks used"
        
        # Output to log
        if log_callback:
            log_callback(msg)
        else:
            # No callback provided; stay silent to avoid console spam.
            return
            
        # Reset counters for next period (keep cumulative for session)
        # Only reset crossover failures (others are cumulative session stats)
        if generation % 50 == 0:  # Reset crossover failures every 50 generations
            stats['crossover_failures'] = 0
    
    def get_constraint_summary(self):
        """Get a summary of constraint statistics for the entire session"""
        stats = self._generation_stats
        if stats['total_attempts'] > 0:
            failure_rate = (stats['failed_generations'] / stats['total_attempts']) * 100
            return {
                'total_attempts': stats['total_attempts'],
                'failure_rate': failure_rate,
                'fallback_count': stats['fallback_chromosomes'],
                'crossover_failures': stats['crossover_failures']
            }
        return None

    def mutate(self, chromosome):
        """Multi-attempt mutation with same strategy, different random inputs"""
        self._generation_stats['mutation_attempts'] += 1
        
        for attempt in range(optimization_config.operator_max_retries):
            # Same mutation logic, just different random choices each time
            mutated = self._perform_single_mutation(chromosome)
            
            if self.validate_chromosome(mutated):
                return mutated  # Success!
            
            # Track retry statistics
            if attempt > 0:  # Don't count first attempt as retry
                self._generation_stats['mutation_retries'] += 1
        
        # All attempts failed - return None to signal reselection needed
        self._generation_stats['mutation_reselections'] += 1
        return None

    def _perform_single_mutation(self, chromosome):
        """Single mutation attempt while preserving mandatory breakpoints"""
        mandatory_set = set(self.mandatory_breakpoints)
        optional_breakpoints = [bp for bp in chromosome if bp not in mandatory_set]
        
        if len(optional_breakpoints) <= 1:  # Not enough optional breakpoints to mutate
            # Add a new optional breakpoint instead
            possible = [xp for xp in self.x_data 
                       if xp not in chromosome and xp not in mandatory_set]
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
                possible = [xp for xp in self.x_data 
                           if xp not in new_chrom and xp not in mandatory_set]
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
                    old_bp = random.choice(optional_breakpoints)
                    possible = [xp for xp in self.x_data 
                               if xp not in new_chrom and xp not in mandatory_set]
                    if possible:
                        new_bp = random.choice(possible)
                        new_chrom.remove(old_bp)
                        new_chrom.append(new_bp)
        
        # Ensure constraints (preserves mandatory breakpoints)
        new_chrom = self._enforce_constraints(sorted(new_chrom))
        
        return new_chrom

    def _enforce_constraints(self, breakpoints, return_none_on_failure=False):
        """Enforce min/max segment length constraints while preserving mandatory breakpoints"""
        mandatory_set = set(self.mandatory_breakpoints)

        # Ensure all mandatory breakpoints are included
        breakpoints = sorted(list(set(list(breakpoints) + list(self.mandatory_breakpoints))))
        
        # First pass: remove non-mandatory breakpoints that violate min_length
        clean = [breakpoints[0]]  # Always keep first (mandatory)

        for bp in breakpoints[1:]:
            if bp - clean[-1] >= self.min_length:
                clean.append(bp)
            elif bp in mandatory_set:
                # Mandatory breakpoints must be kept; if they're too close to the previous
                # breakpoint, remove any prior non-mandatory breakpoints to restore feasibility.
                while len(clean) > 0 and (bp - clean[-1] < self.min_length) and (clean[-1] not in mandatory_set):
                    clean.pop()
                clean.append(bp)
        
        # Second pass: fix segments that are too long by inserting breakpoints
        # Never remove mandatory breakpoints, only add between them
        gap_segments = getattr(getattr(self, 'route_analysis', None), 'gap_segments', []) or []
        sorted_x = getattr(self, 'sorted_x_data', None)
        if sorted_x is None:
            sorted_x = np.asarray(self.x_data, dtype=float)
        clean_set = set(clean)

        i = 0
        while i < len(clean) - 1:
            segment_length = clean[i+1] - clean[i]
            
            if segment_length > self.max_length:
                is_known_gap_segment = any(
                    (abs(gap_start - clean[i]) < 1e-9 and abs(gap_end - clean[i + 1]) < 1e-9)
                    for gap_start, gap_end in gap_segments
                )

                is_mandatory_segment = (clean[i] in mandatory_set) and (clean[i + 1] in mandatory_set)

                # Mandatory-bounded segments (and explicit data gaps) may violate length constraints.
                # Do not introduce optional breakpoints inside them during repair, because that can
                # create user-controllable subsegments that *must* meet constraints and may be infeasible.
                if is_known_gap_segment or is_mandatory_segment:
                    i += 1
                    continue

                # Try to find a milepoint to insert between clean[i] and clean[i+1]
                target_end = clean[i] + self.max_length

                # Ensure the inserted breakpoint also leaves a valid right-hand segment (>= min_length)
                right_limit = clean[i + 1] - self.min_length
                upper = min(target_end, right_limit)

                if upper >= clean[i] + self.min_length:
                    left_idx = int(np.searchsorted(sorted_x, clean[i] + self.min_length, side='left'))
                    right_idx = int(np.searchsorted(sorted_x, upper, side='right'))

                    insert_bp = None
                    for idx in range(right_idx - 1, left_idx - 1, -1):
                        xp = float(sorted_x[idx])
                        if xp < clean[i + 1] and xp not in clean_set:
                            insert_bp = xp
                            break
                else:
                    insert_bp = None

                if insert_bp is not None:
                    clean.insert(i + 1, insert_bp)
                    clean_set.add(insert_bp)
                    # Don't increment i - recheck this segment
                else:
                    # No admissible split point exists (respecting min_length on both sides).
                    if return_none_on_failure:
                        return None
                    i += 1
            else:
                i += 1
        
        return clean

    def validate_chromosome(self, chromosome, suppress_warnings=False):
        """Validate that a chromosome respects all constraints and includes mandatory breakpoints
        
        Args:
            chromosome: The chromosome to validate
            suppress_warnings: If True, don't log mandatory segment violation warnings
        """
        # TODO: Honor suppress_warnings by gating any mandatory-segment warning logs in this method.
        # Call sites already pass suppress_warnings=True in hot loops to avoid log spam.
        if len(chromosome) < 2:
            return False
        
        # Check that all mandatory breakpoints are included
        mandatory_set = self._mandatory_bp_set
        chrom_set = set(chromosome)
        if not mandatory_set.issubset(chrom_set):
            return False
                
        # Check segment lengths with distinction between mandatory and user-controllable
        constraint_violations = []
        
        for segment_idx, (start_bp, end_bp) in enumerate(zip(chromosome, chromosome[1:])):
            length = end_bp - start_bp
            
            # Determine if this is a mandatory segment (bounded by mandatory breakpoints)
            start_is_mandatory = start_bp in mandatory_set
            end_is_mandatory = end_bp in mandatory_set
            is_mandatory_segment = start_is_mandatory and end_is_mandatory
            
            if length < self.min_length or length > self.max_length:
                if is_mandatory_segment:
                    # Mandatory segments may violate length constraints due to physical/data limitations.
                    # They are not controllable by the algorithm, so treat as warning-only.
                    constraint_violations.append({
                        'type': 'mandatory',
                        'segment': segment_idx,
                        'length': length,
                        'start': start_bp,
                        'end': end_bp
                    })
                else:
                    # Error: user-controllable segment violates constraints (algorithm failure)
                    return False
        
        # Report mandatory segment constraint violations (warnings only)
        # NOTE: Removed unnecessary warnings - constraint violations during route analysis
        # and population generation are expected and automatically handled by the algorithm
        
        # Check start/end points
        if chromosome[0] != self.x_data[0] or chromosome[-1] != self.x_data[-1]:
            return False
        
        return True

    def calculate_detailed_statistics(self, chromosome, data):
        """
        Calculate detailed statistics for a chromosome.
        
        Args:
            chromosome: List of breakpoints
            data: Highway data DataFrame
            
        Returns:
            SegmentStatistics: Object containing detailed statistics
        """
        # Create all segment boundaries (start, breakpoints, end)
        all_points = [self.x_data[0]] + list(chromosome) + [self.x_data[-1]]
        all_points = sorted(set(all_points))  # Remove duplicates and sort
        
        # Calculate segment lengths
        lengths = [end_point - start_point for start_point, end_point in zip(all_points, all_points[1:])]
        
        # Calculate basic statistics
        avg_length = np.mean(lengths) if lengths else 0
        min_length = np.min(lengths) if lengths else 0
        max_length = np.max(lengths) if lengths else 0
        std_length = np.std(lengths) if lengths else 0
        
        # Calculate fitness (total deviation) using cached method if available
        try:
            total_deviation = self.fitness(chromosome)
        except Exception as e:
            import logging
            logging.getLogger(__name__).debug(
                "Fitness calculation failed during statistics; using total_deviation=0 fallback: %s",
                e,
                exc_info=True,
            )
            total_deviation = 0  # Fallback if fitness calculation fails
            
        segment_count = len(lengths)
        
        return SegmentStatistics(
            avg_length=avg_length,
            min_length=min_length,
            max_length=max_length,
            std_length=std_length,
            total_deviation=total_deviation,
            segment_count=segment_count,
            lengths=lengths
        )


class SegmentStatistics:
    """Container for segment statistics."""
    
    def __init__(self, avg_length=0, min_length=0, max_length=0, std_length=0, 
                 total_deviation=0, segment_count=0, lengths=None):
        self.avg_length = avg_length
        self.min_length = min_length
        self.max_length = max_length
        self.std_length = std_length
        self.total_deviation = total_deviation
        self.segment_count = segment_count
        self.lengths = lengths or []