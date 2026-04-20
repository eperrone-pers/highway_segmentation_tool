"""
Highway Segmentation Analysis Package

Extensible framework for optimization analysis methods supporting multiple
highway route processing with standardized interfaces and shared utilities.

This package provides:
- Base interfaces for analysis method development
- Shared genetic algorithm utilities
- Registry system for method discovery
- Standardized result structures
- Support for single-objective, multi-objective, and constrained optimization

Architecture:
- analysis.base: AnalysisMethodBase interface
- analysis.methods: Individual analysis method implementations  
- analysis.utils: Shared utilities (GA functions, validation)
- analysis.results: Result structures and formatting
- analysis.registry: Method discovery and management

Usage:
    from analysis import analysis_registry
    from analysis.methods.single_objective import SingleObjectiveAnalysis
    
    # Get method from registry
    method = analysis_registry.get_method('single')
    result = method.run_analysis(data, x_column, y_column, min_length, max_length)

Author: Highway Segmentation GA Team
Phase: 1.95 - Analysis Methods Extraction & Extensible Framework
"""

# Package version for compatibility tracking
__version__ = "1.95.0"
__author__ = "Highway Segmentation GA Team"  

# Public API will be populated as we implement the methods
# This will be updated in subsequent steps
__all__ = [
    # Will include: 'analysis_registry', 'SingleObjectiveAnalysis', etc.
]

# TODO: Import statements will be added as we create the modules
# from .registry import analysis_registry
# from .methods.single_objective import SingleObjectiveAnalysis
# from .methods.multi_objective import MultiObjectiveAnalysis  
# from .methods.constrained import ConstrainedAnalysis