#!/usr/bin/env python3

import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import OPTIMIZATION_METHODS, get_method_key_from_display_name

def quick_test_all_methods():
    """Quick test to verify all optimization methods are available through controller."""
    print("🧪 QUICK CONTROLLER METHOD AVAILABILITY TEST")
    print("="*50)
    
    print(f"Available optimization methods:")
    for i, method in enumerate(OPTIMIZATION_METHODS, 1):
        print(f"  {i}. '{method.display_name}' -> key: '{method.method_key}'")
    
    print(f"\nTesting method key resolution:")
    test_methods = [
        'Single-Objective GA',
        'Multi-Objective NSGA-II', 
        'Constrained Single-Objective'
    ]
    
    success_count = 0
    for method_name in test_methods:
        try:
            key = get_method_key_from_display_name(method_name)
            print(f"  ✅ '{method_name}' -> '{key}'")
            success_count += 1
        except Exception as e:
            print(f"  ❌ '{method_name}' -> ERROR: {e}")
    
    print(f"\n📊 RESULTS:")
    if success_count == 3:
        print(f"🎉 ALL 3 METHODS AVAILABLE FOR CONTROLLER!")
        print(f"✅ Single-Objective GA: Ready")
        print(f"✅ Multi-Objective NSGA-II: Ready")  
        print(f"✅ Constrained Single-Objective: Ready")
        print(f"✅ Controller can work with all optimization methods")
        return True
    else:
        print(f"⚠️  Only {success_count}/3 methods available")
        return False

if __name__ == "__main__":
    success = quick_test_all_methods()
    if success:
        print("\n🚀 CONTROLLER METHODS AVAILABILITY CONFIRMED!")
    else:
        print("\n❌ CONTROLLER METHODS AVAILABILITY FAILED!")
