# Highway Segmentation Analysis - User Guide

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [User Interface Guide](#user-interface-guide)
4. [Analysis Methods](#analysis-methods)
5. [Basic Workflow](#basic-workflow)
6. [Understanding Results](#understanding-results)
7. [Data Import & Export](#data-import--export)
8. [Advanced Configuration](#advanced-configuration)
9. [Troubleshooting](#troubleshooting)
10. [Technical Reference](#technical-reference)

---

## Overview

The Highway Segmentation Analysis application provides advanced statistical and optimization-based methods for dividing highway data into optimal segments for pavement analysis. The system offers four distinct analysis approaches, from traditional genetic algorithms to statistical change point detection methods.

### Key Features

- **🧬 Multiple Analysis Methods**: Genetic algorithms (single/multi-objective, constrained) and statistical AASHTO CDA analysis
- **📊 Smart Data Handling**: Automatic gap detection with mandatory breakpoint insertion
- **🎯 Flexible Optimization**: Configure parameters for your specific analysis requirements  
- **📈 Interactive Visualization**: Click-to-explore results with detailed segment information
- **💾 Comprehensive Export**: JSON, Excel, and CSV outputs with complete analysis metadata
- **⚙️ Persistent Settings**: Your preferences are automatically saved between sessions
- **🔧 Extensible Architecture**: Easy addition of new analysis methods and parameters

### Supported Analysis Approaches

1. **Single-Objective Genetic Algorithm**: Traditional optimization minimizing segment variation
2. **Multi-Objective NSGA-II**: Pareto front exploration of quality vs. segment length tradeoffs
3. **Constrained Optimization**: Target-length segmentation with penalty enforcement
4. **AASHTO Enhanced CDA**: Statistical change point detection with Bonferroni correction

---

## Getting Started

### System Requirements

- **Operating System**: Windows 10+, macOS 10.14+, or Linux
- **Python**: Version 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB+ recommended for large datasets)
- **Storage**: 100MB free space plus data storage requirements

### Installation

1. **Extract Application**: Unzip all files to your desired installation directory
2. **Install Dependencies**: Run `pip install -r requirements.txt` from the project directory
3. **Launch Application**: Execute `python src/gui_main.py` or run the provided batch/shell script
4. **Verify Installation**: The GUI should open and display "Ready" in the status bar

### Quick Start

1. Click **📁 Browse Data File** and select a CSV file with milepoint and measurement columns
2. Choose your analysis method from the **Method Selection** dropdown
3. Adjust parameters as needed (defaults work well for most cases)
4. Click **🚀 Run Analysis** to begin processing
5. Review results in the **📈 Visualization** and **📋 Summary** tabs
6. Export your results using **💾 Save Results**

---

## User Interface Guide

The interface is split into two main panels with organized sections for efficient workflow:

### Left Panel - Configuration & Control

#### 📊 **Data Import Section**

- **Data File Path**: Shows currently loaded file with validation status
- **📁 Browse Data File**: Select CSV files from your filesystem
- **Column Mapping**:
  - **X Column**: Milepoint/chainage data (auto-detected: "milepoint", "chainage", "location") 
  - **Y Column**: Measurement values (auto-detected: "structural_strength_ind", "value", "measurement")
  - **Route Column**: Optional multi-route support (auto-detected: "route", "RDB", "section")
- **🔄 Reload Data**: Refresh data with new column selections

#### ⚙️ **Analysis Parameters**

**Universal Parameters** (all methods):
- **Minimum Segment Length**: Shortest allowed segment in miles (default: 0.5)
- **Maximum Segment Length**: Longest allowed segment in miles (default: 10.0) 
- **Gap Threshold**: Distance triggering mandatory breakpoints (default: 0.5)

**Genetic Algorithm Parameters** (Single, Multi-Objective, Constrained):
- **Population Size**: Solutions per generation (default: 100)
- **Number of Generations**: Optimization iterations (default: 100) 
- **Mutation Rate**: Random change probability (default: 0.05)
- **Crossover Rate**: Solution mixing probability (default: 0.8)
- **Elite Ratio**: Top solutions preserved (default: 0.05)

**Constrained Method Parameters**:
- **Target Avg Length**: Desired average segment length in miles
- **Length Tolerance**: Acceptable deviation from target (±miles)
- **Penalty Weight**: Constraint enforcement strength (1-1000)

**AASHTO CDA Parameters**:
- **Alpha (α)**: Statistical significance level (default: 0.05, range: 0.001-0.49)
- **Error Estimation Method**: 
  - Method 1: MAD with Normal Distribution
  - Method 2: Std Dev of Differences (**Recommended**)
  - Method 3: Std Dev of Measurements
- **Use Segment Length**: Apply segment-length-specific analysis (recommended: Yes)
- **Min Segment Datapoints**: Minimum points per segment (default: 1)
- **Max Segments**: Maximum segments allowed (default: None = unlimited)
- **Min Section Difference**: Minimum mean difference between adjacent segments (default: 0.0)
- **Diagnostic Output**: Enable detailed processing information (default: No)

#### 🔬 **Method Selection**

Choose from four analysis approaches:

1. **Single-Objective GA**: Best for straightforward segmentation minimizing variation
2. **Multi-Objective NSGA-II**: Best for exploring quality vs. segment length tradeoffs  
3. **Constrained Single-Objective**: Best when targeting specific average segment lengths
4. **AASHTO CDA Statistical Analysis**: Best for statistically-justified, deterministic segmentation

#### 🔧 **Performance Settings**
- **Cache Clear Interval**: Optimization memory management (default: 50)
- **Enable Performance Stats**: Show detailed timing information
- **Custom Save Name**: Base filename for result exports

### Right Panel - Execution & Results

#### 🚀 **Action Buttons**
- **🚀 Run Analysis**: Execute the selected method with current parameters
- **📁 Load & Plot Results**: Import previously saved JSON results
- **❓ Help**: Open this comprehensive user guide  
- **❌ Exit**: Close application (with confirmation)

#### 📈 **Results Visualization**
- **Interactive Plots**: Click points to explore solutions
- **Method-Specific Views**: Tailored displays for each analysis type
- **Zoom & Pan**: Standard matplotlib navigation tools
- **Export Options**: Save plots as PNG/SVG files

#### 📋 **Analysis Summary**
- **Key Metrics**: Segment counts, fitness values, constraint satisfaction
- **Processing Details**: Algorithm parameters, execution time, data statistics
- **Validation Information**: Data quality checks and gap analysis results

---

## Analysis Methods

### Single-Objective Genetic Algorithm

**🎯 Purpose**: Find the single best segmentation minimizing within-segment variation.

**🔧 Best Used For**:
- Standard segmentation tasks where homogeneity is the primary goal
- When you need one clear segmentation recommendation
- Baseline comparisons with other methods
- Quick analysis of data characteristics

**📊 Results**:
- One optimal segmentation solution
- Clear visualization with color-coded segments
- Detailed fitness and segment length information

**⚡ Performance**: Fastest method for single-solution requirements

---

### Multi-Objective NSGA-II Optimization

**🎯 Purpose**: Discover the complete range of optimal tradeoffs between segment homogeneity and segment length.

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

**🔧 Best Used For**:
- Research requiring statistical validation of breakpoints
- Regulatory compliance needing documented methodology
- Comparison with established MATLAB/SAS implementations
- When deterministic (non-random) results are required
- Validation of genetic algorithm results

**📊 Statistical Approach**:
- **Change Point Detection**: Identifies statistically significant breakpoints
- **Bonferroni Correction**: Controls family-wise error rate for multiple testing
- **Segmented Processing**: Analyzes sections between mandatory breakpoints independently
- **Deterministic Results**: Same input always produces same output (no randomness)

**⚙️ Key Parameters**:

**Alpha (α) - Statistical Significance**:
- **Purpose**: Controls false positive rate for breakpoint detection
- **Range**: 0.001 to 0.49 (default: 0.05 = 95% confidence)
- **Lower values**: More conservative, fewer breakpoints, higher confidence
- **Higher values**: More sensitive, more breakpoints, lower confidence

**Error Estimation Method**:
- **Method 1**: MAD with Normal Distribution - Robust to outliers
- **Method 2**: Standard Deviation of Differences - **Recommended** for highway data
- **Method 3**: Standard Deviation of Measurements - Traditional approach

**Max Segments**:
- **None (Unlimited)**: Let algorithm find optimal number (**Recommended**)
- **Specific Number**: Limit maximum segments per section (use only if required)

**Diagnostic Output**:
- **Enabled**: Provides detailed console output and enhanced JSON diagnostics
- **Disabled**: Clean processing with standard results only

**📊 Results**:
- **Deterministic Segmentation**: Statistically-justified breakpoint locations
- **Statistical Validation**: Each breakpoint supported by significance testing
- **Section-by-Section Analysis**: Detailed processing information per data section
- **Comprehensive Diagnostics**: Algorithm parameters, processing summary, section details

**🎨 Diagnostic Information (when enabled)**:
```
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

1. **Import Data**: Use 📁 Browse Data File to select your CSV
2. **Verify Columns**: Check that X/Y columns are correctly identified
3. **Choose Method**: Select analysis approach based on your requirements
4. **Adjust Parameters**: Modify defaults based on your data characteristics
5. **Set Output Location**: Configure save path and custom filename

### Step 3: Execute Analysis

1. **Review Configuration**: Verify all settings meet your requirements
2. **Run Analysis**: Click 🚀 Run Analysis and monitor progress
3. **Check Status**: Watch status bar for completion and any warnings
4. **Review Results**: Examine visualization and summary information

### Step 4: Interpret and Export

1. **Understand Results**: Use method-specific guidance for interpretation
2. **Explore Solutions**: For multi-objective, examine different Pareto front points
3. **Validate Output**: Check that breakpoints make physical/practical sense
4. **Export Results**: Save JSON, Excel, and visualization files as needed

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
- **Properties**: Algorithm-determined locations for best performance
- **Identification**: Positioned at statistically/algorithmically optimal points

### Key Performance Metrics

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
- **Bonferroni Correction**: Adjusts for multiple testing across data sections
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
- ✅ Tab-delimited text files (.txt, .tsv)
- ✅ Excel files (.xls, .xlsx) - first sheet only

**Required Column Structure**:
```csv
milepoint,structural_strength_ind,route
196.853,2.45,US101
196.863,2.52,US101
196.873,2.38,US101
```

**Column Detection**:
- **X Column (Milepoint)**: Auto-detected names: "milepoint", "chainage", "location", "mile", "station"
- **Y Column (Measurement)**: Auto-detected names: "structural_strength_ind", "value", "measurement", "data"  
- **Route Column**: Auto-detected names: "route", "RDB", "section", "highway"

**Multi-Route Support**:
- Include route identifier column for analyzing multiple highway sections
- Each route processed independently with combined results
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

**📋 CSV Breakpoints (.csv)**:
- Simple format for integration with other tools
- Columns: RouteID, BreakpointMile, SegmentStart, SegmentEnd, SegmentLength
- Compatible with GIS and mapping software

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
- **Monitor**: Use performance stats to find convergence point

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

### Performance Optimization

**Memory Management**:
- **Cache Clear Interval**: Lower values for memory-constrained systems
- **Large Datasets**: Increase system RAM or reduce population size
- **Multi-Route**: Process routes individually for memory efficiency

**Processing Speed**:
- **Single-Objective**: Fastest method for single solutions
- **AASHTO CDA**: Fast, deterministic processing
- **Multi-Objective**: Moderate speed, explores full solution space
- **Constrained**: Slower due to penalty function evaluation

**Diagnostic Output Strategy**:
- **Enable during development**: Understand algorithm behavior
- **Disable for production**: Clean output and faster processing  
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
- **Column Detection**: Manually specify X/Y columns if auto-detection fails
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

### Performance Issues

**❌ Analysis Taking Too Long**:
- **Reduce Population Size**: Linear impact on processing time
- **Decrease Generations**: Stop when convergence achieved
- **Simplify Data**: Consider data subsampling for initial analysis
- **Method Selection**: Use Single-Objective for faster results

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
- **File Permissions**: Check write access to application directory
- **JSON Format**: Settings file may be corrupted - delete and restart
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
- **Performance Profiling**: Use performance stats to identify bottlenecks

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
- **Bonferroni Correction**: Family-wise error rate control for multiple comparisons

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

### Performance Characteristics

**Method Comparison**:

| Method | Speed | Memory | Deterministic | Multi-Solution | Statistical |
|--------|-------|--------|---------------|----------------|-------------|
| Single-Objective GA | Fast | Moderate | No | No | No |
| Multi-Objective NSGA-II | Moderate | High | No | Yes | No |
| Constrained GA | Slow | Moderate | No | No | No |
| AASHTO CDA | Fast | Low | Yes | No | Yes |

**Scalability Guidelines**:
- **Small datasets** (< 1000 points): All methods perform well
- **Medium datasets** (1000-5000 points): Optimize GA parameters
- **Large datasets** (> 5000 points): Consider AASHTO CDA or reduced GA populations
- **Multi-route datasets**: Process routes independently when possible

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
- **Performance Tests**: Monitor execution time and memory usage

*This user guide covers the complete functionality of the Highway Segmentation Analysis application. For technical support, feature requests, or questions about extending the application, refer to the project documentation or contact the development team.*
