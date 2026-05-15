# Single-Objective GA (`method_key`: `single`)

This document describes the **single-objective genetic algorithm (GA)** implementation used for highway segmentation, as implemented in this repository. It is written in a “technical paper” style so it can be reused as part of a formal method description.

---## Executive Summary for Pavement Engineers

This method finds the **single best** way to divide your pavement network into homogeneous sections based on condition data (IRI, PCI, rutting, cracking indices, etc.). It uses a genetic algorithm to minimize variation within segments while respecting constraints you set (minimum/maximum project lengths).

**When to use this method:**

- You need one clear segmentation recommendation
- You're screening a network for rehabilitation priorities
- You want segments with similar condition for uniform treatment application
- You have standard project length requirements (e.g., 0.5-5 mile projects)
- You need fast results for large networks

**Typical pavement application:** Segment a 50-mile Interstate corridor by IRI to identify rehabilitation project limits that group similar roughness conditions together.

**Key advantages:**

- Fast execution (typically 1-5 minutes for 50-mile corridors)
- Single optimal answer simplifies decision-making
- Respects engineering constraints (min/max project lengths)
- Automatically handles data gaps (bridges, structures)
- Produces segments with uniform condition (low within-segment variation)

**Limitations:**

- Doesn't show tradeoffs between number of segments and quality
- Results vary slightly between runs (stochastic algorithm)
- No explicit control over total number of segments

**Next steps after reading:** See Section 3.3 for practical parameter selection guidance for pavement applications.

---

## 1. Problem formulation

Given a route sampled at positions $x_i$ with measurements $y_i$, the goal is to choose a set of breakpoints that partition the route into contiguous segments such that each segment is **internally homogeneous** (low within-segment variance).

The GA optimizes **only data fit** (no explicit objective/penalty for segment count in this method).

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

Gap analysis defines **mandatory breakpoints**. These always remain in the segmentation and are preserved by all GA operators.

Mandatory breakpoints include:

- route start and end, and
- boundaries around gaps detected using `gap_threshold`.

---

## 2.3 Pavement Engineering Context

### Why Homogeneity Matters for Pavement Management

The goal of minimizing within-segment variance (SSE - Sum of Squared Errors) has direct practical implications for pavement management:

**Treatment Uniformity**: Segments with low internal variation mean:

- Similar deterioration patterns throughout the section
- Uniform treatment can be applied (same overlay thickness, same design)
- More accurate cost estimates (less variability)
- Better performance predictions (consistent baseline)

**Practical Example with IRI Data**:

```text
Poor Segmentation (High SSE):
Segment A: MP 10.0-15.0 (5 miles)
  IRI values: 80, 85, 140, 145, 82, 88, 150 in/mi
  Mean: 110, Std Dev: 33 (high variation!)
  Problem: Mix of good (80s) and fair (140s) pavement
  → Treatment dilemma: Overlay entire 5 miles? Just the bad spots?

Good Segmentation (Low SSE):
Segment B1: MP 10.0-13.0 (3 miles)
  IRI values: 80, 85, 82, 88, 84 in/mi  
  Mean: 84, Std Dev: 3 (very uniform)
  → Clear decision: Preventive maintenance only

Segment B2: MP 13.0-15.0 (2 miles)
  IRI values: 140, 145, 138, 150, 143 in/mi
  Mean: 143, Std Dev: 5 (very uniform)
  → Clear decision: Mill and overlay needed
```

The genetic algorithm finds breakpoint locations (like MP 13.0 above) that create these homogeneous segments.

### What SSE Means for Your Data

**For IRI (roughness):** Lower SSE means ride quality is consistent within segments. Drivers experience similar roughness throughout each segment.

**For PCI (condition index):** Lower SSE means distress types and severity are similar within segments. Treatment recommendations apply uniformly.

**For Rutting:** Lower SSE means structural condition is consistent within segments. Rehabilitation depth requirements are uniform.

**For Cracking:** Lower SSE means similar cracking patterns and severity within segments. Surface treatment strategies are applicable throughout.

### Mandatory Breakpoints and Pavement Features

Mandatory breakpoints (from gaps or must-break columns) ensure the algorithm respects physical realities:

- **Bridge/structure gaps**: Prevents segments from spanning bridges and mainline pavement
- **Pavement type changes**: Forces breaks at asphalt/concrete transitions
- **Treatment boundaries**: Respects recent overlay limits
- **Functional class changes**: Separates Interstate from ramps
- **Construction history**: Breaks at known rehabilitation boundaries

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

### 3.3 Parameter Selection for Pavement Applications

Practical guidance for setting parameters based on pavement engineering requirements:

#### Length Constraints

**For IRI Segmentation on Interstate/Freeway Corridors:**

- `min_length`: 0.5-1.0 miles
  - Rationale: Minimum practical resurfacing project, crew mobilization costs
  - Too small: Excessive short projects, high per-mile costs
- `max_length`: 3-5 miles
  - Rationale: Typical Interstate resurfacing contract size, traffic control limits
  - Balance: Long enough for efficiency, short enough for condition uniformity
- **Example**: 50-mile corridor → expect 10-15 segments with these settings

**For PCI Segmentation on Urban Arterials:**

- `min_length`: 0.2-0.4 miles
  - Rationale: Shorter urban blocks, intersection-to-intersection sections
  - Urban context: More frequent feature changes (signals, intersections)
- `max_length`: 2-3 miles
  - Rationale: Urban project constraints, traffic impacts, staging
- **Example**: 20-mile urban route → expect 8-12 segments

**For Deflection (FWD) Data:**

- `min_length`: 0.5-1.0 miles
  - Rationale: Structural sections, fewer data points (testing every 500-1000 ft)
- `max_length`: 2-3 miles
  - Rationale: Structural rehabilitation project sizes

**For Network-Level Screening:**

- `min_length`: 1.0-2.0 miles
  - Rationale: Larger projects for efficiency, network-level prioritization
- `max_length`: 5-10 miles
  - Rationale: Major rehabilitation projects, multi-year capital planning

#### Algorithm Parameters

**Population Size:**

- **Small networks** (< 20 miles): 50-100 sufficient
- **Medium networks** (20-50 miles): 100-150 recommended
- **Large networks** (> 50 miles): 150-200 for thorough exploration
- **Impact**: Larger populations explore more solutions but take longer
- **Diminishing returns**: Beyond 200, improvement is typically minimal

**Number of Generations:**

- **Quick analysis**: 100 generations (often converges by generation 50-75)
- **Standard analysis**: 150-200 generations (recommended default)
- **High-quality results**: 300+ generations (marginal improvement, research use)
- **How to tell**: Monitor optimization log - if fitness plateaus for 50+ generations, algorithm has converged

**Crossover and Mutation Rates:**

- Use defaults unless you have specific reasons to adjust
- `crossover_rate`: 0.8 (80% of offspring created via crossover)
- `mutation_rate`: 0.2 (20% of offspring mutated)
- **Note**: These are standard GA values that work well for most pavement data

**Elite Ratio:**

- Default: 0.1 (top 10% preserved each generation)
- Ensures best solutions are never lost
- **Rarely needs adjustment**

#### Parameter Tuning Strategy

**Start with these settings for IRI on Interstate:**

```text
min_length: 0.5 miles
max_length: 3.0 miles
population_size: 150
num_generations: 150
(use defaults for other parameters)
```

**Then adjust based on results:**

- **Too many short segments**: Increase `min_length` to 1.0 miles
- **Missing obvious transitions**: Decrease `min_length` to 0.3 miles, check gap_threshold
- **Segments too heterogeneous**: Decrease `max_length` to 2.0 miles
- **Takes too long**: Reduce `population_size` to 100 or `num_generations` to 100
- **Results vary too much between runs**: Increase `num_generations` to 200-300

#### Gap Threshold (Framework Parameter)

Though not a GA parameter, `gap_threshold` critically affects results:

- **High-speed profiler data**: 0.05-0.10 miles (tight, precise data)
- **Manual surveys**: 0.15-0.25 miles (more tolerance for imprecision)
- **Bridge/structure handling**: 0.10-0.20 miles (span small structures)
- **Impact**: Larger threshold → fewer mandatory breaks → more GA freedom

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

### 12.1 Interpreting Results for Pavement Management

#### Understanding the Output

**Breakpoints**: Milepost locations where the algorithm identified significant condition changes. These are candidate project boundaries.

**Fitness Value**: The negative sum of squared errors (SSE). More negative = more internal variation.

- Fitness values are **relative** (compare solutions for same route)
- Cannot compare fitness across different routes or datasets
- Use fitness to compare parameter settings on the same data

**Segment Count**: Total number of segments (treatment sections) identified.

- More segments = better condition uniformity, but more projects to manage
- Fewer segments = simpler management, but more internal variation

**Segment Statistics**: For each segment:

- Start/End mileposts
- Length (miles)
- Mean condition value
- Standard deviation (variability within segment)

#### Example Interpretation

Segmentation of I-40 Eastbound (MP 196-246, 50 miles) using IRI data:

```text
Analysis Configuration:
  Method: Single-Objective GA
  min_length: 0.5 miles
  max_length: 3.0 miles
  population_size: 150
  generations: 150

Results Summary:
  18 segments identified
  Fitness: -8,542 (total SSE)
  Average segment length: 2.78 miles
  Converged at generation 87

Segment Details (selected examples):

Segment 1: MP 196.0-198.5 (2.5 mi)
  Mean IRI: 92 in/mi (Good condition)
  Std Dev: 7 in/mi (very uniform)
  → Recommendation: Preventive maintenance (crack seal, joint repair)
  → Priority: Low (5-7 year timeframe)
  → Budget: ~$15K/mile

Segment 5: MP 210.3-212.8 (2.5 mi)
  Mean IRI: 145 in/mi (Fair condition)
  Std Dev: 12 in/mi (uniform deterioration)
  → Recommendation: Mill and overlay (1.5-2 inch)
  → Priority: Medium (2-4 year timeframe)
  → Budget: ~$200K/mile
  → Note: Investigate cause of deterioration (drainage, base failure?)

Segment 12: MP 232.1-233.8 (1.7 mi)
  Mean IRI: 198 in/mi (Poor condition)
  Std Dev: 28 in/mi (WARNING: high variability!)
  → Recommendation: Field investigation required
  → Priority: High (immediate to 1 year)
  → Action: Cores, FWD testing, drainage evaluation
  → Note: High std dev suggests mixed conditions or localized failures

Segment 18: MP 244.2-246.0 (1.8 mi)
  Mean IRI: 78 in/mi (Excellent condition)
  Std Dev: 5 in/mi (very uniform)
  → Recommendation: Routine maintenance only
  → Priority: None (monitoring only)
```

#### Validation Checklist

Before using results for project planning:

**✅ Physical Feature Alignment:**

- Do breakpoints align with known features?
  - Bridge/structure locations
  - Previous overlay boundaries
  - Construction project limits
  - Pavement type transitions
- Use Google Earth, construction records, maintenance logs to verify

**✅ Segment Length Practicality:**

- Are lengths appropriate for your agency's projects?
  - Check against typical contract sizes
  - Consider traffic control requirements
  - Verify contractor mobilization efficiency
- If many segments near `min_length`: Consider increasing constraint

**✅ Condition Uniformity:**

- Check standard deviations within segments
  - Low std dev (< 10% of mean): Excellent uniformity
  - Medium std dev (10-20% of mean): Acceptable
  - High std dev (> 20% of mean): Investigate further
- High std dev may indicate:
  - Localized distress within section
  - Data quality issues
  - Transition zones
  - Mixed treatments needed

**✅ Field Validation:**

- Visit representative segments
- Verify condition matches data
- Check for features not in database:
  - Recent maintenance
  - Drainage issues
  - Subsurface problems
  - Traffic pattern changes

**✅ Comparison with Engineering Judgment:**

- Do results match experienced staff observations?
- Are there obvious transitions the algorithm missed?
  - May need to adjust `gap_threshold`
  - May need to add must-break columns
- Are there breakpoints that don't make sense?
  - Check data quality
  - Verify input column selection

#### Common Result Patterns and Actions

##### Pattern 1: Too Many Short Segments

- **Observation**: Many segments at or near `min_length`
- **Cause**: Data has high variability, algorithm wants more breaks
- **Action**: Increase `min_length` to force consolidation, or accept that pavement is highly variable

##### Pattern 2: Missing Obvious Transitions

- **Observation**: Known overlay boundary not detected
- **Cause**: Treatment performing similar to adjacent pavement (good!)
- **Action**: If administratively important, add as must-break column

##### Pattern 3: Breakpoints at Every Bridge

- **Observation**: Segment boundaries at each structure
- **Cause**: `gap_threshold` too sensitive
- **Action**: Increase `gap_threshold` to 0.2-0.3 miles to span short bridges

##### Pattern 4: High Variation Within Segments

- **Observation**: Large standard deviations in multiple segments
- **Cause**: `max_length` too large, forcing heterogeneous sections
- **Action**: Reduce `max_length` or accept need for field investigation

#### Using Results for Budget Planning

Once segmentation is validated:

1. **Classify segments by treatment need:**
   - Excellent (IRI < 95): Routine maintenance
   - Good (IRI 95-120): Preventive maintenance
   - Fair (IRI 120-170): Rehabilitation (overlay)
   - Poor (IRI > 170): Reconstruction evaluation

2. **Estimate costs:**
   - Preventive: $10-30K/mile
   - Overlay: $150-300K/mile
   - Reconstruction: $500K-2M/mile

3. **Prioritize by:**
   - Safety (high roughness, high traffic)
   - Network importance (Interstate > arterial)
   - Deterioration rate (monitor annually)
   - Adjacent project opportunities

4. **Develop program:**
   - Year 1: Critical segments (poor condition, high traffic)
   - Years 2-3: Fair condition segments
   - Years 4-5: Preventive maintenance

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

---

## 15. Additional Resources for Pavement Engineers

### Genetic Algorithms

- **Introduction to Genetic Algorithms**: <https://en.wikipedia.org/wiki/Genetic_algorithm>
  - Overview of evolutionary computation principles
- **GA Tutorial for Engineers**: <https://www.mathworks.com/help/gads/what-is-the-genetic-algorithm.html>
  - Practical introduction with examples
- **Genetic Algorithms in Engineering**: <https://link.springer.com/book/10.1007/978-3-662-43505-2>
  - Academic reference for optimization applications

### Pavement Management and Segmentation

- **FHWA Pavement Management Guide**: <https://www.fhwa.dot.gov/pavement/management/>
  - Comprehensive guidance on pavement management systems
- **AASHTO Pavement Management Guide**: <https://www.transportation.org/>
  - Standards and practices for pavement condition assessment
- **NCHRP Pavement Condition Assessment**: <https://www.trb.org/NCHRP/Blurbs/180706.aspx>
  - Research on condition assessment and data collection
- **Long-Term Pavement Performance (LTPP)**: <https://www.fhwa.dot.gov/research/tfhrc/programs/infrastructure/pavements/ltpp/>
  - National database of pavement condition and performance

### Statistical Concepts

- **Understanding SSE (Sum of Squared Errors)**: <https://en.wikipedia.org/wiki/Residual_sum_of_squares>
  - Mathematical foundation of the fitness function
- **Variance and Standard Deviation**: <https://en.wikipedia.org/wiki/Standard_deviation>
  - Measuring data variability within segments
- **Statistical Segmentation Methods**: <https://en.wikipedia.org/wiki/Change_detection>
  - Alternative approaches to segmentation

### Pavement Condition Indices

- **IRI (International Roughness Index)**: <https://www.fhwa.dot.gov/publications/research/infrastructure/pavements/ltpp/13091/002.cfm>
  - FHWA guidance on ride quality measurement
- **PCI (Pavement Condition Index)**: <https://www.asphaltpavement.org/>
  - ASTM standards for condition rating
- **Pavement Distress Types**: <https://www.fhwa.dot.gov/pavement/pub_details.cfm?id=808>
  - Identification and measurement guidance

### Software and Tools

- **Highway Performance Monitoring System (HPMS)**: <https://www.fhwa.dot.gov/policyinformation/hpms.cfm>
  - Federal pavement data collection standards
- **Pavement ME Design**: <https://www.fhwa.dot.gov/pavement/me_design/>
  - Mechanistic-empirical pavement design

### Related Research

For academic users interested in optimization-based segmentation:

- Search terms: "pavement segmentation genetic algorithm", "highway network optimization", "condition-based segmentation"
- Conference proceedings: TRB Annual Meeting, International Conference on Pavement Management
- Journals: Transportation Research Record, Journal of Transportation Engineering, Road Materials and Pavement Design
