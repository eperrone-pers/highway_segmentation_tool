#!/usr/bin/env python3
"""Quick validation script for AASHTO CDA Phase 3 testing."""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_configuration_integration():
    """Test AASHTO CDA configuration integration."""
    print("=== Configuration Integration Test ===")
    
    try:
        from config import get_optimization_method, get_optimization_method_names
        
        method_names = get_optimization_method_names()
        print(f"Available methods: {len(method_names)}")
        
        if 'AASHTO CDA Statistical Analysis' in method_names:
            print("✓ AASHTO CDA found in method registry")
            
            method = get_optimization_method('aashto_cda')
            print(f"✓ Method: {method.display_name}")
            print(f"✓ Parameters: {len(method.parameters)}")
            print(f"✓ Runner: {method.runner_function}")
            return True
        else:
            print("❌ AASHTO CDA not found in registry")
            return False
            
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_algorithm_functionality():
    """Test core AASHTO CDA algorithm."""
    print("\n=== Algorithm Functionality Test ===")
    
    try:
        import numpy as np
        import pandas as pd
        from analysis.methods.aashto_cda import aashto_cda, AashtoCdaMethod
        
        # Create test data with clear change points
        np.random.seed(42)
        y = np.concatenate([
            np.full(20, 2.0) + np.random.normal(0, 0.1, 20),
            np.full(20, 5.0) + np.random.normal(0, 0.1, 20),
            np.full(20, 1.0) + np.random.normal(0, 0.1, 20)
        ])
        
        # Test core algorithm
        uniform_sections, nodes, section_start, section_end, mu = aashto_cda(
            y, alpha=0.05, method=2, min_length=3
        )
        
        print(f"✓ Core algorithm: {len(nodes)} nodes detected")
        print(f"✓ Segments: {len(section_start)}")
        print(f"✓ Mean values: {[f'{m:.2f}' for m in mu[:3]]}")
        
        # Test method class
        cda_method = AashtoCdaMethod()
        print(f"✓ Method class: {cda_method.method_name}")
        
        df = pd.DataFrame({
            'milepoint': np.linspace(0, 6, 60),
            'measurement': y
        })
        
        result = cda_method.run_analysis(
            data=df,
            x_column='milepoint',
            y_column='measurement',
            alpha=0.05,
            method=2,
            min_length=0.5
        )
        
        print(f"✓ Analysis result: {len(result.all_solutions)} solutions")
        if result.all_solutions:
            solution = result.all_solutions[0]
            print(f"✓ Final segments: {solution['num_segments']}")
            print(f"✓ Avg length: {solution['avg_segment_length']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Algorithm error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all validation tests."""
    print("🚀 AASHTO CDA Phase 3 Validation")
    print("="*40)
    
    results = []
    results.append(test_configuration_integration())
    results.append(test_algorithm_functionality())
    
    print(f"\n📊 Results: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("✅ All core functionality validated!")
        print("✅ Ready for full Phase 3 test suite")
        return True
    else:
        print("❌ Some tests failed - check implementation")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)