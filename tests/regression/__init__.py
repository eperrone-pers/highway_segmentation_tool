"""
Regression Test Suite for Highway Segmentation GA

This package contains comprehensive regression tests that validate the complete
workflow for all optimization methods and data configurations. The regression
test suite ensures that changes to the codebase don't break existing functionality
and that all optimization methods continue to produce valid, consistent results.

Test Coverage:
    Methods Tested:
        - single: Single-objective genetic algorithm optimization
        - multi: Multi-objective NSGA-II optimization
        - constrained: Constrained single-objective with penalty functions
        - aashto_cda: AASHTO Enhanced Cumulative Difference Approach
    
    Data Configurations:
        - single_route: Single route data (test_data_single_route.csv)
        - multi_route: Multi-route data (TestMultiRoute.csv)
        
    Total Test Matrix: 4 methods × 2 datasets = 8 comprehensive tests

Key Components:
    test_complete_workflow_regression.py: Main test file with 8 parametrized tests
    conftest.py: Test fixtures, utilities, and configuration management
    test_parameters_template.json: Standardized parameter configurations
    validate_regression_outputs.py: JSON schema validation utility
    outputs/: Generated test artifacts (JSON results + Excel exports)
    README.md: Comprehensive usage and troubleshooting guide

Test Philosophy:
    - End-to-End Validation: Tests complete optimization workflows
    - Production Equivalence: Uses same code paths as GUI application
    - Comprehensive Coverage: All method/dataset combinations tested
    - Schema Compliance: All outputs validated against JSON schema
    - Performance Awareness: Optimized parameters for speed while maintaining accuracy

Usage:
    # Run all regression tests
    pytest tests/regression/ -v
    
    # Run specific method tests
    pytest tests/regression/ -k "single" -v
    
    # Validate all JSON outputs
    python tests/regression/validate_regression_outputs.py

Integration Benefits:
    - CI/CD Integration: Perfect for automated testing pipelines
    - Regression Detection: Immediately catches breaking changes
    - Quality Assurance: Ensures consistent output format and quality
    - Performance Monitoring: Track optimization performance over time
    - Documentation Validation: Living examples of expected system behavior

Author: Highway Segmentation GA Team
Version: 1.95+ (Comprehensive Regression Framework)
"""