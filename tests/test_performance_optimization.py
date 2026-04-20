#!/usr/bin/env python3
"""
Performance Optimization Test for Population Generation
=====================================================
Tests the optimized _generate_chromosome_by_splitting method performance
using the test TxDOT data in tests/test_data/txdot_data.csv.

This test can be run repeatedly to validate performance improvements
and ensure optimization changes don't introduce regressions.

Usage: python test_performance_optimization.py (from tests directory)
"""

import sys
import os
import time
import numpy as np
import pandas as pd

# Add src to Python path for imports (from tests directory)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_with_real_data():
    """Test performance improvement using real TxDOT data"""
    print("🚀 Performance Test with Real TxDOT Data")
    print("=" * 50)
    
    # Load the real data from test data directory
    data_file = 'test_data/txdot_data.csv'
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return
    
    try:
        from analysis.utils.genetic_algorithm import HighwaySegmentGA
        print("✅ Successfully imported HighwaySegmentGA")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return
        
    # Load real data
    try:
        data = pd.read_csv(data_file)
        print(f"✅ Loaded {len(data)} data points from {data_file}")
        print(f"   Milepoint range: {data['milepoint'].min():.1f} - {data['milepoint'].max():.1f}")
        
        # Display first few rows to understand structure
        print(f"   Data columns: {list(data.columns)}")
        
        # Create RouteAnalysis object from loaded data
        from data_loader import analyze_route_gaps
        route_analysis = analyze_route_gaps(
            data, 
            x_column='milepoint',
            y_column='structural_strength_ind',
            route_id="PERFORMANCE_TEST",
            gap_threshold=0.5,
        )
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    # Initialize GA with real data and specified parameters
    try:
        ga = HighwaySegmentGA(
            data=route_analysis,
            x_column='milepoint',  # Add column parameters
            y_column='structural_strength_ind',
            min_length=0.5,
            max_length=5.0,
            population_size=100,
            mutation_rate=0.05,
            crossover_rate=0.8,
            gap_threshold=0.5,
        )
        print(f"✅ Initialized GA with real data")
        print(f"   Route length: {ga.milepoints[-1] - ga.milepoints[0]:.1f} miles")
        print(f"   Mandatory breakpoints: {len(ga.mandatory_breakpoints)} points")
        
    except Exception as e:
        print(f"❌ GA initialization error: {e}")
        return
    
    # Test individual splitting method performance
    print(f"\n🎯 Testing Optimized Splitting Method")
    print("-" * 40)
    
    test_targets = [8, 12, 15, 20]  # Various segment counts to test
    route_length = ga.milepoints[-1] - ga.milepoints[0]
    
    total_time = 0
    total_calls = 0
    
    for target in test_targets:
        print(f"\nTarget segments: {target}")
        run_times = []
        segment_counts = []
        
        # Run multiple times for statistical significance
        for run in range(5):  # 5 runs per target
            start_time = time.perf_counter()
            
            try:
                result = ga._generate_chromosome_by_splitting(
                    target_segments=target,
                    mandatory_list=ga.mandatory_breakpoints,
                    splittable_length=route_length
                )
                
                end_time = time.perf_counter()
                run_time = end_time - start_time
                run_times.append(run_time)
                segment_counts.append(len(result) - 1)
                
            except Exception as e:
                print(f"   ⚠️ Error in run {run+1}: {e}")
                continue
        
        if run_times:
            avg_time = np.mean(run_times)
            avg_segments = np.mean(segment_counts)
            min_time, max_time = min(run_times), max(run_times)
            
            print(f"   Average time: {avg_time*1000:.2f}ms")
            print(f"   Time range: {min_time*1000:.2f} - {max_time*1000:.2f}ms")
            print(f"   Average segments: {avg_segments:.1f} (target: {target})")
            
            total_time += sum(run_times)
            total_calls += len(run_times)
    
    if total_calls > 0:
        avg_per_call = total_time / total_calls
        print(f"\n📊 Splitting Method Performance:")
        print(f"   Total test calls: {total_calls}")
        print(f"   Average time per call: {avg_per_call*1000:.2f}ms")
        
        # Compare against baseline (33ms from validation)
        baseline_time = 0.033
        if avg_per_call < baseline_time:
            speedup = baseline_time / avg_per_call
            print(f"   ✅ Speedup vs baseline: {speedup:.1f}x faster!")
        else:
            slowdown = avg_per_call / baseline_time
            print(f"   ⚠️ Slowdown vs baseline: {slowdown:.1f}x slower")
    
    # Test full population generation
    print(f"\n🏭 Full Population Generation Performance:")
    print("-" * 45)
    
    try:
        start_time = time.perf_counter()
        population = ga.generate_diverse_initial_population()
        end_time = time.perf_counter()
        
        generation_time = end_time - start_time
        
        # Analyze population quality
        valid_count = 0
        segment_counts = []
        
        for chromo in population:
            if ga.validate_chromosome(chromo):
                valid_count += 1
            segment_counts.append(len(chromo) - 1)
        
        print(f"   Population size: {len(population)}")
        print(f"   Valid chromosomes: {valid_count}/{len(population)} ({valid_count/len(population)*100:.1f}%)")
        print(f"   Generation time: {generation_time:.3f}s")
        print(f"   Time per chromosome: {generation_time/len(population)*1000:.2f}ms")
        print(f"   Segment count range: {min(segment_counts)} - {max(segment_counts)}")
        print(f"   Average segments: {np.mean(segment_counts):.1f}")
        
        # Compare with baseline
        baseline_pop_time = 0.033  # From validation
        if generation_time < baseline_pop_time:
            improvement = baseline_pop_time / generation_time  
            print(f"   ✅ Performance improvement: {improvement:.1f}x faster!")
        else:
            regression = generation_time / baseline_pop_time
            print(f"   ⚠️ Performance regression: {regression:.1f}x slower")
            
    except Exception as e:
        print(f"❌ Population generation error: {e}")
        
    print(f"\n✅ Performance test completed successfully!")

if __name__ == "__main__":
    test_with_real_data()