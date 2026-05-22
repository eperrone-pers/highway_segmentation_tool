"""
Preprocessing Methods

This module contains concrete implementations of preprocessing methods.
Each method extends PreprocessingMethodBase and implements specific preprocessing logic.

Available Methods:
- Tukey Fences: Outlier detection and handling using Interquartile Range (IQR) method
"""

from preprocessing.methods.tukey_fences import TukeyFencesPreprocessor

__all__ = [
    "TukeyFencesPreprocessor",
]
