"""
Test runner for Phase 1 multi-route processing functionality.

This script runs all Phase 1 tests with appropriate configuration
and provides detailed reporting of test results.
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """Run Phase 1 tests with comprehensive reporting."""
    # Get the test directory
    test_dir = Path(__file__).parent
    project_root = test_dir.parent
    src_dir = project_root / "src"
    
    # Add src to Python path
    sys.path.insert(0, str(src_dir))
    
    print("=" * 70)
    print("🚀 HIGHWAY SEGMENTATION GA - PHASE 1 TEST SUITE")
    print("=" * 70)
    print("Testing multi-route processing functionality...")
    print()
    
    # Define Phase 1 test files
    phase1_tests = [
        "unit/test_phase1_file_manager.py",
        "unit/test_phase1_parameter_manager.py", 
        "ui/test_route_filter_ui.py",
        "integration/test_phase1_complete_workflow.py"
    ]
    
    # Test categories and descriptions
    test_descriptions = {
        "unit/test_phase1_file_manager.py": "File Manager Route Processing",
        "unit/test_phase1_parameter_manager.py": "Parameter Manager Route Handling", 
        "ui/test_route_filter_ui.py": "Route Filter Dialog UI",
        "integration/test_phase1_complete_workflow.py": "End-to-End Workflow"
    }
    
    # Run tests for each category
    total_passed = 0
    total_failed = 0
    failed_categories = []
    
    for test_file in phase1_tests:
        test_path = test_dir / test_file
        category = test_descriptions.get(test_file, test_file)
        
        print(f"📋 Testing: {category}")
        print(f"   File: {test_file}")
        print(f"   Path: {test_path}")
        
        if not test_path.exists():
            print(f"   ❌ Test file not found: {test_path}")
            failed_categories.append(category)
            continue
        
        # Run pytest on the specific test file
        try:
            cmd = [
                sys.executable, "-m", "pytest", 
                str(test_path), 
                "-v",  # Verbose output
                "--tb=short",  # Short traceback format
                "--strict-markers",  # Strict marker checking
                "--durations=10",  # Show 10 slowest tests
                "-m", "not slow"  # Skip slow tests by default
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                cwd=str(project_root)
            )
            
            if result.returncode == 0:
                print(f"   ✅ PASSED - All tests in {category}")
                # Parse output for test count
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'passed' in line and ('failed' in line or 'error' in line):
                        print(f"   📊 {line.strip()}")
                        break
                    elif 'passed' in line:
                        print(f"   📊 {line.strip()}")
                        break
            else:
                print(f"   ❌ FAILED - Issues found in {category}")
                failed_categories.append(category)
                # Show failed test details
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'FAILED' in line or 'ERROR' in line:
                        print(f"      🔸 {line.strip()}")
                
                # Show error summary
                if result.stderr:
                    print(f"   💥 Errors: {result.stderr.strip()}")
                    
        except Exception as e:
            print(f"   💥 Exception running tests: {e}")
            failed_categories.append(category)
        
        print()
    
    # Summary
    print("=" * 70)
    print("📈 PHASE 1 TEST SUMMARY")
    print("=" * 70)
    
    total_categories = len(phase1_tests)
    passed_categories = total_categories - len(failed_categories)
    
    print(f"Total Test Categories: {total_categories}")
    print(f"Passed Categories: {passed_categories}")
    print(f"Failed Categories: {len(failed_categories)}")
    print()
    
    if failed_categories:
        print("❌ FAILED CATEGORIES:")
        for category in failed_categories:
            print(f"   • {category}")
        print()
    
    if passed_categories == total_categories:
        print("🎉 ALL PHASE 1 TESTS PASSED!")
        print("✅ Multi-route processing functionality is working correctly")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("🔧 Please review failed categories and fix issues before proceeding to Phase 2")
    
    print()
    print("=" * 70)
    
    return 0 if passed_categories == total_categories else 1


def run_specific_test_type(test_type):
    """Run a specific type of Phase 1 tests."""
    test_dir = Path(__file__).parent
    project_root = test_dir.parent
    
    type_mapping = {
        'unit': ['unit/test_phase1_file_manager.py', 'unit/test_phase1_parameter_manager.py'],
        'ui': ['ui/test_phase1_route_filter_dialog.py'],
        'integration': ['integration/test_phase1_complete_workflow.py'],
        'file': ['unit/test_phase1_file_manager.py'],
        'param': ['unit/test_phase1_parameter_manager.py'],
        'dialog': ['ui/test_phase1_route_filter_dialog.py'],
        'workflow': ['integration/test_phase1_complete_workflow.py']
    }
    
    if test_type not in type_mapping:
        print(f"❌ Unknown test type: {test_type}")
        print(f"Available types: {', '.join(type_mapping.keys())}")
        return 1
    
    print(f"🚀 Running {test_type} tests for Phase 1...")
    
    test_files = type_mapping[test_type]
    for test_file in test_files:
        test_path = test_dir / test_file
        if test_path.exists():
            cmd = [sys.executable, "-m", "pytest", str(test_path), "-v"]
            subprocess.run(cmd, cwd=str(project_root))
        else:
            print(f"❌ Test file not found: {test_path}")
    
    return 0


if __name__ == "__main__":
    # Allow running specific test types via command line
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        exit_code = run_specific_test_type(test_type)
    else:
        exit_code = main()
    
    sys.exit(exit_code)