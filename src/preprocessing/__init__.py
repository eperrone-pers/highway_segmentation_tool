"""
Preprocessing Framework

This module provides an extensible framework for preprocessing route data
before analysis. Preprocessing methods can perform operations like outlier
detection, data smoothing, and normalization.

Key Components:
- PreprocessingMethodBase: Abstract base class for all preprocessing methods
- PreprocessingResult: Result container with modification log
- DataModificationContext: Framework-controlled data modification API
- DataModification: Individual modification record

Design Philosophy:
- Algorithm implementation = black box (developer's choice)
- Data modification = controlled API (framework enforced)
- All modifications automatically logged for traceability
"""

from preprocessing.base import (
    DataModification,
    DataModificationContext,
    PreprocessingResult,
    PreprocessingMethodBase,
)

__all__ = [
    "DataModification",
    "DataModificationContext",
    "PreprocessingResult",
    "PreprocessingMethodBase",
]
