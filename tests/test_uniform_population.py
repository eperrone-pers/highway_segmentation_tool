#!/usr/bin/env python3
"""
Test the uniform initial population generation algorithm
"""
import sys
sys.path.append('src')

import pandas as pd
from analysis.utils.genetic_algorithm import HighwaySegmentGA
from data_loader import analyze_route_gaps
from config import optimization_config

def test_uniform_population():
    """Test the uniform initial population generation algorithm"""
    
    # Load data
    data = pd.read_csv('data/txdot_data.csv')
    # Use default highway column names for analysis
    x_column, y_column = "milepoint", "structural_strength_ind"
    route_analysis = analyze_route_gaps(data, x_column, y_column, route_id="UNIFORM_POPULATION_TEST", gap_threshold=0.5)
    
    # Create GA instance
    ga = HighwaySegmentGA(
        data=route_analysis,
        x_column=x_column,
        y_column=y_column,
        min_length=0.5,
        max_length=5.0,
        population_size=100,  # Use 100 for good bin distribution
        mutation_rate=0.05,
        crossover_rate=0.8,
        gap_threshold=0.5,
    )
    
    print("=== TESTING UNIFORM INITIAL POPULATION ===")
    print(f"Population size: {ga.population_size}")
    print()
    
    # Generate initial population
    population = ga.generate_diverse_initial_population()
    
    # Analyze results
    segment_counts = [len(chrom) - 1 for chrom in population]
    segment_counts.sort()
    
    print(f"\n=== RESULTS ANALYSIS ===")
    print(f"Population generated: {len(population)} solutions")
    print(f"Segment range: {min(segment_counts)} - {max(segment_counts)}")
    print(f"Average segments: {sum(segment_counts) / len(segment_counts):.1f}")
    
    # Count solutions in different ranges
    ranges = [
        (0, 30, "Low (0-30)"),
        (30, 50, "Medium-Low (30-50)"), 
        (50, 70, "Medium-High (50-70)"),
        (70, 90, "High (70-90)"),
        (90, 120, "Very High (90-120)"),
        (120, 150, "Extreme (120+)")
    ]
    
    for min_range, max_range, label in ranges:
        count = sum(1 for s in segment_counts if min_range <= s < max_range)
        percent = (count / len(segment_counts)) * 100
        print(f"  {label}: {count} solutions ({percent:.1f}%)")
    
    # Show top and bottom segments
    print(f"\nTop 10 highest: {segment_counts[-10:]}")
    print(f"Bottom 10 lowest: {segment_counts[:10]}")
    
    # Check if we achieved the goal
    high_segment_count = sum(1 for s in segment_counts if s >= 80)
    very_high_count = sum(1 for s in segment_counts if s >= 100)
    
    print(f"\n=== SUCCESS METRICS ===")
    print(f"Solutions ≥80 segments: {high_segment_count} ({high_segment_count/len(population)*100:.1f}%)")
    print(f"Solutions ≥100 segments: {very_high_count} ({very_high_count/len(population)*100:.1f}%)")
    print(f"Maximum achieved: {max(segment_counts)} segments")
    
    if max(segment_counts) >= 100:
        print("✅ SUCCESS: Achieved 100+ segment solutions!")
    elif max(segment_counts) >= 80:
        print("⚠️  PARTIAL: Achieved 80+ but not 100+ segments")
    else:
        print("❌ FAILURE: Did not achieve 80+ segment solutions")

if __name__ == "__main__":
    test_uniform_population()