# Highway Segmentation Analysis - User Guide

## Table of Contents

1. [Overview](#overview)
2. [Pavement Analysis Context](#pavement-analysis-context)
3. [Getting Started](#getting-started)
4. [User Interface Guide](#user-interface-guide)
5. [Common Tasks](#common-tasks)
6. [Analysis Methods](#analysis-methods)
7. [Common Pavement Analysis Scenarios](#common-pavement-analysis-scenarios)
8. [Basic Workflow](#basic-workflow)
9. [Understanding Results](#understanding-results)
10. [Pavement-Specific Parameter Guidance](#pavement-specific-parameter-guidance)
11. [Data Import & Export](#data-import--export)
12. [Advanced Configuration](#advanced-configuration)
13. [Troubleshooting](#troubleshooting)
14. [Technical Reference](#technical-reference)

---

## Overview

The Highway Segmentation Analysis application provides advanced statistical and optimization-based methods for dividing highway data into optimal segments for pavement analysis. The system offers four distinct analysis approaches, from traditional genetic algorithms to statistical change point detection methods.

### Key Features

- **🧬 Multiple Analysis Methods**: Genetic algorithms (single/multi-objective, constrained) and statistical AASHTO CDA analysis
- **📊 Smart Data Handling**: Automatic gap detection with mandatory breakpoint insertion
- **🎯 Flexible Optimization**: Configure parameters for your specific analysis requirements  
- **📈 Interactive Visualization**: Click-to-explore results with detailed segment information
- **💾 Comprehensive Export**: JSON and Excel outputs with complete analysis metadata
- **⚙️ Persistent Settings**: Your preferences are automatically saved between sessions
- **🔧 Extensible Architecture**: Easy addition of new analysis methods and parameters

### Currently Supported Analysis Approaches

1. **Single-Objective Genetic Algorithm**: Traditional optimization minimizing segment variation
2. **Multi-Objective NSGA-II**: Pareto front exploration of quality vs. segment length tradeoffs
3. **Constrained Optimization**: Target-length segmentation with penalty enforcement
4. **AASHTO Enhanced CDA**: Statistical change point detection (citation: [CITATIONS.md](CITATIONS.md))

---

## Pavement Analysis Context

### Why Segmentation Matters for Pavement Management

Pavement networks are inherently variable due to:

- **Construction History**: Different construction dates, materials, and techniques
- **Traffic Loading**: Varying traffic volumes, vehicle types, and axle loads across sections
- **Environmental Conditions**: Climate variations, drainage differences, subgrade changes
- **Maintenance History**: Different rehabilitation timing, methods, and treatment effectiveness
- **Functional Classification**: Interstate vs. arterial vs. collector roads requiring different design standards
- **Structural Composition**: Varying layer thicknesses, base types, and pavement structures

**Segmentation Goal**: Divide the network into homogeneous sections where:

- Pavement condition is relatively uniform within segments
- Similar treatment strategies and priorities apply
- Deterioration patterns and rates are consistent
- Resource allocation and project limits are optimized
- Performance predictions are more accurate

### Common Pavement Indices for Segmentation

This tool works with any numeric pavement condition index:

- **IRI (International Roughness Index)**: Ride quality measurement, typical range 40-250 inches/mile
- **PCI (Pavement Condition Index)**: Overall condition rating, 0-100 scale (100 = excellent)
- **Rutting Depth**: Structural distress indicator, typically 0-25mm
- **Cracking Indices**: Alligator cracking, longitudinal cracking, etc. (% area or length)
- **Structural Numbers**: Composite measure of pavement layer strength
- **Deflection Data**: FWD (Falling Weight Deflectometer) measurements indicating structural capacity
- **Friction Numbers**: Surface safety measurements (skid resistance)
- **Texture Depth**: Surface drainage and noise characteristics

### Typical Pavement Segmentation Applications

1. **Network-Level Planning**: Divide network into treatment sections for budget allocation and multi-year programming
2. **Project-Level Design**: Identify homogeneous sections within projects to optimize treatment limits and reduce costs
3. **Performance Modeling**: Create consistent sections for deterioration curve development and life-cycle analysis
4. **Data Quality Control**: Identify anomalous data, equipment calibration issues, or transition zones
5. **Historical Analysis**: Track condition changes over time in statistically consistent sections
6. **Treatment Effectiveness**: Evaluate rehabilitation performance in homogeneous test sections
7. **Pavement Management Systems**: Define analysis sections for optimal resource allocation

### Segmentation vs. Engineering Judgment

**Automated segmentation complements, not replaces, engineering judgment:**

- ✅ **Advantages**: Objective, repeatable, statistically justified, processes large datasets efficiently
- ✅ **Best for**: Initial screening, validating existing sections, large-scale network analysis
- ⚠️ **Limitations**: Cannot account for all local knowledge, upcoming projects, or political boundaries
- 🔧 **Best Practice**: Use algorithms to identify candidate breakpoints, then validate with field knowledge and agency constraints

---

## Getting Started

### Installation

1. **Extract Application**: Unzip all files to your desired installation directory
2. **Install Dependencies**: Run `pip install -r requirements.txt` from the project directory
3. **Optional (Recommended for CLI)**: Run `pip install -e .` to enable the `highway-seg` command
4. **Launch Application**: Execute `python src/run.py`
5. **Verify Installation**: The GUI should open and show the main window with the **Optimization Log** tab

### Quick Start

1. In **📁 File Operations**, click **Browse...** next to **Data File** and select a CSV
2. Select **X Column (Distance)** and **Y Column (Data Values)** (these are not auto-selected)
3. Optional (multi-route files): pick **Route Column (Optional)** then click **Filter** to select which routes to process
4. Set **Gap Threshold (miles)** (controls where mandatory breakpoints are inserted at data gaps)
5. Under **Results File (Required):** type a base name and click **Browse...** to choose an output folder
6. In **🔬 Optimization Method**, choose a method and adjust the method-specific parameters shown below it
7. Click **🚀 Start Optimization** and monitor progress in the **Optimization Log** tab
8. When complete, the enhanced visualization window will open automatically

- If you want to open a different results file later, use **📊 Load & Plot Results**

---

## User Interface Guide

The interface is split into a left configuration pane and a right execution/results pane.

### Left Panel - Configuration & Control

#### 📁 **File Operations**

- **Data File / Browse...**: Select an input CSV. The app reads headers immediately and populates the column dropdowns.
- **X Column (Distance)** and **Y Column (Data Values)**: You must select these explicitly for each new file.
- **Route Column (Optional)**:
  - Set to **None - treat as single route** to analyze the file as one route.
  - Set to a column name to enable multi-route mode, then use **Filter** to pick which route IDs to process.
  - In multi-route mode, rows with missing route IDs (blank/empty) are excluded from analysis and this is logged.
    If all rows are missing/invalid for the selected route column, the run is blocked with an error.
- **Gap Threshold (miles)**: Framework parameter used by all methods; gaps larger than this force mandatory breakpoints.
- **Must-Break Columns (Optional)**: Select one or more additional input columns whose *value changes* must force a breakpoint.
  - Example use cases: pavement type/class, lane count, functional class.
  - These breaks are treated as **mandatory** (the analysis cannot span across a change).
- **Reset to Defaults**: Resets parameters back to their defaults.
- **Results File (Required)**:
  - Left field sets the base results filename.
  - **Browse...** chooses the output folder (recommended). If you don’t choose a folder, results may save into the current working directory.

#### 🔬 **Optimization Method**

- **Optimization Method** dropdown: Select the method.
- **Method Description**: Updates based on selection.
- **Method Parameters**: The parameter widgets under the dropdown change by method. These values are saved into the output JSON as inputs.

#### ⚙️ **Runtime & Caching**

- Contains runtime/caching options (for example, cache management). Use defaults unless you have a reason to tune.

### Right Panel - Execution & Results

#### 🚀 **Action Buttons**

- **🚀 Start Optimization**: Validates inputs, loads data if needed, then runs the selected method.
- **⏹ Stop**: Requests a graceful stop (the run halts after the current step/generation).
- **📊 Load & Plot Results**: Open an existing results JSON and launch the enhanced visualization window.
- **Copy command line for this analysis**: Creates a run spec JSON and copies a runnable CLI command to your clipboard.
- **❓ Help**: Opens a Documentation dialog with buttons to open the User Guide and any available method-specific docs in your browser.
- **❌ Exit**: Exits the application (saving settings).

#### 🗂️ **Results Tabs**

- **Optimization Log**: Live run log output.
- **Results Files**: A human-readable summary extracted from a schema-compliant results JSON (populated after a run and/or when you load a results file).

#### 📈 **Enhanced Visualization Window**

When you load results (or when a run completes), the enhanced visualization window can display:

- A **Route** selector for multi-route results
- A segmentation plot (right pane)
- A Pareto front plot (left pane) for multi-objective methods
- A **Break Attributes Diagram** (optional): a compact lane view that shows the values of the selected must-break columns along the x-axis
- **📊 Export to Excel** to export the loaded results

---

## Common Tasks

### To run a new analysis (end-to-end)

1. Select your input data: **Browse...** next to **Data File**
2. Choose **X Column (Distance)** and **Y Column (Data Values)**
3. Optional: for multi-route datasets, choose a **Route Column (Optional)** and click **Filter** to select routes
4. Set **Gap Threshold (miles)**
5. Choose where results will save:
   - Enter a base name under **Results File (Required)**
   - Click **Browse...** to pick an output folder
6. Select an **Optimization Method** and adjust its parameters
7. Click **🚀 Start Optimization**
   - If you click **⏹ Stop** before completion, the run may stop without saving a consolidated results file.
   - If an output file already exists, you’ll be prompted to overwrite.
8. After completion, review:
   - **Results Files** tab (summary)
   - The enhanced visualization window (opens automatically)
   - Use **📊 Load & Plot Results** to reopen results later

### To filter which routes are processed

1. Set **Route Column (Optional)** to the column that contains route IDs
2. Click **Filter**
3. In the dialog, click routes to toggle selection, or type in the search box and use **Add Route**
4. Click **OK** to apply (the UI will show “N of M selected”)

- Tip: **Select All Routes** / **Clear All Routes** are convenient for large files.
- In multi-route mode you must select at least one route.

- Note: If the selected route column contains missing route IDs (blank/empty), those rows are excluded from analysis.
  If that excludes all rows, multi-route analysis cannot proceed.

### To load and visualize an existing results file

1. Click **📊 Load & Plot Results**
2. Choose a `.json` results file
3. If `jsonschema` is installed, the app validates the JSON and logs any warnings
4. Use the enhanced visualization window to explore the plots and switch routes

### To export results to Excel

1. Load results (either after a run, or via **📊 Load & Plot Results**)
2. In the enhanced visualization window, click **📊 Export to Excel**
3. Choose an output `.xlsx` file

---

## Analysis Methods

This section is a user-facing overview of each method. Method parameters are shown directly in the UI under **🔬 Optimization Method** and are saved into the results JSON as part of the run metadata.

Method documentation: each method can provide a dedicated doc at `src/analysis/methods/docs/<method_key>/README.md`. This guide links to those docs and keeps only high-level “which method should I use?” guidance.

### Single-Objective Genetic Algorithm

**🎯 Purpose**: Find the single best segmentation minimizing within-segment variation.

Method docs: [src/analysis/methods/docs/single/README.md](src/analysis/methods/docs/single/README.md)

**🔧 Best Used For**:

- Standard segmentation tasks where homogeneity is the primary goal
- When you need one clear segmentation recommendation
- Baseline comparisons with other methods
- Quick analysis of data characteristics

**📊 Results**:

- One optimal segmentation solution
- Clear visualization with color-coded segments
- Detailed fitness and segment length information

**🛣️ Pavement Applications**:

- **Network screening**: Rapidly identify sections needing immediate attention for budget prioritization
- **Maintenance planning**: Group similar condition sections for efficient treatment scheduling
- **Budget justification**: Demonstrate statistically significant condition differences to support funding requests
- **Quality assurance**: Validate consistency of data collection equipment and procedures
- **Baseline analysis**: Establish reference segmentation for comparing with other methods

**📊 Typical Pavement Parameters**:

For **IRI segmentation** on a typical highway corridor:

- **Min Length**: 0.3-0.5 miles (minimum practical project length, crew mobilization)
- **Max Length**: 2-5 miles (typical resurfacing project limits, budget constraints)
- **Gap Threshold**: 0.05-0.1 miles (typical GPS/DMI data spacing, bridge/structure gaps)
- **Population Size**: 100-200 (sufficient exploration for pavement networks)
- **Generations**: 100-200 (usually achieves convergence for condition data)

**Example Workflow**: 50-mile Interstate corridor with IRI data

- Set Gap Threshold = 0.1 miles (accounts for measurement spacing and bridge gaps)
- Min Length = 0.5 miles (agency minimum project length)
- Max Length = 3.0 miles (typical resurfacing contract size)
- Expected outcome: 15-25 segments for typical heterogeneous corridor
- Validate breakpoints against maintenance records and known treatment boundaries

---

### Multi-Objective NSGA-II Optimization

**🎯 Purpose**: Discover the complete range of optimal tradeoffs between segment homogeneity and segment length.

Method docs: [src/analysis/methods/docs/multi/README.md](src/analysis/methods/docs/multi/README.md)

**🔧 Best Used For**:

- Exploring multiple segmentation possibilities
- Understanding quality vs. practicality tradeoffs
- When segment count preferences vary among stakeholders
- Research and comparative analysis

**📊 Results**:

- **Pareto Front Plot**: Shows all optimal solution tradeoffs
- **Interactive Exploration**: Click any point to see detailed segmentation
- **Solution Comparison**: Easily switch between different optimal solutions
- **Export Flexibility**: Save any selected solution from the front

**🎨 Navigation**:

- **Left Plot**: Pareto front (Total Deviation vs. Average Segment Length)
- **Right Plot**: Detailed view of selected solution with segment visualization
- **Point Selection**: Click any Pareto front point to examine that solution
- **Multiple Solutions**: Each point represents a different optimal balance

**📈 Interpretation**:

- **Lower-left points**: Better homogeneity, more segments, shorter lengths
- **Upper-right points**: Fewer segments, longer lengths, more variation
- **Front shape**: Reveals data characteristics and optimization constraints

**🛣️ Pavement Applications**:

- **Project alternatives analysis**: Present multiple options to decision-makers showing cost vs. quality tradeoffs
- **Budget scenario planning**: Explore "what-if" scenarios for different funding levels
- **Stakeholder engagement**: Show range of possibilities when preferences vary among management, engineering, and operations
- **Treatment strategy evaluation**: Compare fine-grained maintenance vs. major rehabilitation approaches

**📊 Typical Pavement Parameters**:

For **PCI segmentation** on arterial network:

- **Min Length**: 0.2-0.4 miles (smaller projects acceptable on arterials)
- **Max Length**: 2-4 miles (typical urban project limits)
- **Population Size**: 150-300 (need good Pareto front diversity)
- **Generations**: 200-400 (multi-objective requires more iterations)
- **Archive Size**: 50-100 (number of Pareto solutions to maintain)

**Interpreting Results for Pavement Management**:

On a Pareto front for PCI data:

- **Lower-left solutions**: More segments, better condition homogeneity, higher treatment costs
  - Use when: Quality is critical, detailed analysis needed, sufficient budget available
- **Upper-right solutions**: Fewer segments, longer projects, more internal variation
  - Use when: Budget constrained, simpler management preferred, accept some heterogeneity
- **Middle solutions**: Balanced approach, often most practical for agencies

---

### Constrained Single-Objective Optimization

**🎯 Purpose**: Find the best segmentation while targeting a specific average segment length.

Method docs: [src/analysis/methods/docs/constrained/README.md](src/analysis/methods/docs/constrained/README.md)

**🔧 Best Used For**:

- Meeting regulatory requirements for segment lengths
- Standardizing analysis across multiple highway sections
- Balancing analysis quality with operational constraints
- When segment length consistency is important

**⚙️ Configuration**:

- **Target Avg Length**: Your desired average (e.g., 2.0 miles)
- **Length Tolerance**: Acceptable deviation (e.g., ±0.2 miles)  
- **Penalty Weight**: Enforcement strength (higher = stricter, range: 1-1000)

**📊 Results**:

- Optimal segmentation respecting your length constraint
- **Constraint Satisfaction Report**: Clear YES/NO constraint achievement
- **Achievement Analysis**: Target vs. achieved average length comparison
- **Penalty Impact**: Shows how constraint affected the optimization

**✅ Success Indicators**:

- "Constraint satisfied: YES" in results summary
- Achieved average within your specified tolerance
- Reasonable fitness value considering the constraint

**🛣️ Pavement Applications**:

- **Regulatory compliance**: Meet DOT requirements for standard segment lengths in reporting systems
- **Standardized analysis**: Ensure consistency across multiple districts or highway sections
- **Contractor coordination**: Match typical construction project sizes for bidding efficiency
- **Pavement management systems**: Align with existing PMS section definitions

**📊 Typical Pavement Parameters**:

For **meeting 1-mile agency standard** with IRI data:

- **Target Avg Length**: 1.0 miles (agency requirement)
- **Length Tolerance**: ±0.2 miles (acceptable range: 0.8-1.2 miles)
- **Penalty Weight**: Start at 100-200, increase if constraint not satisfied
- **Min Length**: 0.5 miles (allow shorter segments where data demands)
- **Max Length**: 1.5 miles (prevent extremely long outliers)

**Common Agency Standards**:

- **State DOTs**: Often require 0.5-mile or 1-mile standard sections for reporting
- **Local agencies**: May use shorter 0.1-mile sections for urban arterials
- **Research studies**: Sometimes need specific lengths for statistical power (e.g., 0.25-mile)

---

### AASHTO Enhanced CDA Statistical Analysis

**🎯 Purpose**: Statistically-justified, deterministic segmentation using change point detection theory.

Method docs: [src/analysis/methods/docs/aashto_cda/README.md](src/analysis/methods/docs/aashto_cda/README.md)

**🔧 Best Used For**:

- Research requiring statistical validation of breakpoints
- Regulatory compliance needing documented methodology
- Comparison with established MATLAB/SAS implementations
- When deterministic (non-random) results are required
- Validation of genetic algorithm results

**📊 Statistical Approach**:

- **Change Point Detection**: Identifies statistically significant breakpoints
- **Segmented Processing**: Analyzes sections between mandatory breakpoints independently
- **Deterministic Results**: Same input always produces same output (no randomness)

**📚 Reference**:

This implementation is based on the AASHTO CDA research code. If you use AASHTO CDA results from this tool, cite:

- Katicha, S., Flintsch, G. (2025). *Enhanced AASHTO Cumulative Difference Approach (CDA) for Pavement Data Segmentation*. Transportation Research Record (accepted).

**⚙️ Key Parameters**:

**Alpha (α) - Statistical Significance**:

- **Purpose**: Controls false positive rate for breakpoint detection
- **Range**: Typically between 0.001 and 0.49 (the exact default is shown in the UI)
- **Lower values**: More conservative, fewer breakpoints, higher confidence
- **Higher values**: More sensitive, more breakpoints, lower confidence

**Error Estimation Method**:

This setting controls how the algorithm estimates the random measurement error standard deviation ($\sigma$). That $\sigma$ value is used in the change point significance test.

- **Method 1**: MAD with Normal Distribution
  - Uses the *difference sequence* `diff(y)` and estimates $\sigma$ via a scaled Median Absolute Deviation (MAD).
  - Most robust when your measurements include spikes/outliers.
- **Method 2**: Standard Deviation of Differences (**Recommended**)
  - Uses the *difference sequence* `diff(y)` and estimates $\sigma$ from the sample standard deviation of differences.
  - Often works well for highway data because differencing reduces the influence of slow trends/level shifts.
- **Method 3**: Standard Deviation of Measurements
  - Estimates $\sigma$ directly from the sample standard deviation of `y`.
  - Can be overly influenced by real step-changes (which are exactly what the method is trying to detect).

Note: Methods 1 and 2 both work on `diff(y)` and divide by $\sqrt{2}$ to convert difference variability into an estimate of measurement error.

**Use Segment-Specific Length**:

- **Enabled (recommended)**: The significance test scales by the length of each candidate segment.
- **Disabled**: The significance test scales by the total data length instead (less typical).

**Max Segments**:

- **None (Unlimited)**: No explicit cap is applied; the algorithm stops when it no longer finds statistically significant change points.
- **Specific Number**: Applies a hard cap on the number of segments *within each section between mandatory breakpoints* (gaps). The algorithm may still return fewer segments if additional change points are not significant.

**Diagnostic Output**:

- **Enabled**: Prints verbose step-by-step diagnostics to the console and adds extra diagnostic fields into the results JSON (under the run statistics/diagnostics section).
- **Disabled**: Runs without the extra diagnostic logging.

**📊 Results**:

- **Deterministic Segmentation**: Statistically-justified breakpoint locations
- **Statistical Validation**: Each breakpoint supported by significance testing
- **Section-by-Section Analysis**: Detailed processing information per data section
- **Comprehensive Diagnostics**: Algorithm parameters, processing summary, section details

**🎨 Diagnostic Information (when enabled)**:

```text
=== AASHTO CDA Analysis: Route_Name ===
Total mandatory breakpoints: 8
Segmentable sections to process: 7

Section 1: [196.853 to 198.104] - length: 1.251 miles, points: 65
  -> CDA found 3 internal breakpoints
...
Final result: 49 segments from 49 breakpoints
```

**📄 Enhanced JSON Export**:

- Algorithm metadata and parameters
- Processing summary with section-by-section details
- Statistical validation information
- Diagnostic data for method verification

**🔬 When to Use AASHTO CDA**:

- ✅ Research requiring statistical justification
- ✅ Regulatory submissions needing documented methodology  
- ✅ Validation of other segmentation approaches
- ✅ When reproducibility is critical
- ✅ Comparison with published AASHTO procedures

**🛣️ Pavement Applications**:

- **Research publications**: Defensible methodology for peer-reviewed journals
- **Legal/regulatory compliance**: Statistically justified breakpoints for contested decisions
- **Forensic analysis**: Investigate pavement failures with documented change point detection
- **Validation studies**: Compare with engineering judgment or existing segmentation schemes
- **Contract disputes**: Objective evidence of pavement condition transitions

**📊 Typical Pavement Parameters**:

For **IRI analysis** requiring statistical justification:

- **Alpha (α)**: 0.05 (standard 95% confidence level for pavement engineering)
- **Error Estimation**: Method 2 (Std Dev of Differences) - recommended for pavement condition data
- **Use Segment-Specific Length**: Enabled (accounts for varying segment sizes)
- **Max Segments**: None (let statistics determine breakpoints)
- **Diagnostic Output**: Enabled for documentation and verification

**Comparing AASHTO CDA to Genetic Algorithms**:

| Characteristic | AASHTO CDA | Genetic Algorithm |
| -------------- | ---------- | ----------------- |
| Result variability | None (deterministic) | Some (random seed) |
| Statistical justification | Yes (p-values) | No (heuristic optimization) |
| Computational time | Fast | Moderate to slow |
| Number of breakpoints | Data-driven | Parameter-driven |
| Best for | Research, validation | Practical optimization |

**Validation Example**:

```text
Run both AASHTO CDA (α=0.05) and Single-Objective GA on same IRI data:
- AASHTO CDA: 23 segments, statistically justified breakpoints
- GA (min=0.5, max=3.0): 21 segments, optimized for homogeneity
- Agreement: 18 breakpoints within 0.1 miles
→ Conclusion: Both methods identify similar major transitions
→ Use: AASHTO for documentation, GA for operational optimization
```

---

## Common Pavement Analysis Scenarios

This section provides step-by-step guidance for typical pavement engineering applications.

### Scenario 1: Interstate Rehabilitation Prioritization

**Context**: 50-mile Interstate corridor, annual IRI surveys, need to identify and prioritize 10 miles for rehabilitation within budget

**Recommended Approach**:

1. **Method**: Use **Single-Objective GA** for clear, prioritized recommendations
2. **Must-Break Columns**: Set to ["PAVEMENT_TYPE", "MAJOR_STRUCTURE"] to respect construction boundaries
3. **Parameters**:
   - Gap Threshold: 0.1 miles (bridge gaps, measurement spacing)
   - Min Length: 0.5 miles (minimum rehabilitation project)
   - Max Length: 3.0 miles (typical contract size)
   - Population: 150, Generations: 150
4. **Analysis**:
   - Run analysis, obtain one optimal segmentation
   - Sort segments by mean IRI (descending - worst first)
   - Select top segments totaling ~10 miles
5. **Validation**:
   - Cross-check with pavement management system data
   - Verify against recent construction/maintenance records
   - Consider geographic distribution and contractor access
6. **Documentation**: Export to Excel for presentation to management

**Expected Outcome**: Clear prioritization list with statistical justification for selected segments

---

### Scenario 2: Local Agency Network Budget Optimization

**Context**: 500-mile arterial network, limited annual budget, need to show project alternatives to agency board

**Recommended Approach**:

1. **Method**: Use **Multi-Objective NSGA-II** to demonstrate quality vs. cost tradeoffs
2. **Must-Break Columns**: ["FUNCTIONAL_CLASS", "PAVEMENT_TYPE", "JURISDICTION"]
3. **Parameters**:
   - Gap Threshold: 0.05 miles (more sensitive for urban arterials)
   - Min Length: 0.2 miles (allow shorter urban projects)
   - Max Length: 2.0 miles (urban project constraints)
   - Population: 200, Generations: 300, Archive: 75
4. **Presentation Strategy**:
   - Display Pareto front to board: "More segments = higher quality but higher cost"
   - Show 3-5 representative solutions from across the front
   - Highlight tradeoffs: "Option A: 150 segments, $50M vs. Option B: 100 segments, $35M"
5. **Decision Support**:
   - Let decision-makers select preferred balance point
   - Export selected solution for project development
   - Use for multi-year capital improvement planning

**Expected Outcome**: Informed board decision with clear understanding of quality vs. cost tradeoffs

---

### Scenario 3: Research Study Validation and Publication

**Context**: Academic/agency research comparing automated segmentation to traditional engineering judgment

**Recommended Approach**:

1. **Method**: Use **AASHTO CDA** for statistical rigor and reproducibility
2. **Must-Break Columns**: ["TREATMENT_BOUNDARY", "PAVEMENT_TYPE"] if available from records
3. **Parameters**:
   - Alpha: 0.05 (95% confidence - standard for pavement engineering research)
   - Error Estimation: Method 2 (Standard Deviation of Differences)
   - Use Segment-Specific Length: Enabled
   - Diagnostic Output: Enabled (essential for methodology documentation)
4. **Validation Process**:
   - Document all parameters completely
   - Compare automated breakpoints to existing agency segment boundaries
   - Calculate agreement metrics (% within 0.1 miles, mean offset, etc.)
   - Run sensitivity analysis on α values (0.01, 0.05, 0.10)
5. **Publication Documentation**:
   - Export diagnostic JSON for methodology verification
   - Include statistical confidence levels for each breakpoint
   - Provide complete parameter settings in methods section
   - Reference: Katicha & Flintsch (2025) paper

**Expected Outcome**: Peer-reviewable methodology with full statistical justification

---

### Scenario 4: DOT Standard Segment Length Compliance

**Context**: State DOT requires 1.0-mile segments ±0.2 miles for pavement management system reporting

**Recommended Approach**:

1. **Method**: Use **Constrained GA** with agency length requirement
2. **Must-Break Columns**: ["DISTRICT_BOUNDARY", "ROUTE_TYPE"] per agency standards
3. **Parameters**:
   - Target Avg Length: 1.0 miles (agency requirement)
   - Length Tolerance: 0.2 miles (acceptable range: 0.8-1.2 miles)
   - Penalty Weight: Start at 200, increase to 500 if needed
   - Min Length: 0.5 miles (allow exceptions where data demands)
   - Max Length: 1.5 miles (prevent outliers)
4. **Compliance Verification**:
   - Check "Constraint Satisfied: YES" in results
   - Verify achieved average is within 0.8-1.2 mile range
   - Review segment length distribution
5. **Integration**:
   - Export to agency PMS format (Excel or CSV)
   - Validate segment IDs match agency conventions
   - Document any exceptions requiring engineering judgment

**Expected Outcome**: Compliant segmentation ready for PMS import

---

### Scenario 5: Treatment Effectiveness Evaluation

**Context**: Need to create test sections to evaluate mill-and-overlay effectiveness over 5-year period

**Recommended Approach**:

1. **Method**: Use **Single-Objective GA** to create homogeneous pre-treatment sections
2. **Must-Break Columns**: ["TRAFFIC_VOLUME_CLASS", "SUBGRADE_TYPE"] for consistent test conditions
3. **Parameters**:
   - Gap Threshold: 0.05 miles (tight control for research)
   - Min Length: 0.3 miles (minimum statistical sample)
   - Max Length: 1.0 miles (control section size)
   - Higher generations (300+) for refined homogeneity
4. **Section Selection**:
   - Select 5-10 most homogeneous segments (lowest std deviation)
   - Ensure similar pre-treatment condition (IRI, PCI)
   - Match traffic levels across test sections
5. **Monitoring Plan**:
   - Annual condition surveys using same equipment/method
   - Track deterioration rates in consistent sections
   - Compare treated vs. control sections

**Expected Outcome**: Statistically valid test sections for performance comparison

---

## Basic Workflow

### Step 1: Prepare Your Data

**📋 Data Requirements**:

- **File Format**: CSV with headers
- **Required Columns**:
  - Milepoint/location data (numeric)
  - Measurement values (numeric)
- **Optional Columns**:
  - Route identifiers for multi-route analysis
  - Additional metadata (preserved in exports)

**✅ Data Quality Checklist**:

- ✦ Milepoints in ascending order within each route
- ✦ No duplicate milepoint values
- ✦ Measurement values are numeric (missing values allowed)
- ✦ Reasonable milepoint spacing (typically 0.01-0.1 miles)
- ✦ Sufficient data points (minimum 50+ recommended)

### Step 2: Load and Configure

1. **Select input file**: In **📁 File Operations**, click **Browse...** next to **Data File**
2. **Pick columns**: Select **X Column (Distance)** and **Y Column (Data Values)**
3. **Optional (multi-route)**: Select **Route Column (Optional)** and click **Filter** to choose which routes to run
4. **Set framework rules**: Set **Gap Threshold (miles)**
5. **Choose output location/name**: Under **Results File (Required)**, enter a base name and click **Browse...** to choose an output folder
6. **Choose method + parameters**: Select an **Optimization Method** and adjust its method-specific parameters

### Step 3: Execute Analysis

1. **Review Configuration**: Verify all settings meet your requirements
2. **Start**: Click **🚀 Start Optimization**
3. **Monitor**: Watch the **Optimization Log** tab for progress and warnings
4. **Stop if needed**: Click **⏹ Stop** to request a graceful stop

### Step 4: Interpret and Export

1. **Understand Results**: Use method-specific guidance for interpretation
2. **Explore Solutions**: For multi-objective, examine different Pareto front points
3. **Validate Output**: Check that breakpoints make physical/practical sense
4. **Review outputs**:

- Use the **Results Files** tab to review the JSON summary
- Use **📊 Load & Plot Results** to open the enhanced visualization window

1. **Export**: In the enhanced visualization window, click **📊 Export to Excel**

---

## Understanding Results

### Breakpoint Types and Visualization

**Mandatory Breakpoints (forced boundaries)**:

- **Origin**:
  - **Gap breaks**: data gaps exceeding the Gap Threshold
  - **Attribute breaks**: value changes in selected *Must-Break Columns*
- **Purpose**: Prevent segments from spanning discontinuities or forbidden attribute changes
- **Properties**: Cannot be moved/removed by optimization algorithms

**Optimized Breakpoints (algorithm-selected)**:

- **Origin**: Placed by analysis algorithms for optimal segmentation
- **Purpose**: Define boundaries that minimize within-segment variation
- **Properties**: Algorithm-determined locations for best segmentation quality
- **Identification**: Positioned at statistically/algorithmically optimal points

**Break Attributes Diagram (optional)**:

- If you selected Must-Break Columns for the run, the visualization can show a per-attribute “lane” diagram at the top of the segmentation plot.
- Hovering a lane box shows the attribute name and value for that x-range.

### Key Result Metrics

**Total Deviation (Fitness)**:

- **Measurement**: Sum of all individual point deviations from segment means
- **Optimization Goal**: Lower values indicate more homogeneous segments
- **Comparison**: Use to compare solution quality across methods
- **Units**: Same as your measurement data (e.g., structural strength units)

**Segment Count**:

- **Significance**: Total number of segments created by the analysis
- **Influencing Factors**: Min/max length constraints, data characteristics, method settings
- **Tradeoffs**: More segments → better homogeneity but increased complexity
- **Practical Limits**: Consider maintenance and analysis resource requirements

**Average Segment Length**:

- **Calculation**: Mean length across all segments in the solution
- **Variability**: Individual segments may vary significantly from average
- **Targeting**: Primary constraint in constrained optimization method
- **Planning**: Important for resource allocation and maintenance scheduling

**Constraint Satisfaction** (Constrained Method Only):

- **Validation**: Clear YES/NO indication of constraint achievement
- **Tolerance Check**: Whether achieved average falls within specified range
- **Penalty Analysis**: Impact of constraint enforcement on solution quality

### Statistical Validation (AASHTO CDA)

**Statistical Significance**:

- **Alpha Level**: Confidence level for breakpoint detection (e.g., 0.05 = 95% confidence)
- **Change Points**: Each breakpoint statistically justified by significance testing
- **Reproducibility**: Deterministic results enable method validation and comparison

**Section Processing Details**:

- **Independent Analysis**: Each data section analyzed separately for statistical validity
- **Processing Summary**: Number of sections, total datapoints, breakpoints found per section
- **Diagnostic Information**: Detailed algorithm execution data for method verification

### Result Quality Assessment

**✅ Good Segmentation Indicators**:

- Breakpoints aligned with visible data changes
- Reasonable segment lengths for your application
- Low total deviation relative to data range
- Constraint satisfaction (if using constrained method)
- Consistent segment statistics within acceptable ranges

**⚠️ Potential Issues**:

- Extremely short segments (check min length setting)
- Very long segments with high internal variation
- Constraint not satisfied after reasonable penalty weight adjustment
- Breakpoints in unexpected locations (may indicate data quality issues)

### Interpreting Results for Pavement Data

**Practical Examples with IRI Data**:

```text
Segment 1: MP 10.0-12.5 (2.5 mi), Mean IRI = 85 in/mi, Std Dev = 8 in/mi
  ✅ Interpretation: Good condition, excellent uniformity
  → Treatment: Routine maintenance (crack sealing, joint repair)
  → Priority: Low (5-7 year timeframe)
  → Budget: ~$15K/mile preventive maintenance

Segment 2: MP 12.5-14.8 (2.3 mi), Mean IRI = 145 in/mi, Std Dev = 22 in/mi
  ⚠️ Interpretation: Fair condition, moderate variability
  → Treatment: Consider mill & overlay (may have localized failures)
  → Priority: Medium (2-4 year timeframe)
  → Budget: ~$200K/mile rehabilitation
  → Note: Investigate high std dev - possible localized distress

Segment 3: MP 14.8-16.2 (1.4 mi), Mean IRI = 195 in/mi, Std Dev = 35 in/mi
  ❌ Interpretation: Poor condition, high variability
  → Treatment: Requires detailed investigation before design
  → Priority: High (immediate to 1 year)
  → Budget: $300-500K/mile (reconstruction possible)
  → Action: Field investigation, cores, FWD testing recommended
```

**Red Flags for Pavement Data**:

**High Standard Deviation Within Segments**:

- **Possible Causes**:
  - Inadequate segmentation (algorithm needs more breakpoints - decrease min length)
  - Data quality issues (outliers, sensor errors, calibration drift)
  - Real transition zones (structure approaches, overlay limits, base failures)
  - Mixed conditions (alligator cracking + good sections in same segment)
- **Investigation**:
  - Review raw data plot - look for obvious outliers
  - Check maintenance records - was segment partially treated?
  - Consider field visit - visual validation of variability

**Very Short Segments** (< 0.3 miles):

- **May Indicate**:
  - Real transitions (excellent! - bridge approach, overlay edge, drainage change)
  - Measurement noise (increase min length or gap threshold)
  - Data collection issues (GPS errors, equipment malfunction)
- **Action**: Cross-reference with construction plans, satellite imagery, field notes

**Unrealistic Breakpoint Locations**:

- **Examples**:
  - Mid-bridge breakpoints → Increase gap threshold to span structures
  - Too frequent changes → Increase min segment length
  - Missing obvious transitions → Decrease gap threshold, check must-break columns
  - Breakpoint in middle of recent overlay → Data quality issue or old data

### Validating Results Against Field Knowledge

**✅ Cross-Check with Agency Records**:

- Maintenance history database (treatment dates and types)
- Construction project locations and limits
- Visual condition survey data and distress maps
- Pavement management system existing sections
- Known problem areas (frequent complaints, high maintenance)
- Traffic volume changes (new developments, ramp additions)

**Validation Example**:

```text
Algorithm Result: Breakpoint at MP 15.32
Agency Records Check:
  - Construction database: Overlay project ended at MP 15.28 (2018)
  - Google Earth historical: Clear pavement color change at ~MP 15.3
  - Maintenance notes: "Transition from 2018 overlay to original 1998 pavement"
  ✅ VALIDATED: Algorithm correctly identified treatment boundary
  → Confidence: High - use this breakpoint in final segmentation

Algorithm Result: Breakpoint at MP 23.67
Agency Records Check:
  - No construction records near this location
  - Google Earth: No visible change
  - Maintenance notes: None
  - BUT: Plotted data shows clear IRI jump from 90 to 150
  → Investigate: Possible data quality issue or unrecorded event
  → Action: Field visit to verify condition change
  ⚠️ TENTATIVE: Verify before finalizing
```

**When Algorithm Disagrees with Engineering Judgment**:

1. **Algorithm finds breakpoint, engineer doesn't see transition**:
   - Check: Is there a statistical change that's not visually obvious?
   - Consider: Subtle deterioration onset, drainage boundary, base change
   - Action: Field investigation may reveal hidden issue

2. **Engineer sees obvious transition, algorithm misses it**:
   - Check: Gap threshold may be too large, min length too long
   - Consider: Recent construction not yet reflected in condition
   - Action: Adjust parameters or manually add breakpoint

3. **Breakpoints close but not exact** (within 0.1-0.2 miles):
   - **Normal**: Acceptable difference due to discrete data points
   - Action: Use engineering judgment to snap to logical location (structure, intersection)

---

## Pavement-Specific Parameter Guidance

### Gap Threshold Selection for Pavement Data

**Based on Data Collection Method**:

- **High-speed profiler** (Laser/inertial): 0.05-0.10 miles
  - Modern equipment with GPS, very consistent spacing
  - Use 0.05 for research-grade data, 0.10 for production surveys
- **DMI-based surveys**: 0.10-0.15 miles
  - Distance Measuring Instrument, good precision
  - Accounts for GPS drift and odometer accuracy
- **Manual surveys** (distress, visual): 0.20-0.30 miles
  - Lower precision, judgment-based measurement locations
- **Network-level screening**: 0.10-0.20 miles
  - Balance between detail and practicality
- **Bridge/structure gaps**: Set to structure length + 0.05 miles
  - Ensures breakpoints at structure boundaries

**Practical Rule**: Set gap threshold to **2-3× your typical data point spacing**

**Example**: If you collect IRI every 0.01 miles (528 feet), set gap threshold = 0.05 miles

---

### Segment Length Constraints for Pavement Projects

**Minimum Length Considerations**:

| Factor | Typical Min Length | Rationale |
| ------ | ------------------ | --------- |
| **Maintenance Operations** | 0.3-0.5 miles | Crew setup, equipment mobilization, traffic control |
| **Pavement Design** | 0.5-1.0 miles | Design section consistency, material testing |
| **Statistical Validity** | 0.2-0.4 miles | Ensure 30-50+ data points per segment (at 0.01 mi spacing) |
| **Cost Efficiency** | 0.5-1.0 miles | Minimize per-unit costs, contractor efficiency |
| **Interstate/Freeway** | 0.5-1.0 miles | High-speed operations, lane closure constraints |
| **Urban Arterial** | 0.2-0.5 miles | Shorter blocks, more frequent intersections |
| **Rural Highway** | 1.0-2.0 miles | Longer homogeneous sections typical |

**Maximum Length Considerations**:

| Factor | Typical Max Length | Rationale |
| ------ | ------------------ | --------- |
| **Treatment Uniformity** | 2-5 miles | Practical limit for consistent pavement treatment |
| **Budget Planning** | 3-5 miles | Match typical project funding levels ($2-10M) |
| **Contractor Mobilization** | 2-4 miles | Optimal project size for competitive bidding |
| **Condition Monitoring** | 2-3 miles | Manageable section for detailed analysis |
| **Interstate Standards** | 3-5 miles | Typical resurfacing project limits |
| **Urban Constraints** | 1-3 miles | Traffic impacts, staging limitations |

---

### Must-Break Columns for Pavement Networks

**Common Attributes to Force Breakpoints**:

1. **Pavement Type** (`PAVEMENT_TYPE`)
   - Asphalt vs. concrete (completely different deterioration)
   - Composite pavements (AC over PCC)
   - **Critical**: Never span across pavement type changes

2. **Functional Class** (`FUNC_CLASS`)
   - Interstate, arterial, collector (different design standards)
   - Different traffic, maintenance priorities, user expectations

3. **Number of Lanes** (`NUM_LANES`, `LANE_WIDTH`)
   - Capacity changes affect traffic loading
   - Width changes indicate different design periods

4. **Surface Type/Treatment** (`SURF_TYPE`, `LAST_TREATMENT`)
   - Mill & overlay, chip seal, microsurfacing, slurry seal
   - Different expected performance and deterioration

5. **Drainage Class** (`DRAINAGE`, `SUBGRADE_TYPE`)
   - Good, fair, poor drainage (major performance factor)
   - Subgrade type: clay, sand, rock (affects structural capacity)

6. **Structural Section** (`BASE_TYPE`, `DESIGN_PERIOD`)
   - Full-depth asphalt vs. flexible pavement
   - Different base courses (aggregate, stabilized)

7. **Administrative** (`DISTRICT`, `COUNTY`, `JURISDICTION`)
   - Maintenance responsibility boundaries
   - Budget allocation units

**Example Configuration for State DOT**:

```text
Must-Break Columns: ["PAVEMENT_TYPE", "FUNC_CLASS", "LAST_OVERLAY_YEAR"]

Effect:
- Cannot mix asphalt and concrete sections
- Cannot mix Interstate and arterial sections  
- Cannot mix 2018 overlay with 2010 overlay sections

Result: Segments respect both physical and administrative boundaries
```

---

### Method Selection Guide for Pavement Applications

| Scenario | Primary Method | Alternative | Why |
| -------- | -------------- | ----------- | --- |
| **Network screening** (one answer needed) | Single-Objective GA | AASHTO CDA | Fast, clear priorities |
| **Project alternatives** (show options) | Multi-Objective NSGA-II | - | Visualize tradeoffs |
| **Meet standard lengths** | Constrained GA | - | Enforce requirements |
| **Research/validation** | AASHTO CDA | - | Statistical justification |
| **Compare to existing PMS** | AASHTO CDA | Single-Objective GA | Deterministic comparison |
| **Quick analysis** | Single-Objective GA | - | Fastest to converge |
| **High-detail urban** | Multi-Objective NSGA-II | Single-Objective GA | Explore fine segmentation |
| **Rural Interstate** | Single-Objective GA | Constrained GA | Straightforward optimization |
| **Grant applications** | AASHTO CDA | - | Defensible methodology |
| **Asset management** | Constrained GA | Single-Objective GA | Standardized reporting |

---

### Typical Parameter Combinations by Pavement Index

**IRI (Roughness) Data**:

- **Gap Threshold**: 0.1 miles (profiler spacing)
- **Min Length**: 0.5 miles (project minimum)
- **Max Length**: 3.0 miles (typical resurfacing)
- **Must-Break**: PAVEMENT_TYPE, MAJOR_STRUCTURE
- **Why**: IRI is continuous, reflects both structural and surface condition

**PCI (Condition Index) Data**:

- **Gap Threshold**: 0.15 miles (manual survey precision)
- **Min Length**: 0.3 miles (visual assessment sections)
- **Max Length**: 2.0 miles (treatment project size)
- **Must-Break**: PAVEMENT_TYPE, FUNC_CLASS, LAST_TREATMENT
- **Why**: PCI includes multiple distress types, more variability

**Rutting Depth Data**:

- **Gap Threshold**: 0.08 miles (automated rut measurement)
- **Min Length**: 0.5 miles (structural sections)
- **Max Length**: 2.5 miles (rehabilitation limits)
- **Must-Break**: PAVEMENT_TYPE, NUM_LANES, BASE_TYPE
- **Why**: Rutting is structural - respect design sections

**Deflection (FWD) Data**:

- **Gap Threshold**: 0.25 miles (FWD testing spacing, typically 500-1000 ft)
- **Min Length**: 0.5 miles (structural analysis sections)
- **Max Length**: 2.0 miles (rehabilitation planning)
- **Must-Break**: BASE_TYPE, PAVEMENT_TYPE, SUBGRADE_CLASS
- **Why**: Sparser data, structural focus, respect layer boundaries

---

## Data Import & Export

### Import Data Format

**Supported File Types**:

- ✅ CSV files with headers (.csv)

If your data is in Excel or TSV format, convert it to CSV before loading.

**Required Column Structure**:

```csv
milepoint,structural_strength_ind,route
196.853,2.45,US101
196.863,2.52,US101
196.873,2.38,US101
```

**Column Selection**:

- **X Column (Distance)** and **Y Column (Data Values)** must be selected from the dropdowns.
- The app intentionally does not auto-select columns when switching files (to avoid accidental mismatches).
- **Route Column (Optional)** enables multi-route processing; use **Filter** to select which route IDs to run.

**Multi-Route Support**:

- Include route identifier column for analyzing multiple highway sections
- Each route is processed and then consolidated into a single results JSON
- Route filtering available for selective analysis

### Export Formats and Contents

**📊 JSON Results File (.json)**:

```json
{
  "analysis_metadata": {
    "timestamp": "2026-04-13T13:29:18",
    "analysis_method": "aashto_cda",
    "analysis_status": "completed",
    "software_version": {"application": "Highway Segmentation", "version": "1.95.2"}
  },
  "input_parameters": {
    "optimization_method_config": {...},
    "method_parameters": {...},
    "route_processing": {...}
  },
  "route_results": [
    {
      "route_info": {"route_id": "Route_1"},
      "input_data_analysis": {
        "data_summary": {...},
        "gap_analysis": {...},
        "mandatory_segments": {...}
      },
      "processing_results": {
        "pareto_points": [
          {
            "segmentation": {
              "breakpoints": [196.853, 199.614, 201.114],
              "segment_stats": [
                {"start": 196.853, "end": 199.614, "length": 2.761, "mean": 2.45, "std": 0.12}
              ]
            }
          }
        ]
      }
    }
  ]
}
```

**📈 Excel Workbook (.xlsx)**:

- **Summary Sheet**: Key metrics and analysis overview
- **Breakpoints Sheet**: All breakpoint locations with segment information
- **Segments Sheet**: Detailed segment statistics (start, end, length, mean, std dev)
- **Parameters Sheet**: Complete analysis configuration used
- **Data Quality Sheet**: Gap analysis and validation information

If you need a simple CSV of breakpoints for GIS/tools, export to Excel or parse the JSON results file.

### File Management Best Practices

**📁 Organization**:

- Create project folders for each analysis study
- Use descriptive filenames including date and analysis type
- Keep original data files separate from results
- Archive completed analyses with documentation

**💾 Backup Strategy**:

- Save both JSON (complete) and Excel (readable) formats
- Export visualizations for presentations and reports
- Document analysis parameters and decisions
- Version control for iterative analysis projects

---

## Advanced Configuration

### Parameter Optimization Guidelines

**Population Size (Genetic Algorithms)**:

- **Small datasets** (< 1000 points): 50-100
- **Medium datasets** (1000-5000 points): 100-200  
- **Large datasets** (> 5000 points): 200-500
- **Impact**: Higher values improve solution quality but increase runtime

**Generation Count (Genetic Algorithms)**:

- **Quick analysis**: 50-100 generations
- **Standard analysis**: 100-200 generations
- **High-quality results**: 200-500 generations
- **Monitor**: Use the Optimization Log and/or the output plots to judge when the run has converged enough for your needs

**AASHTO CDA Alpha Tuning**:

- **Conservative** (fewer breakpoints): α = 0.01 (99% confidence)
- **Standard** (balanced): α = 0.05 (95% confidence) - **Recommended**
- **Sensitive** (more breakpoints): α = 0.10 (90% confidence)
- **Research**: α = 0.001 (99.9% confidence) for highest confidence

**Constraint Penalty Weights**:

- **Light enforcement**: 10-100
- **Moderate enforcement**: 100-500 (**Start here**)
- **Strong enforcement**: 500-1000
- **Signs of over-penalization**: Very poor fitness with exact constraint satisfaction

### Runtime & Resource Settings

**Cache / Memory Management**:

- **Cache Clear Interval**: Lower values for memory-constrained systems
- **Large Datasets**: Increase system RAM or reduce population size
- **Multi-Route**: Process routes individually for memory efficiency

**Diagnostic Output Strategy**:

- **Enable during development**: Understand algorithm behavior
- **Disable for production**: Cleaner, less verbose output
- **Enable for validation**: Compare with reference implementations
- **Save diagnostic JSON**: Archive detailed processing information

### Multi-Route Analysis

**Route Processing Options**:

- **Combined Analysis**: All routes in single optimization (genetic algorithms)
- **Independent Analysis**: Each route optimized separately (AASHTO CDA)
- **Comparative Analysis**: Run same method on multiple routes for comparison

**Route Selection**:

- Filter specific routes for targeted analysis
- Compare results across similar highway types
- Identify routes requiring different parameter settings

---

## Troubleshooting

### Pavement Data Specific Issues

**❌ "Segments Don't Match Field Observations"**:

- **Diagnosis**: Algorithm breakpoints don't align with known pavement features
- **Possible Causes**:
  - Must-Break Columns not capturing treatment boundaries
  - Data is outdated and doesn't reflect recent rehabilitation
  - Gap threshold too large, spanning structures or transitions
  - Data quality issues (outliers, sensor errors) misleading algorithm
- **Solutions**:
  - Add "LAST_TREATMENT_YEAR" or "OVERLAY_DATE" to Must-Break Columns
  - Verify data currency - when was it collected vs. when was construction?
  - Reduce gap threshold to 0.05-0.08 miles for sensitive detection
  - Plot raw data - look for obvious outliers or equipment issues
  - Field visit to validate actual pavement condition

**❌ "Too Many Short Segments on Good Pavement"**:

- **Diagnosis**: Algorithm creating micro-segments (< 0.3 mi) where pavement appears uniform
- **Possible Causes**:
  - Algorithm oversensitive to normal data variation/noise
  - High-precision equipment detecting real but minor variations
  - Data collection equipment calibration changed mid-survey
- **Solutions**:
  - Increase min_length to 0.5-1.0 miles (practical project minimum)
  - Use AASHTO CDA with lower α (e.g., 0.01) for more conservative detection
  - Check if newer equipment has higher precision than historical data
  - Consider if micro-segments align with real features (patches, joints)
  - Review data collection report for equipment/procedure changes

**❌ "Missing Known Treatment Boundaries"**:

- **Diagnosis**: Recent overlay limit not detected as breakpoint
- **Possible Causes**:
  - Treatment boundary not yet evident in selected condition index
  - New pavement still performing like old (immediate post-construction)
  - Data collected before treatment was completed
- **Solutions**:
  - Add "CONSTRUCTION_YEAR" column as Must-Break attribute
  - Manually add breakpoint at known project limit
  - Wait 6-12 months for performance difference to emerge
  - Use different index (IRI changes faster than cracking)
- **Note**: Similar condition across treatment boundary is OK if treatments are performing well!

**❌ "Breakpoint at Every Bridge"**:

- **Diagnosis**: Algorithm placing breakpoints at each bridge approach
- **Possible Causes**:
  - Gap threshold too sensitive to bridge data gaps
  - Bridge approach slabs actually different from mainline
  - GPS positioning errors near overpasses
- **Solutions**:
  - Increase gap threshold to 0.2-0.3 miles (span short bridges)
  - Pre-process data to interpolate over short structures (< 0.1 mi)
  - Add "BRIDGE_ID" column, filter out approach data
  - Consider: May actually want breaks at major river crossings (different maintenance)
  - Decision: Small bridges - span them; major structures - break there

**❌ "Results Vary Between Multiple Runs" (Genetic Algorithm methods)**:

- **Diagnosis**: Running same data/parameters gives slightly different results
- **Expected Behavior**: Genetic algorithms include randomness by design
- **Typical Impact**: Minor differences in breakpoint locations (usually < 0.2 miles)
- **Solutions**:
  - Increase generations (200-300) for better convergence
  - Run 3-5 times, look for consistent major breakpoints
  - Use AASHTO CDA if deterministic results required (research, legal)
  - Accept minor variation - focus on major trends
- **Best Practice**: Run multiple times, validate consistent breakpoints against field knowledge

**❌ "IRI Shows Breakpoint, But Cracking Data Doesn't"**:

- **Diagnosis**: Different indices showing different segmentation
- **Explanation**: Normal! Different distress types progress differently
  - IRI: Responds to roughness (structural + surface)
  - Cracking: Surface distress only
  - Rutting: Structural loading response
- **Approach**:
  - Choose index matching your treatment decision (surface vs. structural)
  - For comprehensive analysis, run segmentation on multiple indices
  - Overlay results to identify sections needing different treatment types
  - Example: High IRI + low cracking → structural issue (milling won't help)

---

### Common Data Issues

**❌ "No data loaded" Error**:

- **Check File Path**: Ensure CSV file exists and is accessible
- **Verify File Format**: Headers required, check for encoding issues
- **Column Selection**: Ensure **X Column (Distance)** and **Y Column (Data Values)** are selected
- **Data Validation**: Ensure numeric data in measurement columns

**❌ "Insufficient Data Points" Warning**:

- **Minimum Requirements**: At least 10 points per expected segment
- **Gap Analysis**: Large gaps may fragment data into small sections
- **Parameter Adjustment**: Reduce minimum segment length or increase gap threshold
- **Data Quality**: Check for excessive missing values

**❌ "No Valid Segments Found" Error**:

- **Length Constraints**: Min/max length settings may be too restrictive
- **Gap Threshold**: Too small values create excessive mandatory breakpoints
- **Data Range**: Verify milepoint values span reasonable distance
- **Parameter Relaxation**: Increase max length or decrease min length

**❌ "No Valid Routes" / route column error**:

- **Cause**: In multi-route mode, the selected route column contains only missing route IDs (blank/empty).
- **Fix**: Choose a different route column, or select **None - treat as single route**.

### Analysis Problems

**❌ Genetic Algorithm Not Converging**:

- **Increase Generations**: More iterations often improve results
- **Adjust Population Size**: Larger populations explore solution space better
- **Check Constraints**: Overly restrictive constraints may prevent convergence
- **Parameter Tuning**: Try different mutation/crossover rates

**❌ Constrained Method Not Satisfying Constraint**:

- **Increase Penalty Weight**: Higher values enforce constraints more strongly
- **Relax Tolerance**: Wider acceptable range may enable satisfaction
- **Check Feasibility**: Ensure target length is achievable with your data
- **Parameter Adjustment**: Modify min/max length constraints

**❌ AASHTO CDA Finding No Breakpoints**:

- **Reduce Alpha**: More sensitive detection (try α = 0.10)
- **Check Data Variation**: Uniform data may not have detectable change points
- **Min Section Difference**: Reduce threshold for detecting section differences
- **Diagnostic Output**: Enable to understand algorithm decision process

### Runtime Issues

**❌ Analysis Taking Too Long**:

- **Reduce Population Size**: Linear impact on processing time
- **Decrease Generations**: Stop when convergence achieved
- **Simplify Data**: Consider data subsampling for initial analysis
- **Optimization Method**: Use Single-Objective if you only need a single recommended solution

**❌ Memory Errors**:

- **Reduce Cache Clear Interval**: More frequent memory cleanup
- **Smaller Population**: Linear impact on memory usage
- **Data Segmentation**: Process large datasets in smaller sections
- **System Resources**: Close other applications, increase virtual memory

**❌ Results Not Saving**:

- **File Permissions**: Ensure write access to save directory
- **Disk Space**: Verify sufficient storage for result files
- **File Path Length**: Avoid excessively long paths/filenames
- **Special Characters**: Use standard alphanumeric filenames

### Interface Issues

**❌ Help Window Not Opening**:

- **File Location**: Ensure USER_GUIDE.md exists in project directory
- **Encoding Issues**: Check file is UTF-8 encoded
- **Markdown Support**: Install markdown package for enhanced display
- **Fallback Display**: Plain text view should work without markdown

**❌ Visualization Not Displaying**:

- **Matplotlib Installation**: Verify required plotting libraries
- **Result Data**: Ensure analysis completed successfully
- **Memory Issues**: Close other applications if visualization fails
- **Export Alternative**: Save plots to files if display fails

**❌ Settings Not Persisting**:

- **Where settings are stored**: The app writes a local `app_settings.json` file next to the application code.
- **File Permissions**: Ensure the application directory is writable (especially on macOS/Linux if installed under protected folders)
- **JSON Format**: Settings file may be corrupted - delete `app_settings.json` and restart
- **Default Restoration**: Application creates new settings file automatically
- **Manual Configuration**: Re-enter critical settings after reset

### Getting Help

**📚 Additional Resources**:

- **Technical Documentation**: Review architecture and extensibility sections
- **Example Data**: Use provided test datasets to verify installation
- **Parameter Guides**: Consult method-specific parameter recommendations
- **Community Support**: Engage with other users for application tips

**🐛 Reporting Issues**:

- **Include Version Information**: Note software version and system details
- **Provide Data Context**: Describe dataset characteristics and analysis goals
- **Attach Configuration**: Export settings file with issue reports
- **Error Messages**: Copy complete error text and diagnostic output
- **Reproducible Examples**: Minimal test cases help diagnose problems

**🔧 Advanced Troubleshooting**:

- **Log Files**: Enable diagnostic output for detailed processing information
- **Parameter Experimentation**: Systematic testing to isolate issues
- **Method Comparison**: Cross-validate results using different analysis approaches
- **Data Preprocessing**: Clean and validate data before analysis
- **Profiling**: Use the Optimization Log output and diagnostics to identify bottlenecks

---

## Technical Reference

### Algorithm Details

**Genetic Algorithm Implementation**:

- **Selection**: Tournament selection with configurable pressure
- **Crossover**: Uniform crossover with boundary constraints
- **Mutation**: Gaussian perturbation with adaptive scaling
- **Elite Preservation**: Top solutions maintained across generations
- **Constraint Handling**: Penalty functions for length and feasibility constraints

**NSGA-II Multi-Objective**:

- **Dominance**: Pareto dominance with crowding distance calculation
- **Diversity**: Crowding distance maintains solution spread
- **Archive**: External archive for non-dominated solutions
- **Objectives**: Total deviation vs. average segment length

**AASHTO CDA Statistical Method**:

- **Algorithm**: Enhanced Cumulative Difference Approach
- **Change Point Detection**: Statistical significance testing for breakpoints
- **Error Estimation**: Multiple methods for measurement error characterization
- **Segmented Processing**: Independent analysis of data sections between gaps

### Data Structures

**RouteAnalysis Object**:

- Standardized data container for all analysis methods
- Automatic gap detection and mandatory breakpoint generation
- Validation and quality checking functionality
- Multi-route support with individual route processing

**AnalysisResult Object**:

- Universal result format across all analysis methods
- Pareto front storage for multi-objective results
- Statistical metadata and processing information
- Extensible structure for new method integration

### Configuration System

**Parameter Definition Classes**:

- **NumericParameter**: Standard numeric inputs with validation
- **OptionalNumericParameter**: Nullable numeric values (e.g., unlimited max segments)
- **SelectParameter**: Dropdown selections with predefined options
- **BoolParameter**: Boolean checkboxes for feature toggles
- **TextParameter**: String inputs with validation rules

**Dynamic UI Generation**:

- Automatic widget creation from parameter definitions
- Method-specific parameter visibility and organization
- Real-time validation and error messaging
- Persistent settings with automatic save/restore

### Extension Architecture

**Adding New Analysis Methods**:

1. **Create Method Class**: Extend AnalysisMethodBase
2. **Define Parameters**: Create parameter list in config.py
3. **Register Method**: Add to OPTIMIZATION_METHODS configuration
4. **Implement Interface**: Provide run_analysis() method
5. **Integration**: Method automatically appears in UI

**Parameter Extension**:

- Define new parameter types by extending ParameterDefinition
- Implement widget creation and value handling methods
- Add parameter validation and constraint checking
- Register in appropriate method parameter lists

**Export Format Enhancement**:

- Extend ExtensibleJsonResultsManager for new result types
- Add plugin system for custom result processing
- Implement new visualization types for method-specific displays
- Maintain backward compatibility with existing formats

### Method Characteristics

**Method Comparison**:

| Method | Deterministic | Multi-Solution | Statistical |
| --- | --- | --- | --- |
| Single-Objective GA | No | No | No |
| Multi-Objective NSGA-II | No | Yes | No |
| Constrained GA | No | No | No |
| AASHTO CDA | Yes | No | Yes |

### Quality Assurance

**Validation Approaches**:

- **Cross-Method Validation**: Compare results across different analysis approaches  
- **Statistical Testing**: Use AASHTO CDA for statistically-justified breakpoints
- **Parameter Sensitivity**: Test robustness to parameter variations
- **Reference Comparison**: Validate against published methods and implementations

**Testing Framework**:

- **Unit Tests**: Individual component validation
- **Integration Tests**: Full workflow testing with sample data
- **Regression Tests**: Ensure updates don't break existing functionality

*This user guide covers the complete functionality of the Highway Segmentation Analysis application. For technical support, feature requests, or questions about extending the application, refer to the project documentation or contact the development team.*
