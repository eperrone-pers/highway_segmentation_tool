#!/usr/bin/env python3

import sys
from pathlib import Path
from unittest.mock import Mock

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import OPTIMIZATION_METHODS, get_method_key_from_display_name

def test_display_names():
    """Simple test to verify display names are working correctly."""
    print("Testing display names...")
    
    for method in OPTIMIZATION_METHODS:
        print(f"  Method: '{method.display_name}' -> key: '{method.method_key}'")
    
    # Test the function that was failing
    print("\nTesting get_method_key_from_display_name function:")
    test_names = ['Single-Objective GA', 'Multi-Objective NSGA-II', 'Constrained Single-Objective']
    
    for name in test_names:
        try:
            key = get_method_key_from_display_name(name)
            print(f"  ✓ '{name}' -> '{key}'")
        except ValueError as e:
            print(f"  ❌ '{name}' -> ERROR: {e}")
    
    print("\n✅ Display name test completed")

if __name__ == "__main__":
    test_display_names()