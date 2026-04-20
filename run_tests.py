#!/usr/bin/env python3
"""
Test Runner Script for Highway Segmentation GA

This script provides convenient commands for running different test suites
with proper configuration and reporting.

Usage:
    python run_tests.py --help
    python run_tests.py --unit
    python run_tests.py --integration  
    python run_tests.py --all
    python run_tests.py --coverage
    python run_tests.py --performance
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

# Ensure we're in the project root
PROJECT_ROOT = Path(__file__).parent
os.chdir(PROJECT_ROOT)

def run_command(cmd, description=""):
    """Run a command and handle errors."""
    if description:
        print(f"\\n==== {description} ====")
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}")
            sys.exit(1)
            
    except FileNotFoundError:
        print(f"Error: Command not found. Make sure pytest is installed.")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Run Highway Segmentation GA Tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--ui", action="store_true", help="Run UI tests only")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage report")
    parser.add_argument("--performance", action="store_true", help="Run performance benchmarks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--pattern", help="Run tests matching specific pattern")
    parser.add_argument("--file", help="Run specific test file")
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]
    
    if args.verbose:
        base_cmd.append("-v")
    
    # Determine what to run
    if args.unit:
        cmd = base_cmd + ["-m", "unit", "tests/unit/"]
        run_command(cmd, "Running Unit Tests")
        
    elif args.integration:
        cmd = base_cmd + ["-m", "integration", "tests/integration/"]
        run_command(cmd, "Running Integration Tests")
        
    elif args.ui:
        cmd = base_cmd + ["-m", "ui", "tests/ui/"]
        run_command(cmd, "Running UI Tests")
        
    elif args.performance:
        cmd = base_cmd + ["-m", "performance", "--benchmark-only"]
        run_command(cmd, "Running Performance Benchmarks")
        
    elif args.coverage:
        cmd = base_cmd + ["--cov=src", "--cov-report=html", "--cov-report=term"]
        run_command(cmd, "Running Tests with Coverage")
        print("\\nCoverage report generated in htmlcov/index.html")
        
    elif args.pattern:
        cmd = base_cmd + ["-k", args.pattern]
        run_command(cmd, f"Running Tests Matching Pattern: {args.pattern}")
        
    elif args.file:
        cmd = base_cmd + [args.file]
        run_command(cmd, f"Running Test File: {args.file}")
        
    elif args.all:
        # Run all test categories
        print("=== Running Complete Test Suite ===")
        
        # Unit tests first
        cmd = base_cmd + ["-m", "unit", "tests/unit/"]
        run_command(cmd, "Unit Tests")
        
        # Integration tests
        cmd = base_cmd + ["-m", "integration", "tests/integration/"]
        run_command(cmd, "Integration Tests")
        
        # UI tests (if any exist)
        if Path("tests/ui").exists() and any(Path("tests/ui").glob("test_*.py")):
            cmd = base_cmd + ["-m", "ui", "tests/ui/"]
            run_command(cmd, "UI Tests")
        
        print("\\n=== All Tests Completed ===")
        
    else:
        # Default: run all tests except performance
        cmd = base_cmd + ["tests/", "-m", "not performance"]
        run_command(cmd, "Running All Tests (except performance)")

if __name__ == "__main__":
    # Check if pytest is available
    try:
        import pytest
    except ImportError:
        print("Error: pytest not found. Please install requirements:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    
    # Check if we're in the right directory
    if not Path("src").exists() or not Path("tests").exists():
        print("Error: Please run this script from the project root directory")
        print("(The directory containing 'src' and 'tests' folders)")
        sys.exit(1)
    
    main()