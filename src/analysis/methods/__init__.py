"""
Analysis Methods Package

Individual analysis method implementations following the AnalysisMethodBase interface.
Each method is implemented in a separate module for maintainability and extensibility.

Core Methods:
- single_objective: Fast single-objective genetic algorithm optimization
- multi_objective: NSGA-II multi-objective Pareto front optimization  
- constrained: Penalty-based constrained single-objective optimization

All methods implement the standard AnalysisMethodBase interface:
- run_analysis(): Core optimization execution
- method_name: Human-readable name for GUI display
- method_key: Method identifier for results handling

Future methods can be added by implementing the same interface pattern.
"""

__version__ = "1.95.0"

# Import available analysis methods
from .single_objective import SingleObjectiveMethod
from .multi_objective import MultiObjectiveMethod
from .constrained import ConstrainedMethod
from .deb_feasibility_constrained import DebFeasibilityConstrainedMethod

__all__ = [
    'SingleObjectiveMethod',
    'MultiObjectiveMethod',
    'ConstrainedMethod',
    'DebFeasibilityConstrainedMethod',
]

# Available methods for easy access
AVAILABLE_METHODS = {
    'single': SingleObjectiveMethod,
    'multi': MultiObjectiveMethod,
    'constrained': ConstrainedMethod,
    'constrained_deb': DebFeasibilityConstrainedMethod,
}