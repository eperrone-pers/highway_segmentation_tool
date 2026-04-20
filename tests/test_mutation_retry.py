#!/usr/bin/env python3
"""
Test Mutation Retry Implementation
=================================
Tests the new mutation retry logic to ensure it properly handles failures
and chromosome reselection.
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

def test_mutation_retry_logic():
    """Test mutation retry implementation"""
    print("🧪 Testing Mutation Retry Logic")
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
        route_id="MUTATION_TEST",
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
    
    # Create test population for chromosomes to mutate
    population = ga.generate_diverse_initial_population()
    
    # Test mutation with different chromosome types
    test_cases = [
        "Simple chromosome (few segments)",
        "Complex chromosome (many segments)", 
        "Medium chromosome (moderate segments)",
        "Minimal chromosome (mandatory only)"
    ]
    
    success_count = 0
    failure_count = 0
    kept_original_count = 0
    
    # Reset statistics
    ga._generation_stats.update({
        'mutation_attempts': 0,
        'mutation_retries': 0,
        'mutation_reselections': 0
    })
    
    print(f"\n📊 Testing {len(test_cases)} mutation scenarios:")
    
    for i, case_name in enumerate(test_cases):
        print(f"\n{i+1}. {case_name}")
        
        # Select different types of chromosomes for each test
        if i == 0:  # Simple chromosome
            chromosome = min(population, key=len)
        elif i == 1:  # Complex chromosome  
            chromosome = max(population, key=len)
        elif i == 2:  # Medium
            sorted_pop = sorted(population, key=len)
            mid_idx = len(sorted_pop) // 2
            chromosome = sorted_pop[mid_idx]
        else:  # Minimal (mandatory only)
            chromosome = list(ga.mandatory_breakpoints)
        
        original_segments = len(chromosome) - 1
        print(f"   Original: {original_segments} segments")
        
        # Perform mutation
        mutated = ga.mutate(chromosome)
        
        if mutated is not None:
            mutated_segments = len(mutated) - 1
            if mutated != chromosome:
                print(f"   ✅ Success: Mutated to {mutated_segments} segments")
                success_count += 1
            else:
                print(f"   ✅ No change: Kept original {original_segments} segments")
                kept_original_count += 1
        else:
            print(f"   ❌ Failed: Returned None after retries")
            failure_count += 1
    
    # Test edge cases
    print(f"\n🔬 Edge Case Testing:")
    
    # Test with chromosome that has no optional breakpoints
    mandatory_only = list(ga.mandatory_breakpoints)
    print(f"5. Mandatory-only chromosome ({len(mandatory_only)-1} segments)")
    mutated = ga.mutate(mandatory_only)
    if mutated is not None:
        if len(mutated) > len(mandatory_only):
            print(f"   ✅ Success: Added breakpoint(s) to get {len(mutated)-1} segments")
            success_count += 1
        else:
            print(f"   ✅ No change: Kept mandatory-only structure")
            kept_original_count += 1
    else:
        print(f"   ❌ Failed: Returned None")
        failure_count += 1
    
    # Print final statistics
    stats = ga._generation_stats
    total_attempts = stats['mutation_attempts']
    
    print(f"\n📈 Mutation Retry Statistics:")
    print(f"   Total attempts: {total_attempts}")
    print(f"   Successful mutations: {success_count}")
    print(f"   Kept original (valid but no change): {kept_original_count}")
    print(f"   Failed mutations: {failure_count}")  
    print(f"   Retries used: {stats['mutation_retries']}")
    print(f"   Chromosome reselections: {stats['mutation_reselections']}")
    
    if total_attempts > 0:
        success_rate = (success_count + kept_original_count) / total_attempts * 100
        print(f"   Overall success rate: {success_rate:.1f}%")
        
        if stats['mutation_retries'] > 0:
            avg_retries = stats['mutation_retries'] / total_attempts
            print(f"   Average retries per attempt: {avg_retries:.2f}")
    
    # Validate that successful mutations are valid
    print(f"\n🔍 Validation Check:")
    print(f"   Testing mutations on sample population...")
    
    valid_mutations = 0
    total_mutations = 0
    
    # Test mutation on a sample of population
    for i, chrom in enumerate(population[:10]):  # Test first 10 chromosomes
        mutated = ga.mutate(chrom)
        if mutated is not None:
            total_mutations += 1
            if ga.validate_chromosome(mutated):
                valid_mutations += 1
    
    if total_mutations > 0:
        validity_rate = valid_mutations / total_mutations * 100
        print(f"   Valid mutations: {valid_mutations}/{total_mutations} ({validity_rate:.1f}%)")
    else:
        print(f"   No successful mutations to validate")
    
    print(f"\n✅ Mutation retry test completed!")
    
    # Test passes if we had some successful mutations and all were valid
    return success_count > 0 and (total_mutations == 0 or validity_rate == 100.0)

if __name__ == "__main__":
    success = test_mutation_retry_logic()
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Tests failed!")