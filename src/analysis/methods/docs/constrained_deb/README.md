# Constrained GA (Deb Feasibility) (`method_key`: `constrained_deb`)

This document describes the **Deb-feasibility constrained genetic algorithm** used for highway segmentation in this repository.

This method is intentionally additive: it provides a second constrained GA variant alongside the penalty-based constrained method (`method_key="constrained"`).

---

## 0. Plain-language overview

This method is for cases where you want segments that:

1. **Fit the data well** (segments should look internally consistent), and
2. **Have a practical average length** (e.g., “on average, about 1 mile per segment”).

It uses a **genetic algorithm (GA)** to search for a good set of breakpoint milepoints. The “Deb feasibility” part means:

- If a candidate segmentation **meets the average-length requirement**, it is treated as **strictly better** than any candidate that does not.
- Only after that constraint is satisfied does the GA focus on optimizing data fit.

This is different from the penalty-based constrained GA (`constrained`), where “meeting the length target” is encouraged via a penalty term. Here it is treated as a **hard-ish constraint** using a well-known rule set (Deb’s feasibility rules).

### A quick example

Suppose a 50-mile route and you’d like segments that average **about 1.0 mile**, with a tolerance of **±0.2 miles**.

- Set `target_avg_length = 1.0`
- Set `length_tolerance = 0.2`

The GA will prefer any segmentation whose *average (non-gap) segment length* falls in $[0.8, 1.2]$ over any segmentation outside that band.

### What you get

You get a single “best” breakpoint set (per route) that:

- Always includes route boundaries and gap boundaries (mandatory breakpoints)
- Tries to satisfy `min_length`/`max_length`
- Prioritizes meeting the average length constraint, then improves fit

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

### 3.0 How to think about the key parameters

- Use `min_length` / `max_length` to encode **engineering practicality** (“don’t create 0.05-mile segments”, “don’t allow 20-mile segments”).
- Use `target_avg_length` / `length_tolerance` to encode the **planning preference** for the overall average.
- Use GA parameters to trade off **runtime vs stability**.

### 3.1 Segment constraints

- `min_length` (miles): minimum allowed segment length
- `max_length` (miles): maximum allowed segment length

Notes:

- These apply at the individual-segment level.
- If you set `min_length` too high relative to your route length (or to the available non-gap mileage), the search space can become very constrained.

### 3.2 GA parameters

- `population_size`
- `num_generations`
- `crossover_rate`
- `mutation_rate`
- `elite_ratio`

Rules of thumb:

- If results vary too much between runs, increase `population_size` and/or `num_generations`.
- If runtime is too high, decrease `population_size` first (then `num_generations`).

### 3.3 Constraint parameters

- `target_avg_length` (miles): desired average segment length
- `length_tolerance` (miles): acceptable absolute deviation from the target

How these interact:

- A small `length_tolerance` makes the constraint harder to satisfy.
- If the constraint is unrealistically tight, the GA will still return a result, but it may remain infeasible (see “both infeasible” case in Deb rules below).

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

## 7.1 What Deb feasibility means in practice

In practice, when you run an analysis you can interpret the GA’s behavior like this:

- Early generations often explore many solutions that violate the average-length target.
- As soon as the population finds feasible solutions, selection pressure shifts strongly toward keeping feasibility.
- Within the feasible set, the GA behaves like an ordinary “best fit” GA.

If you see the algorithm “stuck” near-but-not-in tolerance, it’s a sign the constraint band may be too tight for the other constraints (min/max length + mandatory breakpoints + gaps).

---

## 8. Operators and repair

The method reuses the same breakpoint-based operators as the other GA methods:

- crossover via `crossover_with_retries(...)`
- mutation via `mutation_with_retries(...)`

Mandatory breakpoints are preserved by operator design.

Invalid chromosomes are repaired using `ga._enforce_constraints(...)`.

---

## 9. Tuning and troubleshooting

### Recommended tuning workflow

1. **Set the hard bounds first**
   - Pick `min_length` and `max_length` based on what your team considers actionable.

2. **Pick a realistic target band**
   - Start with a tolerance that you expect can be met (e.g., `length_tolerance = 0.2–0.5`).
   - If you need very tight control (e.g., ±0.05), expect you’ll need more generations and that some datasets may be infeasible.

3. **Stabilize the GA**
   - If results jump around between runs, increase `population_size` and/or `num_generations`.

### Common symptoms and fixes

- **No/very few feasible solutions (constraint not met)**
  - Increase `length_tolerance`
  - Ensure `target_avg_length` is between `min_length` and `max_length`
  - Increase `population_size` / `num_generations`
  - Check whether gaps + mandatory breakpoints force segment sizes that make the target band unrealistic

- **Segments are too short / “chattery”**
  - Increase `min_length`
  - Consider lowering mutation rate slightly if the population keeps breaking good structures

- **Segments are too long / too few breakpoints**
  - Decrease `max_length`
  - Decrease `target_avg_length`

- **Runtime is too slow**
  - Reduce `population_size`
  - Reduce `num_generations`
  - Increase `cache_clear_interval` only if memory is stable and you want fewer cache resets

---

## 10. Outputs and result structure

The method returns an `AnalysisResult` with one solution in `all_solutions`.

The best solution includes (selected highlights):

- `chromosome`: breakpoint list
- `fitness` / `deviation_fitness`: base fitness $f_{\text{base}}(B)$
- `avg_segment_length`: $L(B)$ (gap-only-excluding average length)
- `target_avg_length`, `length_deviation`, `length_tolerance`
- `constraint_violation`, `is_feasible`

### 10.1 Method-owned segmentation payload

For export, this method includes a method-owned `segmentation` payload containing:

- breakpoints
- segment count / segment lengths
- `average_segment_length` (gap-only-excluding)

This avoids requiring the exporter to impose a single global definition.

---

## 11. Implementation map (source of truth)

Key implementation locations:

- Runner + Deb comparisons + selection: `src/analysis/methods/deb_feasibility_constrained.py`
- GA engine (fitness, caching, average length): `src/analysis/utils/genetic_algorithm.py`
- Operators and retry wrappers: `src/analysis/utils/ga_utilities.py`
- Parameter definitions: `src/config.py`

---

## 12. Relationship to the penalty-based constrained method

If you are choosing between constrained methods:

- Use `constrained_deb` when “meeting the average-length target” should be treated as a **first-class constraint**.
- Use `constrained` when you prefer a **soft trade-off** between fit and length via a penalty weight.

Both methods share the same breakpoint representation and gap-aware mandatory breakpoints.
