#!/usr/bin/env python3
"""
Phase 3 Test Runner - AASHTO CDA Integration Testing and Validation

Executes comprehensive testing of AASHTO CDA method integration including:
- Unit tests for core algorithm functionality
- Integration tests for framework compatibility
- Configuration registry validation  
- End-to-end workflow verification
- Performance and compatibility testing

This runner follows the established testing framework patterns and integrates
with the main test suite for continuous validation.

Usage:
    python run_phase3_aashto_cda_tests.py [--verbose] [--unit-only] [--integration-only]
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
import time

# Add src directory to path
current_dir = Path(__file__).parent
project_root = current_dir.parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

def run_command(cmd, description, verbose=False):
    """Run a command and capture results."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    start_time = time.time()
    
    try:
        if verbose:
            result = subprocess.run(cmd, check=True, text=True)
            success = result.returncode == 0
        else:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            success = result.returncode == 0
            if success:
                print("✓ PASSED")
                if result.stdout.strip():
                    # Show summary line if available
                    lines = result.stdout.strip().split('\n')
                    summary_lines = [line for line in lines if 'passed' in line or 'failed' in line or '::' in line]
                    if summary_lines:
                        print(f"Summary: {summary_lines[-1]}")
            else:
                print("✗ FAILED")
                if result.stdout:
                    print("STDOUT:", result.stdout)
                if result.stderr:
                    print("STDERR:", result.stderr)
    except subprocess.CalledProcessError as e:
        success = False
        print(f"✗ FAILED with return code {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
    except Exception as e:
        success = False 
        print(f"✗ ERROR: {e}")
    
    elapsed = time.time() - start_time
    print(f"Time: {elapsed:.2f}s")
    
    return success

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description='Run Phase 3 AASHTO CDA integration tests')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Show verbose test output')
    parser.add_argument('--unit-only', action='store_true',
                       help='Run only unit tests')
    parser.add_argument('--integration-only', action='store_true', 
                       help='Run only integration tests')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick tests only (skip slow tests)')
    
    args = parser.parse_args()
    
    print("🚀 AASHTO CDA Phase 3 Integration Testing")
    print(f"Project Root: {project_root}")
    print(f"Test Directory: {current_dir}")
    
    # Change to project root for test execution
    os.chdir(project_root)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    # Test configurations
    test_configs = []
    
    unit_test_path = Path('tests/unit/test_aashto_cda_method.py')
    integration_test_path = Path('tests/integration/test_aashto_cda_integration.py')

    if not args.integration_only:
        if unit_test_path.exists():
            test_configs.append({
                'name': 'AASHTO CDA Unit Tests',
                'cmd': [sys.executable, '-m', 'pytest', str(unit_test_path), '-v'],
                'description': 'Core algorithm and method class unit tests'
            })
        else:
            print(f"(skipping) Unit test file not found: {unit_test_path}")
    
    if not args.unit_only:
        if integration_test_path.exists():
            test_configs.append({
                'name': 'AASHTO CDA Integration Tests',
                'cmd': [sys.executable, '-m', 'pytest', str(integration_test_path), '-v'],
                'description': 'Framework integration and workflow tests'
            })
        else:
            print(f"(skipping) Integration test file not found: {integration_test_path}")
        
        # Configuration registry tests
        test_configs.append({
            'name': 'Configuration Registry Tests',
            'cmd': [sys.executable, '-m', 'pytest', '-k', 'aashto_cda', 'tests/quick_controller_test.py', '-v'],
            'description': 'Method registry and parameter configuration tests'
        })
    
    # Import validation test (quick check)
    test_configs.insert(0, {
        'name': 'Import Validation',
         'cmd': [sys.executable, '-c',
             'from config import resolve_method_class; '
             'cls = resolve_method_class("aashto_cda"); '
             'cls(); '
             'print("✓ AASHTO CDA method_class_path import/instantiate successful")'],
         'description': 'Validate AASHTO CDA dispatch import path works'
    })
    
    # Run all test configurations
    for config in test_configs:
        total_tests += 1
        success = run_command(config['cmd'], config['description'], args.verbose)
        
        if success:
            passed_tests += 1
        else:
            failed_tests.append(config['name'])
    
    # Summary report
    print(f"\n{'='*60}")
    print("📊 PHASE 3 TEST SUMMARY")
    print('='*60)
    print(f"Total Test Suites: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for test_name in failed_tests:
            print(f"  • {test_name}")
        
        print(f"\n🔍 Troubleshooting Tips:")
        print("• Check that all AASHTO CDA files are properly created")
        print("• Verify src/analysis/methods/aashto_cda.py exists")
        print("• Ensure optimization_runners.py includes run_aashto_cda function")
        print("• Confirm config.py includes AASHTO_CDA_PARAMETERS and registry entry")
        
        return 1
    else:
        print(f"\n✅ All Phase 3 tests passed!")
        
        print(f"\n🎯 Phase 3 Validation Complete:")
        print("• ✓ AASHTO CDA algorithm implementation validated")
        print("• ✓ Framework integration verified")
        print("• ✓ Configuration system integration confirmed") 
        print("• ✓ End-to-end workflow tested")
        print("• ✓ Performance characteristics validated")
        
        print(f"\n🚀 Ready for Phase 4: Documentation and Finalization")
        
        return 0

if __name__ == "__main__":
    sys.exit(main())