# Single-Objective GA (`method_key`: `single`)

This document describes the **single-objective genetic algorithm (GA)** implementation used for highway segmentation, as implemented in this repository. It is written in a “technical paper” style so it can be reused as part of a formal method description.

---

## 1. Problem formulation

Given a route sampled at positions $x_i$ with measurements $y_i$, the goal is to choose a set of breakpoints that partition the route into contiguous segments such that each segment is **internally homogeneous** (low within-segment variance).

The GA optimizes **only data fit** (no explicit objective/penalty for segment count in this method).

---

## 2. Inputs, data model, and assumptions

### 2.1 Input data

The method consumes either:

- a `RouteAnalysis` object (preferred), which contains precomputed mandatory breakpoints from gap detection, or
- a raw DataFrame (fallback/testing path), in which case gap analysis is computed internally.

Key fields:

- `x_column`: distance/milepoint coordinate (units: miles)
- `y_column`: measurement being segmented
- `gap_threshold`: used to identify data gaps and create mandatory breakpoints

### 2.2 Mandatory breakpoints (gap-aware segmentation)

Gap analysis defines **mandatory breakpoints**. These always remain in the segmentation and are preserved by all GA operators.

Mandatory breakpoints include:

- route start and end, and
- boundaries around gaps detected using `gap_threshold`.

---

## 3. Parameter interface

### 3.1 User-configurable parameters

The authoritative definitions (names, defaults, validation bounds) are in `src/config.py` under `SINGLE_OBJECTIVE_GA_PARAMETERS`.

Core parameters:

- `min_length` (miles): minimum allowed segment length
- `max_length` (miles): maximum allowed segment length
- `population_size`: number of individuals per generation
- `num_generations`: number of GA iterations
- `crossover_rate`: probability of applying crossover when producing children
- `mutation_rate`: probability of mutating each offspring
- `elite_ratio`: fraction of the parent population preserved via elitism each generation

Runtime/caching parameters (present in the UI/config):

- `enable_performance_stats`: toggles collection of timing/diversity statistics
- `cache_clear_interval`: defined in config/UI; **the current single-objective runner does not explicitly clear caches on an interval** (unlike some other runners)

### 3.2 Internal constants (not user-configurable)

The GA uses internal constants from `AlgorithmConstants` (see `src/config.py`), including:

- `operator_max_retries` (default: 4): retry budget used by crossover/mutation wrappers
- `init_population_max_retries` (default: 10): retry budget for some initialization pathways
- `tournament_size` (default: 3): selection tournament size (the single-objective runner uses tournament size 3)

---

## 4. Chromosome representation

Each chromosome is a **sorted list of breakpoint positions** (milepoints), including the route boundaries.

Let the chromosome be $B = [b_0, b_1, \dots, b_K]$ with:

- $b_0 = x_{\min}$ and $b_K = x_{\max}$ (route bounds)
- $B$ is strictly increasing (after de-duplication)
- all mandatory breakpoints are included: $B_\text{mandatory} \subseteq B$

Segments are interpreted as half-open intervals:

$$[b_0, b_1), [b_1, b_2), \dots, [b_{K-1}, b_K)$$

and segment membership is determined using `x` comparisons consistent with that convention.

The number of segments is $K$ (i.e., `len(B) - 1`).

---

## 5. Constraints and feasibility

The method enforces engineering constraints on **user-controllable** segments:

- for any non-mandatory-bounded segment, its length must satisfy:

$$\texttt{min\_length} \le (b_{i+1} - b_i) \le \texttt{max\_length}$$

**Important distinction**: segments bounded by mandatory breakpoints (for example, across a real data gap) may violate length constraints due to physical/data limitations. These are treated as **warning-only** and do not invalidate a chromosome.

Feasibility checks include:

- route start/end must match the first and last `x` values,
- all mandatory breakpoints must appear in the chromosome,
- all user-controllable segment lengths must satisfy min/max constraints.

---

## 6. Fitness function (single objective)

### 6.1 Objective

The fitness is based on **sum of squared errors within each segment** (SSE). For each segment $s$ with points $y_j$, define the segment mean $\mu_s$.

Total SSE:

$$\mathrm{SSE}(B) = \sum_{s} \sum_{j\in s} (y_j - \mu_s)^2$$

The GA is written as a **maximization**, so it returns:

$$\mathrm{fitness}(B) = -\mathrm{SSE}(B)$$

Thus, “better” solutions have fitness values closer to 0 (less negative).

### 6.2 Efficient computation

Fitness uses an $O(K)$ computation based on prefix sums over sorted data:

For a segment with $n$ points, sum $S=\sum y$ and sum of squares $Q=\sum y^2$:

$$\sum (y-\mu)^2 = Q - \frac{S^2}{n}$$

This avoids per-point allocation and speeds up evaluation significantly.

### 6.3 Caching

Fitness evaluation uses chromosome-level caching:

- key: `tuple(breakpoints)`
- value: computed fitness

The single-objective runner also enables **hybrid segment caching mode**, which can reuse statistics for repeated segment boundaries.

---

## 7. Initialization (initial population generation)

The initial population is designed to cover a wide range of segment counts to avoid premature convergence.

### 7.1 Segment-count range estimation

Initialization estimates a feasible segment-count range based on total splittable length (between mandatory breakpoints) and length constraints.

### 7.2 Uniform 10-bin distribution (preferred when feasible)

When `population_size >= 50` and the estimated segment-count range is sufficiently wide, initialization attempts a **10-bin uniform distribution** over segment counts:

1. Divide the feasible segment-count range into 10 bins.
2. For each bin, generate approximately equal numbers of chromosomes.
3. Each chromosome targets a segment count selected uniformly within the bin.

Chromosomes are generated using a **progressive splitting** procedure:

- start from mandatory breakpoints
- repeatedly split the currently-longest splittable segment
- choose an admissible breakpoint from available sampled `x` positions
- stop when the target segment count is reached or no further splits are possible

If a targeted segment count is infeasible (because of discrete `x` sampling + constraints), the initializer retries and may fall back.

### 7.3 Fallback strategy distribution

If uniform binning is not used (or fails), the initializer uses a strategy mix:

- few segments (low complexity)
- medium segments (balanced)
- many segments (high accuracy focus)
- random (exploration)

Any invalid chromosome is repaired via constraint enforcement (Section 10).

---

## 8. Main evolutionary loop

For each generation:

1. **Fitness evaluation**: compute fitness for each chromosome.
2. **Parent selection**: tournament selection (size = 3) selects `population_size // 2` parents.
3. **Crossover**: generate offspring until `population_size` is reached.
4. **Mutation**: mutate offspring with probability `mutation_rate`.
5. **Repair/validation**: enforce constraints where needed.
6. **Offspring fitness**: evaluate offspring.
7. **Elitist selection**: preserve top elites from parents, fill remainder with top offspring.

The loop runs for `num_generations` unless an external stop callback terminates early.

---

## 9. Parent selection (tournament)

Tournament selection (size 3) chooses the fittest individual among 3 uniformly sampled candidates, repeated until the parent pool is filled.

Because fitness is maximized, the “best” candidate is the one with the highest (least negative) fitness.

---

## 10. Genetic operators

All operators preserve mandatory breakpoints.

### 10.1 Crossover (physical-cut recombination)

The crossover operator operates only on **optional** breakpoints (non-mandatory).

- Choose a single cut milepoint from the union of optional breakpoints.
- Split each parent’s optional breakpoint list at that physical location.
- Recombine left part of one parent with right part of the other.
- Merge with mandatory breakpoints and sort/de-duplicate.

In the single-objective runner, crossover is applied with probability `crossover_rate`; otherwise children are clones of their parents.

To improve robustness, the implementation uses a retry wrapper (up to `operator_max_retries`) and a fast local validation focused on the segment that straddles the cut point.

### 10.2 Mutation (add/remove/move)

Mutation also acts only on optional breakpoints, using one of the following actions:

- **add**: insert a new optional breakpoint at an admissible sampled `x` position inside a segment
- **remove**: delete an optional breakpoint if the merged segment remains valid
- **move**: relocate an optional breakpoint to a new admissible sampled `x` position between its neighbors

Mutation uses a retry wrapper (up to `operator_max_retries`) and fast validation of only the segments impacted by the edit. When the GA instance is available, mutation attempts are constraint-aware (they preferentially select admissible positions that preserve length constraints).

### 10.3 Constraint enforcement / repair

After crossover/mutation (and during initialization), chromosomes are repaired using `_enforce_constraints`, which:

1. Ensures all mandatory breakpoints are present.
2. Removes optional breakpoints that create too-short segments (and may remove adjacent optionals to keep mandatory points feasible).
3. For user-controllable too-long segments, inserts a breakpoint at a sampled `x` position that satisfies both:

   - left segment length $\le$ `max_length`, and
   - right segment length $\ge$ `min_length`.

Segments that are known gaps or bounded by mandatory breakpoints are not split during repair.

---

## 11. Survivor selection (elitism)

The method uses **elitist generational replacement**:

- Preserve `elite_count = max(1, floor(population_size * elite_ratio))` best parents.
- Fill the remaining slots with the best offspring.

This guarantees that the best fitness in the population is non-decreasing across generations (modulo ties).

---

## 12. Outputs and result structure

The returned results include:

- best chromosome (breakpoints), best fitness
- mandatory breakpoints used
- per-run optimization statistics (fitness history, population size, rates, optional performance stats)
- `all_solutions`: first entry is the best solution; additional entries include other final-population chromosomes

---

## 13. Reproducibility

The GA uses Python’s `random` module and NumPy random sampling in initialization. There is no built-in seed parameter in the method interface, so runs are non-deterministic unless you set seeds externally.

---

## 14. Implementation map (source of truth)

Key implementation locations:

- Runner (evolution loop, parent selection, operator wiring): `src/analysis/methods/single_objective.py`
- GA engine (fitness, initialization, constraint enforcement, validation, elitism): `src/analysis/utils/genetic_algorithm.py`
- Operator retry wrappers (physical-cut crossover, constraint-aware mutation): `src/analysis/utils/ga_utilities.py`
- Parameter definitions (`SINGLE_OBJECTIVE_GA_PARAMETERS`): `src/config.py`
