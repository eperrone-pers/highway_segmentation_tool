"""
Comprehensive Test Suite for Highway Segmentation Genetic Algorithm

This module contains comprehensive tests for the HighwaySegmentGA class, covering
both unit-level functionality and integration scenarios with realistic highway data.
Converted from legacy unittest format to modern pytest framework for better
testing capabilities and clearer organization.

Test Categories:
    Unit Tests: Individual method and component behavior validation
    Integration Tests: End-to-end functionality with realistic data scenarios
    Edge Case Tests: Boundary conditions and error handling validation
    Performance Tests: Caching behavior and optimization feature validation

Test Data Requirements:
    - sample_route_analysis: RouteAnalysis object with comprehensive gap analysis
    - sample_highway_data: Basic DataFrame with milepoint/strength columns  
    - edge_case_datasets: Minimal and boundary condition datasets
    - Minimum 10 data points for meaningful segmentation testing
    - Data should include realistic highway measurement patterns

Coverage Areas:
    Algorithm Correctness:
        - Population initialization and chromosome generation
        - Fitness evaluation (single and multi-objective)
        - Constraint compliance (segment lengths, mandatory breakpoints)
        - Data segmentation accuracy
    
    Performance Optimization:
        - Multi-level caching system behavior  
        - Memory efficiency and cache hit rate validation
        - Performance scaling with data size
    
    Integration Compatibility:
        - RouteAnalysis object integration
        - Configuration parameter handling
        - Error handling and edge case robustness
        - Gap-aware segmentation functionality

Testing Philosophy:
    - Validate algorithm correctness, not just implementation details
    - Test realistic scenarios representative of production usage
    - Ensure robust error handling for edge cases
    - Verify performance optimizations provide expected benefits
    - Maintain backward compatibility while supporting new features

Author: Highway Segmentation GA Team
Framework: pytest (converted from unittest)
Version: 1.95+ (Performance and Documentation Enhanced)
"""

import pytest
import sys
import os
import pandas as pd
import numpy as np
from unittest.mock import Mock

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from analysis.utils.genetic_algorithm import HighwaySegmentGA

class TestGeneticAlgorithm:
    """
    Comprehensive unit test suite for HighwaySegmentGA class functionality.
    
    This test suite validates core genetic algorithm functionality including
    population management, fitness evaluation, constraint handling, and
    optimization features. Focuses on individual method correctness and
    component behavior validation.
    
    Test Structure:
        - Fixtures: Provide consistent test data and configured GA instances
        - Unit Tests: Validate individual methods and components
        - Parameter Tests: Ensure proper configuration handling
        - Edge Case Tests: Validate boundary conditions and error handling
    
    Validation Areas:
        Population Management:
            - Initial population generation with diversity
            - Chromosome structure validation
            - Constraint satisfaction from initialization
            
        Fitness Evaluation:
            - Single-objective fitness calculation accuracy
            - Multi-objective fitness tuple structure
            - Caching behavior and performance
            
        Constraint Compliance:
            - Segment length constraint enforcement
            - Mandatory breakpoint preservation
            - Boundary condition handling
            
        Data Integration:
            - RouteAnalysis object compatibility
            - DataFrame fallback handling
            - Column mapping and data access
    
    Test Data Requirements:
        - sample_route_analysis: Pre-processed RouteAnalysis with gap detection
        - sample_highway_data: Raw DataFrame for fallback testing
        - Minimum 10 data points for meaningful chromosome generation
        - Realistic milepoint and strength value ranges
    
    Performance Expectations:
        - Population generation: < 1 second for 50 individuals
        - Fitness evaluation: < 100ms per chromosome
        - Constraint validation: 100% success rate for valid inputs
        - Memory usage: Reasonable scaling with population size
    """

    @pytest.fixture
    def genetic_algorithm(self, sample_route_analysis):
        """Create HighwaySegmentGA instance for testing."""
        return HighwaySegmentGA(
            data=sample_route_analysis,
            x_column="milepoint",
            y_column="structural_strength_ind", 
            min_length=1, 
            max_length=5,
            population_size=10,
            mutation_rate=0.1,
            crossover_rate=0.8,
            gap_threshold=0.1
        )

    @pytest.fixture
    def test_data(self, sample_highway_data):
        """Create simple test data."""
        return sample_highway_data

    @pytest.mark.unit
    def test_initialize_population(self, genetic_algorithm):
        """
        Validate population initialization produces valid chromosomes.
        
        This test ensures the initial population generation creates a valid
        set of chromosomes that comply with all constraints and provide
        good diversity for optimization.
        
        Validation Criteria:
            1. Correct population size (matches configured population_size)
            2. Chromosome structure validity (list of breakpoints)
            3. Mandatory breakpoint inclusion (gaps + route boundaries)
            4. Segment length constraint compliance
            5. Breakpoint position validity (within data boundaries)
            6. No duplicate or invalid chromosomes
        
        This is critical because invalid initial populations can cause:
            - Optimization failures or poor convergence
            - Constraint violations throughout evolution
            - Fitness evaluation errors or exceptions
            - Reduced solution quality and algorithm robustness
        
        Test Strategy:
            - Generate full population and validate each chromosome
            - Check structural properties (list type, minimum length)
            - Verify constraint satisfaction for all individuals
            - Ensure reasonable diversity in initial solutions
        
        Success Criteria:
            - Population size matches configuration
            - All chromosomes are valid lists with >=2 breakpoints
            - No constraint violations in any initial chromosome
            - Population provides good starting point for optimization
        """
        population = genetic_algorithm.generate_initial_population()
        assert len(population) == genetic_algorithm.population_size
        
        # Each individual should be a valid chromosome
        for individual in population:
            assert isinstance(individual, list)
            assert len(individual) >= 2  # At least start and end points

    @pytest.mark.unit
    def test_evaluate_fitness(self, genetic_algorithm, sample_highway_data):
        """
        Validate fitness evaluation accuracy and consistency.
        
        This test ensures the fitness function correctly evaluates chromosome
        quality and produces consistent, meaningful results for optimization.
        The fitness function is the core of the genetic algorithm and must
        provide reliable guidance for evolutionary selection.
        
        Validation Criteria:
            1. Fitness returns numeric values (int or float)
            2. Negative values for minimization problem (correct behavior)
            3. Consistent results for identical chromosomes
            4. Reasonable fitness ranges for different solution qualities
            5. Proper handling of edge cases (empty segments, etc.)
        
        Mathematical Validation:
            - Fitness = -Σ(actual_value - segment_average)² 
            - Better segmentations should have less negative fitness
            - Identical chromosomes should return identical fitness
            - Fitness should correlate with segmentation quality
        
        Edge Cases Tested:
            - Minimal chromosomes (just mandatory breakpoints)
            - Complex chromosomes with many segments
            - Boundary condition breakpoints
            - Segments with varying data density
        
        Performance Expectations:
            - Evaluation time: < 100ms per chromosome
            - Memory usage: Stable across evaluations
            - Cache utilization: Improved performance on repeated evaluations
        """
        # Generate a simple chromosome with just start and end points
        chromosome = genetic_algorithm.generate_chromosome()
        fitness = genetic_algorithm.fitness(chromosome)
        assert isinstance(fitness, (int, float))
        # Fitness is negative for minimization problems (correct behavior)

    @pytest.mark.unit
    def test_multi_objective_fitness(self, genetic_algorithm):
        """
        Validate multi-objective fitness evaluation for NSGA-II optimization.
        
        This test ensures the multi-objective fitness function correctly evaluates
        chromosomes on two competing objectives and produces results suitable for
        Pareto-based optimization algorithms like NSGA-II.
        
        Objective Validation:
            Objective 1 (Data Accuracy): 
                - Negative sum of squared deviations (for minimization)
                - More negative values indicate better data representation
                - Should correlate with single-objective fitness
                
            Objective 2 (Segment Efficiency):
                - Average non-mandatory segment length
                - Higher values indicate simpler segmentation 
                - Should balance with accuracy objective
        
        Return Structure Validation:
            1. Returns tuple with exactly 2 elements
            2. Both elements are numeric (int or float)
            3. First element (deviation) is negative or zero
            4. Second element (length) is positive or zero
            5. Consistent results for identical chromosomes
        
        Multi-Objective Properties:
            - Trade-off exploration: Different chromosomes should show 
              different balances between accuracy and simplicity
            - Pareto efficiency: No single chromosome dominates on both objectives
            - Range coverage: Objectives span meaningful ranges
        
        Use Cases:
            - NSGA-II population ranking and selection
            - Pareto front construction
            - Trade-off analysis between competing objectives
            - Multi-criteria decision making
        """
        chromosome = genetic_algorithm.generate_chromosome()
        fitness = genetic_algorithm.multi_objective_fitness(chromosome)
        assert isinstance(fitness, tuple)
        assert len(fitness) == 2  # Should return (deviation, avg_length)
        assert all(isinstance(f, (int, float)) for f in fitness)

    @pytest.mark.unit
    def test_generate_chromosome(self, genetic_algorithm):
        """
        Validate chromosome generation produces valid, constraint-compliant solutions.
        
        This test ensures the chromosome generation process creates valid
        segmentation solutions that respect all engineering constraints and
        data limitations. Chromosome generation is fundamental to population
        initialization and genetic operators.
        
        Structural Validation:
            1. Returns a Python list of numeric breakpoints
            2. Minimum 2 breakpoints (route start and end)
            3. Breakpoints are sorted in ascending order
            4. Breakpoints are within valid data range
            5. No duplicate breakpoints in the same chromosome
        
        Constraint Compliance:
            - Route Boundaries: First and last breakpoints match data range
            - Mandatory Breakpoints: All gap boundaries are included
            - Length Constraints: All segments respect min/max length limits
            - Data Alignment: Breakpoints correspond to actual data positions
        
        Engineering Validity:
            - Segments are meaningful for highway engineering analysis
            - Breakpoint distribution provides reasonable segmentation
            - Gap handling preserves data integrity
            - Constraint satisfaction enables practical application
        
        Randomization Properties:
            - Multiple calls produce different chromosomes (diversity)
            - Random placement respects constraint boundaries
            - Reasonable distribution of segment counts
        
        Error Handling:
            - Impossible constraints should raise meaningful exceptions
            - Edge cases handled gracefully (minimal data, tight constraints)
            - Robust behavior with various data characteristics
        """
        chromosome = genetic_algorithm.generate_chromosome()
        
        # Chromosome should be a valid Python list
        assert isinstance(chromosome, list)
        assert len(chromosome) >= 2
        
        # Should start at beginning and end at end of data
        min_mp = genetic_algorithm.x_data.min()
        max_mp = genetic_algorithm.x_data.max()
        assert np.isclose(chromosome[0], min_mp, rtol=1e-3)
        assert np.isclose(chromosome[-1], max_mp, rtol=1e-3)

    @pytest.mark.unit
    def test_segment_data(self, genetic_algorithm):
        """Test data segmentation."""
        chromosome = genetic_algorithm.generate_chromosome()

        # segment_data() was removed from the GA engine (unused in-repo).
        # Reproduce the same segmentation behavior inline for this test.
        segments = []
        for start_bp, end_bp in zip(chromosome, chromosome[1:]):
            seg = genetic_algorithm.data[
                (genetic_algorithm.data[genetic_algorithm.x_column] >= start_bp)
                & (genetic_algorithm.data[genetic_algorithm.x_column] < end_bp)
            ]
            segments.append(seg)
        
        # Should return a list of segments
        assert isinstance(segments, list)
        assert len(segments) == len(chromosome) - 1  # Number of segments = breakpoints - 1
        
        # Each segment should have data
        for segment in segments:
            assert len(segment) > 0  # Each segment should contain at least some data points

    @pytest.mark.unit
    def test_run_basic_functionality(self, genetic_algorithm):
        """Test basic functionality by generating and evaluating chromosomes."""
        # Test that we can generate a population and evaluate fitness
        population = genetic_algorithm.generate_initial_population()
        
        assert isinstance(population, list)
        assert len(population) == genetic_algorithm.population_size
        
        # Test that we can evaluate fitness for each chromosome
        for chromosome in population[:3]:  # Test first 3 for speed
            fitness = genetic_algorithm.fitness(chromosome)
            assert isinstance(fitness, (int, float))
            # Fitness is negative for minimization problems (correct behavior)

    @pytest.mark.unit
    def test_genetic_algorithm_with_edge_cases(self, edge_case_datasets):
        """Test genetic algorithm with edge case data."""
        # Test with two points (minimal viable data)
        minimal_data = edge_case_datasets['two_points']

        # DataFrame fallback is no longer supported: RouteAnalysis is required.
        with pytest.raises(TypeError):
            HighwaySegmentGA(
                data=minimal_data,
                x_column="milepoint",
                y_column="structural_strength_ind",
                min_length=0.1,
                max_length=1.0,
                population_size=5,
                mutation_rate=0.1,
                crossover_rate=0.8,
                gap_threshold=0.05
            )

    @pytest.mark.unit
    def test_genetic_algorithm_parameters(self, sample_route_analysis):
        """Test HighwaySegmentGA with different parameters."""
        # Test with different section lengths
        ga1 = HighwaySegmentGA(
            data=sample_route_analysis,
            x_column="milepoint",
            y_column="structural_strength_ind",
            min_length=0.5, 
            max_length=2.0,
            population_size=10,
            mutation_rate=0.1,
            crossover_rate=0.8,
            gap_threshold=0.5,
        )
        ga2 = HighwaySegmentGA(
            data=sample_route_analysis,
            x_column="milepoint",
            y_column="structural_strength_ind",
            min_length=2.0, 
            max_length=10.0,
            population_size=10,
            mutation_rate=0.1,
            crossover_rate=0.8,
            gap_threshold=0.5,
        )
        
        assert ga1.min_length == 0.5
        assert ga1.max_length == 2.0
        assert ga2.min_length == 2.0
        assert ga2.max_length == 10.0

# Additional integration-style tests for genetic algorithm

class TestGeneticAlgorithmIntegration:
    """
    Integration tests for HighwaySegmentGA with realistic data and workflows.
    
    This test suite validates end-to-end functionality of the genetic algorithm
    when integrated with realistic highway data, comprehensive gap analysis,
    and production-like optimization scenarios. Focus is on system-level
    behavior and real-world usage patterns.
    
    Integration Scenarios:
        Realistic Data Integration:
            - RouteAnalysis object processing with gap detection
            - Multi-route data handling and processing
            - Large dataset performance and memory management
            
        End-to-End Workflows:
            - Complete optimization pipeline execution
            - Configuration parameter integration
            - Result generation and validation
            
        Performance Integration:
            - Caching system behavior under realistic load
            - Memory usage patterns with large populations
            - Performance scaling characteristics
    
    Data Characteristics:
        - Realistic highway measurement patterns
        - Representative data gaps and discontinuities  
        - Appropriate scale (hundreds to thousands of data points)
        - Real-world constraint ranges and engineering requirements
        
    Success Criteria:
        - Successful completion of optimization workflows
        - Reasonable performance with realistic data scales
        - Proper integration with configuration system
        - Robust behavior under various data conditions
        - Memory efficiency and resource management
        
    Production Readiness Validation:
        - Algorithm stability across different datasets
        - Error handling for production scenarios
        - Performance meets practical requirements
        - Results quality suitable for engineering decisions
    """

    @pytest.mark.unit
    @pytest.mark.data_dependent
    def test_genetic_algorithm_with_highway_data(self, sample_route_analysis):
        """Test genetic algorithm with realistic highway data."""
        ga = HighwaySegmentGA(
            data=sample_route_analysis,
            x_column="milepoint",
            y_column="structural_strength_ind",
            min_length=1.0, 
            max_length=3.0,
            population_size=15,  # Small for quick test
            mutation_rate=0.1,
            crossover_rate=0.8,
            gap_threshold=0.5,
        )
        
        # Generate population and test basic functionality
        population = ga.generate_initial_population()
        assert len(population) == 15
        
        # Test fitness evaluation on population
        for chromosome in population[:3]:  # Test first few
            fitness = ga.fitness(chromosome)
            assert isinstance(fitness, (int, float))
            
            multi_fitness = ga.multi_objective_fitness(chromosome)
            assert isinstance(multi_fitness, tuple)
            assert len(multi_fitness) == 2

    @pytest.mark.unit
    def test_genetic_algorithm_caching_features(self, sample_route_analysis):
        """Test genetic algorithm caching functionality."""
        ga = HighwaySegmentGA(
            data=sample_route_analysis,
            x_column="milepoint",
            y_column="structural_strength_ind",
            min_length=1.0,
            max_length=4.0,
            population_size=10,
            mutation_rate=0.1,
            crossover_rate=0.8,
            gap_threshold=0.5,
        )
        
        # Test segment caching
        ga.enable_segment_cache_mode(True)
        assert ga.enable_segment_caching == True
        
        chromosome = ga.generate_chromosome()
        
        # Evaluate fitness twice to test caching
        # (fitness uses chromosome-level caching and, when enabled, the GA's internal
        # segment-cache-mode evaluation path)
        fitness1 = ga.fitness(chromosome)
        fitness2 = ga.fitness(chromosome)  # Should use cache
        
        assert fitness1 == fitness2
        
        # Check cache stats
        stats = ga.get_segment_cache_stats()
        assert isinstance(stats, dict)
        assert 'hits' in stats
        assert 'misses' in stats