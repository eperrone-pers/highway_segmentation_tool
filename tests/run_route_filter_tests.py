"""
Test runner specifically for route filter UI functionality.

Run with: python tests/run_route_filter_tests.py
"""

import os
import sys
import pytest
from pathlib import Path


def main():
    """Run route filter UI tests with detailed reporting."""
    # Get the test directory
    test_dir = Path(__file__).parent
    project_root = test_dir.parent
    
    print("=" * 60)
    print("🎨 ROUTE FILTER UI TEST SUITE")
    print("=" * 60)
    print("Testing Phase 1 route filter functionality...")
    print()
    
    # Set up test configuration
    os.chdir(project_root)
    
    # Run the specific UI tests
    test_file = str(test_dir / "ui" / "test_route_filter_ui.py")
    
    # Pytest arguments for detailed output
    pytest_args = [
        test_file,
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--color=yes",  # Colored output
        "-x",  # Stop on first failure (for debugging)
        "--durations=10",  # Show slowest 10 tests
    ]
    
    print(f"Running tests from: {test_file}")
    print("-" * 60)
    
    # Run pytest
    exit_code = pytest.main(pytest_args)
    
    print("-" * 60)
    if exit_code == 0:
        print("🎉 ALL ROUTE FILTER UI TESTS PASSED!")
        print("\nPhase 1 route filter functionality is working correctly:")
        print("  ✅ Filter Routes button creation and state management")
        print("  ✅ Route info display and text updates") 
        print("  ✅ Route column change handling")
        print("  ✅ Route filter dialog integration")
        print("  ✅ End-to-end multi-route workflow")
    else:
        print(f"❌ SOME TESTS FAILED (exit code: {exit_code})")
        print("\nReview the test output above for details.")
    
    print("=" * 60)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())