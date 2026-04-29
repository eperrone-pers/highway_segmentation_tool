#!/usr/bin/env python3
"""
Diagnostic test for high-segment chromosome generation and preservation
"""
import sys
sys.path.append('src')

import pandas as pd
import random
from analysis.utils.genetic_algorithm import HighwaySegmentGA
from data_loader import analyze_route_gaps

def _run_high_segment_generation_diagnostic():
    """Test if we can generate and preserve high-segment chromosomes"""
    
    # Load data
    data = pd.read_csv('tests/test_data/test_data_single_route.csv')
    # Use default highway column names for analysis
    x_column, y_column = "milepoint", "structural_strength_ind"
    route_analysis = analyze_route_gaps(data, x_column, y_column, route_id="HIGH_SEGMENTS_TEST", gap_threshold=0.5)
    
    # Create GA instance
    ga = HighwaySegmentGA(
        data=route_analysis,
        x_column=x_column,
        y_column=y_column,
        min_length=0.5,
        max_length=5.0,
        population_size=50,
        mutation_rate=0.05,
        crossover_rate=0.8,
        gap_threshold=0.5,
    )
    
    print("=== HIGH-SEGMENT CHROMOSOME DIAGNOSTIC TEST ===")
    print(f"Theoretical max segments: {int((data[x_column].max() - data[x_column].min()) / 0.5)}")
    print(f"Mandatory breakpoints: {len(ga.mandatory_breakpoints)}")
    print()
    
    # Test 1: Direct high-segment generation
    print("TEST 1: Direct generation of high-segment chromosomes")
    high_segment_targets = [80, 90, 100, 110, 120]
    
    for target in high_segment_targets:
        try:
            chrome = ga.generate_chromosome_with_target_segments(target)
            actual_segments = len(chrome) - 1
            print(f"  Target {target} segments -> Got {actual_segments} segments")
            
            # Test constraint enforcement impact
            constrained = ga._enforce_constraints(chrome.copy())
            final_segments = len(constrained) - 1
            print(f"    After constraints: {final_segments} segments (lost {actual_segments - final_segments})")
            
        except Exception as e:
            print(f"  Target {target} segments -> FAILED: {e}")
    
    print()
    
    # Test 2: Initial population analysis
    print("TEST 2: Initial population segment distribution")
    population = ga.generate_diverse_initial_population()
    
    segment_counts = [len(chrome) - 1 for chrome in population]
    segment_counts.sort()
    
    print(f"  Population size: {len(population)}")
    print(f"  Segment range: {min(segment_counts)} - {max(segment_counts)}")
    print(f"  Average segments: {sum(segment_counts) / len(segment_counts):.1f}")
    
    # Count high-segment solutions
    thresholds = [50, 60, 70, 80, 90, 100]
    for threshold in thresholds:
        count = sum(1 for s in segment_counts if s >= threshold)
        percent = (count / len(segment_counts)) * 100
        print(f"  Solutions >= {threshold} segments: {count} ({percent:.1f}%)")
    
    print()
    print(f"Top 10 highest: {segment_counts[-10:]}")
    print(f"Bottom 10 lowest: {segment_counts[:10]}")
    
    return max(segment_counts)


def test_high_segment_generation():
    """Pytest entrypoint for the high-segment diagnostic."""
    max_achieved = _run_high_segment_generation_diagnostic()
    assert isinstance(max_achieved, int)

if __name__ == "__main__":
    max_achieved = _run_high_segment_generation_diagnostic()
    print(f"\n=== SUMMARY ===")
    print(f"Maximum segments achieved: {max_achieved}")
    print(f"Target (theoretical max): 126")
    
    if max_achieved < 80:
        print("❌ PROBLEM: Not generating high-segment solutions")
        print("💡 DIAGNOSIS: Issue with chromosome generation or constraint enforcement")
    elif max_achieved >= 100:
        print("✅ SUCCESS: High-segment generation working!")
    else:
        print("⚠️  PARTIAL: Some high segments but not reaching full potential")