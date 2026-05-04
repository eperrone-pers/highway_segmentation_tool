# Highway Segmentation Analysis - User Guide

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [User Interface Guide](#user-interface-guide)
4. [Common Tasks](#common-tasks)
5. [Analysis Methods](#analysis-methods)
6. [Basic Workflow](#basic-workflow)
7. [Understanding Results](#understanding-results)
8. [Data Import & Export](#data-import--export)
9. [Advanced Configuration](#advanced-configuration)
10. [Troubleshooting](#troubleshooting)
11. [Technical Reference](#technical-reference)

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

## Getting Started

### Installation

1. **Extract Application**: Unzip all files to your desired installation directory
2. **Install Dependencies**: Run `pip install -r requirements.txt` from the project directory
3. **Launch Application**: Execute `python src/gui_main.py` or run the provided batch/shell script
4. **Verify Installation**: The GUI should open and show the main window with the **Optimization Log** tab

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
  - In multi-route mode, rows with missing/invalid route IDs (blank/`none`/`null`/`nan`) are excluded from analysis and this is logged.
    If all rows are missing/invalid for the selected route column, the run is blocked with an error.
- **Gap Threshold (miles)**: Framework parameter used by all methods; gaps larger than this force mandatory breakpoints.
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

- Note: If the selected route column contains missing/invalid route IDs (blank/`none`/`null`/`nan`), those rows are excluded from analysis.
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

**🔴 Red Breakpoints (Mandatory)**:

- **Origin**: Data gaps exceeding the Gap Threshold
- **Purpose**: Prevent segments from spanning data discontinuities  
- **Properties**: Cannot be moved by optimization algorithms
- **Identification**: Appear at exact boundaries of data gaps

**🟢 Green Breakpoints (Optimized)**:

- **Origin**: Placed by analysis algorithms for optimal segmentation
- **Purpose**: Define boundaries that minimize within-segment variation
- **Properties**: Algorithm-determined locations for best segmentation quality
- **Identification**: Positioned at statistically/algorithmically optimal points

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

- **Cause**: In multi-route mode, the selected route column contains only missing/invalid route IDs (blank/`none`/`null`/`nan`).
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
