"""
Highway Segmentation Analysis Package

Extensible framework for optimization analysis methods supporting multiple
highway route processing with standardized interfaces and shared utilities.

This package provides:
- Base interfaces for analysis method development
- Shared genetic algorithm utilities
- Support for single-objective, multi-objective, and constrained optimization

Architecture:
- analysis.base: AnalysisMethodBase interface
- analysis.methods: Individual analysis method implementations
- analysis.utils: Shared utilities (GA functions)

Usage:
    from analysis.methods.single_objective import SingleObjectiveMethod
    result = SingleObjectiveMethod().run_analysis(route_analysis, x_column, y_column, **params)

Author: Highway Segmentation GA Team
Phase: 1.95 - Analysis Methods Extraction
"""

# Package version for compatibility tracking
__version__ = "1.95.0"
__author__ = "Highway Segmentation GA Team"  

__all__ = []