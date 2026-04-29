#!/usr/bin/env python3
"""
Integration tests for analysis method objective function usage.

These tests verify that each analysis method (SingleObjectiveMethod, MultiObjectiveMethod, 
ConstrainedMethod) correctly uses the genetic algorithm objective functions and processes
the results with correct mathematical interpretations.

CRITICAL PURPOSE: Prevent regressions where GA calculates correct values but analysis 
methods interpret or process them incorrectly, leading to wrong optimization behavior.
"""

import pytest
import sys
import os
import numpy as np
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
import tempfile

# Add src to path for imports
current_dir = os.path.dirname(__file__)
tests_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(tests_dir)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from analysis.methods.single_objective import SingleObjectiveMethod
    from analysis.methods.multi_objective import MultiObjectiveMethod
    from analysis.methods.constrained import ConstrainedMethod
    from analysis.utils.genetic_algorithm import HighwaySegmentGA
    from data_loader import analyze_route_gaps
except ImportError as e:
    pytest.skip(f"Required analysis modules not available: {e}", allow_module_level=True)


class TestAnalysisMethodObjectiveUsage:
    """Test that analysis methods correctly use GA objective functions."""
    
    @pytest.fixture
    def sample_route_data(self):
        """Generate consistent test route data."""
        np.random.seed(42)
        x_values = np.linspace(0, 10, 50)
        y_values = np.random.normal(2.0, 0.3, 50)
        
        # Create DataFrame and then RouteAnalysis (required contract)
        route_df = pd.DataFrame({
            'BDFO': x_values,
            'SCI': y_values
        })

        route_analysis = analyze_route_gaps(
            route_df,
            x_column='BDFO',
            y_column='SCI',
            route_id='test_route_001',
            gap_threshold=0.3,
        )
        
        return {
            'route_analysis': route_analysis,
            'x_column': 'BDFO',
            'y_column': 'SCI',
            'route_id': 'test_route_001'
        }
    
    @pytest.fixture
    def basic_params(self):
        """Standard parameters for all methods using existing API."""
        return {
            'min_length': 0.5,
            'max_length': 3.0,
            'population_size': 20,
            'num_generations': 5,  # Small for testing
            'mutation_rate': 0.05,
            'crossover_rate': 0.8,
            'gap_threshold': 0.3
        }


class TestSingleObjectiveMethodCorrectness(TestAnalysisMethodObjectiveUsage):
    """Test SingleObjectiveMethod uses GA fitness correctly."""
    
    def test_single_objective_method_processes_negative_fitness(self, sample_route_data, basic_params):
        """
        CRITICAL: SingleObjectiveMethod should correctly handle negative fitness values from GA.
        Verify method recognizes that more negative = better solution.
        """
        method = SingleObjectiveMethod()
        
        # Run analysis using existing run_analysis interface
        params = dict(basic_params)
        gap_threshold = params.pop('gap_threshold')
        result = method.run_analysis(
            data=sample_route_data['route_analysis'],
            route_id=sample_route_data['route_id'],
            x_column=sample_route_data['x_column'],
            y_column=sample_route_data['y_column'],
            gap_threshold=gap_threshold,
            **params,
        )
        
        # Verify result structure
        assert result is not None, "Analysis should return a result"
        assert hasattr(result, 'all_solutions'), "Result should have all_solutions"
        assert len(result.all_solutions) > 0, "Should have at least one solution"
        
        best_solution = result.best_solution
        
        # CRITICAL: Fitness should be negative (deviation-based, lower is better)
        fitness = best_solution.get('fitness')
        assert fitness is not None, "Best solution should have fitness value"
        assert fitness < 0, f"SingleObjective fitness should be negative (deviation-based), got {fitness}"
        
        # Verify objective_values field exists for unified export
        objective_values = best_solution.get('objective_values')
        assert objective_values is not None, "Solution should have objective_values for unified export"
        assert len(objective_values) >= 1, "Single-objective should have at least 1 objective value"
        assert objective_values[0] < 0, f"Primary objective should be negative: {objective_values[0]}"
    
    def test_single_objective_solution_quality_interpretation(self, sample_route_data, basic_params):
        """
        REGRESSION TEST: Verify SingleObjectiveMethod correctly identifies better solutions.
        Higher fitness = better solution (less deviation, closer to 0).
        """
        method = SingleObjectiveMethod()
        
        # Run analysis using existing interface
        params = dict(basic_params)
        gap_threshold = params.pop('gap_threshold')
        result = method.run_analysis(
            data=sample_route_data['route_analysis'],
            route_id=sample_route_data['route_id'],
            x_column=sample_route_data['x_column'],
            y_column=sample_route_data['y_column'],
            gap_threshold=gap_threshold,
            **params,
        )
        
        # Check multiple solutions for fitness ordering
        all_solutions = result.all_solutions
        assert len(all_solutions) >= 1, "Should have multiple solutions to compare"
        
        # Best solution should be first in all_solutions
        best_fitness = all_solutions[0].get('fitness')
        assert best_fitness is not None, "Best solution should have fitness"
        
        # If we have multiple solutions, verify best is actually best (highest fitness)
        if len(all_solutions) > 1:
            for i in range(1, min(5, len(all_solutions))):  # Check first few solutions
                other_fitness = all_solutions[i].get('fitness', 0)
                assert best_fitness >= other_fitness, (
                    f"Best solution should have highest (least negative) fitness: "
                    f"best={best_fitness} vs other[{i}]={other_fitness}"
                )


class TestMultiObjectiveMethodCorrectness(TestAnalysisMethodObjectiveUsage):
    """Test MultiObjectiveMethod uses NSGA-II objectives correctly."""
    
    def test_multi_objective_processes_tuple_objectives_correctly(self, sample_route_data, basic_params):
        """
        CRITICAL REGRESSION TEST: MultiObjectiveMethod should correctly process 
        (-deviation, +avg_length) tuples from NSGA-II GA.
        
        This prevents the inversion bug where wrong objective signs led to 
        maximizing positive deviation and minimizing segment length.
        """
        method = MultiObjectiveMethod()
        
        # Run multi-objective analysis using existing interface
        params = dict(basic_params)
        gap_threshold = params.pop('gap_threshold')
        result = method.run_analysis(
            data=sample_route_data['route_analysis'],
            route_id=sample_route_data['route_id'],
            x_column=sample_route_data['x_column'],
            y_column=sample_route_data['y_column'],
            gap_threshold=gap_threshold,
            **params,
        )
        
        # Verify result structure
        assert result is not None, "Multi-objective analysis should return result"
        assert hasattr(result, 'all_solutions'), "Result should have all_solutions (Pareto front)" 
        assert len(result.all_solutions) > 0, "Should have Pareto solutions"
        
        # Check all Pareto solutions for correct objective structure
        for i, solution in enumerate(result.all_solutions[:5]):  # Check first 5 solutions
            # CRITICAL: Each solution should have objective_values with correct signs
            objective_values = solution.get('objective_values')
            assert objective_values is not None, f"Solution {i} should have objective_values"
            assert len(objective_values) == 2, f"Multi-objective should have exactly 2 objectives, got {len(objective_values)}"
            
            deviation_obj, length_obj = objective_values
            
            # CRITICAL REGRESSION PREVENTION: Verify correct objective signs
            assert deviation_obj < 0, (
                f"Solution {i}: Deviation objective should be negative (NSGA-II maximizes -deviation), "
                f"got {deviation_obj}"
            )
            assert length_obj >= 0, (
                f"Solution {i}: Length objective should be non-negative (NSGA-II maximizes +length), "
                f"got {length_obj}"
            )
            
            # Additional sanity checks
            avg_segment_length = solution.get('avg_segment_length', 0)
            assert avg_segment_length > 0, f"Solution {i} should have positive avg segment length"

            # The multi-objective length objective is computed in the GA as the
            # average segment length excluding *gap-only* segments.
            chromosome = solution.get('chromosome')
            assert chromosome is not None, f"Solution {i} should include chromosome"

            route_analysis = sample_route_data.get('route_analysis', None)
            gap_segments = getattr(route_analysis, 'gap_segments', [])
            gap_set = set((float(g[0]), float(g[1])) for g in (gap_segments or []))

            expected_lengths = []
            for j in range(len(chromosome) - 1):
                start_bp = float(chromosome[j])
                end_bp = float(chromosome[j + 1])
                seg_len = end_bp - start_bp
                if seg_len <= 0:
                    continue
                if (start_bp, end_bp) in gap_set:
                    continue
                expected_lengths.append(seg_len)

            expected_non_gap_avg = float(np.mean(expected_lengths)) if expected_lengths else 0.0
            assert np.isclose(length_obj, expected_non_gap_avg, atol=1e-9), (
                f"Solution {i}: Length objective ({length_obj}) should equal the GA-defined non-mandatory "
                f"gap-excluding average ({expected_non_gap_avg})"
            )
    
    def test_multi_objective_pareto_front_mathematical_validity(self, sample_route_data, basic_params):
        """
        CRITICAL: Verify Pareto front solutions exhibit correct trade-off relationships.
        
        In a valid Pareto front for (-deviation, +avg_length):
        - No solution should dominate all others in both objectives
        - Solutions should represent meaningful trade-offs
        """
        method = MultiObjectiveMethod()
        
        # Run analysis with sufficient generations to get diverse Pareto front
        extended_params = basic_params.copy()
        extended_params['num_generations'] = 10
        
        params = dict(extended_params)
        gap_threshold = params.pop('gap_threshold')
        result = method.run_analysis(
            data=sample_route_data['route_analysis'],
            route_id=sample_route_data['route_id'],
            x_column=sample_route_data['x_column'],
            y_column=sample_route_data['y_column'],
            gap_threshold=gap_threshold,
            **params,
        )
        
        pareto_solutions = result.all_solutions
        assert len(pareto_solutions) >= 2, "Should have multiple Pareto solutions for trade-off analysis"
        
        # Extract objective values for analysis
        objectives = []
        for sol in pareto_solutions:
            obj_vals = sol.get('objective_values', [])
            if len(obj_vals) == 2:
                objectives.append((obj_vals[0], obj_vals[1]))
        
        assert len(objectives) >= 2, "Should have at least 2 solutions with valid objectives"
        
        # CRITICAL: Verify Pareto dominance relationships
        for i, (dev1, len1) in enumerate(objectives):
            for j, (dev2, len2) in enumerate(objectives):
                if i != j:
                    # Check if solution i dominates solution j
                    # (i dominates j if i is better or equal in all objectives and strictly better in at least one)
                    i_better_dev = dev1 >= dev2  # More negative is better for deviation
                    i_better_len = len1 >= len2   # More positive is better for length
                    i_strictly_better = dev1 > dev2 or len1 > len2
                    
                    if i_better_dev and i_better_len and i_strictly_better:
                        # Solution i dominates solution j - this shouldn't happen in a proper Pareto front
                        pytest.fail(
                            f"Solution {i} dominates solution {j} - invalid Pareto front!\n"
                            f"Solution {i}: deviation={dev1}, length={len1}\n" 
                            f"Solution {j}: deviation={dev2}, length={len2}"
                        )
        
        # Verify objective value ranges are reasonable
        deviations = [obj[0] for obj in objectives]
        lengths = [obj[1] for obj in objectives]
        
        assert all(d < 0 for d in deviations), "All deviation objectives should be negative"  
        assert all(l > 0 for l in lengths), "All length objectives should be positive"
        
        # Should have some diversity in objective values (not all identical)
        dev_range = max(deviations) - min(deviations)  
        len_range = max(lengths) - min(lengths)
        assert dev_range > 0, "Pareto front should have diversity in deviation values"
        assert len_range > 0, "Pareto front should have diversity in length values"


class TestConstrainedMethodCorrectness(TestAnalysisMethodObjectiveUsage):
    """Test ConstrainedMethod uses penalized objectives correctly."""
    
    def test_constrained_method_applies_length_constraints(self, sample_route_data, basic_params):
        """
        CRITICAL: ConstrainedMethod should apply length constraint penalties correctly.
        Solutions violating target average length should have worse (more negative) fitness.
        """
        method = ConstrainedMethod()
        
        # Set up constraint parameters
        constrained_params = basic_params.copy()
        constrained_params.update({
            'target_avg_length': 2.0,      # Target 2.0 mile segments
            'penalty_weight': 1000.0,      # Large penalty for violations
            'length_tolerance': 0.1,       # Allow ±0.1 mile deviation
        })
        
        # Run constrained analysis using new input_parameters format
        result = method.run_analysis(
            data=sample_route_data['route_analysis'],
            route_id=sample_route_data['route_id'],
            x_column=sample_route_data['x_column'],
            y_column=sample_route_data['y_column'],
            gap_threshold=constrained_params['gap_threshold'],
            input_parameters=constrained_params
        )
        
        # Verify result structure
        assert result is not None, "Constrained analysis should return result"
        assert hasattr(result, 'all_solutions'), "Result should have all_solutions"
        assert len(result.all_solutions) > 0, "Should have at least one solution"
        
        best_solution = result.best_solution
        
        # CRITICAL: Fitness should reflect constraint penalty
        fitness = best_solution.get('fitness')
        assert fitness is not None, "Solution should have fitness value"
        assert fitness < 0, f"Constrained fitness should be negative, got {fitness}"
        
        # Verify constraint handling
        avg_segment_length = best_solution.get('avg_segment_length', 0)
        target_length = constrained_params['target_avg_length']
        tolerance = constrained_params['length_tolerance']
        
        # Best solution should ideally be close to target (within tolerance or with reasonable penalty)
        length_deviation = abs(avg_segment_length - target_length)
        
        if length_deviation <= tolerance:
            # Within tolerance - should have minimal additional penalty beyond base deviation
            print(f"✅ Solution within tolerance: avg={avg_segment_length:.3f}, target={target_length}, dev={length_deviation:.3f}")
        else:
            # Outside tolerance - fitness should reflect penalty
            print(f"⚠️ Solution outside tolerance but may be best achievable: avg={avg_segment_length:.3f}, target={target_length}, dev={length_deviation:.3f}")
        
        # Verify objective_values structure for unified export
        objective_values = best_solution.get('objective_values')
        assert objective_values is not None, "Solution should have objective_values"
        assert len(objective_values) >= 1, "Should have at least 1 objective value"
        assert objective_values[0] < 0, f"Primary objective should be negative: {objective_values[0]}"
    
    def test_constrained_penalty_prevents_extreme_violations(self, sample_route_data, basic_params):
        """
        REGRESSION TEST: Verify constraint penalties prevent extreme constraint violations.
        With proper penalties, solutions should not deviate extremely from target lengths.
        """
        method = ConstrainedMethod()
        
        # Set up strict constraints
        strict_params = basic_params.copy()
        strict_params.update({
            'target_avg_length': 1.5,      # Target 1.5 mile segments  
            'penalty_weight': 5000.0,      # Very large penalty
            'length_tolerance': 0.05,      # Very tight tolerance
            'num_generations': 15          # More generations for convergence
        })
        
        # Run analysis using new input_parameters format
        result = method.run_analysis(
            data=sample_route_data['route_analysis'],
            route_id=sample_route_data['route_id'],
            x_column=sample_route_data['x_column'],
            y_column=sample_route_data['y_column'],
            gap_threshold=strict_params['gap_threshold'],
            input_parameters=strict_params
        )
        
        best_solution = result.best_solution
        avg_segment_length = best_solution.get('avg_segment_length', 0)
        target_length = strict_params['target_avg_length']
        
        # With strict penalties, solution should be reasonably close to target
        length_deviation = abs(avg_segment_length - target_length)
        max_acceptable_deviation = 1.0  # Allow up to 1.0 mile deviation (reasonable given constraints)
        
        assert length_deviation <= max_acceptable_deviation, (
            f"With strict penalties, solution should be reasonably close to target: "
            f"avg={avg_segment_length:.3f}, target={target_length}, deviation={length_deviation:.3f} > {max_acceptable_deviation}"
        )
        
        # Fitness should reflect penalty application
        fitness = best_solution.get('fitness')
        base_deviation_fitness = best_solution.get('deviation_fitness', fitness)
        
        # If there was a constraint violation, fitness should be worse than base deviation fitness
        tolerance = strict_params['length_tolerance']
        if length_deviation > tolerance:
            # Should have penalty applied
            excess = (length_deviation - tolerance)
            expected_penalty = strict_params['penalty_weight'] * (excess ** 2)
            expected_constrained_fitness = base_deviation_fitness - expected_penalty
            
            # Allow some numerical tolerance in penalty calculation
            assert abs(fitness - expected_constrained_fitness) < 10, (
                f"Constrained fitness should reflect penalty: "
                f"expected≈{expected_constrained_fitness:.1f}, got={fitness:.1f}, penalty={expected_penalty:.1f}"
            )


class TestIntegratedObjectiveConsistency(TestAnalysisMethodObjectiveUsage):
    """Test consistency between all methods' objective function usage."""
    
    def test_all_methods_produce_negative_primary_objectives(self, sample_route_data, basic_params):
        """
        CONSISTENCY TEST: All methods should produce negative primary objective values 
        since they all minimize some form of deviation/error.
        """
        methods = [
            ('single_objective', SingleObjectiveMethod()),
            ('multi_objective', MultiObjectiveMethod()), 
            ('constrained', ConstrainedMethod())
        ]
        
        
        for method_name, method_instance in methods:
            # Run analysis with each method using appropriate interface
            method_params = basic_params.copy()
            if method_name == 'constrained':
                method_params.update({
                    'target_avg_length': 2.0,
                    'penalty_weight': 1000.0,
                    'length_tolerance': 0.2
                })
            
            # Handle different API styles for different methods
            if method_name in ['single_objective', 'multi_objective']:
                # Single and multi-objective use old API with positional arguments
                result = method_instance.run_analysis(
                    data=sample_route_data['route_analysis'],
                    route_id=sample_route_data['route_id'],
                    x_column=sample_route_data['x_column'],
                    y_column=sample_route_data['y_column'],
                    min_length=method_params.get('min_length', 0.5),
                    max_length=method_params.get('max_length', 10.0),
                    **{k: v for k, v in method_params.items() if k not in ['min_length', 'max_length']}
                )
            elif method_name == 'constrained':
                # Constrained uses new input_parameters API
                result = method_instance.run_analysis(
                    data=sample_route_data['route_analysis'],
                    route_id=sample_route_data['route_id'],
                    x_column=sample_route_data['x_column'], 
                    y_column=sample_route_data['y_column'],
                    gap_threshold=method_params.get('gap_threshold', 0.3),
                    input_parameters=method_params
                )
            
            # Verify primary objective is negative for all methods
            best_solution = result.best_solution
            objective_values = best_solution.get('objective_values', [])
            assert len(objective_values) > 0, f"{method_name} should have objective_values"
            
            primary_objective = objective_values[0]
            assert primary_objective < 0, (
                f"{method_name} primary objective should be negative (minimization-based), "
                f"got {primary_objective}"
            )
            
            # Additional method-specific checks
            if method_name == 'multi_objective':
                assert len(objective_values) == 2, f"Multi-objective should have 2 objectives"
                assert objective_values[1] > 0, f"Multi-objective second objective should be positive"
            else:
                assert len(objective_values) >= 1, f"{method_name} should have at least 1 objective"


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v", "--tb=short"])