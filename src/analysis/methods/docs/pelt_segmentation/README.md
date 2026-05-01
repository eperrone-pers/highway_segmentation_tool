# PELT Segmentation (ruptures)

## Summary

This method performs **deterministic change-point segmentation** using **PELT** (Pruned Exact Linear Time) as implemented in the Python package **`ruptures`**.

Within each route, the algorithm partitions the measurement series into segments whose values are “approximately homogeneous” under a chosen cost model (typically a **piecewise-constant mean** model).

In this application, the method is integrated into the extensible analysis framework as:

- **Method key**: `pelt_segmentation`
- **Return type**: `single_objective` (a single best segmentation is returned)
- **Output**: breakpoint milepoints (`chromosome`) compatible with the app’s visualization and JSON schema.

---

## Plain-language overview

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

## What PELT does

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

## Gap-aware segmented processing (important)

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

## Parameters

Parameters are configured in the GUI under the `pelt_segmentation` method and validated by the framework.

### Change-point detection

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

### Smoothing (optional)

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

### Segment length constraints

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

### Suggested starting points

If you want a reasonable “first run” configuration:

- `model = l2`
- `jump = 1` (increase later if you need speed)
- `smooth_window_miles = 0.5–1.0` with `smoothing_method = median` if the signal has spikes
- Start `penalty` with a small grid (e.g., 50, 100, 200, 400) and choose the smallest value that avoids over-segmentation

### Troubleshooting checklist

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

---

## Output format

The method returns a single `AnalysisResult` containing:

- `all_solutions[0].chromosome`: sorted list of milepoint breakpoints (includes route start/end and gap boundaries)
- `mandatory_breakpoints`: mandatory boundaries (route boundaries + gap boundaries)
- `input_parameters`: saved for reproducibility in JSON

The JSON exporter will compute segment lengths and per-segment summary statistics from the breakpoint list.

### Interpreting outputs when tuning

When you are tuning, focus on:

- How many segments are produced (too many / too few)
- Whether breakpoints align with visibly meaningful changes
- Whether any segments violate your max length preference (if `max_length` is enabled)

---

## Implementation notes (for developers)

- Implementation class: `analysis.methods.pelt_segmentation.PeltSegmentationMethod`
- Dependency: `ruptures` (BSD 2-Clause license)
- Import behavior: `ruptures` is imported lazily inside `run_analysis()` so the app can start even if the package is missing.
- Robustness:
  - Very short gap-bounded sections are skipped (they cannot satisfy `min_size`).
  - If `ruptures` raises inside a section, the method logs a warning and continues, relying on mandatory breakpoints to preserve validity.

If you see warnings about short sections, it usually indicates that gaps are creating very small segmentable ranges relative to `min_length`.

---

## References

1. Killick, R., Fearnhead, P., & Eckley, I. A. (2012).
   *Optimal detection of changepoints with a linear computational cost.*
   Journal of the American Statistical Association, 107(500), 1590–1598.

2. `ruptures` documentation — PELT user guide:
   <https://centre-borelli.github.io/ruptures-docs/user-guide/detection/pelt/>

3. `ruptures` documentation — least-squares mean-shift cost (`CostL2`):
   <https://centre-borelli.github.io/ruptures-docs/user-guide/costs/costl2/>

4. `ruptures` GitHub repository (license and source):
   <https://github.com/deepcharles/ruptures>
