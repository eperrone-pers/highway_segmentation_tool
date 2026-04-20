"""
Analysis Utilities Package

Shared utilities for genetic algorithm implementations and analysis methods.
Contains common functions used across multiple optimization approaches.

Modules:
- ga_utilities: Core genetic algorithm operations (selection, crossover, mutation)
- validation: Parameter validation and constraint checking utilities

These utilities are designed to be method-agnostic and support extensibility
for future analysis method implementations.
"""

__version__ = "1.95.0"

# Import GA utilities functions
from .ga_utilities import (
    tournament_selection,
    nsga2_tournament_selection, 
    nsga2_compare,
    crossover_with_retries,
    perform_single_crossover,
    mutation_with_retries,
    perform_single_mutation,
    fast_non_dominated_sort,
    dominates,
    calculate_crowding_distance,
    analyze_population_diversity,
    batch_fitness_evaluation,
    batch_multi_objective_fitness
)

# TODO: Imports will be added as we implement more utility modules
# from .validation import ParameterValidator

__all__ = [
    # Will include: 'GAUtilities', 'ParameterValidator', etc.
]