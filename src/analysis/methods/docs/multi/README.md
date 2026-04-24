# Multi-Objective NSGA-II (`method_key`: `multi`)

This document describes the **multi-objective genetic algorithm** implementation based on **NSGA-II** (Non-dominated Sorting Genetic Algorithm II) used for highway segmentation in this repository. It is written in a “technical paper” style so it can be reused as part of a formal method description.

---

## 1. Problem formulation

Given a route sampled at positions $x_i$ with measurements $y_i$, the goal is to choose a set of breakpoints that partition the route into contiguous segments. Unlike the single-objective method, this method optimizes **two competing objectives** and returns a **Pareto front** of non-dominated solutions.

---

## 2. Inputs, data model, and assumptions

### 2.1 Input data

The method consumes either:

- a `RouteAnalysis` object (preferred), which contains precomputed mandatory breakpoints from gap detection, or


Key fields:

- `x_column`: distance/milepoint coordinate (units: miles)
- `y_column`: measurement being segmented
- `gap_threshold`: used to identify data gaps and create mandatory breakpoints

### 2.2 Mandatory breakpoints (gap-aware segmentation)

Gap analysis defines **mandatory breakpoints** that always remain in the segmentation and are preserved by genetic operators.

Mandatory breakpoints include route start/end and boundaries around detected gaps.

---

## 3. Parameter interface

### 3.1 User-configurable parameters

The authoritative definitions (names, defaults, validation bounds) are in `src/config.py` under `MULTI_OBJECTIVE_NSGA2_PARAMETERS`.

Core parameters:

- `min_length` (miles): minimum allowed segment length
- `max_length` (miles): maximum allowed segment length
- `population_size`: number of individuals per generation
- `num_generations`: number of NSGA-II generations
- `crossover_rate`: probability of applying crossover when producing children
- `mutation_rate`: probability of mutating each offspring

Runtime/caching parameters:

- `cache_clear_interval`: generations between cache clears (see notes in Section 12)
- `enable_performance_stats`: toggles collection of timing/diversity statistics

### 3.2 Internal constants (not user-configurable)

The GA uses internal constants from `AlgorithmConstants` (see `src/config.py`), including:

- `operator_max_retries` (default: 4): retry budget used by crossover/mutation wrappers
- `min_front_size` (default: 2): crowding distance special-case threshold

---

## 4. Chromosome representation

Each chromosome is a **sorted list of breakpoint positions** (milepoints), including route boundaries and all mandatory breakpoints.

Let the chromosome be $B = [b_0, b_1, \dots, b_K]$ with:

- $b_0 = x_{\min}$ and $b_K = x_{\max}$
- $B$ is strictly increasing (after de-duplication)
- $B_\text{mandatory} \subseteq B$

Segments are interpreted as half-open intervals:

$$[b_0, b_1), [b_1, b_2), \dots, [b_{K-1}, b_K)$$

---

## 5. Constraints and feasibility

Engineering constraints apply to **user-controllable** segments:

$$\texttt{min\_length} \le (b_{i+1} - b_i) \le \texttt{max\_length}$$

Segments bounded by mandatory breakpoints (for example, around real data gaps) may violate length constraints due to data limitations and do not invalidate a chromosome.

Feasibility checks include:

- route start/end match the first and last sampled `x` values,
- all mandatory breakpoints are present,
- all user-controllable segments respect min/max length.

---

## 6. Multi-objective fitness definition

NSGA-II in this codebase assumes **both objectives are maximized**. Objectives are constructed so that “better” means larger.

### 6.1 Objective 1: data fit (deviation)

Define within-segment SSE as:

$$\mathrm{SSE}(B) = \sum_{s} \sum_{j\in s} (y_j - \mu_s)^2$$

The returned objective value is:

$$f_1(B) = -\mathrm{SSE}(B)$$

So solutions with lower SSE have higher (less negative) $f_1$.

### 6.2 Objective 2: simplicity via average segment length

The second objective is the **average length of non-mandatory segments**, returned as a positive value:

$$f_2(B) = \mathrm{mean\_length}(\text{non-mandatory segments})$$

This promotes solutions with fewer/larger user-controllable segments. Segments that touch mandatory boundaries are excluded from this average (because they are forced by gaps/bounds).

### 6.3 Returned objective vector

The GA returns:

$$\mathbf{f}(B) = (f_1(B), f_2(B)) = (-\mathrm{SSE}(B), \mathrm{avg\_nonmandatory\_length}(B))$$

These are stored as raw values in the output JSON for plotting/transforms.

---

## 7. NSGA-II non-dominated sorting

### 7.1 Dominance definition

With both objectives maximized, a solution $A$ dominates $B$ if:

$$f_1(A) \ge f_1(B) \;\wedge\; f_2(A) \ge f_2(B) \;\wedge\; (f_1(A) > f_1(B) \;\vee\; f_2(A) > f_2(B))$$

### 7.2 Fast non-dominated sorting

The implementation computes objective vectors for all chromosomes and then performs fast non-dominated sorting to produce fronts:

- front 0: non-dominated set (Pareto front)
- front 1: dominated only by front 0
- etc.

---

## 8. Crowding distance (diversity preservation)

Within a front, NSGA-II uses crowding distance to preserve a diverse spread of solutions.

For each objective:

1. Sort solutions in the front by objective value.
2. Assign boundary solutions infinite crowding distance.
3. For interior solutions, add normalized neighbor differences.

Higher crowding distance is preferred.

---

## 9. Initialization

Initial population generation uses the same diverse initializer as the GA engine:

- estimate feasible segment-count range from length constraints and mandatory breakpoints
- attempt uniform 10-bin distribution when feasible
- otherwise fall back to a strategy-based distribution (few/medium/many/random)

Invalid chromosomes are repaired via constraint enforcement.

---

## 10. Variation operators

The method uses the same breakpoint-based operators as the single-objective GA.

### 10.1 Crossover

“Physical-cut” crossover recombines **optional** breakpoints across a cut milepoint selected from the union of parent optional breakpoints. Mandatory breakpoints are always preserved.

The runner applies crossover with probability `crossover_rate`; otherwise children are clones.

### 10.2 Mutation

Mutation performs one of: add, remove, or move an optional breakpoint, then repairs constraints. Mutation is applied per-offspring with probability `mutation_rate`.

Retry wrappers are used for robustness.

---

## 11. Environmental selection (NSGA-II)

The runner implements NSGA-II environmental selection each generation by:

1. Creating offspring via selection/crossover/mutation.
2. Combining parent + offspring populations.
3. Sorting the combined population into non-dominated fronts.
4. Filling the next generation by taking entire fronts in order until capacity is reached.
5. If the next front would overflow capacity, selecting the remaining slots by **descending crowding distance** within that front.

---

## 12. Outputs and result structure

The returned results include:

- `all_solutions`: the final Pareto front (each entry contains `chromosome` and raw objective values)
- `fitness` / `objective_values`: raw GA objective values `[negative_deviation, avg_segment_length]`
- `num_segments`: number of segments
- per-run optimization statistics (Pareto size, generation counts, optional performance stats)
- mandatory breakpoints used

The runner also computes a “compromise” solution by normalizing both objectives and choosing the minimum summed score. This is used for logging and may be used as a primary selection in downstream consumers.

---

## 13. Reproducibility

The method uses Python’s `random` module and NumPy sampling. There is no built-in seed parameter exposed through the method interface, so runs are non-deterministic unless seeds are set externally.

---

## 14. Implementation map (source of truth)

Key implementation locations:

- Runner (NSGA-II loop, environmental selection, result assembly): `src/analysis/methods/multi_objective.py`
- GA engine (objective definitions, dominance, sorting, crowding distance): `src/analysis/utils/genetic_algorithm.py`
- Selection and operators (NSGA-II tournament selection, crossover/mutation retry wrappers): `src/analysis/utils/ga_utilities.py`
- Parameter definitions (`MULTI_OBJECTIVE_NSGA2_PARAMETERS`): `src/config.py`

---

## 15. Code-review notes (suggestions only)

The following are observations from reading the current implementation, listed for discussion before making any code changes:

- The call site for NSGA-II tournament selection in `src/analysis/methods/multi_objective.py` should be double-checked against the function signature in `src/analysis/utils/ga_utilities.py` to ensure the arguments are in the intended order.
- Cache clearing logic should be reviewed to confirm it targets the actual GA cache attributes (the GA class stores `_fitness_cache` / `_multi_fitness_cache` and exposes `clear_cache()`).
