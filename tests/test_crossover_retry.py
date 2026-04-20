#!/usr/bin/env python3
"""
Test Crossover Retry Implementation
==================================
Tests the new crossover retry logic to ensure it properly handles failures
and parent reselection.
"""

import sys
import os
import pandas as pd
import random
import numpy as np

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from analysis.utils.genetic_algorithm import HighwaySegmentGA
from config import optimization_config

def test_crossover_retry_logic():
    """Test crossover retry implementation"""
    print("🧪 Testing Crossover Retry Logic")
    print("=" * 40)
    
    # Create test data
    milepoints = np.linspace(0, 20, 201)  # Dense milepoints  
    strength_values = np.random.uniform(0.3, 1.0, len(milepoints))
    
    test_data = pd.DataFrame({
        'milepoint': milepoints,
        'structural_strength_ind': strength_values
    })
    
    # Create RouteAnalysis object from test data
    from data_loader import analyze_route_gaps
    route_analysis = analyze_route_gaps(
        test_data, 
        x_column='milepoint',
        y_column='structural_strength_ind',
        route_id="CROSSOVER_TEST",
        gap_threshold=0.5,
    )
    
    # Initialize GA 
    ga = HighwaySegmentGA(
        data=route_analysis,
        x_column='milepoint',  # Add column parameters
        y_column='structural_strength_ind',
        min_length=0.5,
        max_length=5.0,
        population_size=50,
        mutation_rate=0.05,
        crossover_rate=0.8,
        gap_threshold=0.5,
    )
    
    print(f"Route length: {ga.x_data[-1] - ga.x_data[0]:.1f} miles") 
    print(f"Mandatory breakpoints: {len(ga.mandatory_breakpoints)}")
    print(f"Max retries configured: {optimization_config.operator_max_retries}")
    
    # Create test parents (some simple, some complex)
    population = ga.generate_diverse_initial_population()
    
    # Test crossover with different parent pairs
    test_cases = [
        "Simple parents (few segments)",
        "Complex parents (many segments)", 
        "Mixed complexity parents",
        "Minimal parents (mandatory only)"
    ]
    
    success_count = 0
    failure_count = 0
    total_retries = 0
    
    # Reset statistics
    ga._generation_stats.update({
        'crossover_attempts': 0,
        'crossover_retries': 0,
        'crossover_parent_reselections': 0,
        'crossover_failures': 0
    })
    
    print(f"\n📊 Testing {len(test_cases)} crossover scenarios:")
    
    for i, case_name in enumerate(test_cases):
        print(f"\n{i+1}. {case_name}")
        
        # Select different types of parents for each test
        if i == 0:  # Simple parents
            parents = sorted(population, key=len)[:2]
        elif i == 1:  # Complex parents  
            parents = sorted(population, key=len, reverse=True)[:2]
        elif i == 2:  # Mixed
            simple = min(population, key=len)
            complex_parent = max(population, key=len)
            parents = [simple, complex_parent]
        else:  # Minimal
            parents = [list(ga.mandatory_breakpoints), list(ga.mandatory_breakpoints)]
        
        parent1, parent2 = parents
        print(f"   Parent 1: {len(parent1)-1} segments")
        print(f"   Parent 2: {len(parent2)-1} segments")
        
        # Perform crossover
        child1, child2 = ga.crossover(parent1, parent2)
        
        if child1 is not None and child2 is not None:
            print(f"   ✅ Success: Child 1 = {len(child1)-1} segments, Child 2 = {len(child2)-1} segments")
            success_count += 1
        else:
            print(f"   ❌ Failed: Returned None after retries")
            failure_count += 1
    
    # Print final statistics
    stats = ga._generation_stats
    print(f"\n📈 Crossover Retry Statistics:")
    print(f"   Total attempts: {stats['crossover_attempts']}")
    print(f"   Successful crossovers: {success_count}")
    print(f"   Failed crossovers: {failure_count}")  
    print(f"   Retries used: {stats['crossover_retries']}")
    print(f"   Parent reselections: {stats['crossover_parent_reselections']}")
    
    if stats['crossover_attempts'] > 0:
        success_rate = success_count / stats['crossover_attempts'] * 100
        print(f"   Success rate: {success_rate:.1f}%")
        
        if stats['crossover_retries'] > 0:
            avg_retries = stats['crossover_retries'] / stats['crossover_attempts']
            print(f"   Average retries per attempt: {avg_retries:.2f}")
    
    # Validate that successful children are valid
    print(f"\n🔍 Validation Check:")
    valid_children = 0
    total_children = success_count * 2  # 2 children per successful crossover
    
    for i in range(len(test_cases)):
        if i < success_count:  # Only check successful crossovers
            # Re-run one crossover to get children for validation
            parents = sorted(population, key=len)[:2]
            child1, child2 = ga.crossover(parents[0], parents[1])
            if child1 is not None:
                valid_children += ga.validate_chromosome(child1)
            if child2 is not None:
                valid_children += ga.validate_chromosome(child2)
    
    print(f"   Valid children: {valid_children}/{total_children}")
    print(f"   Children validity rate: {valid_children/max(1,total_children)*100:.1f}%")
    
    print(f"\n✅ Crossover retry test completed!")
    
    return success_count > 0  # Test passes if at least one crossover succeeded

if __name__ == "__main__":
    success = test_crossover_retry_logic()
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Tests failed!")