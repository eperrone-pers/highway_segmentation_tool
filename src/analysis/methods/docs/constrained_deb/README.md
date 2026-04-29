# Constrained GA (Deb Feasibility) (`method_key`: `constrained_deb`)

This document describes the **Deb-feasibility constrained genetic algorithm** used for highway segmentation in this repository.

This method is intentionally additive: it provides a second constrained GA variant alongside the penalty-based constrained method (`method_key="constrained"`).

---

## 1. Problem formulation

Given a route sampled at positions $x_i$ with measurements $y_i$, the goal is to choose a set of breakpoints that partition the route into contiguous segments.

This method optimizes **data fit** (deviation) while enforcing a **target average segment length** constraint using **Deb’s feasibility rules** (constraint-domination), rather than a penalty-weighted objective.

---

## 2. Inputs, data model, and assumptions

### 2.1 Input data

The method requires a `RouteAnalysis` object (see `src/data_loader.py`) which provides:

- `route_data`: a DataFrame containing the route’s samples
- mandatory breakpoints (route boundaries + gap boundaries)
- gap metadata (for export/plotting)

Passing a raw DataFrame raises a `TypeError`.

### 2.2 Mandatory breakpoints (gap-aware segmentation)

Gap analysis defines mandatory breakpoints that are always preserved by genetic operators.

---

## 3. Parameter interface

The authoritative parameter definitions (names, defaults, validation bounds) are in `src/config.py` under `DEB_FEASIBILITY_CONSTRAINED_PARAMETERS`.

### 3.1 Segment constraints

- `min_length` (miles): minimum allowed segment length
- `max_length` (miles): maximum allowed segment length

### 3.2 GA parameters

- `population_size`
- `num_generations`
- `crossover_rate`
- `mutation_rate`
- `elite_ratio`

### 3.3 Constraint parameters

- `target_avg_length` (miles): desired average segment length
- `length_tolerance` (miles): acceptable absolute deviation from the target

### 3.4 Runtime/caching parameters

- `cache_clear_interval`: generations between cache clears (calls `ga.clear_cache()`)
- `enable_performance_stats`: toggles collection of timing/diversity stats

---

## 4. Chromosome representation

Each chromosome is a **sorted list of breakpoint positions** (milepoints), including:

- route start/end, and
- all mandatory breakpoints.

If the chromosome is $B = [b_0, b_1, \dots, b_K]$, segments are interpreted as:

$$[b_0, b_1), [b_1, b_2), \dots, [b_{K-1}, b_K)$$

---

## 5. Base objective (data fit)

The GA engine returns a base fitness that is the **negative sum of squared errors** (SSE) across segments:

$$f_{\text{base}}(B) = -\mathrm{SSE}(B)$$

Higher $f_{\text{base}}$ means better fit (less deviation).

---

## 6. Constraint definition (target average segment length)

### 6.1 Average segment length used for the constraint

This method uses the GA engine’s shared definition of average segment length:

- compute segment lengths for all consecutive breakpoint intervals
- exclude **gap-only** segments (intervals whose boundaries exactly match a detected gap)
- average the remaining (data-bearing) segment lengths

In code this is computed by `HighwaySegmentGA._calculate_non_mandatory_avg_length(...)` (legacy name).

### 6.2 Deviation and violation

Let $L(B)$ be the gap-only-excluding average length for chromosome $B$.

Define absolute deviation from target:

$$d(B) = |L(B) - L_{\text{target}}|$$

Define constraint violation (a non-negative scalar):

$$v(B) = \max(0, d(B) - \tau)$$

where $\tau$ is `length_tolerance`.

A solution is feasible when $v(B) = 0$.

---

## 7. Deb feasibility rules (constraint-domination)

When comparing two candidates $A$ and $B$:

1. If $A$ is feasible and $B$ is infeasible, $A$ is better.
2. If both are feasible, prefer the one with higher $f_{\text{base}}$ (better data fit).
3. If both are infeasible, prefer the one with smaller violation $v(\cdot)$ (tie-break by higher $f_{\text{base}}$).

This comparison is used for:

- tournament-based parent selection, and
- elitist environmental selection.

---

## 8. Operators and repair

The method reuses the same breakpoint-based operators as the other GA methods:

- crossover via `crossover_with_retries(...)`
- mutation via `mutation_with_retries(...)`

Mandatory breakpoints are preserved by operator design.

Invalid chromosomes are repaired using `ga._enforce_constraints(...)`.

---

## 9. Outputs and result structure

The method returns an `AnalysisResult` with one solution in `all_solutions`.

The best solution includes (selected highlights):

- `chromosome`: breakpoint list
- `fitness` / `deviation_fitness`: base fitness $f_{\text{base}}(B)$
- `avg_segment_length`: $L(B)$ (gap-only-excluding average length)
- `target_avg_length`, `length_deviation`, `length_tolerance`
- `constraint_violation`, `is_feasible`

### 9.1 Method-owned segmentation payload

For export, this method includes a method-owned `segmentation` payload containing:

- breakpoints
- segment count / segment lengths
- `average_segment_length` (gap-only-excluding)

This avoids requiring the exporter to impose a single global definition.

---

## 10. Implementation map (source of truth)

Key implementation locations:

- Runner + Deb comparisons + selection: `src/analysis/methods/deb_feasibility_constrained.py`
- GA engine (fitness, caching, average length): `src/analysis/utils/genetic_algorithm.py`
- Operators and retry wrappers: `src/analysis/utils/ga_utilities.py`
- Parameter definitions: `src/config.py`
