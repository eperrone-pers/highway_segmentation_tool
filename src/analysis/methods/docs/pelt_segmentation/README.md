# PELT Segmentation (ruptures)

---

## Executive Summary for Pavement Engineers

PELT (Pruned Exact Linear Time) is a **deterministic change-point detection** method from signal processing and time series analysis. While not specifically designed for pavement engineering, it's highly effective for spatial pavement data and offers unique advantages.

**Key characteristics:**

- ✅ **Deterministic**: Same data always produces same result (reproducible)
- ✅ **Fast**: Typically < 1 second execution time
- ✅ **Excellent smoothing**: Built-in rolling mean/median for noisy data
- ✅ **Flexible sensitivity**: Penalty parameter controls breakpoint detection
- ✅ **Open-source**: BSD-licensed `ruptures` Python package

**When to use PELT:**

- ✅ Noisy data requiring smoothing (FWD deflections, high-frequency profiling)
- ✅ Fast exploratory analysis and parameter tuning
- ✅ Validating other segmentation methods (compare with AASHTO CDA or GA)
- ✅ General change-point detection without AASHTO requirement
- ✅ Want tunable sensitivity (penalty parameter) vs. statistical threshold

**When to use AASHTO CDA instead:**

- ✅ Need statistical justification with p-values and confidence levels
- ✅ Regulatory/agency requirements for AASHTO-aligned methodology
- ✅ Research publications requiring established pavement engineering methods
- ✅ Want intuitive statistical interpretation (α = 0.05 = 95% confidence)

**When to use GA methods instead:**

- ✅ Need to optimize specific objectives (minimize within-segment variation)
- ✅ Have hard constraints on segment lengths (e.g., PMS requires 1-mile average)
- ✅ Want to explore multiple objectives (Pareto front analysis)
- ✅ Need flexible operational optimization

### Key Difference: PELT vs. AASHTO CDA

| Aspect | PELT | AASHTO CDA |
| --- | --- | --- |
| Origin | Signal processing / computer science | AASHTO pavement standards |
| Control parameter | Penalty (cost tradeoff) | Alpha (significance level) |
| Intuition | "How much does a breakpoint cost?" | "How confident must we be?" |
| Smoothing | Excellent (built-in rolling window) | Limited (pre-process data separately) |
| Statistical justification | Algorithmic optimization | Hypothesis testing with p-values |
| Pavement field adoption | Growing (newer application) | Established (AASHTO-aligned) |
| Best for | Noisy data, quick exploration | Research, regulatory compliance |
| Citation | Killick et al. (2012) JASA | Katicha & Flintsch (2025) TRR |

**Typical pavement application:**

State DOT collected high-frequency IRI data (every 0.01 mile) with significant noise and occasional sensor spikes. Need quick segmentation without manual data cleaning. Use PELT with penalty=15, median smoothing window=0.5 miles to detect major condition changes while filtering noise. Compare results with AASHTO CDA for validation.

**Recommended workflow for pavement engineers:**

```text
Primary method: AASHTO CDA (statistical baseline)
Secondary method: PELT (validation and noisy data handling)
Tertiary method: GA (operational optimization if constraints needed)

Run both PELT and CDA, compare breakpoint locations
High agreement → robust segmentation
Disagreement → investigate data quality or parameter tuning
```

**Next steps after reading:** See Section 3 for parameter guidance and Section 6 for method selection decision framework.

---

## 1. Summary

This method performs **deterministic change-point segmentation** using **PELT** (Pruned Exact Linear Time) as implemented in the Python package **`ruptures`**.

Within each route, the algorithm partitions the measurement series into segments whose values are “approximately homogeneous” under a chosen cost model (typically a **piecewise-constant mean** model).

In this application, the method is integrated into the extensible analysis framework as:

- **Method key**: `pelt_segmentation`
- **Return type**: `single_objective` (a single best segmentation is returned)
- **Output**: breakpoint milepoints (`chromosome`) compatible with the app’s visualization and JSON schema.

---

## 2. Plain-language overview

Think of PELT as an automated way to answer:

> “Where does the pavement behavior change enough that we should start a new segment?”

You give it a route’s measurements (e.g., structural strength vs milepoint) and it returns a list of **breakpoints**. Between breakpoints, the signal is treated as “stable enough” under the chosen model.

In practice:

- If the data is noisy, PELT can over-segment (many short segments).
- If the penalty is too high, it can under-segment (few long segments).

This implementation also respects real-world constraints:

- **Gaps** (missing data regions) are treated as hard boundaries.
- Optional **minimum** and **maximum** segment lengths can be enforced.

### A tiny example

Suppose you have milepoints 0–10 and the measurements are mostly flat until mile 4, then jump up and stay flat until mile 8, then change again.

PELT will typically return breakpoints near `[0, ~4, ~8, 10]` (plus any mandatory gap boundaries).

---

## 2.5 Pavement Engineering Context

### Why PELT for Pavement Data?

PELT was originally developed for time series and signal processing, but it works exceptionally well for spatial pavement data because:

#### Spatial Autocorrelation

Condition measurements at nearby locations are similar (like time series at nearby time points). PELT's algorithms naturally handle this structure.

#### Noise Handling

PELT's built-in smoothing (rolling mean/median) is ideal for:

- **High-frequency IRI**: Laser profilers at 0.01-mile intervals with sensor noise
- **FWD deflection basins**: High variability from testing conditions
- **Automated surveys**: Rapid data collection with occasional anomalies
- **Continuous monitoring**: Real-time pavement sensors with spikes

#### Fast Exploration

Pavement engineers often need quick "first look" segmentation before detailed analysis. PELT provides:

- Sub-second execution for typical datasets
- Easy parameter sweeps (try multiple penalties quickly)
- Visual validation before committing to final analysis

### PELT vs. AASHTO CDA: Philosophical Difference

Both are deterministic change-point methods, but approach the problem differently:

**AASHTO CDA (Statistical Hypothesis Testing):**

```text
Question: "Is this change statistically significant?"

Approach:
  Test each potential breakpoint for significance
  Require p-value < α (e.g., 0.05)
  Accept breakpoint if 95% confident change is real
  
Advantage:
  Clear statistical interpretation
  "We are 95% confident this is a real condition change"
  
Challenge:
  Less direct control over segment count
  Alpha parameter doesn't directly tune sensitivity
```

**PELT (Penalized Optimization):**

```text
Question: "What's the best tradeoff between fit and complexity?"

Approach:
  Minimize: (within-segment cost) + (penalty × number of breakpoints)
  Penalty controls "cost" of adding a breakpoint
  Higher penalty → fewer breakpoints → simpler segmentation
  
Advantage:
  Direct control over complexity via penalty
  Easy to sweep parameters and compare
  
Challenge:
  Less direct statistical interpretation
  Penalty value is data-dependent (no universal "right" value)
```

**Practical implication:**

```text
AASHTO CDA:
  "These breakpoints are statistically justified at 95% confidence"
  Good for: regulatory compliance, research, documentation
  
PELT:
  "These breakpoints optimize the fit/complexity tradeoff at penalty=20"
  Good for: exploration, noisy data, quick analysis, comparison
```

### Real-World Pavement Examples

#### Example 1: High-Frequency IRI with Noise

```text
Data:
  - Interstate, 50 miles
  - IRI collected every 0.01 mile (5,000 points)
  - Laser profiler with occasional spikes from joints/patches
  - Range: 45-130 in/mi
  
Challenge:
  Raw data too noisy for clean segmentation
  Spikes create false breakpoints
  
PELT Solution:
  penalty: 15
  smooth_window_miles: 0.5 (50-point rolling median)
  smoothing_method: median (robust to spikes)
  model: l2
  
Result:
  - 12 segments detected
  - Noise filtered effectively
  - Breakpoints align with visible condition changes
  - Runtime: 0.8 seconds
  
Validation:
  - Ran AASHTO CDA on same data (pre-smoothed)
  - 11 breakpoints from CDA
  - High agreement (10 of 12 PELT breakpoints within 0.2 miles of CDA)
  - Conclusion: PELT segmentation is robust
```

#### Example 2: FWD Deflection Basin Data

```text
Data:
  - State highway, 15 miles
  - FWD deflections every 500 feet
  - High variability (temperature effects, testing conditions)
  - Structural index calculated from basin parameters
  
Challenge:
  Very noisy data (CV > 25%)
  Need to find major structural changes only
  
PELT Solution:
  penalty: 50 (high - filter noise)
  smooth_window_miles: 1.0 (aggressive smoothing)
  smoothing_method: median
  model: l1 (robust to outliers)
  
Result:
  - 5 segments detected (conservative)
  - Captured major foundation changes
  - Filtered out testing variability
  - Ready for structural evaluation
  
Engineering interpretation:
  - Segment 1: Strong foundation (high deflection index)
  - Segment 2: Weak zone (low index) → priority for rehab
  - Segment 3-5: Moderate strength variations
```

#### Example 3: Quick Exploratory Analysis

```text
Scenario:
  Project manager needs quick segmentation for budget planning
  Full statistical analysis comes later
  
Workflow:
  1. Load PCI data (100-foot intervals)
  2. Run PELT with penalty sweep: [10, 20, 30, 50]
  3. Compare segment counts: 25, 15, 12, 8
  4. Select penalty=20 (15 segments = reasonable for 30-mile corridor)
  5. Export to Excel for preliminary treatment planning
  6. Later: Validate with AASHTO CDA for final report
  
Time investment:
  - 5 minutes total (including plotting)
  - Enables quick decision-making
  - Refined analysis can follow
```

### When Pavement Engineers Should Consider PELT

**Strong use cases:**

- ✅ **Noisy data requiring smoothing**: FWD, continuous profiling, automated surveys
- ✅ **Quick preliminary analysis**: Budget planning, project scoping, data quality checks
- ✅ **Method comparison studies**: Run alongside AASHTO CDA and GA methods
- ✅ **Exploratory parameter tuning**: Test multiple configurations quickly
- ✅ **Non-regulatory applications**: Internal analysis without strict compliance requirements

**Weak use cases (use AASHTO CDA instead):**

- ❌ **Regulatory reporting**: Federal/state agencies requiring AASHTO-aligned methods
- ❌ **Research publications**: Peer review favors established statistical methods
- ❌ **Audit requirements**: Statistical justification with p-values needed
- ❌ **Grant applications**: Funding tied to standard methodologies

### Integration with Agency Workflows

**Recommended agency practice:**

```text
Tier 1: Quick Analysis (PELT)
  - Initial data review and QC
  - Preliminary segment identification
  - Budget ballpark estimates
  - Runtime: minutes
  
Tier 2: Statistical Validation (AASHTO CDA)
  - Formal segmentation with statistical justification
  - Comparison with PELT results
  - Documentation for reports
  - Runtime: minutes
  
Tier 3: Operational Optimization (GA)
  - Length-constrained segmentation if needed
  - PMS integration requirements
  - Multi-objective analysis
  - Runtime: minutes to hours
  
Final Deliverable:
  Report shows all three methods agree (demonstrates robustness)
```

---

## 3. What PELT does

Given a sequence of measurements $y_1,\dots,y_n$, PELT finds a set of change points (segment boundaries) that minimizes a **penalized** objective:

$$
\min_{\tau} \sum_{k} \; C\bigl(y_{(\tau_{k-1}+1):\tau_k}\bigr) \; + \; \beta \cdot |\tau|,
$$

where:

- $C(\cdot)$ is the within-segment cost (depends on the chosen model)
- $|\tau|$ is the number of change points
- $\beta$ is a non-negative penalty (our UI parameter `penalty`)

Intuition:

- Larger penalty $\beta$ ⇒ fewer change points ⇒ longer segments
- Smaller penalty $\beta$ ⇒ more change points ⇒ shorter segments (more sensitive to noise)

The `ruptures` implementation uses pruning rules to reduce the dynamic-programming search space while still finding the optimal segmentation under the chosen cost and penalty (see Killick et al., 2012).

### What the penalty means (in plain terms)

The penalty is what stops PELT from creating a breakpoint for every wiggle.

- **Low penalty** → “I’m okay with lots of segments”
- **High penalty** → “Only create a new segment when the change is clearly worth it”

---

## 4. Gap-aware segmented processing (important)

Highway data often contains **gaps** (missing measurement regions). The app detects these gaps upstream and produces a `RouteAnalysis` with:

- `mandatory_breakpoints`: route start/end and gap boundary milepoints
- `gap_segments`: intervals representing missing regions

This method **never segments across gaps**. Instead, it:

1. Splits the route into **segmentable sections** between consecutive mandatory breakpoints.
2. Runs PELT **independently inside each segmentable section**.
3. Unions all discovered internal breakpoints with the mandatory breakpoints.

This architecture matches the deterministic CDA method integration pattern and ensures that exported breakpoints are always consistent with gap constraints.

Practical implication: if you have many gaps (or a very aggressive gap threshold), you will get many small independent sections. Each section is segmented separately.

---

## 5. Parameters

Parameters are configured in the GUI under the `pelt_segmentation` method and validated by the framework.

### 5.1 Change-point detection

- **Cost Model (`model`)**
  - `l2` (recommended): detects **mean shifts** under least-squares cost.
  - `l1`: more robust mean-shift cost (less sensitive to outliers).
  - `rbf`: kernel-based cost, can detect more general distribution shifts.

- **Penalty (`penalty`)**
  - The primary sensitivity control. Higher values produce fewer breakpoints.
  - Recommended tuning approach: start with a small grid (e.g., 50, 100, 200, 400) and pick the smallest penalty that avoids “chattering”.

- **Jump (`jump`)**
  - A performance/sensitivity tradeoff.
  - `jump = 1`: every sample index is a candidate change point (highest resolution).
  - `jump = k`: only indices `k, 2k, 3k, ...` are candidates (faster, but breakpoint locations are effectively snapped to this grid).

### 5.2 Smoothing (optional)

- **Smoothing Window (miles) (`smooth_window_miles`)**
  - `None`: smoothing off (uses raw measurements).
  - Positive value: apply a centered rolling smoother before running PELT.

- **Smoothing Method (`smoothing_method`)**
  - `mean`: rolling mean.
  - `median`: rolling median (recommended when spikes/outliers are present).

Notes:

- The method estimates sample spacing from the local section’s milepoints and converts miles → samples.
- Smoothing usually reduces noise-driven breakpoints and can make penalty tuning easier.

Example:

- If your milepoint spacing is ~0.1 miles, setting `smooth_window_miles = 1.0` gives roughly a 10-sample rolling window.

### 5.3 Segment length constraints

- **Min Segment Length (`min_length`)**
  - Enforced as PELT’s `min_size` (minimum number of samples between change points) within each segmentable section.

- **Max Segment Length (`max_length`)**
  - PELT does not natively enforce a maximum length.
  - The method therefore applies a **post-processing split**: any **non-gap** segment longer than `max_length` is split by inserting additional breakpoints.
  - Inserted breakpoints are snapped to the nearest existing milepoint value and attempt to respect `min_length`.

Important nuance:

- `min_length` is enforced during change-point detection (it prevents too-close breakpoints inside a section).
- `max_length` is enforced after the fact by splitting any overlong non-gap segments.

---

## Tuning guidance (practical)

A good tuning workflow is:

1. Set engineering constraints first:
   - `min_length`: minimum practically actionable segment size (e.g., 0.5–1.0 miles)
   - `max_length`: maximum acceptable “averaging” length (e.g., 3–10 miles)

2. If the series is noisy, enable smoothing:
   - `smooth_window_miles = 0.5–1.0` as a first pass
   - use `median` if spikes are common

3. Use `penalty` to control the number of segments:
   - Increase penalty to reduce break count.
   - If you see many short segments (“chatter”), the penalty is too low and/or smoothing is off.

4. Adjust `jump` if runtime is high:
   - Increase to 2, 5, 10 to speed up at the cost of breakpoint granularity.

Rules of thumb:

- Too many breaks ⇒ increase `penalty`, increase `min_length`, add smoothing.
- Breaks look “late/early” by a consistent grid ⇒ reduce `jump`.
- Outlier-driven breaks ⇒ use `l1` model or median smoothing.

### 6.1 Suggested starting points

If you want a reasonable “first run” configuration:

- `model = l2`
- `jump = 1` (increase later if you need speed)
- `smooth_window_miles = 0.5–1.0` with `smoothing_method = median` if the signal has spikes
- Start `penalty` with a small grid (e.g., 50, 100, 200, 400) and choose the smallest value that avoids over-segmentation

### 6.2 Troubleshooting checklist

- **Too many segments / chattering**
  - Increase `penalty`
  - Increase `min_length`
  - Enable smoothing (try `median`)

- **Too few segments / missing obvious changes**
  - Decrease `penalty`
  - Reduce smoothing window (or disable smoothing)

- **Breakpoints look “snapped” or coarse**
  - Reduce `jump` (e.g., from 10 → 5 → 1)

- **Run time is high**
  - Increase `jump`
  - Consider switching `rbf` → `l2` if you don’t need general distribution shifts

- **Method runs but produces no internal breakpoints**
  - This can happen when sections between mandatory breakpoints are very short (due to gaps) and can’t satisfy the minimum segment size in samples.
  - Try reducing `min_length`, or reconsider the gap threshold upstream.

### 6.3 Pavement-Specific Troubleshooting

#### Problem: Results don't match visual inspection

```text
Symptom:
  You see obvious condition change at MP 5.3,
  but PELT puts breakpoint at MP 5.8
  
Likely causes:
  1. Penalty too high (increase sensitivity)
     → Try lower penalty: 20 → 15 → 10
  2. Smoothing obscuring change
     → Reduce smooth_window: 1.0 → 0.5 → None
  3. Jump too coarse
     → Reduce jump: 10 → 5 → 1
  
Diagnosis:
  Plot smoothed data - does change show up?
  If not: Reduce smoothing
  If yes: Reduce penalty
```

#### Problem: Different results from AASHTO CDA

```text
Symptom:
  PELT finds 15 breakpoints, CDA finds 10
  Only 7 breakpoints agree between methods
  
Interpretation:
  This is normal - different algorithms, different criteria
  
Actions:
  1. Compare common breakpoints (the 7 that agree)
     → These are robust, both methods detect them
  2. Examine unique PELT breakpoints (8 extra)
     → Are they subtle changes? Or noise-driven?
     → Try increasing penalty to filter
  3. Examine unique CDA breakpoints (3 extra)
     → Are they statistically justified but subtle?
     → Try decreasing PELT penalty to capture
  
Decision:
  If high agreement (70%+): Both methods valid
  If low agreement (< 50%): Investigate data quality
```

#### Problem: Segmentation too coarse for operational use

```text
Symptom:
  PELT produces only 3 segments in 20-mile corridor
  Not enough detail for treatment planning
  
Solutions:
  1. Decrease penalty: 50 → 30 → 20 → 15
  2. Reduce smoothing if enabled
  3. Check if data is genuinely homogeneous
     (Maybe pavement really is uniform!)
  4. Consider GA methods if you need specific count
```

#### Problem: Penalty tuning doesn't seem to change results

```text
Symptom:
  Tried penalty = [10, 20, 50, 100]
  All give approximately same breakpoints
  
Interpretation:
  Data has very clear change-points
  Changes are strong enough that penalty doesn't matter much
  
Good news:
  Segmentation is robust!
  Clear condition boundaries in data
  
Recommendation:
  Use moderate penalty (20) for documentation
  Results are stable across reasonable parameter range
```

---

## 7. Output format

The method returns a single `AnalysisResult` containing:

- `all_solutions[0].chromosome`: sorted list of milepoint breakpoints (includes route start/end and gap boundaries)
- `mandatory_breakpoints`: mandatory boundaries (route boundaries + gap boundaries)
- `input_parameters`: saved for reproducibility in JSON

The JSON exporter will compute segment lengths and per-segment summary statistics from the breakpoint list.

### 7.1 Interpreting outputs when tuning

When you are tuning, focus on:

- How many segments are produced (too many / too few)
- Whether breakpoints align with visibly meaningful changes
- Whether any segments violate your max length preference (if `max_length` is enabled)

### 7.2 Results Interpretation: Pavement Examples

#### Example 1: Successful IRI Segmentation

```text
Input Data:
  Route: State Highway 42, MP 0-25
  Data: IRI every 0.1 mile
  Range: 55-125 in/mi
  
Configuration:
  penalty: 18
  smooth_window: 0.5 miles, median
  model: l2
  min_length: 0.5, max_length: 8.0
  
PELT Results:
  Breakpoints: [0.0, 3.2, 7.8, 12.5, 18.3, 22.1, 25.0]
  Segments: 6
  
Interpretation:
  Segment 1 (MP 0.0-3.2): IRI ~65, "Good"
  Segment 2 (MP 3.2-7.8): IRI ~95, "Fair" ↓
  Segment 3 (MP 7.8-12.5): IRI ~72, "Good" ↑ (rehab zone?)
  Segment 4 (MP 12.5-18.3): IRI ~110, "Poor" ↓
  Segment 5 (MP 18.3-22.1): IRI ~68, "Good" ↑
  Segment 6 (MP 22.1-25.0): IRI ~88, "Fair"
  
Engineering assessment:
  - 6 segments is operationally reasonable
  - Breakpoints align with visible condition changes
  - Segments 2 and 4 are priority treatment candidates
  - Segment 3 shows recent maintenance (investigate history)
  
Validation:
  - Ran AASHTO CDA (alpha=0.05): 7 breakpoints
  - 5 of 6 PELT breakpoints within 0.3 miles of CDA
  - High agreement → robust segmentation
```

#### Example 2: Noisy FWD Data

```text
Input Data:
  Route: Interstate 70, MP 100-115
  Data: FWD structural index every 500 ft
  High variability (CV = 28%)
  
Configuration:
  penalty: 40 (high - filter noise)
  smooth_window: 1.0 mile, median
  model: l1 (robust)
  min_length: 1.0, max_length: 10.0
  
PELT Results:
  Breakpoints: [100.0, 104.8, 109.2, 115.0]
  Segments: 3
  
Interpretation:
  Segment 1 (MP 100-104.8): Index ~75, Strong
  Segment 2 (MP 104.8-109.2): Index ~52, Weak ↓
  Segment 3 (MP 109.2-115.0): Index ~68, Moderate ↑
  
Engineering assessment:
  - Conservative segmentation (3 segments only)
  - Appropriate for noisy data
  - Segment 2 is clear structural weak zone
  - Priority for forensic investigation
  
Next steps:
  - GPR survey in Segment 2
  - Core samples at breakpoints
  - Verify foundation conditions
```

#### Example 3: Comparison Study

```text
Objective:
  Compare PELT, AASHTO CDA, and Single-Objective GA
  
Data:
  20-mile corridor, PCI data
  
Results:
  PELT (penalty=20): 8 breakpoints
  AASHTO CDA (alpha=0.05): 9 breakpoints  
  Single GA (pop=100, gen=200): 7 breakpoints
  
Analysis:
  Common breakpoints (all 3 methods): 6
  → These are robust, all methods agree
  
  PELT unique: 2 breakpoints
  → Subtle changes, statistical but not optimal for GA
  
  CDA unique: 3 breakpoints
  → Statistically significant, PELT missed (penalty too high?)
  
  GA unique: 1 breakpoint
  → Optimization found benefit, but not statistically obvious
  
Conclusion:
  High overall agreement (75% overlap)
  Segmentation is robust across methods
  6 common breakpoints form core segmentation
  Method-specific breakpoints represent subtle differences
  
Recommendation for agency:
  Use AASHTO CDA as baseline (statistical justification)
  Validate with PELT and GA
  Document multi-method agreement
```

---

## 8. When to Use PELT vs. Other Methods

### Decision Framework

```text
Do you need statistical justification (p-values)?
  YES → Use AASHTO CDA (not PELT)
  NO → Continue
  
Is agency compliance required for AASHTO-aligned methods?
  YES → Use AASHTO CDA (not PELT)
  NO → Continue
  
Is your data very noisy requiring smoothing?
  YES → PELT is excellent choice (built-in smoothing)
  NO → Continue
  
Do you need fast exploratory analysis?
  YES → PELT or AASHTO CDA (both < 1 second)
  NO → Continue
  
Do you have hard constraints on segment lengths?
  YES → Use Constrained GA (penalty or Deb)
  NO → Continue
  
Do you want to explore quality vs. length tradeoffs?
  YES → Use Multi-Objective NSGA-II
  NO → PELT, CDA, or Single GA all suitable
```

### PELT vs. AASHTO CDA (Detailed Comparison)

**Use PELT when:**

- ✅ Data is noisy and needs smoothing (built-in rolling window)
- ✅ Quick exploratory analysis (no statistical documentation required)
- ✅ Want tunable sensitivity via penalty parameter
- ✅ Comparing multiple methods (PELT as second opinion)
- ✅ Internal analysis without regulatory requirements
- ✅ Preliminary budget planning or scoping

**Use AASHTO CDA when:**

- ✅ Need statistical justification (p-values, confidence levels)
- ✅ Regulatory compliance or federal reporting
- ✅ Research publications (peer review)
- ✅ Agency requires AASHTO-aligned methodology
- ✅ Want intuitive parameter (alpha = significance level)
- ✅ Final segmentation for official documentation

**Run both (Recommended):**

```text
Best practice for pavement engineers:
  
  1. Run AASHTO CDA first (statistical baseline)
     → Establishes statistically justified segments
     → Documents with confidence levels
     
  2. Run PELT second (validation)
     → Confirms major breakpoints
     → Tests robustness across methods
     
  3. Compare results
     → High agreement? Excellent - robust segmentation
     → Disagreement? Investigate data quality or parameters
     
  4. Document both
     → "Segmentation validated using two independent methods"
     → Demonstrates thoroughness and rigor
```

### PELT vs. GA Methods

**Use PELT when:**

- ✅ Don't need optimization objectives (just find changes)
- ✅ No length constraints required
- ✅ Want deterministic results (reproducible)
- ✅ Speed is important (< 1 second)
- ✅ Change-point detection is the goal

**Use Single-Objective GA when:**

- ✅ Want to minimize within-segment variation (optimization)
- ✅ Need to incorporate mandatory breakpoints
- ✅ Optimization is more important than change-point detection
- ✅ Willing to accept stochastic results (varies slightly between runs)

**Use Constrained GA when:**

- ✅ Must achieve target average segment length
- ✅ PMS integration requires specific lengths
- ✅ Agency standards mandate length constraints
- ✅ PELT/CDA can't satisfy operational requirements

**Use Multi-Objective GA when:**

- ✅ Want to explore quality vs. length tradeoffs
- ✅ Decision-maker needs multiple options (Pareto front)
- ✅ Balancing competing objectives
- ✅ PELT/CDA too simple for complex requirements

### Method Selection Summary Table

| Your Primary Need | First Choice | Second Choice | Third Choice |
| --- | --- | --- | --- |
| Statistical justification | AASHTO CDA | — | — |
| Noisy data + smoothing | **PELT** | AASHTO CDA (pre-smooth) | — |
| Fast exploration | **PELT** or AASHTO CDA | Single GA | — |
| Reproducible results | **PELT** or AASHTO CDA | — | — |
| Target segment length | Constrained GA | — | — |
| Multi-objective tradeoffs | Multi-Objective GA | — | — |
| Regulatory compliance | AASHTO CDA | — | — |
| Method validation | **PELT** + AASHTO CDA | + Single GA | — |
| Research publication | AASHTO CDA | **PELT** comparison | GA comparison |
| Operational segmentation | AASHTO CDA | **PELT** | Single GA |

### Real-World Agency Scenarios

#### Scenario 1: State DOT Annual IRI Analysis

```text
Requirement:
  Segment 2,000 miles of Interstate for PMS update
  Need statistically defensible results
  Data quality varies by district
  
Recommended approach:
  Primary: AASHTO CDA (statistical, AASHTO-aligned)
  Validation: PELT (quick check, handles noisy districts)
  
Workflow:
  1. Run CDA on all routes (statistical baseline)
  2. Run PELT on subset (QC check)
  3. Flag routes where methods disagree (investigate)
  4. Document CDA as primary, PELT as validation
```

#### Scenario 2: Consultant Forensic Investigation

```text
Requirement:
  Investigate premature pavement failure
  Data includes FWD, IRI, GPR
  Need comprehensive analysis
  
Recommended approach:
  Use all methods, compare:
  - PELT: Quick look, handle FWD noise
  - AASHTO CDA: Statistical justification
  - Single GA: Optimization perspective
  
Workflow:
  1. PELT for initial exploration (fast)
  2. AASHTO CDA for statistical segments
  3. Single GA for optimal breakpoints
  4. Report shows all three agree on failure zone
  5. Multi-method validation strengthens findings
```

#### Scenario 3: Research University Study

```text
Requirement:
  Compare segmentation methods
  Publish in peer-reviewed journal
  Need rigorous methodology
  
Recommended approach:
  Test suite:
  - AASHTO CDA (statistical baseline)
  - PELT (alternative deterministic)
  - Single GA (optimization)
  - Multi-Objective GA (tradeoff exploration)
  
Contribution:
  Document when methods agree/disagree
  Provide guidance for practitioners
  Validate new AASHTO CDA approach
```

---

## 9. Implementation notes (for developers)

- Implementation class: `analysis.methods.pelt_segmentation.PeltSegmentationMethod`
- Dependency: `ruptures` (BSD 2-Clause license)
- Import behavior: `ruptures` is imported lazily inside `run_analysis()` so the app can start even if the package is missing.
- Robustness:
  - Very short gap-bounded sections are skipped (they cannot satisfy `min_size`).
  - If `ruptures` raises inside a section, the method logs a warning and continues, relying on mandatory breakpoints to preserve validity.

If you see warnings about short sections, it usually indicates that gaps are creating very small segmentable ranges relative to `min_length`.

---

## 10. References and Additional Resources

### Primary Citations

**1. Killick, R., Fearnhead, P., & Eckley, I. A. (2012).**  
   *Optimal detection of changepoints with a linear computational cost.*  
   Journal of the American Statistical Association, 107(500), 1590–1598.

- **Description**: Original PELT algorithm paper
- **Key contribution**: Pruned exact linear time algorithm for optimal change-point detection
- **Relevance**: Foundation for the `ruptures` implementation used in this tool
- **Access**: <https://doi.org/10.1080/01621459.2012.737745> (journal) or search on Google Scholar

#### ruptures Python Package

- **Documentation**: <https://centre-borelli.github.io/ruptures-docs/>
- **GitHub**: <https://github.com/deepcharles/ruptures>
- **License**: BSD 2-Clause (compatible with this project)
- **Citation**: Truong, C., Oudre, L., & Vayatis, N. (2020). Selective review of offline change point detection methods. Signal Processing, 167, 107299.

### ruptures Documentation Resources

**PELT User Guide:**

- <https://centre-borelli.github.io/ruptures-docs/user-guide/detection/pelt/>
- Explains PELT parameters and usage
- Examples and code snippets

**Cost Functions:**

- **L2 (least-squares)**: <https://centre-borelli.github.io/ruptures-docs/user-guide/costs/costl2/>
- **L1 (robust)**: <https://centre-borelli.github.io/ruptures-docs/user-guide/costs/costl1/>
- **RBF (kernel)**: <https://centre-borelli.github.io/ruptures-docs/user-guide/costs/costrbf/>

**Tutorials and Examples:**

- <https://centre-borelli.github.io/ruptures-docs/examples/>
- Practical examples for different data types
- Parameter tuning guidance

### Change-Point Detection Background

**General Introduction:**

- **Wikipedia**: <https://en.wikipedia.org/wiki/Change_detection>
  - Accessible overview of change-point detection
  - Links to key papers and methods
- **Tutorial**: "A Survey of Methods for Time Series Change Point Detection" (Aminikhanghahi & Cook, 2017)
  - Comprehensive review of change-point methods
  - Available on arXiv and journal sites

**Signal Processing for Spatial Data:**

- Change-point methods originally from time series
- Directly applicable to spatial pavement data (distance as "time")
- Smoothing and filtering techniques transfer well

### Pavement Data Analysis Resources

**Comparison with AASHTO CDA:**

- See `src/analysis/methods/docs/aashto_cda/README.md` for detailed AASHTO CDA documentation
- **Key paper**: Katicha, S., Flintsch, G. (2025), "Enhanced AASHTO Cumulative Difference Approach (CDA) for Pavement Data Segmentation" *Transportation Research Record*, Accepted
- **Recommendation**: Use both PELT and AASHTO CDA, compare results

**Pavement Management Resources:**

- **FHWA Pavement Management**: <https://www.fhwa.dot.gov/pavement/>
  - Federal guidance on pavement data analysis
  - Standards and best practices
- **TRB Pavement Committees**: <https://www.trb.org>
  - AKM20: Pavement Management Systems
  - AKT60: Pavement Monitoring, Evaluation, and Data Storage
  - Annual meeting sessions on segmentation

**Data Collection Standards:**

- **AASHTO PP 49**: Standard Practice for Pavement Condition Data Collection
- **HPMS Field Manual**: <https://www.fhwa.dot.gov/policyinformation/hpms/fieldmanual/>
  - Federal data collection requirements
  - Quality standards

### Method Comparison Resources

**Other Segmentation Methods in This Tool:**

- **Single-Objective GA**: `src/analysis/methods/docs/single/README.md`
  - Optimization-based segmentation
  - Minimizes within-segment variation
- **Multi-Objective NSGA-II**: `src/analysis/methods/docs/multi/README.md`
  - Explores quality vs. length tradeoffs
  - Pareto front analysis
- **Constrained GA (Penalty)**: `src/analysis/methods/docs/constrained/README.md`
  - Target segment length with tunable tradeoff
- **Constrained GA (Deb)**: `src/analysis/methods/docs/constrained_deb/README.md`
  - Hard length constraints via feasibility rules
- **AASHTO CDA**: `src/analysis/methods/docs/aashto_cda/README.md`
  - Statistical change-point detection (recommended comparison)

**When to Use Which Method:**

See Section 8 of this document for detailed decision framework.

### Software and Implementation

**This Implementation:**

- **Class**: `analysis.methods.pelt_segmentation.PeltSegmentationMethod`
- **File**: `src/analysis/methods/pelt_segmentation.py`
- **Dependencies**: `ruptures` (installed via `requirements.txt`)
- **License**: MIT (this project) + BSD 2-Clause (ruptures)

**Testing:**

- **Unit tests**: `tests/` directory
- **Regression tests**: Validate against reference results
- **Example**: See `tests/README.md` for test suite documentation

### Academic Research

**Search Terms:**

- "Change-point detection pavement"
- "PELT algorithm applications"
- "Pavement condition segmentation"
- "Spatial change-point detection"
- "Highway data analysis segmentation"

**Relevant Journals:**

- *Journal of the American Statistical Association* (JASA) - original PELT paper
- *Transportation Research Record* (TRR) - pavement applications
- *Signal Processing* - change-point methods
- *Journal of Transportation Engineering* (ASCE)
- *International Journal of Pavement Engineering*

**Related Research Topics:**

- Bayesian change-point detection
- Optimal partitioning algorithms
- Pruning strategies for dynamic programming
- Pavement condition monitoring
- Network-level pavement analysis

### Training and Education

**Online Courses:**

- **Statistical Learning**: Stanford Online, Coursera
  - Change-point detection modules
  - Time series analysis
- **Signal Processing**: edX, Coursera
  - Filtering and smoothing techniques
  - Change detection methods

**Professional Development:**

- **TRB Annual Meeting**: Pavement data analysis workshops
- **FHWA NHI Courses**: Pavement management training
- **University Short Courses**: Transportation asset management

### Practical Guides and Tutorials

**Using ruptures:**

- Official tutorials: <https://centre-borelli.github.io/ruptures-docs/examples/>
- GitHub discussions: <https://github.com/deepcharles/ruptures/discussions>
- Stack Overflow: Tag "ruptures" or "change-point-detection"

**Parameter Tuning:**

- See Section 6 of this document for detailed guidance
- Experiment with penalty sweep: [10, 20, 50, 100]
- Compare with AASHTO CDA for validation

**Pavement-Specific Applications:**

- See Section 2.5 "Pavement Engineering Context" for real-world examples
- See Section 7.2 "Results Interpretation" for case studies

### Getting Help

**Technical Questions about PELT:**

- `ruptures` documentation and tutorials (comprehensive)
- GitHub issues: <https://github.com/deepcharles/ruptures/issues>
- Original paper (Killick et al., 2012)

**Implementation Questions:**

- Check `src/analysis/methods/pelt_segmentation.py` code comments
- Review `tests/README.md` for test examples
- File issues on project repository

**Application Questions:**

- Compare with AASHTO CDA (see Section 8)
- Review pavement engineering examples (Section 2.5 and 7.2)
- Consult TRB committees and pavement management experts

### Summary: PELT in the Pavement Engineering Toolkit

**PELT's Role:**

```text
Primary strength: Deterministic change-point detection with excellent
                  smoothing for noisy data
  
Best use: Fast exploration, validation, noisy data handling

Position in workflow: Secondary/validation method after AASHTO CDA
                      (or primary for non-regulatory applications)

Key citation: Killick et al. (2012) - original PELT algorithm

Implementation: ruptures package (BSD-licensed, well-maintained)
```

**Recommended Reading Path:**

1. Start with this README (complete guide)
2. Review Section 2.5 (Pavement Engineering Context)
3. Try examples in Section 7.2 (Results Interpretation)
4. Compare with AASHTO CDA (Section 8)
5. Consult Killick et al. (2012) for algorithmic details
6. Explore ruptures documentation for advanced features
