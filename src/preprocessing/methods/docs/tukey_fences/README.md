# Tukey Fences Outlier Detection (`method_key`: `tukey_fences`)

This document describes the **Tukey Fences outlier detection preprocessing method** implementation for highway segmentation data preprocessing. It is written in a "technical paper" style so it can be reused as part of formal method descriptions.

---

## Executive Summary for Pavement Engineers

This preprocessing method identifies and handles **outliers** in pavement condition data (IRI, PCI, rutting, etc.) using the Interquartile Range (IQR) statistical method, also known as Tukey's Fences. Outliers are values that fall significantly outside the normal range of measurements and typically result from equipment errors, sensor spikes, or GPS positioning issues.

**When to use this method:**

- Data collected from automated equipment prone to sensor errors (profilers, FWD, etc.)
- Visual inspection shows obvious spikes or anomalies in condition plots
- Known data quality issues from GPS drift or calibration problems
- Agency policy requires outlier removal before analysis
- You want to improve segmentation reliability by cleaning noisy data

**Typical pavement application:** Remove IRI sensor spikes (values > 400 in/mi) from profiler data before segmentation to prevent false breakpoints at equipment malfunction locations.

**Key advantages:**

- **Well-established method**: IQR-based detection is standard in statistical analysis
- **Segment-aware**: Computes outlier thresholds separately for each structural segment (e.g., asphalt vs. concrete)
- **Flexible handling**: Choose to remove, cap, or interpolate outliers
- **Complete traceability**: Logs every modification with x-location, old value, new value, and reason
- **Respects boundaries**: Never modifies data across attribute break boundaries

**Three handling options:**

1. **Remove**: Delete outlier data points entirely (reduces data volume)
2. **Cap**: Replace outliers with the nearest fence value (preserves data density)
3. **Interpolate**: Replace outliers with values interpolated from neighbors (smoothest result)

**Limitations:**

- Requires at least 4 data points per segment for reliable quartile calculation
- Cannot interpolate at segment boundaries (no neighbors available)
- May be too aggressive (k=1.5) or too conservative (k=3.0) for some data distributions
- Assumes outliers are errors, not real condition anomalies

**Next steps after reading:** See Section 4 for parameter selection guidance by pavement data type.

---

## 1. Method Overview and Problem Formulation

### 1.1 The Outlier Problem in Pavement Data

Pavement condition measurement systems produce data that can contain:

- **Sensor spikes**: Equipment malfunctions causing extreme values (e.g., IRI > 500 in/mi)
- **GPS positioning errors**: Incorrect x-coordinates leading to apparent rapid changes
- **Calibration drift**: Systematic bias in measurements over time
- **Environmental interference**: Rain, construction zones, temporary conditions

These outliers can:

- Create false segment boundaries (algorithm interprets spikes as transitions)
- Inflate within-segment variance (segments appear less homogeneous than they are)
- Mislead treatment selection (outliers suggest worse condition than reality)
- Reduce statistical power (outliers dominate variance calculations)

**Goal**: Identify and handle outliers **before** segmentation algorithms run, ensuring clean data for analysis.

### 1.2 The IQR (Interquartile Range) Method

Tukey Fences use the IQR to define "normal" data range:

1. **Calculate quartiles**:
   - Q1 (25th percentile): 25% of data below this value
   - Q3 (75th percentile): 75% of data below this value
   - IQR = Q3 - Q1 (spread of middle 50% of data)

2. **Define fences** (outlier boundaries):
   - Lower fence = Q1 - k × IQR
   - Upper fence = Q3 + k × IQR
   - Common k values: 1.5 (mild outliers) or 3.0 (extreme outliers only)

3. **Identify outliers**: Any value below lower fence or above upper fence

4. **Handle outliers**: Remove, cap, or interpolate based on user choice

**Why IQR is robust**: Uses middle 50% of data (Q1-Q3), so extreme values don't affect the threshold calculation itself. This makes it more resistant to outliers than methods using mean/standard deviation.

---

## 2. Inputs, Data Model, and Assumptions

### 2.1 Input Data

The method operates on a `RouteAnalysis` object containing:

- **route_data**: DataFrame with x (distance) and y (condition) measurements
- **x_column**: Distance/milepoint column name (e.g., "Milepoint_Mile")
- **y_column**: Condition measurement column name (e.g., "IRI", "PCI", "Rutting")
- **mandatory_breakpoints**: Set of x-coordinates defining segment boundaries
  - Includes: route start/end, gap boundaries, and **attribute break boundaries**
  - **Critical**: Ensures outlier thresholds computed separately per structural section

### 2.2 Parameters

**k_factor** (outlier sensitivity multiplier):

- **Default**: 1.5 (standard outlier detection, moderately aggressive)
- **Range**: Typically 1.0 to 3.0
- **Effect**: Lower k = more points flagged as outliers, higher k = only extreme outliers
- **Common values**:
  - k=1.5: Tukey's original "outlier" definition
  - k=3.0: Tukey's "far outlier" definition (very conservative)
  - k=1.0: Aggressive outlier removal (use with caution)

**action** (outlier handling strategy):

- **Options**: "remove", "cap", "interpolate"
- **remove**: Delete outlier points entirely
  - **Use when**: Data density is high, removing points won't create gaps
  - **Effect**: Reduces total data points, can create small gaps
  - **Best for**: Extreme outliers that are clearly errors
  
- **cap**: Replace outlier values with nearest fence boundary
  - **Use when**: Want to preserve data density (same number of points)
  - **Effect**: Maintains x-coordinates, constrains y-values to fence range
  - **Best for**: Pavement indices with valid ranges (PCI: 0-100, can't exceed)
  
- **interpolate**: Replace outlier y-values with linear interpolation from neighbors
  - **Use when**: Want smooth data, neighbors exist on both sides
  - **Effect**: Most conservative change, maintains data density and smoothness
  - **Best for**: Continuous data like IRI, deflection where smoothness matters

### 2.3 Segment-Aware Processing

**Critical feature**: The method processes each segment between mandatory breakpoints **independently**.

**Why this matters**:

```text
Example: Route with asphalt (MP 0-10) and concrete (MP 10-20) sections

Asphalt section: IRI typically 80-120 in/mi
Concrete section: IRI typically 60-90 in/mi

WITHOUT segment-aware processing (WRONG):
- Global Q1 = 70, Q3 = 110, IQR = 40
- Fences: [10, 170] (using k=1.5)
- Problem: Normal concrete values (60-70) near lower bound
- Result: May incorrectly flag good concrete as outliers

WITH segment-aware processing (CORRECT):
- Asphalt segment: Q1=85, Q3=115, IQR=30, Fences=[40, 160]
- Concrete segment: Q1=65, Q3=85, IQR=20, Fences=[35, 115]
- Result: Appropriate thresholds for each pavement type
```

**Implementation**: Mandatory breakpoints from:

- Gap threshold (Step 2 in pipeline)
- **Early Attribute Break Columns** (Step 3 in pipeline) ← This is key!
- Route start/end boundaries

**Takeaway**: Use **Early Attribute Break Columns** (Step 3) to ensure preprocessing operates within structurally homogeneous segments.

---

## 3. Algorithm Details

### 3.1 Pseudocode

```python
def tukey_fences_preprocess(route_data, x_col, y_col, mandatory_breakpoints, k_factor, action):
    """Apply Tukey Fences outlier detection segment-by-segment."""
    
    # Initialize modification tracking
    modifications = []
    processed_data = route_data.copy()
    
    # Sort mandatory breakpoints to define segments
    segments = list of consecutive breakpoint pairs
    
    for each segment [start, end] in segments:
        # Get data points in this segment
        segment_points = points where start <= x <= end
        
        if len(segment_points) < 4:
            skip segment  # Need ≥4 points for reliable quartiles
            continue
        
        # Calculate IQR bounds FOR THIS SEGMENT ONLY
        Q1, Q3 = percentiles(segment_points.y, [25, 75])
        IQR = Q3 - Q1
        
        if IQR == 0:
            skip segment  # All values identical
            continue
        
        lower_fence = Q1 - k_factor * IQR
        upper_fence = Q3 + k_factor * IQR
        
        # Identify outliers in this segment
        outliers = points where y < lower_fence OR y > upper_fence
        
        for each outlier in outliers:
            if action == "remove":
                delete point from processed_data
                log modification: (x, old_y, None, "removed outlier")
            
            elif action == "cap":
                new_y = lower_fence if y < lower_fence else upper_fence
                replace y with new_y
                log modification: (x, old_y, new_y, "capped to fence")
            
            elif action == "interpolate":
                if not at segment boundary:
                    new_y = (y_prev + y_next) / 2
                    replace y with new_y
                    log modification: (x, old_y, new_y, "interpolated")
    
    return processed_data, modifications
```

### 3.2 Minimum Data Requirements

- **Minimum points per segment**: 4 (required for quartile calculation)
- **Segments with < 4 points**: Skipped, no preprocessing applied
- **Segments with IQR = 0**: Skipped (all values identical, no outliers possible)

### 3.3 Interpolation Boundary Handling

**Problem**: Can't interpolate outliers at segment start or end (no neighbors on both sides)

**Solution**: Leave boundary outliers unchanged when using interpolate action

**Example**:

```text
Segment: MP 10.0-15.0 with outlier at MP 10.0
- Previous point would be in different segment (MP < 10.0)
- Interpolating across segment boundary would mix different structures
- Result: Outlier at MP 10.0 remains unchanged
```

**Best practice**: Use "remove" or "cap" if many boundary outliers expected

---

## 4. Parameter Selection Guidance for Pavement Applications

### 4.1 By Pavement Data Type

**IRI (International Roughness Index):**

**Recommended configuration**:

- k_factor: 1.5 (standard detection)
- action: interpolate
- Early breaks: ["PAVEMENT_TYPE"] if mixing asphalt/concrete

**Rationale**:

- IRI is continuous measurement, interpolation preserves smooth profile
- Common outliers: Sensor spikes > 300 in/mi (profiler malfunction)
- Interpolation doesn't create gaps in continuous data
- k=1.5 catches most sensor errors without being over-aggressive

**Example outcome**:

```text
Before: 85, 88, 450 (spike), 92, 87  
After:  85, 88, 90 (interpolated from 88 and 92), 92, 87
```

---

**PCI (Pavement Condition Index):**

**Recommended configuration**:

- k_factor: 1.5
- action: cap
- Early breaks: ["PAVEMENT_TYPE", "FUNCTIONAL_CLASS"]

**Rationale**:

- PCI has valid range [0, 100], values outside this are errors
- Capping preserves data density for manual survey data
- Different pavement types/functional classes have different typical PCI ranges
- k=1.5 appropriate for manual survey variability

**Example outcome**:

```text
Before: 75, 72, -5 (error), 130 (error), 70
After:  75, 72, 0 (capped), 100 (capped), 70
```

---

**Rutting Depth:**

**Recommended configuration**:

- k_factor: 2.0 (moderate)
- action: remove
- Early breaks: ["PAVEMENT_TYPE", "NUM_LANES"]

**Rationale**:

- Rutting is structural distress, extreme values may be real (localized failures)
- k=2.0 more conservative, only removes clear equipment errors
- Removing points acceptable for rutting (less dense than profiler data)
- Lane configuration affects rutting patterns

---

**FWD Deflection Data:**

**Recommended configuration**:

- k_factor: 3.0 (very conservative)
- action: remove
- Early breaks: ["BASE_TYPE", "PAVEMENT_TYPE"]

**Rationale**:

- Deflection data is sparse (500-1000 ft spacing)
- High k=3.0 ensures only extreme outliers removed
- Structural data - don't want to remove real structural anomalies
- Base type strongly affects deflection, must separate

---

### 4.2 By Data Quality Situation

**High-quality, well-maintained equipment:**

- k_factor: 3.0 (conservative)
- action: cap or interpolate
- Reasoning: Few outliers expected, preserve most data

**Suspect data quality, known equipment issues:**

- k_factor: 1.5 (standard)
- action: interpolate or remove
- Reasoning: More aggressive removal justified

**Legacy/historical data with unknown collection methods:**

- k_factor: 2.0 (moderate)
- action: cap
- Reasoning: Balanced approach, preserve density for statistical analysis

**Research data requiring full traceability:**

- Don't use preprocessing (leave Steps 1, 4, 6 as "None")
- Alternative: Use k=3.0, action=remove, document all modifications
- Reasoning: Research may need raw data justification

---

## 5. Pavement Engineering Context and Examples

### 5.1 Real-World Scenario: Interstate IRI Profiler Data

**Situation**: 50-mile Interstate corridor with annual IRI surveys using van-mounted profiler

**Known issues**:

- Occasional GPS drop-outs cause position errors
- Sensor occasionally spikes when hitting bridge expansion joints
- Data mixing asphalt sections (MP 0-30) and concrete sections (MP 30-50)

**Configuration**:

```text
Step 2: Gap Threshold = 0.1 miles
Step 3: Early Attribute Break Columns = ["PAVEMENT_TYPE"]
Step 4: Primary Preprocessing = Tukey Fences
  - k_factor = 1.5
  - action = interpolate
Step 5: Late Attribute Break Columns = ["COUNTY"]
```

**Results**:

```text
Preprocessing Summary:
- Segments processed: 2 (asphalt section, concrete section)
- Outliers detected: 47
- Points modified: 47 (interpolated)
- Points removed: 0

Asphalt section (MP 0-30):
- IRI range before: 65-385 in/mi
- IRI range after: 65-145 in/mi
- Q1=82, Q3=98, IQR=16
- Fences: [58, 122] with k=1.5
- Outliers: 32 points > 122 (sensor spikes)
- Example: MP 14.3 changed from 385 → 94 (interpolated)

Concrete section (MP 30-50):
- IRI range before: 55-280 in/mi
- IRI range after: 55-92 in/mi
- Q1=68, Q3=82, IQR=14
- Fences: [47, 103] with k=1.5
- Outliers: 15 points > 103 (sensor spikes)
- Example: MP 42.1 changed from 280 → 75 (interpolated)
```

**Impact on segmentation**:

- Without preprocessing: 8 false breakpoints at sensor spike locations
- With preprocessing: Clean segmentation respecting true pavement transitions
- Treatment planning: More confident in segment homogeneity for project scoping

---

### 5.2 When NOT to Use Preprocessing

**Scenario 1: Bridge approach transitions**

**Problem**: Rapid IRI increase from 70 → 150 in/mi over 0.1 mile at bridge approach

**Risk**: Preprocessing might flag approach section as outliers if using aggressive k=1.0

**Solution**:

- Use Early Attribute Breaks for "MAJOR_STRUCTURE" (creates separate segment)
- Or use conservative k=3.0
- Or skip preprocessing for this route

**Lesson**: Real condition changes are not outliers!

---

**Scenario 2: Construction zone data**

**Problem**: Construction activity creates temporary high roughness values

**Risk**: Preprocessing removes real (but temporary) bad conditions

**Solution**:

- Skip preprocessing if analyzing construction zone performance
- Document that data includes temporary conditions
- Or: Use Late Attribute Breaks for "CONSTRUCTION_ZONE" to analyze separately

---

### 5.3 Verification and Quality Control

**After preprocessing, always check**:

1. **Modification count**:
   - Typical: < 5% of data points modified
   - Warning: > 10% modified suggests over-aggressive k or data quality issues
  
2. **Modified locations**:
   - Do they align with known problem areas (equipment calibration changes, etc.)?
   - Are they randomly distributed or clustered?
  
3. **Value changes**:
   - Are old values extreme (e.g., IRI > 300)?
   - Are new values reasonable for that location?
  
4. **Segment statistics**:
   - Did variance decrease significantly within segments?
   - Are segments now more homogeneous?

**Example verification output from JSON results**:

```json
{
  "preprocessing_summary": {
    "preprocessing_applied": true,
    "phases": [
      {
        "phase_name": "primary",
        "method_key": "tukey_fences",
        "method_name": "Tukey Fences Outlier Detection",
        "parameters": {
          "k_factor": 1.5,
          "action": "interpolate"
        },
        "modifications_summary": "Modified 47 point(s)"
      }
    ],
    "total_modifications": 47
  },
  "preprocessing_modification_log": [
    [
      {
        "modification_type": "point_interpolated",
        "x_value": 14.3,
        "original_y_value": 385.2,
        "new_y_value": 94.1,
        "reason": "interpolated from neighbors"
      }
    ]
  ]
}
```

---

## 6. Mathematical Formulation

### 6.1 Quartile Calculation

For a segment with $n$ data points sorted as $y_1 \leq y_2 \leq ... \leq y_n$:

**First quartile** (Q1, 25th percentile):
$$Q_1 = y_{[\lfloor 0.25n \rfloor]}$$

**Third quartile** (Q3, 75th percentile):
$$Q_3 = y_{[\lfloor 0.75n \rfloor]}$$

**Interquartile range**:
$$\text{IQR} = Q_3 - Q_1$$

### 6.2 Fence Boundaries

**Lower fence**:
$$F_L = Q_1 - k \cdot \text{IQR}$$

**Upper fence**:
$$F_U = Q_3 + k \cdot \text{IQR}$$

**Outlier criterion**:
$$\text{outlier}(y_i) = \begin{cases}
\text{true} & \text{if } y_i < F_L \text{ or } y_i > F_U \\
\text{false} & \text{otherwise}
\end{cases}$$

### 6.3 Interpolation Formula

For an outlier at position $i$ with neighbors at positions $i-1$ and $i+1$:

$$y_i^{\text{new}} = \frac{y_{i-1} + y_{i+1}}{2}$$

This is simple linear interpolation assuming uniform spacing. For non-uniform spacing, inverse distance weighting could be used:

$$y_i^{\text{new}} = \frac{w_{i-1} y_{i-1} + w_{i+1} y_{i+1}}{w_{i-1} + w_{i+1}}$$

where $w_j = \frac{1}{|x_i - x_j|}$

Current implementation uses simple averaging for computational efficiency and robustness.

---

## 7. Technical Implementation Notes

### 7.1 Data Modification Context System

The implementation uses a `DataModificationContext` to ensure:

- **Complete traceability**: Every modification automatically logged
- **Mandatory breakpoint preservation**: Cannot accidentally remove/modify breakpoint locations
- **Atomic operations**: All modifications tracked at point level
- **Metadata generation**: Automatic creation of modification log for JSON export

### 7.2 Integration with Processing Pipeline

**Pipeline position**: Step 4 (Primary Preprocessing)

**Dependencies**:

- **Step 2 (Gap Analysis)**: Provides gap-based mandatory breakpoints
- **Step 3 (Early Attribute Break Columns)**: Provides structure-based mandatory breakpoints
  - **Critical dependency**: Early breaks define preprocessing segments

**Outputs**:

- Modified `RouteAnalysis` object with cleaned data
- Complete modification log (every changed point)
- Preprocessing metadata (method, parameters, statistics)
- Human-readable summary

### 7.3 Performance Characteristics

**Computational complexity**: O(n·m) where n = data points, m = number of segments

**Typical performance**:

- 50-mile corridor, 5000 points, 10 segments: < 0.1 seconds
- 500-mile network, 50000 points, 100 segments: < 1 second

**Memory usage**: O(n) for data copy and modification log

---

## 8. References and Further Reading

**Tukey, J.W. (1977)**. *Exploratory Data Analysis*. Addison-Wesley. ISBN 0-201-07616-0.

- Original definition of box plots and outlier fences

**ASTM E1926-08(2015)**. *Standard Practice for Computing International Roughness Index of Roads from Longitudinal Profile Measurements*.

- Standards for IRI measurement and data quality

**AASHTO R 56-14**. *Standard Practice for Certification of Inertial Profiling Systems*.

- Specifications for profiler accuracy and calibration

**McGhee, K.K. (2004)**. *Automated Pavement Distress Collection Techniques*. NCHRP Synthesis 334.

- Discussion of data quality issues in automated pavement surveys

---

## 9. Glossary

**IQR (Interquartile Range)**: The spread of the middle 50% of data (Q3 - Q1)

**Quartile**: Values that divide data into quarters (Q1 at 25%, Q2/median at 50%, Q3 at 75%)

**Fence**: Boundary beyond which values are considered outliers

**k-factor**: Multiplier controlling fence distance (1.5 = standard, 3.0 = extreme outliers only)

**Early Attribute Breaks**: Structural boundaries applied before preprocessing (Step 3)

**Mandatory Breakpoints**: X-coordinates where segments must begin/end (from gaps and attribute breaks)

**Segment-aware processing**: Computing statistics separately for each structural section

**Data Modification Context**: System ensuring complete traceability of preprocessing changes

---

## Appendix: Comparison with Alternative Outlier Detection Methods

### A.1 Tukey Fences vs. Standard Deviation Method

**Standard Deviation Method**: $\text{outlier if } |y - \mu| > k \cdot \sigma$

**Advantages of Tukey Fences**:

- More robust to outliers (uses quartiles, not mean/std which are influenced by outliers)
- Better for skewed distributions
- Less sensitive to extreme values in threshold calculation

**When Standard Deviation is better**:

- Normally distributed data with few outliers
- Need to preserve more marginal values
- Computational efficiency critical (mean/std faster than quartiles)

### A.2 Tukey Fences vs. Z-Score Method

**Z-Score Method**: $z = \frac{y - \mu}{\sigma}$, outlier if $|z| > k$

**Advantages of Tukey Fences**:

- Doesn't assume normal distribution
- Outliers don't affect the threshold calculation
- More interpretable for skewed pavement data

**When Z-Score is better**:

- Data is approximately normal
- Need standardized comparison across different data types
- Statistical testing framework required

### A.3 Tukey Fences vs. Moving Median/MAD

**Moving Median Absolute Deviation**: Local outlier detection using rolling windows

**Advantages of Tukey Fences**:

- Segment-aware processing respects structural boundaries
- Simpler conceptually (single threshold per segment)
- Doesn't require window size selection

**When Moving MAD is better**:

- Need to detect localized outliers in otherwise uniform segments
- Gradual trends in data
- No clear segment boundaries available

---

**Document version**: 1.0  
**Last updated**: 2026-05-22  
**Implementation**: `src/preprocessing/methods/tukey_fences.py`  
**Method key**: `tukey_fences`
