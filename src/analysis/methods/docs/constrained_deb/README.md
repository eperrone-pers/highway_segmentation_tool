# Constrained GA (Deb Feasibility) (`method_key`: `constrained_deb`)

This document describes the **Deb-feasibility constrained genetic algorithm** used for highway segmentation in this repository.

This method is intentionally additive: it provides a second constrained GA variant alongside the penalty-based constrained method (`method_key="constrained"`).

---

## Executive Summary for Pavement Engineers

This method is very similar to the **Constrained GA** but uses a different approach to enforce the length constraint. Instead of using a penalty weight, it treats the length constraint as a **hard requirement** using Deb's feasibility rules.

**Key difference from penalty-based constrained GA:**

- **Penalty method** (`constrained`): Tunable tradeoff via penalty weight - you control how much to sacrifice quality for length compliance
- **Deb method** (`constrained_deb`): Binary distinction - feasible solutions (meeting length target) **always** beat infeasible solutions, regardless of quality

**When to use Deb Feasibility instead of penalty-based:**

- ✅ Length requirement is **absolutely mandatory** (regulatory, PMS requirement)
- ✅ You want simpler parameter tuning (no penalty weight to adjust)
- ✅ "Meet the constraint" is more important than "optimize quality"
- ✅ Willing to accept lower data quality if that's what it takes to meet length target
- ✅ Previous penalty-based attempts couldn't satisfy constraint at any weight

**When to use penalty-based constrained GA instead:**

- ✅ Length target is important but not absolute (guideline vs. requirement)
- ✅ You want explicit control over quality vs. constraint tradeoff
- ✅ Willing to tune penalty weight to find right balance
- ✅ Quality matters as much as length compliance

**Typical pavement application:** State DOT has absolute requirement that Interstate segments average 1.0 ± 0.2 miles for federal reporting, and quality is secondary to compliance.

**How it works:**

1. GA searches for solutions that meet the length constraint
2. **Any** solution within tolerance is considered better than **any** solution outside tolerance
3. Among feasible solutions, picks the one with best data quality
4. Among infeasible solutions (if constraint can't be met), picks the one closest to target

**Success indicator:** Results show "Constraint satisfied: YES" (is_feasible: true)

**Advantage over penalty method:** Simpler - no penalty weight to tune, just set tolerance.

**Disadvantage:** Less control - can't fine-tune the quality vs. compliance tradeoff.

**Next steps after reading:** See Section 3.0 for parameter guidance and Section 9 for troubleshooting.

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

## 2.3 Pavement Engineering Context

### When Hard Constraints Make Sense

**Regulatory compliance scenarios:**

Some agencies face strict requirements where "close enough" isn't acceptable:

- **Federal reporting**: HPMS requires specific segment definitions
- **Grant compliance**: Funding tied to standardized section lengths
- **Legal requirements**: Court-ordered monitoring using fixed sections
- **Interstate agreements**: Multi-state consistency requirements
- **Software constraints**: Legacy PMS only accepts exact lengths

#### Example: Federal HPMS Reporting

```text
Requirement:
  "Interstate pavement sections shall be reported in
   1.0-mile increments with maximum 0.1-mile deviation"
  
Consequence of non-compliance:
  - Federal funding eligibility at risk
  - Audit findings
  - Manual data correction required
  
Solution:
  Use Deb Feasibility with:
    target_avg_length: 1.0
    length_tolerance: 0.1  (strict!)
  
  Algorithm will ONLY accept solutions within 0.9-1.1 mile average
```

### Deb Feasibility vs. Penalty Method: Practical Comparison

#### Scenario: 50-mile corridor, target 1.0 ± 0.2 miles

**Penalty Method Results:**

```text
With penalty_weight = 100:
  Achieved: 1.25 miles (outside tolerance)
  SSE: 4,800 (excellent quality)
  Constraint satisfied: NO
  
With penalty_weight = 500:
  Achieved: 1.08 miles (within tolerance)
  SSE: 6,200 (good quality)
  Constraint satisfied: YES ✓
  
Characteristic:
  - Tunable tradeoff between quality and constraint
  - Can choose "acceptable quality loss" via weight
  - Requires experimentation to find right weight
```

**Deb Feasibility Results:**

```text
With same constraints:
  Achieved: 1.02 miles (within tolerance)
  SSE: 7,100 (acceptable quality)
  Constraint satisfied: YES ✓
  
Characteristic:
  - Automatically enforces constraint as hard requirement
  - No weight tuning needed
  - May sacrifice more quality to ensure feasibility
  - Simpler to use but less controllable
```

**Decision guide:**

**Use Penalty Method when:**

- You can accept "close" to target if quality is much better
- Want to explicitly control the tradeoff
- Have time to experiment with penalty weights
- Compliance is important but not absolute

**Use Deb Feasibility when:**

- Must meet constraint, period (regulatory requirement)
- Want simpler setup (no weight tuning)
- Willing to accept whatever quality is needed for compliance
- Penalty method failed to satisfy constraint at reasonable weights

### Real-World Agency Example

**State DOT Scenario:**

```text
Agency Mandate:
  "All Interstate segments in PMS must average 1.0 miles
   per 23 CFR 490 federal requirements"
  
Previous Approach:
  - Used penalty-based constrained GA
  - Tried penalty weights: 100, 300, 500, 800
  - Never achieved constraint satisfaction
  - Always got 1.3-1.5 mile averages
  
Solution:
  - Switched to Deb Feasibility
  - Set target: 1.0, tolerance: 0.2
  - Result: 1.07 miles ✓ (satisfied!)
  - Quality: 15% worse SSE than penalty method
  - Decision: Acceptable - compliance is mandatory
  
Outcome:
  - Federal reporting requirement met
  - PMS integration successful
  - Funding eligibility maintained
```

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

### 3.5 Parameter Selection for Pavement Applications

#### Target Average Length and Tolerance

**Use same guidance as penalty-based constrained GA:**

See Constrained GA documentation Section 3.5 for detailed guidance on:

- Setting target based on agency requirements
- Typical tolerances (20% of target is common)
- Feasibility checks

**Key difference for Deb Feasibility:**

With Deb method, tolerance is more critical because it's a hard cutoff:

**Tight tolerance (±0.1 miles):**

```text
Effect:
  - Very strict requirement
  - May be difficult to satisfy
  - Algorithm will sacrifice significant quality if needed
  
Use when:
  - Regulatory requirement is precise
  - No flexibility allowed
  
Risk:
  - May get poor segmentation quality
  - Or fail to satisfy constraint entirely
```

**Moderate tolerance (±0.2 miles) - RECOMMENDED:**

```text
Effect:
  - Reasonable flexibility
  - Usually achievable
  - Modest quality sacrifice
  
Use when:
  - Standard agency application
  - Balances compliance with practicality
```

**Relaxed tolerance (±0.3-0.5 miles):**

```text
Effect:
  - Easy to satisfy
  - Minimal quality sacrifice
  - Wide acceptable range
  
Use when:
  - Target is guideline, not strict requirement
  - Flexibility acceptable
  
Note:
  If tolerance is this wide, consider using
  unconstrained method instead
```

#### Algorithm Parameters

**Population Size:**

- **Minimum**: 150 (Deb feasibility needs good exploration)
- **Recommended**: 200-250 (helps find feasible solutions)
- **Large/difficult**: 300+ (tight constraints, hard-to-satisfy targets)

**Generations:**

- **Minimum**: 150
- **Recommended**: 200-300 (Deb method may take longer to find feasibility)
- **Difficult constraints**: 400-500

**Why more than penalty method?**

Deb feasibility uses binary distinction (feasible/infeasible), which can slow convergence:

- Early generations may all be infeasible
- Once feasibility found, sudden shift in selection pressure
- More generations help stabilize

**Other parameters:**

- Use defaults for crossover_rate, mutation_rate, elite_ratio
- Same min/max_length guidance as other GA methods

#### Recommended Starting Configuration

**For typical Interstate 1-mile standard:**

```text
target_avg_length: 1.0
length_tolerance: 0.2

min_length: 0.5
max_length: 2.0

population_size: 200
num_generations: 250

crossover_rate: 0.8 (default)
mutation_rate: 0.2 (default)
elite_ratio: 0.1 (default)

cache_clear_interval: 50 (default)
enable_performance_stats: true
```

**Expected outcomes:**

- Constraint satisfaction: YES (within 0.8-1.2 miles)
- Runtime: 8-20 minutes (depending on hardware)
- Quality: 10-30% worse SSE than unconstrained
- Acceptable tradeoff for compliance

#### When to Increase Parameters

**If constraint not satisfied after first run:**

```text
Step 1: Increase generations to 400
Step 2: Increase population to 300
Step 3: Widen tolerance to 0.3 (if allowed)
Step 4: Check if target is realistic (see Section 9)
```

**If results vary a lot between runs:**

```text
Step 1: Increase population to 300
Step 2: Increase generations to 400
Step 3: Run multiple times, select most consistent
```

**If runtime too long:**

```text
Step 1: Reduce population to 150
Step 2: Reduce generations to 200
Step 3: Accept that results may be less stable
```

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

#### No/very few feasible solutions (constraint not met)

- Increase `length_tolerance`
- Ensure `target_avg_length` is between `min_length` and `max_length`
- Increase `population_size` / `num_generations`
- Check whether gaps + mandatory breakpoints force segment sizes that make the target band unrealistic

**Pavement-specific diagnosis:**

```text
Problem: Constraint never satisfied
  Achieved: 1.45 miles, Target: 1.0 ± 0.2
  
Check 1: Are there many mandatory breakpoints?
  → Count gaps and must-break column changes
  → Each mandatory break constrains solution space
  → May make target infeasible
  
Check 2: Is min_length too high?
  → If min_length = 0.8 and target = 1.0
  → Very little room for algorithm to work
  → Try min_length = 0.5
  
Check 3: Run unconstrained GA for comparison
  → What average does it naturally produce?
  → If unconstrained gives 2.5 miles average
  → Then 1.0-mile target may be unrealistic
  
Check 4: Is tolerance too tight?
  → Try doubling tolerance: 0.2 → 0.4
  → See if constraint becomes satisfiable
```

#### Segments are too short / "chattery"

- Increase `min_length`
- Consider lowering mutation rate slightly if the population keeps breaking good structures

#### Segments are too long / too few breakpoints

- Decrease `max_length`
- Decrease `target_avg_length`

#### Runtime is too slow

- Reduce `population_size`
- Reduce `num_generations`
- Increase `cache_clear_interval` only if memory is stable and you want fewer cache resets

#### Constraint satisfied but quality is poor (high SSE)

```text
Problem:
  Constraint: YES (achieved 1.03 miles)
  But: SSE 50% higher than unconstrained
  And: Many segments have high std dev
  
Diagnosis:
  Target forces unnatural segmentation
  Algorithm sacrificing quality for compliance
  
Options:
  1. Accept quality loss (compliance is mandatory)
  2. Try penalty method instead (more control)
  3. Relax tolerance if allowed
  4. Reconsider if target is appropriate
  
Decision framework:
  - If compliance is regulatory: Accept quality loss
  - If target is guideline: Switch to penalty method
  - If quality matters most: Use unconstrained method
```

### Comparing Deb vs. Penalty Method Results

#### Recommendation: Run both methods and compare

```text
Scenario: 60-mile route, target 1.0 ± 0.2 miles

Penalty Method (weight=300):
  Constraint: YES
  Achieved: 1.06 miles
  SSE: 5,400
  Segments: 54
  
Deb Feasibility:
  Constraint: YES
  Achieved: 0.98 miles
  SSE: 6,100 (13% worse)
  Segments: 59
  
Analysis:
  - Both satisfy constraint
  - Penalty method gave better quality
  - Deb method closer to target center
  
Decision:
  - For this data: Use penalty method
  - Better quality, still compliant
  - Save Deb method for stricter requirements
```

**When Deb method wins:**

- Penalty method can't satisfy constraint at any weight
- Need to be very close to target (within tight tolerance)
- Simpler parameter tuning outweighs quality difference

---

## 10. Outputs and result structure

The method returns an `AnalysisResult` with one solution in `all_solutions`.

The best solution includes (selected highlights):

- `chromosome`: breakpoint list
- `fitness` / `deviation_fitness`: base fitness $f_{\text{base}}(B)$
- `avg_segment_length`: $L(B)$ (gap-only-excluding average length)
- `target_avg_length`, `length_deviation`, `length_tolerance`
- `constraint_violation`, `is_feasible`

**Key result fields for pavement engineers:**

```text
is_feasible: true/false
  → Most important field
  → true = constraint satisfied
  → false = constraint not satisfied
  
avg_segment_length: X.XX miles
  → Achieved average (excluding gaps)
  
length_deviation: X.XX miles
  → |achieved - target|
  
constraint_violation: X.XX miles
  → How far outside tolerance (0 if feasible)
  
deviation_fitness / SSE:
  → Data quality metric
  → Compare to unconstrained run
```

**Interpretation example:**

```text
Result:
  is_feasible: true ✓
  target: 1.0, tolerance: 0.2
  avg_segment_length: 1.04
  length_deviation: 0.04 (within 0.2)
  constraint_violation: 0.0 (feasible)
  SSE: 6,200
  
Assessment:
  ✓ Constraint satisfied
  ✓ Close to target center
  ✓ Ready for PMS integration
  
Next steps:
  - Export to Excel
  - Validate sample segments
  - Import into agency systems
```

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

---

## 13. Additional Resources for Pavement Engineers

### Constrained Optimization Theory

- **Deb's Constraint-Handling Method**: K. Deb, "An efficient constraint handling method for genetic algorithms", Computer Methods in Applied Mechanics and Engineering, 2000
  - Original paper describing the feasibility rules
- **Constraint Handling in GAs**: <https://en.wikipedia.org/wiki/Constraint_satisfaction>
  - Overview of different constraint handling approaches

### Comparing Constraint Methods

- **Penalty Methods vs. Feasibility Rules**: <https://link.springer.com/chapter/10.1007/978-3-540-70928-2_42>
  - Academic comparison of approaches
- **When to Use Hard vs. Soft Constraints**: Engineering optimization textbooks

### Pavement Management Standards

See Constrained GA documentation (Section 15) for:

- HPMS reporting requirements
- AASHTO PMS standards
- State DOT best practices
- Federal pavement data guidelines

### Method Selection Guidance

**Decision flowchart for constrained segmentation:**

```text
Need length constraint?
  NO → Use Single-Objective GA
  YES → Continue
  
Is constraint absolutely mandatory?
  NO (guideline) → Use Penalty-Based Constrained GA
  YES (regulatory) → Continue
  
Want control over quality tradeoff?
  YES → Try Penalty-Based first (tune weight)
  NO (compliance only) → Use Deb Feasibility
  
Can penalty method satisfy constraint?
  YES → Use Penalty-Based (better quality)
  NO → Use Deb Feasibility (stricter enforcement)
```

### General Resources

See also:

- **Single-Objective GA** (Section 15) for genetic algorithm fundamentals
- **Constrained GA** (Section 15) for penalty method details and PMS integration
- **Multi-Objective** (Section 15) for exploring tradeoffs without constraints

### Related Research

For academic users:

- Search terms: "Deb constraint handling", "feasibility rules genetic algorithms", "hard constraints optimization"
- Key papers: Deb & Agrawal (2000), Coello Coello constraint-handling survey
- Application: Constrained engineering design, structural optimization
