# AASHTO CDA Statistical Analysis (`method_key`: `aashto_cda`)

This document describes the **Enhanced AASHTO Cumulative Difference Approach (CDA)** for statistical change-point detection in pavement data segmentation.

---

## Executive Summary for Pavement Engineers

The AASHTO CDA method is a **statistical change-point detection** approach fundamentally different from the genetic algorithm (GA) methods in this tool. It provides **deterministic, statistically justified** breakpoints based on the Enhanced AASHTO Cumulative Difference Approach.

**Key characteristics:**

- ✅ **Statistical rigor**: Each breakpoint has statistical justification with significance testing
- ✅ **Deterministic**: Same data always produces same result (no randomness)
- ✅ **AASHTO-aligned**: Based on established pavement engineering standards
- ✅ **Research-grade**: Peer-reviewed methodology published in Transportation Research Record
- ✅ **Reproducible**: Critical for regulatory compliance and academic work

**When to use AASHTO CDA:**

- ✅ Need statistical justification for breakpoints (research, publications, peer review)
- ✅ Regulatory/audit requirements for reproducibility and traceability
- ✅ Validating other segmentation methods (use CDA as statistical baseline)
- ✅ Agency standard practice requires AASHTO-aligned approaches
- ✅ Want deterministic results (same every time, no random variation)
- ✅ Documenting pavement condition changes with statistical confidence

**When to use GA methods instead:**

- ✅ Need to balance multiple objectives (e.g., quality + target segment length)
- ✅ Have hard constraints on segment lengths (e.g., PMS requires 1-mile segments)
- ✅ Want to explore tradeoffs (Pareto front exploration)
- ✅ Need flexible optimization for complex requirements

**Key difference from GA methods:**

| Aspect | AASHTO CDA | GA Methods |
| --- | --- | --- |
| Approach | Statistical hypothesis testing | Evolutionary optimization |
| Reproducibility | 100% deterministic | Stochastic (varies between runs) |
| Justification | P-values, significance levels | Fitness scores |
| Speed | Very fast (< 1 second) | Slower (minutes for large datasets) |
| Constraints | Limited (min points, max segments) | Flexible (length targets, min/max) |
| Output | Single statistically justified result | Single optimized or Pareto front |
| Best for | Research, validation, standards | Operational optimization |

**Typical pavement application:**

State DOT analyzing 5 years of IRI data on Interstate corridor. Need to identify statistically significant changes in pavement condition to justify rehabilitation project phases. Use AASHTO CDA with α=0.05 to detect change-points with 95% confidence, then present results to management and federal oversight with statistical backing.

**Authoritative reference:**

> Katicha, S., Flintsch, G. (2025), "Enhanced AASHTO Cumulative Difference Approach (CDA) for Pavement Data Segmentation" *Transportation Research Record*, Accepted.

This peer-reviewed paper is the **authoritative technical reference** for this method. See Section 6 (Additional Resources) for full citation and links.

**Next steps after reading:** See Section 3 for parameter guidance and Section 5 for method selection decision framework.

---

## 0. Purpose

Deterministic statistical segmentation using the Enhanced AASHTO Cumulative Difference Approach (CDA).

## 1. References

**Primary Citation (Required):**

Katicha, S., Flintsch, G. (2025), "Enhanced AASHTO Cumulative Difference Approach (CDA) for Pavement Data Segmentation" *Transportation Research Record*, Accepted.

**Additional References:**

- Full citation details and BSD license terms: `CITATIONS.md`
- MATLAB reference implementation: `src/analysis/methods/docs/aashto_cda/aashto_cda.m`
- Python implementation: `src/analysis/methods/aashto_cda.py`

**Important:**

When using AASHTO CDA results in publications, reports, or presentations, **you must cite the Katicha & Flintsch (2025) paper**. This is both an academic courtesy and a license requirement. See `CITATIONS.md` for complete BSD license terms.

## 2. Statistical Methods in Pavement Context

### What is Change-Point Detection?

Change-point detection identifies locations where statistical properties of data change significantly. In pavement engineering:

#### Example: IRI Data

```text
Milepost:    0.0  0.5  1.0  1.5  2.0  2.5  3.0  3.5  4.0
IRI (in/mi): 65   68   63   95   98   102  97   94   99
                           ↑
                    Change-point detected!
                    (Mean shifts from ~65 to ~98)
```

AASHTO CDA uses **cumulative difference** statistical testing to identify these shifts with quantifiable confidence.

### Why Statistical Segmentation for Pavement?

**Historical Context:**

Pavement management has long relied on AASHTO standards for data analysis. The Cumulative Difference Approach aligns with:

- AASHTO Guide for Local Calibration of MEPDG
- Standard engineering practice for hypothesis testing
- Federal and state requirements for statistical justification

**Key advantages over visual/manual segmentation:**

1. **Objective**: No subjective judgment calls
2. **Reproducible**: Different engineers get same result
3. **Defensible**: Statistical p-values provide justification
4. **Consistent**: Same methodology across all corridors
5. **Auditable**: Clear statistical criteria for breakpoints

### What CDA Detects

**Primary detection target:** Statistically significant shifts in **mean condition value**

**Pavement examples:**

- **IRI shifts**: Pavement quality changes (reconstruction boundary, deterioration front)
- **PCI changes**: Different construction eras or maintenance histories
- **Rutting depth**: Structural capacity changes along corridor
- **Structural index**: Layer thickness or material property boundaries
- **Deflection data**: Foundation strength changes

**What CDA does NOT optimize:**

- Target segment lengths (use constrained GA for this)
- Multiple competing objectives (use multi-objective GA)
- Complex operational constraints

### Alpha Parameter: Statistical Confidence

**α (alpha) = significance level** for hypothesis testing

**Interpretation:**

```text
α = 0.05 means:
  "We require 95% confidence that a change-point is real"
  
Or equivalently:
  "We accept 5% risk of false positive (detecting change that isn't real)"
```

**Tradeoff:**

- **Smaller α** (e.g., 0.01): More conservative, fewer breakpoints, higher confidence
- **Larger α** (e.g., 0.10): More liberal, more breakpoints, lower confidence

**Standard practice:** α = 0.05 (95% confidence) aligns with engineering convention

### Research vs. Operational Use

**Research applications:**

- Publishing pavement condition studies
- Validating new segmentation algorithms
- Academic analysis requiring peer review
- Developing agency methodologies
- Forensic investigation of pavement performance

**Operational applications:**

- Standard agency segmentation practice
- Regulatory compliance reporting
- Multi-year condition trend analysis
- Project limit justification
- Budget allocation documentation

**Hybrid approach (Recommended):**

Many agencies use **AASHTO CDA for baseline**, then apply **GA methods for operational optimization**:

1. Run CDA to establish statistical segments
2. Use as validation for GA-based results
3. Document that operational segmentation is statistically sound

---

## 3. Parameters (UI)

See `src/config.py` for the authoritative parameter list and defaults.

### Basic Parameters

- `alpha`: significance level for change point detection (default: 0.05)
- `method`: error estimation method (1/2/3) (default: 2)
- `use_segment_length`: whether the test scales by each segment length vs total length (default: True)
- `min_segment_datapoints`: minimum points per segment (default: 3)
- `max_segments`: optional cap on segments per section between mandatory breakpoints (default: None)
- `min_section_difference`: merge adjacent segments whose means are too similar (default: 0.0, disabled)
- `enable_diagnostic_output`: verbose console diagnostics + extra diagnostic fields in results JSON (default: False)

### 3.1 Parameter Selection for Pavement Applications

#### Alpha (Significance Level)

**α = 0.10 (Liberal):**

```text
Effect:
  - More breakpoints detected
  - Catches subtle condition changes
  - Lower confidence requirement (90%)
  - Higher risk of false positives
  
Use when:
  - Exploratory analysis
  - Want to see all potential change-points
  - Data is high quality with low noise
  - Over-segmentation acceptable
  
Example:
  Dense IRI data (every 0.01 mile) on well-maintained Interstate
```

**α = 0.05 (Standard, RECOMMENDED):**

```text
Effect:
  - Balanced breakpoint detection
  - 95% confidence (standard engineering practice)
  - Aligns with AASHTO conventions
  - Good tradeoff: sensitivity vs. specificity
  
Use when:
  - General pavement segmentation
  - Research publications (standard α)
  - Agency standard practice
  - Default for most applications
  
Example:
  Annual IRI data collection on state highway network
```

**α = 0.01 (Conservative):**

```text
Effect:
  - Fewer breakpoints (only major changes)
  - 99% confidence requirement
  - Lower risk of false positives
  - May miss subtle changes
  
Use when:
  - Noisy data (e.g., deflection basins)
  - High consequences of false positives
  - Want only "obvious" breakpoints
  - Preventing over-segmentation critical
  
Example:
  Falling Weight Deflectometer (FWD) data with high variability
```

**Practical guidance:**

```text
Start with α = 0.05

If too many breakpoints:
  → Reduce α to 0.01
  
If too few breakpoints:
  → Increase α to 0.10
  → Or check if data genuinely homogeneous
```

#### Method (Error Estimation)

**Method 1: MAD (Median Absolute Deviation):**

```text
Description:
  Uses MAD with normal distribution assumption
  Robust to outliers
  
Use when:
  - Data has occasional extreme values
  - Suspect outlier contamination
  - Want robust statistical testing
  
Example:
  IRI data with occasional sensor glitches
```

**Method 2: Difference-Based (RECOMMENDED, DEFAULT):**

```text
Description:
  Standard deviation of differences between consecutive points
  Accounts for autocorrelation in pavement data
  Generally most appropriate for continuous pavement measurements
  
Use when:
  - Standard pavement condition data
  - IRI, PCI, rutting collected continuously
  - Default choice for most applications
  
Example:
  Standard highway network IRI data
```

**Method 3: Direct Standard Deviation:**

```text
Description:
  Standard deviation of measurements directly
  Simpler but may not account for autocorrelation
  
Use when:
  - Data points are independent
  - Discrete sampling (not continuous profile)
  
Example:
  PCI surveys at discrete 100-foot intervals
```

**Recommendation:** Use **Method 2** (default) unless you have specific reason to change.

#### min_segment_datapoints

**Purpose:** Minimum number of data points required per segment

**Typical values:**

```text
3-5 points: Standard minimum (default: 3)
  - Allows basic statistical testing
  - Works for most pavement data
  
5-10 points: Conservative minimum
  - Better statistical power
  - Use with dense data
  
10+ points: Very conservative
  - Only for very dense datasets
  - Prevents small segments
```

**Depends on data density:**

```text
IRI every 0.01 mile (dense):
  → Can use min = 5-10 points
  → 0.05-0.10 mile minimum segments
  
PCI every 100 feet (moderate):
  → Use min = 3-5 points  
  → 300-500 feet minimum segments
  
Manual condition survey (sparse):
  → Use min = 3 points
  → Respect data density limitations
```

#### min_section_difference

**Purpose:** Merge adjacent segments if their mean values differ by less than threshold

##### Default: 0.0 (disabled)

**When to enable:**

```text
Problem: CDA detecting many breakpoints for tiny differences
Example:
  Segment A: IRI = 65 in/mi
  Segment B: IRI = 67 in/mi
  Difference: 2 in/mi (not practically significant)
  
Solution:
  Set min_section_difference = 5
  → Segments with <5 in/mi difference get merged
  → Reduces "chattery" segmentation
```

**Typical values for common pavement indices:**

```text
IRI (in/mi):
  5-10: Ignore small differences
  15-20: Only major condition shifts
  
PCI (0-100 scale):
  5-10: Typical threshold
  15-20: Major classification changes
  
Rutting depth (mm):
  2-3: Small differences
  5+: Significant changes
  
Structural indices:
  Depends on scale - typically 5-10% of range
```

**Recommendation:**

```text
Initial run: Leave at 0 (disabled)
  → See all statistically detected breakpoints
  
If results too "chattery":
  → Enable with threshold = "practical significance"
  → What's the smallest change that matters operationally?
```

#### max_segments

**Purpose:** Optional cap on number of segments per section (between mandatory breakpoints)

##### Default: None (unlimited)

**When to use:**

```text
Scenario: Very dense data causing excessive segmentation
  
Problem:
  - CDA finds 50 breakpoints in 10-mile section
  - Too many segments for practical use
  
Solution:
  - Set max_segments = 10
  - CDA keeps 10 most significant breakpoints
  - Discards weaker change-points
```

**Typical values:**

- 10-20: Reasonable segment count for operational use
- 5-10: Conservative (major changes only)
- None: Research/validation work (want all breakpoints)

#### use_segment_length

**Purpose:** Whether statistical test scales by segment length vs. total length

##### Default: True (recommended)

**Technical detail:**

```text
True (default):
  Test statistic accounts for each segment's length
  More appropriate for most applications
  
False:
  Test statistic uses total data length
  Original formulation (not recommended)
```

**Recommendation:** Leave at **True** (default) unless replicating older analyses.

#### enable_diagnostic_output

**Purpose:** Verbose diagnostics for research and troubleshooting

##### Default: False

**When True:**

- Prints detailed algorithm steps to console
- Adds extra diagnostic fields to results JSON
- Useful for understanding algorithm decisions
- Helpful when validating implementation

**Use when:**

- Comparing with MATLAB reference implementation
- Debugging unexpected segmentation
- Research requiring full algorithm trace
- Learning how CDA works internally

#### Recommended Starting Configuration

**For typical pavement segmentation:**

```text
alpha: 0.05                    # Standard 95% confidence
method: 2                      # Difference-based (default)
use_segment_length: True       # Recommended
min_segment_datapoints: 3      # Standard minimum
max_segments: None             # No cap (see all breakpoints)
min_section_difference: 0.0    # Disabled initially
enable_diagnostic_output: False # Clean output
```

**Expected outcomes:**

- Fast execution (< 1 second for most datasets)
- Deterministic, reproducible results
- Statistically justified breakpoints
- Suitable for research and operational use

**Refinement workflow:**

```text
Step 1: Run with defaults
Step 2: Review segmentation
Step 3: Adjust if needed:
  - Too many segments? Reduce alpha or enable min_section_difference
  - Too few segments? Increase alpha
  - Noisy data? Try method 1 (MAD)
  - Want simplified? Set max_segments
Step 4: Re-run and compare
```

## 4. Outputs and Results Interpretation

### Standard Outputs

- Breakpoints (mandatory + detected internal breakpoints)
- Deterministic segmentation results
- Optional diagnostics in the results JSON when enabled

### Key Result Fields for Pavement Engineers

**Breakpoint locations:**

```text
breakpoints: [0.0, 1.25, 3.47, 5.82, 8.90, 10.5]
  → 0.0 = start
  → 1.25, 3.47, 5.82, 8.90 = detected change-points
  → 10.5 = end
  
Result: 5 segments with statistically significant differences
```

**Segment statistics:**

```text
Each segment includes:
  - start/end locations
  - segment length
  - mean condition value
  - standard deviation
  - number of data points
```

### Interpretation Example: IRI Data

**Scenario:** 10-mile Interstate segment, α = 0.05

```text
Input:
  - 1,000 IRI measurements (every 0.01 mile)
  - Range: 55-120 in/mi
  
AASHTO CDA Results:
  
  Segment 1: MP 0.0-1.25 (1.25 mi)
    Mean IRI: 62 in/mi
    Std Dev: 4.2
    Classification: "Good"
    
  Segment 2: MP 1.25-3.47 (2.22 mi)
    Mean IRI: 89 in/mi
    Std Dev: 6.1
    Classification: "Fair"
    ↑ Statistically significant increase at MP 1.25
    
  Segment 3: MP 3.47-5.82 (2.35 mi)
    Mean IRI: 68 in/mi
    Std Dev: 5.3  
    Classification: "Good"
    ↑ Statistically significant decrease at MP 3.47
    (Likely rehabilitation project boundary)
    
  Segment 4: MP 5.82-8.90 (3.08 mi)
    Mean IRI: 105 in/mi
    Std Dev: 8.7
    Classification: "Poor"
    ↑ Major deterioration front at MP 5.82
    
  Segment 5: MP 8.90-10.5 (1.60 mi)
    Mean IRI: 72 in/mi
    Std Dev: 4.9
    Classification: "Good"
    ↑ Construction/reconstruction boundary at MP 8.90
```

**Pavement engineering interpretation:**

```text
Breakpoint at MP 1.25:
  → Condition deteriorates significantly
  → Check construction records (age transition?)
  → Candidate for preventive maintenance
  
Breakpoint at MP 3.47:
  → Condition improves (drops from 89 to 68)
  → Likely recent rehabilitation
  → Verify maintenance history
  
Breakpoint at MP 5.82:
  → Major deterioration (jumps to 105)
  → Priority rehabilitation candidate
  → Structural investigation recommended
  
Breakpoint at MP 8.90:
  → Sharp improvement to 72
  → Recent reconstruction or major rehab
  → Document as project limit
```

### Statistical Confidence

**Key concept:** All detected breakpoints satisfy α = 0.05 criterion

```text
What this means:
  "We are 95% confident these are real condition changes,
   not random data fluctuations"
  
Practical implication:
  Can defend segmentation decisions to:
    - Management
    - Federal oversight (FHWA)
    - Budget committees
    - Consultants/contractors
    - Legal proceedings (if needed)
```

### Comparing with GA Results (Validation Workflow)

**Recommended practice:**

```text
Step 1: Run AASHTO CDA (statistical baseline)
  → Establishes statistically justified segments
  
Step 2: Run Single-Objective GA (optimization)
  → Optimizes for minimum within-segment variation
  
Step 3: Compare results
  → Do GA breakpoints align with CDA breakpoints?
  → If yes: GA solution is statistically sound
  → If no: Investigate why (may be valid reasons)
  
Step 4: Document
  → "GA segmentation validated against AASHTO CDA"
  → Shows due diligence and technical rigor
```

**Example comparison:**

```text
AASHTO CDA breakpoints:
  [0.0, 1.25, 3.47, 5.82, 8.90, 10.5]
  
Single-Objective GA breakpoints:
  [0.0, 1.18, 3.52, 5.79, 8.95, 10.5]
  
Analysis:
  ✓ High agreement (all within 0.1 mile)
  ✓ GA found similar condition boundaries
  ✓ Both methods identify same major changes
  
Conclusion:
  GA optimization is statistically defensible
```

### Exporting Results for Stakeholders

**For technical audiences (engineers):**

- Include statistical parameters (α, method)
- Show segment means and standard deviations
- Reference Katicha & Flintsch (2025) paper
- Document reproducibility (deterministic results)

**For non-technical audiences (management):**

- Focus on condition changes ("IRI increased from 62 to 89")
- Show segments on map with color coding
- Emphasize "statistically significant" (95% confidence)
- Link to treatment recommendations and costs

**For regulatory compliance:**

- Full parameter documentation
- Citation to peer-reviewed methodology
- Reproducible analysis (provide input data)
- Diagnostic output (if required)

---

## 5. When to Use AASHTO CDA vs. Other Methods

### Decision Framework

```text
Do you need statistical justification for breakpoints?
  YES → Use AASHTO CDA
  NO → Continue
  
Do you need 100% reproducible results?
  YES → Use AASHTO CDA or PELT
  NO → GA methods acceptable
  
Do you have hard constraints on segment length?
  YES → Use Constrained GA (penalty or Deb)
  NO → Continue
  
Do you want to explore tradeoffs?
  YES → Use Multi-Objective NSGA-II
  NO → Use Single-Objective GA or AASHTO CDA
  
Is this for research or publication?
  YES → Use AASHTO CDA (with GA for comparison)
  NO → Any method appropriate
```

### AASHTO CDA vs. Single-Objective GA

**AASHTO CDA:**

```text
Strengths:
  ✓ Statistical justification (p-values)
  ✓ Deterministic (reproducible)
  ✓ Very fast (< 1 second)
  ✓ No parameter tuning (just set alpha)
  ✓ Research-grade methodology
  
Limitations:
  ✗ No length constraints
  ✗ No optimization objectives
  ✗ Limited control over results
  
Best for:
  - Research and validation
  - Regulatory compliance
  - Statistical baseline
  - Quick exploratory analysis
```

**Single-Objective GA:**

```text
Strengths:
  ✓ Optimizes specific objective (min SSE)
  ✓ Can incorporate mandatory breakpoints
  ✓ Flexible for different goals
  
Limitations:
  ✗ Stochastic (varies between runs)
  ✗ Slower (minutes)
  ✗ No statistical justification
  ✗ Requires parameter tuning
  
Best for:
  - Operational segmentation
  - Minimizing within-segment variation
  - Flexible optimization
```

**Recommendation:**

```text
Run both:
  1. AASHTO CDA for statistical baseline
  2. Single-Objective GA for optimization
  3. Compare results for validation
  
Report both:
  "Segmentation optimized using GA,
   validated against AASHTO CDA statistical analysis"
```

### AASHTO CDA vs. PELT Segmentation

Both are **deterministic change-point detection** methods, but differ in approach:

**AASHTO CDA:**

```text
Approach:
  Cumulative difference statistical testing
  AASHTO-aligned methodology
  
Control:
  Alpha parameter (significance level)
  Clear statistical interpretation
  
Best for:
  - AASHTO compliance required
  - Statistical justification needed
  - Research publications
  
Citation:
  Katicha & Flintsch (2025)
```

**PELT:**

```text
Approach:
  Optimal partitioning with penalty
  Computer science / signal processing origin
  
Control:
  Penalty parameter (sensitivity tuning)
  Less direct statistical interpretation
  
Best for:
  - General change-point detection
  - Flexible sensitivity tuning
  - Smoothing noisy data
  
Citation:
  Killick et al. (2012)
```

**Which to choose:**

```text
Pavement engineering context:
  → AASHTO CDA (standard methodology)
  
General data analysis:
  → Either (compare both)
  
Noisy data requiring smoothing:
  → PELT (has smoothing window option)
  
Agency requires AASHTO methods:
  → AASHTO CDA (obvious choice)
```

### AASHTO CDA vs. Constrained GA Methods

**Use Constrained GA when:**

You need specific segment lengths (e.g., PMS requires 1-mile average) AND statistical justification is secondary to operational requirements.

**Use AASHTO CDA when:**

Statistical validity is primary concern and segment lengths are flexible.

**Can't combine directly:**

AASHTO CDA doesn't support target length constraints. If you need both:

```text
Option 1: Use constrained GA, validate with CDA
Option 2: Use CDA, then manually adjust boundaries
Option 3: Use CDA for technical analysis, constrained GA for operational implementation
```

### Method Selection Summary Table

| Your Primary Need | Recommended Method | Alternative |
| --- | --- | --- |
| Statistical justification | **AASHTO CDA** | PELT |
| Reproducible results | **AASHTO CDA** or PELT | Single GA |
| Target segment length | Constrained GA | — |
| Multi-objective tradeoffs | Multi-Objective GA | — |
| Research publication | **AASHTO CDA** | + GA for comparison |
| Regulatory compliance | **AASHTO CDA** | PELT |
| Fast exploration | **AASHTO CDA** | PELT |
| Minimize variation | Single-Objective GA | AASHTO CDA |
| Complex constraints | Constrained GA | — |

---

## 6. Additional Resources for Pavement Engineers

### Primary Citation (REQUIRED)

**Katicha, S., Flintsch, G. (2025)**  
*"Enhanced AASHTO Cumulative Difference Approach (CDA) for Pavement Data Segmentation"*  
*Transportation Research Record*, Accepted.

**This is the authoritative reference** for the AASHTO CDA method. The paper provides:

- Complete mathematical derivation
- Statistical validation
- Comparison with other methods
- Pavement engineering case studies
- Performance benchmarks

**Access:**

- Check Transportation Research Board (TRB) website: <https://www.trb.org>
- Search TRR journal archives: <https://journals.sagepub.com/home/trr>
- Contact authors for preprints (standard academic practice)

**When to cite:**

- ✅ Any publication using AASHTO CDA results
- ✅ Reports to agencies or federal oversight
- ✅ Conference presentations
- ✅ Technical documentation
- ✅ Software incorporating this method (BSD license requirement)

### AASHTO Standards and Guides

**AASHTO Mechanistic-Empirical Pavement Design Guide (MEPDG):**

- Includes guidance on data segmentation
- Statistical analysis of pavement data
- Available: <https://me-design.com> or through AASHTO bookstore

**AASHTO Guide for Local Calibration:**

- Chapter on data analysis and segmentation
- Statistical methods for pavement data

**AASHTO PP 49:** Standard Practice for Pavement Condition Data Collection

- Data quality requirements
- Sampling and segmentation considerations

### Statistical Background

**Change-Point Detection:**

- **Wikipedia overview**: <https://en.wikipedia.org/wiki/Change_detection>
  - Accessible introduction to concepts
- **Academic surveys**: Search "change-point detection survey" on Google Scholar
  - Comprehensive reviews of methods

**Cumulative Sum (CUSUM) Methods:**

- Foundation for cumulative difference approach
- Quality control and statistical process control
- <https://en.wikipedia.org/wiki/CUSUM>

**Hypothesis Testing:**

- Understanding alpha, p-values, significance
- Any introductory statistics textbook
- Khan Academy: <https://www.khanacademy.org/math/statistics-probability>

### Pavement Management Resources

**Federal Highway Administration (FHWA):**

- <https://www.fhwa.dot.gov/pavement/>
- Pavement management guidance
- Data collection and analysis standards

**Transportation Research Board (TRB):**

- <https://www.trb.org>
- Pavement committees (AKM20, AKT60)
- Conference proceedings and research

**National Cooperative Highway Research Program (NCHRP):**

- <https://www.trb.org/NCHRP/NCHRP.aspx>
- Research reports on pavement segmentation
- Best practices for agencies

### Software and Implementation

**This Implementation:**

- Python translation: `src/analysis/methods/aashto_cda.py`
- MATLAB reference: `src/analysis/methods/docs/aashto_cda/aashto_cda.m`
- License and attribution: `CITATIONS.md` (BSD 2-Clause)

**Original MATLAB Implementation:**

- Available from research authors
- Validated against this Python translation
- Contact: Samer Katicha (see paper)

**Comparison Tools:**

- Use both implementations for validation
- Results should match within numerical precision
- See `tests/` for validation test cases

### Related Research

**Academic search terms:**

- "Pavement data segmentation"
- "Change-point detection pavement"
- "AASHTO cumulative difference"
- "Statistical segmentation IRI"
- "Highway condition segmentation"

**Key journals:**

- *Transportation Research Record* (TRR)
- *Journal of Transportation Engineering* (ASCE)
- *Road Materials and Pavement Design*
- *International Journal of Pavement Engineering*

**Related methods in literature:**

- Bayesian change-point detection
- Hidden Markov Models for pavement
- Wavelet-based segmentation
- Machine learning approaches

### Comparison with Other Segmentation Methods

See also documentation for:

- **Single-Objective GA** (`src/analysis/methods/docs/single/README.md`)
  - For optimization-based approach
- **Multi-Objective NSGA-II** (`src/analysis/methods/docs/multi/README.md`)
  - For exploring quality vs. length tradeoffs
- **PELT Segmentation** (`src/analysis/methods/docs/pelt_segmentation/README.md`)
  - For alternative deterministic change-point detection

### Training and Education

**TRB Annual Meeting:**

- Sessions on pavement data analysis
- Workshops on statistical methods
- Networking with researchers and practitioners

**FHWA National Highway Institute (NHI):**

- Pavement management training courses
- <https://www.nhi.fhwa.dot.gov>

**University Courses:**

- Pavement management systems
- Statistical analysis in civil engineering
- Transportation asset management

### Getting Help

**Technical questions about the method:**

- See Katicha & Flintsch (2025) paper (primary reference)
- Contact research authors (academic courtesy)
- TRB pavement committees

**Implementation questions:**

- Check `tests/README.md` for test examples
- Review `src/analysis/methods/aashto_cda.py` code comments
- Compare Python vs. MATLAB implementations

**Application questions:**

- State DOT pavement management units
- Consulting firms specializing in PMS
- TRB knowledge networks and committees
