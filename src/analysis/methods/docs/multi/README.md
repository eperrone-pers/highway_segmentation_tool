# Multi-Objective NSGA-II (`method_key`: `multi`)

This document describes the **multi-objective genetic algorithm** implementation based on **NSGA-II** (Non-dominated Sorting Genetic Algorithm II) used for highway segmentation in this repository. It is written in a “technical paper” style so it can be reused as part of a formal method description.

---## Executive Summary for Pavement Engineers

This method finds **multiple optimal solutions** that show the tradeoff between pavement condition uniformity (quality) and project size (practicality). Instead of one answer, you get a **Pareto front** - a curve showing all the best balances between having many short, homogeneous segments versus fewer longer segments.

**When to use this method:**

- You need to present multiple options to decision-makers or stakeholders
- Budget is uncertain and you want to show "what-if" scenarios
- Quality vs. cost tradeoffs need to be explicitly visualized
- Different stakeholders prefer different segment granularity
- You want to explore the full range of reasonable segmentation strategies

**Typical pavement application:** Show agency management 3-5 segmentation alternatives for a 100-mile arterial network, demonstrating how "15 projects of 6.7 miles" compares to "30 projects of 3.3 miles" in terms of condition uniformity and budget implications.

**Key advantages:**

- **Informed decision-making**: Visualize quality-vs-quantity tradeoffs explicitly
- **Flexible planning**: Select solution based on actual budget availability
- **Stakeholder engagement**: Show range of possibilities when preferences differ
- **Transparent**: Every point on Pareto front is optimal for its specific balance
- **Comprehensive**: Explores solution space more thoroughly than single-objective

**Limitations:**

- Takes longer to run (2-3× more generations than single-objective)
- Requires user to select final solution from Pareto front (not automatic)
- More complex to explain to non-technical audiences
- Multiple runs show more variability due to stochastic nature

**How to interpret results:** The Pareto front is a curve in 2D space:

- **X-axis**: Average segment length (miles)
- **Y-axis**: Solution quality (lower total deviation = better)
- **Left side** of curve: More segments, shorter lengths, better quality, higher total project count
- **Right side** of curve: Fewer segments, longer lengths, acceptable quality, simpler management
- **Middle**: Balanced compromises

Every point on the curve is **non-dominated** - you can't improve one objective without sacrificing the other.

**Next steps after reading:** See Section 3.3 for parameter guidance and Section 12.1 for detailed Pareto front interpretation.

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

## 2.3 Pavement Engineering Context

### The Quality vs. Practicality Tradeoff

In pavement management, there's always a tension between:

**Quality (Homogeneity):**

- More breakpoints → more segments → better condition uniformity within each segment
- Advantages: Precise treatment selection, accurate cost estimates, better performance
- Disadvantages: More projects to manage, higher per-mile costs, complex coordination

**Practicality (Simplicity):**

- Fewer breakpoints → fewer segments → longer projects
- Advantages: Simpler management, economies of scale, fewer contract mobilizations
- Disadvantages: More condition variation within segments, less precise treatment

This method makes this tradeoff explicit by optimizing both objectives simultaneously.

### Real-World Example

Consider a 60-mile Interstate corridor with IRI data:

**High-Quality Solution** (left side of Pareto front):

```text
25 segments, average 2.4 miles each
Total SSE: 5,200 (excellent uniformity)
Implications:
  ✓ Very homogeneous segments (precise treatment selection)
  ✓ Minimize material waste (exact needs)
  ✗ 25 separate projects to manage
  ✗ More traffic control setups
  ✗ Higher per-mile costs
Best for: Well-funded agencies, detailed analysis, research studies
```

**Balanced Solution** (middle of Pareto front):

```text
15 segments, average 4.0 miles each
Total SSE: 6,800 (good uniformity)
Implications:
  ✓ Reasonable homogeneity
  ✓ Manageable project count
  ✓ Good cost efficiency
  ~ Some internal variation acceptable
Best for: Most agencies, practical project planning
```

**Simple Solution** (right side of Pareto front):

```text
8 segments, average 7.5 miles each  
Total SSE: 9,500 (acceptable uniformity)
Implications:
  ✓ Simple project portfolio
  ✓ Major economies of scale
  ✓ Fewer mobilizations
  ✗ More condition variation within segments
  ✗ May need variable treatment depths
Best for: Budget-constrained agencies, major rehabilitation programs
```

### When Multi-Objective Analysis Adds Value

**Budget uncertainty scenarios:**

- "We have $8-12M available" → Show what segmentation makes sense at each level
- Multi-year planning with uncertain future funding

**Stakeholder alignment:**

- Engineering staff wants fine-grained analysis (more segments)
- Operations staff wants simplicity (fewer projects)
- Management wants options → Pareto front shows the full spectrum

**Treatment strategy exploration:**

- Fine segmentation → Precise preventive maintenance
- Coarse segmentation → Major rehabilitation corridors
- Show both strategies and their implications

**Performance monitoring:**

- Fine segmentation → Track deterioration precisely
- Coarse segmentation → Network-level trends

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

### 3.3 Parameter Selection for Pavement Applications

Multi-objective optimization requires more computational effort than single-objective, so parameters need careful tuning.

#### Length Constraints

**Use the same min/max length guidelines as single-objective method:**

- **Interstate/Freeway**: min=0.5-1.0 mi, max=3-5 mi
- **Urban Arterials**: min=0.2-0.4 mi, max=2-3 mi
- **Rural Highways**: min=1.0-2.0 mi, max=5-8 mi

See single-objective GA documentation (Section 3.3) for detailed rationale.

**Important**: Length constraints define the feasible space that the Pareto front explores. Tighter constraints (smaller range) may reduce Pareto front diversity.

#### Algorithm Parameters

**Population Size:**

- **Minimum recommended**: 150 (multi-objective needs larger populations)
- **Standard**: 200-300 (recommended for most pavement applications)
- **Large networks**: 300-500 (for comprehensive Pareto front coverage)
- **Why larger**: Need to maintain diverse solutions across the entire Pareto front

**Number of Generations:**

- **Minimum**: 200 (multi-objective convergence is slower)
- **Recommended**: 300-400 (allows Pareto front to stabilize)
- **High-quality**: 500+ (research, critical decisions)
- **How to assess**: Check if Pareto front shape is stable in final 100 generations

**Crossover and Mutation Rates:**

- Use defaults (crossover=0.8, mutation=0.2)
- Multi-objective is less sensitive to these than single-objective

**Cache Clear Interval:**

- Default (50 generations) usually sufficient
- Increase to 100 for large populations to reduce overhead

#### Recommended Starting Configuration

**For typical 50-mile Interstate corridor IRI analysis:**

```text
min_length: 0.5 miles
max_length: 3.0 miles
population_size: 250
num_generations: 300
crossover_rate: 0.8 (default)
mutation_rate: 0.2 (default)
cache_clear_interval: 50 (default)
enable_performance_stats: true (helps monitor convergence)
```

**Expected outcomes:**

- Pareto front with 20-40 non-dominated solutions
- Runtime: 5-15 minutes (depending on hardware)
- Segment counts ranging from ~10 to ~30 segments
- Average lengths from ~2 to ~5 miles

#### Parameter Tuning Based on Results

##### Issue: Pareto front too narrow (not enough diversity)

- Increase population_size to 300-400
- Widen min/max length range
- Increase num_generations to 400-500

##### Issue: Takes too long to run

- Reduce population_size to 150-200
- Reduce num_generations to 200-250
- Trade-off: May get less complete Pareto front

##### Issue: Unstable front (varies a lot between runs)

- Increase num_generations to 400-500
- Increase population_size to 300
- Run multiple times and combine fronts

##### Issue: All solutions look similar

- Check if length constraints are too restrictive
- Verify gap_threshold isn't creating too many mandatory breaks
- May indicate data is naturally uniform (not a problem!)

#### Gap Threshold Considerations

Same guidance as single-objective (see Section 3.3 in single-objective documentation):

- High-speed profiler: 0.05-0.10 miles
- Manual surveys: 0.15-0.25 miles
- Impact: More mandatory breaks → less Pareto diversity

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

The second objective is the **average segment length excluding gap-only segments**, returned as a positive value.

In this repository, a **gap-only segment** is a segment whose boundaries exactly match a detected gap interval (gap_start → gap_end). These segments contain no data and are excluded from this average.

This objective promotes solutions with fewer/larger data-bearing segments while avoiding distortion from pure gaps.

### 6.3 Returned objective vector

The GA returns:

$$\mathbf{f}(B) = (f_1(B), f_2(B)) = (-\mathrm{SSE}(B), \mathrm{avgLengthExcludingGaps}(B))$$

These are stored as raw values in the output JSON as `objective_values[0]` and `objective_values[1]` (plotting may apply display transforms configured in `src/config.py`).

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

The runner also computes a “compromise” solution by normalizing both objectives and choosing the minimum summed score. This is used for logging and may be used as a primary selection in downstream consumers.### 12.1 Interpreting the Pareto Front for Pavement Management

### Understanding the Pareto Front Visualization

When you run multi-objective optimization, the enhanced visualization window shows:

**Left Panel - Pareto Front Plot:**

- **X-axis**: Average Segment Length (miles) - increases left to right
- **Y-axis**: Total Deviation (SSE) - lower is better (less variation)
- **Each point**: One complete segmentation solution
- **Shape**: Typically curves from lower-left to upper-right

**Right Panel - Selected Solution Detail:**

- Click any point on the Pareto front
- Shows the detailed segmentation for that solution
- Displays segment boundaries, statistics, and breakpoints

#### Navigating the Pareto Front

**Lower-Left Points** (High Quality, Many Segments):

```text
Characteristics:
  • More breakpoints
  • Shorter segments
  • Lower total SSE (better uniformity)
  • Higher segment count

Pavement Engineering Implications:
  ✓ Precise treatment selection
  ✓ Minimal material waste
  ✓ Better condition uniformity
  ✗ More projects to manage
  ✗ Higher per-mile costs
  ✗ More traffic control setups

Best for:
  • High-detail analysis
  • Well-funded agencies
  • Research studies
  • Performance monitoring
  • Preventive maintenance programs
```

**Upper-Right Points** (Simplicity, Fewer Segments):

```text
Characteristics:
  • Fewer breakpoints
  • Longer segments
  • Higher total SSE (more variation)
  • Lower segment count

Pavement Engineering Implications:
  ✓ Simpler project portfolio
  ✓ Economies of scale
  ✓ Fewer mobilizations
  ✓ Lower overhead costs
  ✗ More condition variation
  ✗ Less precise treatment
  ✗ Variable treatment depths may be needed

Best for:
  • Budget-constrained scenarios
  • Major rehabilitation corridors
  • Network-level prioritization
  • Large contract opportunities
```

**Middle Points** (Balanced Solutions):

```text
Characteristics:
  • Moderate breakpoints
  • Reasonable segment lengths
  • Acceptable uniformity
  • Manageable project count

Pavement Engineering Implications:
  ✓ Practical for most agencies
  ✓ Good quality-cost balance
  ✓ Reasonable project management load
  ✓ Defendable engineering decisions

Best for:
  • Most real-world applications
  • Standard project planning
  • Budget-conscious quality management
```

#### Step-by-Step: Selecting Your Solution

##### Step 1: Define Your Constraints

- Budget available: Total $ for all projects
- Maximum number of projects manageable
- Minimum acceptable quality (maximum std dev within segments)
- Timeline constraints (how many projects per year?)

##### Step 2: Explore the Pareto Front

Click through multiple points on the front:

- **Left side**: Note the segment count and quality
- **Middle**: Look for good balance points
- **Right side**: Check if segments are too heterogeneous

##### Step 3: Apply Engineering Filters

For each candidate solution, check:

```text
✓ Do breakpoints align with known features?
  → Bridges, overlays, treatment boundaries

✓ Are segment lengths practical?
  → Typical contract sizes, crew efficiency

✓ Is condition uniform enough within segments?
  → Check std dev for each segment

✓ Does total project count fit budget?
  → Multiply segment count × typical cost/mile

✓ Can agency manage this many projects?
  → Consider staffing, timeline, priorities
```

##### Step 4: Compare 2-3 Finalists

Select 2-3 points that seem reasonable:

- Export each to Excel
- Calculate total costs
- Review segment-by-segment
- Present to decision-makers with cost/benefit for each

##### Step 5: Make Final Selection

Based on:

- Actual budget availability
- Stakeholder preferences
- Operational constraints
- Engineering judgment

#### Example Interpretation

Analysis of US-61 Arterial (MP 10-80, 70 miles) with PCI data:

```text
Pareto Front Generated:
  40 non-dominated solutions
  Segment counts: 12 to 35
  Average lengths: 2.0 to 5.8 miles
  Total SSE: 4,200 to 8,900

Three Solutions Evaluated:

Option A (Left side - High Quality):
  35 segments, average 2.0 miles
  Total SSE: 4,200 (excellent uniformity)
  Cost estimate: 35 projects × $200K/mi × 2.0 mi = $14M
  Management: 12 projects/year for 3 years
  Recommendation: Too many projects for current staffing

Option B (Middle - Balanced):
  20 segments, average 3.5 miles
  Total SSE: 5,800 (good uniformity)
  Cost estimate: 20 projects × $200K/mi × 3.5 mi = $14M
  Management: 7 projects/year for 3 years
  ✓ SELECTED: Best balance of quality and practicality

Option C (Right side - Simple):
  12 segments, average 5.8 miles
  Total SSE: 8,900 (acceptable uniformity)
  Cost estimate: 12 projects × $200K/mi × 5.8 mi = $13.9M
  Management: 4 projects/year for 3 years
  Concern: Some segments showed high std dev (mixed conditions)
  Recommendation: Rejected due to quality concerns

Final Selection: Option B
Rationale:
  • Manageable project count
  • Acceptable quality (avg std dev = 8 PCI points)
  • Fits 3-year capital plan
  • Total cost within budget authority
  • Stakeholder consensus achieved
```

#### Using Multiple Solutions for Scenario Planning

Don't just pick one solution - use the Pareto front for scenarios:

##### Scenario 1: Full Funding ($14M available)

- Select middle-left solution (25 segments, high quality)
- Implement high-priority segments first
- Phased approach over 4 years

##### Scenario 2: Reduced Funding ($9M available)

- Select middle-right solution (15 segments, acceptable quality)
- Focus on worst-condition corridors
- Defer lower-priority sections

##### Scenario 3: Emergency Funding ($5M immediate)

- Use segmentation to identify top 10 worst segments
- Address critical needs only
- Plan for remaining segments in future years

#### Red Flags When Reviewing Solutions

**Warning signs to investigate:**

**Flat Pareto Front:**

- Indicates limited tradeoff between objectives
- May mean data is naturally uniform (good!)
- Or constraints are too restrictive (widen min/max length)

**Discontinuous Front:**

- Gaps in the Pareto curve
- May need more generations or larger population
- Or indicates discrete jumps due to mandatory breakpoints (acceptable)

**All Solutions Similar:**

- Check if gap_threshold created too many mandatory breaks
- Verify min/max length constraints aren't too tight
- May indicate homogeneous pavement (not a problem)

**Unstable Between Runs:**

- Pareto front shape varies significantly if you run again
- Increase num_generations to 400-500
- Increase population_size to 300-400
- Or accept variability and run 3-5 times, select consensus solutions

#### Documentation for Decision-Makers

When presenting results:

**Include:**

1. Pareto front plot with 3-5 highlighted candidate solutions
2. Table comparing candidates:
   - Segment count
   - Average length
   - Total cost estimate
   - Quality metric (avg std dev)
   - Implementation timeline
3. Map showing breakpoints for each candidate
4. Recommendation with clear rationale
5. Sensitivity: "If budget reduced by 20%, we recommend Option C"

**Avoid:**

- Technical jargon (SSE, fitness, crowding distance)
- Too many options (narrow to 3-5 finalists)
- Presenting without cost estimates
- Ignoring implementation practicality

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

## 15. Additional Resources for Pavement Engineers

### Multi-Objective Optimization

- **Introduction to Multi-Objective Optimization**: <https://en.wikipedia.org/wiki/Multi-objective_optimization>
  - Overview of Pareto optimality and non-dominated solutions
- **NSGA-II Algorithm**: <https://en.wikipedia.org/wiki/Non-dominated_sorting_genetic_algorithm_II>
  - Details on the specific algorithm used in this method
- **Pareto Front Explained**: <https://www.mathworks.com/help/gads/what-is-multiobjective-optimization.html>
  - Visual introduction to Pareto fronts and tradeoffs
- **Multi-Criteria Decision Making**: <https://link.springer.com/book/10.1007/978-1-4614-3597-6>
  - Academic reference for decision-making with multiple objectives

### Pavement Management Decision-Making

- **FHWA Asset Management Primer**: <https://www.fhwa.dot.gov/asset/>
  - Framework for using optimization in pavement management
- **AASHTO Transportation Asset Management Guide**: <https://www.transportation.org/>
  - Guidance on multi-criteria project prioritization
- **NCHRP Multi-Objective Optimization Research**: <https://www.trb.org/NCHRP/Blurbs/180706.aspx>
  - Research on optimization methods for pavement management

### Decision Analysis Tools

- **Cost-Benefit Analysis**: <https://www.fhwa.dot.gov/infrastructure/asstmgmt/>
  - Methods for comparing alternative solutions
- **Risk-Based Decision Making**: <https://safety.fhwa.dot.gov/hsip/>
  - Incorporating uncertainty into project selection

### General Resources

See also Single-Objective GA documentation (Section 15) for:

- Genetic algorithm fundamentals
- Pavement condition indices (IRI, PCI, etc.)
- Statistical concepts
- Pavement management guides

### Related Research

For academic users:

- Search terms: "multi-objective pavement management", "Pareto optimization highway", "NSGA-II infrastructure"
- Key journals: Transportation Research Part C, Computer-Aided Civil and Infrastructure Engineering
- Conference: TRB Annual Meeting Committee AKP30 (Pavement Management Systems)

---

## 16. Code-Review Notes (Suggestions Only)

The following are observations from reading the current implementation, listed for discussion before making any code changes:

- The call site for NSGA-II tournament selection in `src/analysis/methods/multi_objective.py` should be double-checked against the function signature in `src/analysis/utils/ga_utilities.py` to ensure the arguments are in the intended order.
- Cache clearing logic should be reviewed to confirm it targets the actual GA cache attributes (the GA class stores `_fitness_cache` / `_multi_fitness_cache` and exposes `clear_cache()`).
