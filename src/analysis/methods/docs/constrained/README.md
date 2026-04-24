# Constrained Single-Objective GA (`method_key`: `constrained`)

This document describes the **constrained single-objective genetic algorithm** used for highway segmentation in this repository. It is written in the same “technical paper” style as the single-objective and multi-objective method documents.

---

## 1. Problem formulation

Given a route sampled at positions $x_i$ with measurements $y_i$, the goal is to choose a set of breakpoints that partition the route into contiguous segments.

Unlike the pure single-objective method, this method adds a **design constraint**: the user specifies a target average segment length, and the GA is penalized for solutions that deviate beyond a tolerance.

---

## 2. Inputs, data model, and assumptions

### 2.1 Input data

The method requires a `RouteAnalysis` object (see `src/data_loader.py`) which provides:

- `route_data`: a DataFrame containing the route’s samples
- `mandatory_breakpoints`: required breakpoints (route boundaries + gap boundaries)
- gap metadata (for export/plotting)

The `RouteAnalysis` requirement is enforced at runtime: passing a raw DataFrame raises a `TypeError`.

### 2.2 Mandatory breakpoints (gap-aware segmentation)

Gap analysis defines mandatory breakpoints that are always preserved. Genetic operators treat these breakpoints as fixed anchors.

---

## 3. Parameter interface

The authoritative parameter definitions (names, defaults, validation bounds) are in `src/config.py` under `CONSTRAINED_SINGLE_OBJECTIVE_PARAMETERS`.

### 3.1 Segment constraints

- `min_length` (miles): minimum allowed segment length
- `max_length` (miles): maximum allowed segment length

### 3.2 GA parameters

- `population_size`
- `num_generations`
- `crossover_rate`
- `mutation_rate`
- `elite_ratio`

### 3.3 Constraint (target-length) parameters

- `target_avg_length` (miles): desired average segment length
- `length_tolerance` (miles): acceptable absolute deviation from the target before penalties apply
- `penalty_weight`: scales the penalty for deviations beyond tolerance

### 3.4 Runtime/caching parameters

- `cache_clear_interval`: generations between cache clears (calls `ga.clear_cache()`)
- `enable_performance_stats`: toggles collection of timing/diversity history in the returned statistics

---

## 4. Chromosome representation

Each chromosome is a **sorted list of breakpoint positions** (milepoints), including:

- route start/end, and
- all mandatory breakpoints.

If the chromosome is $B = [b_0, b_1, \dots, b_K]$, segments are interpreted as:

$$[b_0, b_1), [b_1, b_2), \dots, [b_{K-1}, b_K)$$

---

## 5. Feasibility and constraint handling

Length constraints apply to **user-controllable** segments:

$$\texttt{min\_length} \le (b_{i+1}-b_i) \le \texttt{max\_length}$$

Segments forced by mandatory breakpoints (e.g., around gaps) may violate these bounds due to data limitations; this does not necessarily invalidate the chromosome.

Population members are repaired via `ga._enforce_constraints(...)` when needed.

---

## 6. Fitness definition (single objective with penalty)

The constrained method still uses the GA engine’s deviation-based fitness, but subtracts a penalty when the average segment length deviates too far from the target.

### 6.1 Base fitness (data fit)

The GA engine returns a base fitness that is the **negative sum of squared errors** (SSE) across segments:

$$f_{\text{base}}(B) = -\mathrm{SSE}(B)$$

Higher $f_{\text{base}}$ means better fit (less deviation).

### 6.2 Average length used by the constraint

The constrained fitness uses:

$$L(B) = \mathrm{avg\_nonmandatory\_segment\_length}(B)$$

This is computed by `HighwaySegmentGA._calculate_non_mandatory_avg_length(...)` and intentionally excludes segments that touch mandatory boundaries.

Define absolute deviation from target:

$$d(B) = |L(B) - L_{\text{target}}|$$

### 6.3 Penalty function

Let $\tau$ be the tolerance and $w$ be the penalty weight.

$$\mathrm{penalty}(B) = \begin{cases}
0 & d(B) \le \tau \\
w\,(d(B)-\tau)^2 & d(B) > \tau
\end{cases}$$

### 6.4 Constrained fitness

The value maximized by the GA loop is:

$$f_{\text{constrained}}(B) = f_{\text{base}}(B) - \mathrm{penalty}(B)$$

---

## 7. “Gap-aware target segments” calculation (reporting)

At startup, the runner computes a **gap-aware target segment count** based on:

- the total route length,
- mandatory breakpoint spacing, and
- `target_avg_length`.

This value is logged and exported (as `target_segments_calculated`) for transparency; it does not directly alter the GA engine’s initialization logic.

---

## 8. Initialization

The initial population is generated using the GA engine’s diverse initializer:

- `ga.generate_diverse_initial_population()`
- followed by per-chromosome validation and repair.

---

## 9. Variation operators

The method uses the same breakpoint-based operators as the other GA methods:

- crossover via `crossover_with_retries(...)`
- mutation via `mutation_with_retries(...)`

Mandatory breakpoints are preserved by operator design.

---

## 10. Selection and elitism

### 10.1 Parent selection

Parents are selected using tournament selection (size 3) based on the constrained fitness values.

### 10.2 Environmental (elitist) selection

Each generation produces offspring and then performs elitist selection by combining parent+offspring and keeping the top $N$ chromosomes by constrained fitness.

---

## 11. Cache management

The runner enables segment caching via `ga.enable_segment_cache_mode(True)` and periodically clears caches:

- every `cache_clear_interval` generations it calls `ga.clear_cache()`.

---

## 12. Outputs and result structure

The method returns an `AnalysisResult` with exactly one solution in `all_solutions`.

The returned best solution includes (selected highlights):

- `chromosome`: breakpoint list
- `fitness`: constrained fitness $f_{\text{constrained}}(B)$
- `unconstrained_fitness` / `deviation_fitness`: base fitness $f_{\text{base}}(B)$
- `avg_segment_length`: the non-mandatory average length $L(B)$ used for the constraint
- `target_avg_length`, `length_deviation`, `is_feasible`

### 12.1 Final best-solution selection rule

At the end of the run, the method chooses the reported “best” solution using a lexicographic rule:

1. minimize `length_deviation` (closest to target), then
2. tie-break by **maximizing** `unconstrained_fitness` (best data fit).

This is intentionally different from simply taking the max constrained fitness, and it matches the code’s stated “closest-to-target” intent.

---

## 13. Reproducibility

The method uses Python’s `random` and NumPy’s random sampling. There is no built-in seed exposed via the method interface; runs are non-deterministic unless seeds are set externally.

---

## 14. Implementation map (source of truth)

Key implementation locations:

- Runner (constraint penalty loop, selection, result assembly): `src/analysis/methods/constrained.py`
- GA engine (chromosome validation, base fitness, non-mandatory average length): `src/analysis/utils/genetic_algorithm.py`
- Operators and retry wrappers: `src/analysis/utils/ga_utilities.py`
- Parameter definitions (`CONSTRAINED_SINGLE_OBJECTIVE_PARAMETERS`): `src/config.py`

---

## 15. Code-review notes (suggestions only)

Observations from reading the current implementation (for discussion, not applied changes):

- `elite_ratio` is accepted and recorded, but the current elitist selection implementation keeps the top $N$ chromosomes and does not explicitly use the ratio as a parameter.
- The final “best solution” is selected by closest-to-target (then best base fitness), rather than strictly taking the max constrained fitness. This is consistent with the runner’s stated intent, but it is important for interpretation.
