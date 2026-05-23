# Constrained Single-Objective GA (`method_key`: `constrained`)

This document describes the **constrained single-objective genetic algorithm** used for highway segmentation in this repository. It is written in the same “technical paper” style as the single-objective and multi-objective method documents.

---## Executive Summary for Pavement Engineers

This method finds the **single best segmentation** that meets a **target average segment length** while still minimizing condition variation within segments. It's designed for agencies that have standard segment length requirements for reporting, pavement management systems, or operational standardization.

**When to use this method:**

- Your agency requires standard segment lengths (e.g., 1.0-mile sections for PMS)
- DOT reporting systems mandate specific average lengths
- You want consistency across multiple corridors or districts
- Budget planning is based on typical project sizes (e.g., "standard 2-mile overlay projects")
- Asset management system requires uniform section lengths
- You need to match existing segmentation schemes while updating condition assessments

**Typical pavement application:** State DOT requires all Interstate pavement sections to average 1.0 ± 0.2 miles for consistency in their pavement management database, but still wants segments to group similar conditions together.

**Key advantages:**

- **Standardization**: Ensures consistent segment lengths across your network
- **Predictability**: Project sizes are uniform, simplifying budget and contractor planning
- **Compliance**: Meets agency or regulatory requirements for segment lengths
- **Compatibility**: Results can integrate with existing PMS that expect standard lengths
- **Balance**: Still optimizes condition uniformity within the length constraint

**Limitations:**

- **Quality compromise**: May sacrifice some condition uniformity to meet length target
- **Tuning required**: Penalty weight needs adjustment to enforce constraint properly
- **Less flexible**: Can't adapt segment lengths as freely to condition transitions
- **May fail**: If target length is unrealistic for the data, constraint may not be satisfied

**How it works:**

- Optimizes condition uniformity (like single-objective GA)
- **Plus** applies penalty when average segment length deviates from target
- Penalty weight controls how strictly the length constraint is enforced
- Higher penalty weight → stricter length enforcement, but possibly worse condition grouping

**Key parameter: Penalty Weight** determines the tradeoff:

- **Low (10-50)**: Soft constraint, may not achieve target but better condition grouping
- **Medium (100-300)**: Balanced enforcement, recommended starting point
- **High (500-1000)**: Strict constraint, will likely achieve target but may compromise quality

**Success indicator:** Results show "Constraint satisfied: YES" with achieved average within your tolerance.

**Next steps after reading:** See Section 3.3 for parameter guidance and Section 12.1 for penalty weight tuning.

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

## 2.3 Pavement Engineering Context

### Why Agencies Need Length Constraints

**Pavement Management System Requirements:**

Many state DOTs and local agencies have standardized their PMS around specific segment lengths:

- **Historical consistency**: "We've always used 1-mile sections in our database"
- **Reporting standards**: HPMS or state reporting systems expect uniform lengths
- **Software limitations**: Older PMS may assume fixed-length sections
- **Interstate comparisons**: Need consistent basis for comparing conditions across network

**Operational Standardization:**

- **Budget planning**: "Our typical resurfacing project is 2 miles"
- **Contractor bidding**: Standard project sizes improve bid competition
- **Resource allocation**: Simplifies crew scheduling and equipment planning
- **Multi-year programming**: Easier to plan with predictable project sizes

**District/Agency Uniformity:**

- Multiple districts analyzing different corridors
- Want consistent methodology across all analyses
- Simplifies training and quality control

### When to Use Constrained vs. Unconstrained Methods

**Use Unconstrained Single-Objective GA when:**

- ✅ Quality (condition uniformity) is the top priority
- ✅ Flexible segment lengths are acceptable
- ✅ No system requirements for standard lengths
- ✅ Data-driven breakpoints matter more than length consistency
- ✅ First-time analysis exploring optimal segmentation

**Use Constrained GA when:**

- ✅ Agency has standard length requirements (PMS, reporting)
- ✅ Need consistency with existing segmentation schemes
- ✅ Budget/operations based on standard project sizes
- ✅ Quality is important but length standardization is mandatory
- ✅ Updating condition data for existing section framework

**Use Multi-Objective NSGA-II when:**

- ✅ Want to see the full tradeoff curve between quality and length
- ✅ No fixed target length, but want to explore options
- ✅ Need to present alternatives to stakeholders

### Real-World Example: State DOT Standard Segments

**Scenario**: State DOT requires Interstate segments to average 1.0 ± 0.2 miles for PMS consistency.

**Without constraint (Single-Objective GA):**

```text
50-mile corridor analyzed:
  22 segments identified
  Average length: 2.27 miles (too long!)
  Total SSE: 4,200 (excellent uniformity)
  
 Problem: Doesn't match PMS requirement
 Result: Cannot import into existing database
```

**With constraint (Target = 1.0 mi, Tolerance = 0.2 mi, Weight = 200):**

```text
50-mile corridor analyzed:
  48 segments identified
  Average length: 1.04 miles ✓ (within tolerance)
  Total SSE: 6,800 (good uniformity)
  Constraint satisfied: YES
  
 Success: Meets PMS requirement
 Result: Can integrate with existing database
 Quality: Acceptable (10% more variation than unconstrained)
```

**Interpretation:**

- Constraint forced more breakpoints (48 vs. 22 segments)
- Achieved target length (1.04 vs. 1.0 miles)
- Modest quality sacrifice (SSE 6,800 vs. 4,200)
- ✓ **Acceptable tradeoff for operational compliance**

### When Constraints Are Too Restrictive

**Warning signs:**

```text
Scenario: Target = 0.5 mi on rural Interstate with few condition changes

Result:
  Constraint satisfied: NO
  Achieved average: 1.2 miles (240% over target)
  Total SSE: 8,500 (poor uniformity)
  
Diagnosis: Target too short for the data
  - Not enough natural breakpoints
  - Would require artificial breaks in homogeneous pavement
  - Algorithm can't satisfy constraint without severe quality loss
  
Recommendation: Relax target to 1.0-1.5 miles
```

**Feasibility check before running:**

- Calculate: `Total Length / Target Avg Length = Expected segment count`
- Check if this many segments makes sense given your data
- If target forces 100+ segments on 50-mile corridor → probably too aggressive

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

### 3.5 Parameter Selection for Pavement Applications

#### Setting the Target Average Length

**Based on agency requirements:**

**State DOT Interstate standards:**

- Common targets: 0.5 mi, 1.0 mi, 2.0 mi
- Check your PMS documentation or data dictionary
- Look at existing section definitions in your database

**Urban arterial standards:**

- Common targets: 0.25 mi, 0.5 mi (shorter urban blocks)
- May vary by functional class

**Research/special studies:**

- May use 0.1 mi, 0.25 mi for detailed analysis
- Balance: shorter → more detail, but harder to achieve uniformly

**Rule of thumb:** Pick a target that results in a reasonable segment count:

```text
Expected segments = Total Route Length / Target Avg Length

For 50-mile corridor:
  Target 2.0 mi → 25 segments (good)
  Target 1.0 mi → 50 segments (acceptable)
  Target 0.5 mi → 100 segments (may be too many)
```

#### Setting the Length Tolerance

**Tolerance defines acceptable deviation before penalty applies:**

**Tight tolerance (±0.1 miles for 1.0 mi target):**

- Acceptable range: 0.9-1.1 miles
- Strict standardization
- May be harder to achieve
- Use when: PMS requirements are rigid

**Moderate tolerance (±0.2 miles for 1.0 mi target):**

- Acceptable range: 0.8-1.2 miles
- Balanced approach
- **Recommended starting point**
- Use when: Some flexibility allowed

**Relaxed tolerance (±0.3 miles for 1.0 mi target):**

- Acceptable range: 0.7-1.3 miles
- Easier to satisfy
- Better condition grouping possible
- Use when: Target is a guideline, not requirement

**Typical tolerance = 20% of target:**

```text
Target 0.5 mi → Tolerance 0.1 mi (20%)
Target 1.0 mi → Tolerance 0.2 mi (20%)
Target 2.0 mi → Tolerance 0.4 mi (20%)
```

#### Tuning the Penalty Weight

**This is the critical parameter for constraint enforcement.**

**Penalty weight determines how strictly the algorithm enforces the length target:**

**Light enforcement (10-50):**

```text
Effect:
  - Treats length target as preference, not requirement
  - Prioritizes condition uniformity
  - May not achieve target
  
Use when:
  - First exploration of constrained approach
  - Want to see "best quality subject to soft length guidance"
  - Target is aspirational
```

**Moderate enforcement (100-300) - RECOMMENDED START:**

```text
Effect:
  - Balanced tradeoff between quality and length constraint
  - Usually achieves target if feasible
  - Modest quality compromise
  
Use when:
  - Standard agency application
  - Length target is important but not absolute
  - Want good balance
  
Recommended starting value: 200
```

**Strong enforcement (500-1000):**

```text
Effect:
  - Heavily prioritizes meeting length target
  - Almost always satisfies constraint if physically possible
  - May significantly compromise condition uniformity
  
Use when:
  - Regulatory requirement is strict
  - PMS integration absolutely requires standard lengths
  - Quality is secondary to standardization
```

**Very strong enforcement (>1000):**

```text
Effect:
  - Extreme enforcement
  - May create poor segmentation just to meet length
  - Can result in breakpoints that don't make sense
  
Use when:
  - Previous weight levels failed to achieve constraint
  - Last resort for critical compliance needs
  
Warning: Inspect results carefully for data quality
```

#### Penalty Weight Tuning Strategy

**Step-by-step approach:**

**1. Start with recommended settings:**

```text
target_avg_length: 1.0 miles (your requirement)
length_tolerance: 0.2 miles (20% of target)
penalty_weight: 200 (moderate)
population_size: 150
num_generations: 150
```

**2. Run analysis and check constraint satisfaction:**

```text
Look for in results:
  "Constraint satisfied: YES" or "NO"
  "Achieved average: X.XX miles"
  "Target: 1.0 miles"
  "Deviation: X.XX miles"
```

**3. Adjust based on results:**

**If constraint NOT satisfied:**

```text
Achieved: 1.5 miles, Target: 1.0, Deviation: 0.5

→ Increase penalty_weight to 400
→ Re-run analysis
→ Repeat until satisfied or hit quality concerns
```

**If constraint satisfied but quality is poor:**

```text
Constraint: YES (achieved 1.02 miles)
But: Very high SSE, segments have high std dev

→ Check if target is realistic
→ Try slightly relaxing tolerance to 0.3
→ Or reduce penalty_weight to 150
→ May need to accept that target conflicts with data
```

**If constraint easily satisfied with great quality:**

```text
Constraint: YES (achieved 0.98 miles)
SSE comparable to unconstrained run

→ Success! Target aligns well with data
→ Current settings are good
→ No adjustment needed
```

#### Algorithm Parameters

**Use same guidance as single-objective GA:**

- **Population size**: 100-150 (typical)
- **Generations**: 150-200 (may need more if constraint is tight)
- **Min/max length**: Set based on pavement application (see single-objective Section 3.3)
- **Crossover/mutation**: Use defaults

**Special consideration:** If penalty weight is high (>500), consider:

- Increasing generations to 250-300 (harder optimization problem)
- Increasing population to 200 (more exploration needed)

#### Complete Example Configuration

##### Scenario: State DOT Interstate IRI segmentation with 1-mile standard

```text
Agency Requirement:
  "Interstate pavement sections shall average 1.0 miles
   for consistency with HPMS reporting"

Recommended Configuration:
  target_avg_length: 1.0
  length_tolerance: 0.2
  penalty_weight: 200 (start here)
  
  min_length: 0.5  (practical minimum project)
  max_length: 2.0  (allow some flexibility)
  
  population_size: 150
  num_generations: 200
  
  crossover_rate: 0.8 (default)
  mutation_rate: 0.2 (default)
  elite_ratio: 0.1 (default)

Expected Outcome:
  - Achieves 1.0 ± 0.2 mile average
  - Reasonable condition uniformity
  - Compatible with PMS requirements
  
If constraint not satisfied after first run:
  → Increase penalty_weight to 400
  → Re-run and verify
```

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

$$L(B) = \mathrm{avgLengthExcludingGaps}(B)$$

This is computed by `HighwaySegmentGA._calculate_non_mandatory_avg_length(...)`.
Despite the legacy name, the current project convention is:

- compute segment lengths for all consecutive breakpoint intervals
- exclude **gap-only** segments (intervals whose boundaries exactly match a detected gap)
- average the remaining (data-bearing) segment lengths

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
- `avg_segment_length`: the gap-only-excluding average length $L(B)$ used for the constraint
- `target_avg_length`, `length_deviation`, `is_feasible`

### 12.1 Interpreting Results for Pavement Management

#### Understanding Constraint Satisfaction

The most important result field is **constraint satisfaction status:**

**"Constraint satisfied: YES":**

```text
Meaning:
  ✓ Achieved average segment length is within tolerance
  ✓ Ready to use for pavement management
  ✓ Meets agency requirements
  
Example:
  Target: 1.0 miles
  Tolerance: 0.2 miles (acceptable: 0.8-1.2)
  Achieved: 1.04 miles ✓
  Deviation: 0.04 miles (well within tolerance)
```

**"Constraint satisfied: NO":**

```text
Meaning:
  ✗ Achieved average is outside tolerance
  ✗ Need to adjust parameters
  ✗ May indicate target is unrealistic
  
Example:
  Target: 1.0 miles
  Tolerance: 0.2 miles (acceptable: 0.8-1.2)
  Achieved: 1.38 miles ✗
  Deviation: 0.38 miles (exceeds tolerance)
  
Action required: See tuning guide below
```

#### Comparing Constrained vs. Unconstrained Quality

Always useful to understand the quality tradeoff:

```text
Unconstrained GA (for comparison):
  18 segments
  Average: 2.78 miles
  Total SSE: 4,200 (excellent uniformity)
  
Constrained GA (target 1.0 mi, tolerance 0.2):
  48 segments
  Average: 1.04 miles ✓
  Total SSE: 5,400 (good uniformity)
  Constraint satisfied: YES
  
Analysis:
  Quality cost: 28% increase in SSE
  Benefit: Meets PMS standard, more segments for detail
  Decision: Acceptable tradeoff for compliance
```

**Quality metrics to check:**

- **Total SSE**: Compare to unconstrained run (expect 10-40% higher)
- **Segment std dev**: Check individual segments for uniformity
- **Breakpoint locations**: Verify they still align with features

#### When Constraint Cannot Be Satisfied

**Diagnosis steps:**

**Step 1: Check if target is realistic**

```text
Calculate expected segments:
  Total length: 50 miles
  Target average: 0.5 miles
  Expected: 100 segments
  
Question: Do you really need 100 treatment projects?
  → Probably too fine-grained
  → Consider target = 1.0 miles (50 segments)
```

**Step 2: Review mandatory breakpoints**

```text
If gap_threshold created many mandatory breaks:
  - Those breaks constrain possible avg lengths
  - May make target infeasible
  
Example:
  10 gaps creating 11 sections
  Each section constrained independently
  Target may be achievable in some sections but not others
  
Solution:
  - Increase gap_threshold to span small gaps
  - Or adjust target based on actual network geometry
```

**Step 3: Increase penalty weight progressively**

```text
Try sequence:
  200 → NO satisfaction
  400 → NO satisfaction
  600 → NO satisfaction, quality degrading
  800 → Still NO
  
Conclusion: Target is physically incompatible with data
  → Relax target or tolerance
  → Or accept that constraint cannot be met
```

**Step 4: Evaluate quality vs. compliance tradeoff**

```text
With penalty_weight = 800:
  Constraint: Still NO (achieved 1.35 vs. target 1.0)
  But: SSE increased 80% vs. unconstrained
  And: Many segments have high internal variation
  
Decision point:
  → Accept that target is unrealistic for this data
  → Either use unconstrained method
  → Or relax target to what data naturally supports
```

#### Practical Example Interpretation

State Route 50 segmentation (60 miles, IRI data):

```text
Agency Requirement: 1.0 mile average ± 0.2

Run 1: penalty_weight = 200
  Result:
    Constraint satisfied: NO
    Achieved average: 1.42 miles
    Deviation: 0.42 miles (exceeds 0.2 tolerance)
    Total SSE: 5,800
  
  Action: Increase penalty weight

Run 2: penalty_weight = 400
  Result:
    Constraint satisfied: YES ✓
    Achieved average: 1.08 miles
    Deviation: 0.08 miles (within tolerance)
    Total SSE: 6,200 (7% worse than Run 1)
    56 segments identified
  
  Validation:
    ✓ Meets agency requirement
    ✓ Quality acceptable (only modest increase in SSE)
    ✓ Breakpoints align with known features
    ✓ Segment std devs reasonable (avg 11 IRI points)
  
  Decision: ACCEPT
  Rationale:
    - Satisfies compliance requirement
    - Quality tradeoff is acceptable
    - Segment count manageable (56 projects)
    - Compatible with existing PMS
  
Implementation:
  → Export to Excel for review
  → Validate top 10 segments in field
  → Import into PMS database
  → Use for 5-year capital planning
```

#### Red Flags in Constrained Results

**Warning Sign 1: Constraint satisfied but very high SSE**

```text
Problem:
  Constraint: YES (achieved 1.02 miles)
  But: SSE 3x higher than unconstrained run
  And: Many segments show high std dev
  
Diagnosis:
  Target forces artificial breaks in homogeneous pavement
  
Solution:
  - Review if target is really necessary
  - Consider relaxing tolerance
  - Or use unconstrained method
```

**Warning Sign 2: Many segments near min_length**

```text
Problem:
  Achieved average: 1.05 miles ✓
  But: 40% of segments are 0.5-0.6 miles (at min_length)
  
Diagnosis:
  Algorithm splitting aggressively to lower average
  Quality may be compromised
  
Solution:
  - Increase min_length to 0.8 miles
  - Or increase target to 1.2 miles
  - Re-run to get more natural segmentation
```

**Warning Sign 3: Penalty weight very high but still not satisfied**

```text
Problem:
  penalty_weight: 1000
  Constraint: NO (achieved 1.45 vs. target 1.0)
  
Diagnosis:
  Target is infeasible for this data/network
  
Solution:
  - Accept that 1.0 mile target doesn't work
  - Adjust target to 1.4-1.5 miles (what data supports)
  - Or use multi-objective to see natural range
```

#### Using Results for PMS Integration

**Once constraint is satisfied:**

**1. Export segmentation:**

- Use "Export to Excel" in visualization window
- Contains all segment boundaries and statistics

**2. Validate sample segments:**

- Field-check 5-10 representative segments
- Verify condition uniformity
- Check breakpoints align with features

**3. Prepare PMS import:**

- Map segment IDs to PMS conventions
- Include:
  - Route/direction
  - Start/end mileposts
  - Length
  - Mean condition
  - Collection date
  - Analysis method ("Constrained GA, target 1.0 mi")

**4. Document methodology:**

For PMS records and audits:

```text
Segmentation Methodology:
  Method: Constrained Single-Objective Genetic Algorithm
  Software: Highway Segmentation Tool v1.95
  Data: 2026 IRI survey
  Target: 1.0 mile average (agency standard)
  Tolerance: 0.2 miles
  Constraint satisfied: YES
  Achieved average: 1.04 miles
  Number of segments: 56
  Quality metric: Total SSE = 6,200
  Date: May 15, 2026
```

**5. Multi-year tracking:**

- Keep segment definitions stable across years
- Update condition data annually
- Re-segment only when major rehab changes geometry
- Track deterioration rates by segment

---

## 13. Solution Selection

At the end of the run, the method chooses the reported “best” solution using a lexicographic rule:

1. minimize `length_deviation` (closest to target), then
2. tie-break by **maximizing** `unconstrained_fitness` (best data fit).

This is intentionally different from simply taking the max constrained fitness, and it matches the code’s stated “closest-to-target” intent.

---

## 14. Reproducibility

The method uses Python’s `random` and NumPy’s random sampling. There is no built-in seed exposed via the method interface; runs are non-deterministic unless seeds are set externally.

---

## 14. Implementation map (source of truth)

Key implementation locations:

- Runner (constraint penalty loop, selection, result assembly): `src/analysis/methods/constrained.py`
- GA engine (chromosome validation, base fitness, average length excluding gap-only segments): `src/analysis/utils/genetic_algorithm.py`
- Operators and retry wrappers: `src/analysis/utils/ga_utilities.py`
- Parameter definitions (`CONSTRAINED_SINGLE_OBJECTIVE_PARAMETERS`): `src/config.py`

---

## 15. Additional Resources for Pavement Engineers

### Constrained Optimization

- **Penalty Function Methods**: <https://en.wikipedia.org/wiki/Penalty_method>
  - Mathematical foundation for constraint handling
- **Constrained Optimization in Engineering**: <https://www.mathworks.com/help/gads/constrained-optimization.html>
  - Practical introduction with examples

### Pavement Management Standards

- **HPMS Field Manual**: <https://www.fhwa.dot.gov/policyinformation/hpms/fieldmanual/>
  - Federal requirements for pavement data reporting
- **AASHTO Pavement Management Guide**: <https://www.transportation.org/>
  - Standard practices for PMS section definitions
- **FHWA Pavement Management**: <https://www.fhwa.dot.gov/pavement/management/>
  - Guidance on data collection and segmentation

### Agency Best Practices

- **NCHRP Report on Pavement Segmentation**: <https://www.trb.org/NCHRP/Blurbs/180706.aspx>
  - Research on optimal segment length selection
- **State DOT Pavement Management Manuals**: Check your state DOT website
  - Many states publish their PMS standards and procedures

### Decision-Making Frameworks

- **Multi-Criteria Decision Analysis**: <https://en.wikipedia.org/wiki/Multiple-criteria_decision_analysis>
  - Balancing compliance vs. quality objectives
- **Engineering Optimization**: <https://link.springer.com/book/10.1007/978-0-387-76635-5>
  - Academic reference for constrained engineering problems

### General Resources

See also:

- **Single-Objective GA documentation** (Section 15) for:
  - Genetic algorithm fundamentals
  - Pavement condition indices
  - Statistical concepts
  
- **Multi-Objective documentation** (Section 15) for:
  - Understanding tradeoffs between objectives
  - Pareto optimization concepts

### Related Research

For academic users:

- Search terms: "constrained pavement segmentation", "penalty function optimization", "standardized section lengths"
- Conference proceedings: TRB Annual Meeting, especially Committee AKP30 (Pavement Management Systems)
- Application papers: Many state DOTs publish their PMS methodologies

---

## 16. Code-Review Notes (Suggestions Only)

Observations from reading the current implementation (for discussion, not applied changes):

- `elite_ratio` is accepted and recorded, but the current elitist selection implementation keeps the top $N$ chromosomes and does not explicitly use the ratio as a parameter.
- The final “best solution” is selected by closest-to-target (then best base fitness), rather than strictly taking the max constrained fitness. This is consistent with the runner’s stated intent, but it is important for interpretation.
