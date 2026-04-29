"""Deb Feasibility Constrained GA Analysis Method

Implements a constrained single-objective GA using Deb's feasibility rules
(constraint-domination) instead of penalty-weighted fitness.

Comparison rules (Deb):
1) Feasible dominates infeasible
2) If both feasible: compare objective (base fitness) only
3) If both infeasible: prefer smaller constraint violation
   (tie-break by objective)

This method is additive-only and reuses the existing GA utilities.

Version: 1.96.0 (Experimental method extension)
"""

from __future__ import annotations

import os
import random
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ..base import AnalysisMethodBase, AnalysisResult
from ..utils import (
    analyze_population_diversity,
    crossover_with_retries,
    mutation_with_retries,
)
from ..utils.segment_metrics import average_length_excluding_gap_segments

# Import GA class and configuration (keep style consistent with other methods)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from analysis.utils.genetic_algorithm import HighwaySegmentGA  # noqa: E402
from config import get_optimization_method  # noqa: E402


class DebFeasibilityConstrainedMethod(AnalysisMethodBase):
    """Constrained GA using Deb feasibility comparisons (no penalty weight)."""

    @property
    def method_name(self) -> str:
        return "Constrained GA (Deb Feasibility)"

    @property
    def method_key(self) -> str:
        return "constrained_deb"

    @property
    def description(self) -> str:
        return (
            "Constraint-domination constrained GA (Deb feasibility rules). "
            "Feasible solutions always dominate infeasible ones; among feasible, "
            "optimize data fit (deviation fitness)."
        )

    def run_analysis(
        self,
        data: Any,
        route_id: str,
        x_column: str,
        y_column: str,
        gap_threshold: float,
        **kwargs,
    ) -> AnalysisResult:
        start_time = time.time()

        input_parameters = kwargs.get("input_parameters", None)
        log_callback = kwargs.get("log_callback", None)
        stop_callback = kwargs.get("stop_callback", None)

        if not hasattr(data, "route_data"):
            raise TypeError(
                "DebFeasibilityConstrainedMethod.run_analysis expects a RouteAnalysis object (with .route_data). "
                "Use analyze_route_gaps(...) to build one from a DataFrame."
            )

        def log(message: str) -> None:
            if log_callback:
                log_callback(message)
            else:
                print(message)

        method_config = get_optimization_method(self.method_key)
        param_defaults = {param.name: param.default_value for param in method_config.parameters}

        # Merge parameters: defaults <- input_parameters <- kwargs
        parameters = dict(param_defaults)
        if input_parameters:
            parameters.update(input_parameters)
        method_params = {
            k: v
            for k, v in kwargs.items()
            if k not in ["input_parameters", "log_callback", "stop_callback"]
        }
        parameters.update(method_params)

        min_length = parameters["min_length"]
        max_length = parameters["max_length"]
        population_size = int(parameters["population_size"])
        num_generations = int(parameters["num_generations"])
        crossover_rate = float(parameters["crossover_rate"])
        mutation_rate = float(parameters["mutation_rate"])
        elite_ratio = float(parameters["elite_ratio"])
        target_avg_length = float(parameters["target_avg_length"])
        length_tolerance = float(parameters["length_tolerance"])
        cache_clear_interval = int(parameters["cache_clear_interval"])
        enable_performance_stats = bool(parameters["enable_performance_stats"])

        log("Initializing Deb-feasibility constrained GA...")
        log(f"Target: {target_avg_length:.2f} mile average segments (±{length_tolerance:.2f} tolerance)")
        log(f"Parameters: {population_size} individuals, {num_generations} generations")

        ga = HighwaySegmentGA(
            data,
            x_column,
            y_column,
            min_length=min_length,
            max_length=max_length,
            population_size=population_size,
            mutation_rate=mutation_rate,
            crossover_rate=crossover_rate,
            gap_threshold=gap_threshold,
        )
        ga.enable_segment_cache_mode(True)

        # Gap-aware target info (used for diagnostics/data_summary only)
        route_df = data.route_data
        total_distance = route_df[x_column].max() - route_df[x_column].min()
        mandatory_breakpoints = sorted(list(ga.mandatory_breakpoints))
        target_segments = self._calculate_gap_aware_target(
            mandatory_breakpoints,
            total_distance,
            target_avg_length,
            min_length,
            max_length,
            log,
        )

        log("Generating diverse initial population...")
        population = ga.generate_diverse_initial_population()
        population = [
            ga._enforce_constraints(chrom) if not ga.validate_chromosome(chrom) else chrom
            for chrom in population
        ]
        log(f"[OK] Generated {len(population)} valid chromosomes")

        # Tracking
        best_base_fitness_history: List[float] = []
        best_violation_history: List[float] = []
        best_avg_length_history: List[float] = []
        generation_times: List[float] = []

        log("\nStarting Deb-feasibility evolution...")
        log("Progress: [" + "-" * 50 + "]")

        for generation in range(num_generations):
            if stop_callback and stop_callback():
                log(f"\n[STOPPED] Optimization stopped by user at generation {generation + 1}")
                break

            gen_start_time = time.time()

            progress_interval = max(1, num_generations // 50)
            if generation % progress_interval == 0:
                progress = int((generation / max(1, num_generations)) * 50)
                bar = "=" * progress + "-" * (50 - progress)
                log(f"\rProgress: [{bar}] {generation}/{num_generations} generations")

            eval_data = [
                self._evaluate_individual(chrom, ga, target_avg_length, length_tolerance)
                for chrom in population
            ]

            base_fitnesses = [e[0] for e in eval_data]
            avg_lengths = [e[1] for e in eval_data]
            deviations = [e[2] for e in eval_data]
            violations = [e[3] for e in eval_data]
            feasible_flags = [v <= 0.0 for v in violations]

            best_idx = self._best_index_deb(feasible_flags, violations, base_fitnesses)
            best_base_fitness_history.append(base_fitnesses[best_idx])
            best_violation_history.append(violations[best_idx])
            best_avg_length_history.append(avg_lengths[best_idx])

            if (generation + 1) % 50 == 0:
                diversity_stats = analyze_population_diversity(population)
                compliance = float(sum(1 for is_ok in feasible_flags if is_ok)) / float(len(feasible_flags) or 1)
                log(f"\nGen {generation + 1}: Best base fitness = {base_fitnesses[best_idx]:.6f}")
                log(
                    f"  Length: {avg_lengths[best_idx]:.3f} miles (target: {target_avg_length:.3f}, "
                    f"dev: {deviations[best_idx]:.3f}, violation: {violations[best_idx]:.3f})"
                )
                log(f"  Population compliance: {compliance:.1%}")
                log(
                    f"  Diversity: {diversity_stats['unique_segment_counts']} types, "
                    f"Range: {diversity_stats['min_segments']}-{diversity_stats['max_segments']} segments"
                )

            # Parent selection using Deb comparisons (tournament)
            parents = self._select_parents_deb(
                population,
                base_fitnesses,
                violations,
                num_parents=max(2, population_size // 2),
            )

            # Offspring generation
            offspring: List[List[float]] = []
            attempts = 0
            max_attempts = population_size * 10

            while len(offspring) < population_size and attempts < max_attempts:
                attempts += 1
                p1, p2 = random.sample(parents, 2)

                if random.random() < crossover_rate:
                    c1, c2 = crossover_with_retries(
                        p1,
                        p2,
                        ga.x_data,
                        ga.mandatory_breakpoints,
                        ga.validate_chromosome,
                    )
                    if c1 is None:
                        continue
                else:
                    c1, c2 = p1[:], p2[:]

                offspring.extend([c1, c2])

            if len(offspring) < population_size:
                log(
                    f"\n[WARNING] Offspring generation hit max attempts ({max_attempts}); "
                    f"padding with parent copies to reach population_size={population_size}"
                )
                while len(offspring) < population_size:
                    offspring.append(random.choice(parents)[:])

            offspring = offspring[:population_size]

            # Mutation
            for i in range(len(offspring)):
                if np.random.rand() < mutation_rate:
                    mutated = mutation_with_retries(
                        offspring[i],
                        ga.x_data,
                        ga.mandatory_breakpoints,
                        ga.validate_chromosome,
                    )
                    if mutated is not None:
                        offspring[i] = mutated

            offspring = [
                ga._enforce_constraints(chrom) if not ga.validate_chromosome(chrom) else chrom
                for chrom in offspring
            ]

            # Environmental selection with Deb ordering (elitism)
            offspring_eval = [
                self._evaluate_individual(chrom, ga, target_avg_length, length_tolerance)
                for chrom in offspring
            ]
            offspring_base = [e[0] for e in offspring_eval]
            offspring_viol = [e[3] for e in offspring_eval]

            population = self._elitist_selection_deb(
                population,
                base_fitnesses,
                violations,
                offspring,
                offspring_base,
                offspring_viol,
                elite_ratio,
            )

            if enable_performance_stats:
                generation_times.append(time.time() - gen_start_time)

            if (generation + 1) % cache_clear_interval == 0 and hasattr(ga, "clear_cache"):
                ga.clear_cache()

        elapsed_time = time.time() - start_time
        log(
            f"\rProgress: [{'=' * 50}] {num_generations}/{num_generations} generations - COMPLETE! ({elapsed_time:.1f}s)"
        )

        final_eval = [
            self._evaluate_individual(chrom, ga, target_avg_length, length_tolerance)
            for chrom in population
        ]
        final_base = [e[0] for e in final_eval]
        final_avg = [e[1] for e in final_eval]
        final_dev = [e[2] for e in final_eval]
        final_viol = [e[3] for e in final_eval]
        final_feasible = [v <= 0.0 for v in final_viol]

        best_idx = self._best_index_deb(final_feasible, final_viol, final_base)
        best_chromosome = population[best_idx]

        segments = [best_chromosome[i + 1] - best_chromosome[i] for i in range(len(best_chromosome) - 1)]

        best_solution: Dict[str, Any] = {
            "chromosome": best_chromosome,
            "fitness": final_base[best_idx],
            "objective_values": [final_base[best_idx], final_avg[best_idx]],
            "unconstrained_fitness": final_base[best_idx],
            "deviation_fitness": final_base[best_idx],
            "num_segments": len(best_chromosome) - 1,
            "avg_segment_length": final_avg[best_idx],
            "target_avg_length": target_avg_length,
            "length_deviation": final_dev[best_idx],
            "length_tolerance": length_tolerance,
            "constraint_violation": final_viol[best_idx],
            "segment_lengths": segments,
            "is_feasible": final_feasible[best_idx],
        }

        # Method-owned segmentation payload for export: average excludes gap-only segments.
        avg_excluding_gaps = average_length_excluding_gap_segments(
            best_chromosome,
            getattr(data, 'gap_segments', []),
        )
        best_solution["segmentation"] = {
            "breakpoints": best_chromosome,
            "segment_count": len(segments),
            "segment_lengths": segments,
            "total_length": (best_chromosome[-1] - best_chromosome[0]) if len(best_chromosome) >= 2 else 0.0,
            "average_segment_length": float(avg_excluding_gaps),
            "segment_details": [],
        }

        final_diversity = analyze_population_diversity(population)
        compliance = float(sum(1 for ok in final_feasible if ok)) / float(len(final_feasible) or 1)

        optimization_stats: Dict[str, Any] = {
            "total_generations": len(best_base_fitness_history),
            "generations_completed": len(best_base_fitness_history),
            "generations_run": len(best_base_fitness_history),
            "final_generation": len(best_base_fitness_history),
            "population_size": population_size,
            "best_base_fitness_history": best_base_fitness_history,
            "best_violation_history": best_violation_history,
            "best_avg_length_history": best_avg_length_history,
            "final_diversity": final_diversity,
            "target_compliance": compliance,
            "constraint_violations": len(final_feasible) - sum(1 for ok in final_feasible if ok),
            "tolerance_used": length_tolerance,
            "average_generation_time": float(np.mean(generation_times)) if generation_times else 0.0,
        }

        # Data summary consistent with constrained method
        if hasattr(ga, "route_analysis") and ga.route_analysis and hasattr(ga.route_analysis, "data_range"):
            data_range = ga.route_analysis.data_range
        else:
            data_range = {
                "x_min": float(route_df[x_column].min()),
                "x_max": float(route_df[x_column].max()),
                "y_min": float(route_df[y_column].min()),
                "y_max": float(route_df[y_column].max()),
            }

        data_summary = {
            "total_data_points": len(route_df),
            "data_range": data_range,
            "mandatory_breakpoints": list(ga.mandatory_breakpoints),
            "target_segments_calculated": target_segments,
            "gap_analysis": {
                "total_gaps": len(ga.route_analysis.gap_segments)
                if hasattr(ga, "route_analysis") and ga.route_analysis
                else 0,
                "gap_segments": [
                    {"start": gap[0], "end": gap[1], "length": gap[1] - gap[0]}
                    for gap in ga.route_analysis.gap_segments
                ]
                if hasattr(ga, "route_analysis") and ga.route_analysis
                else [],
                "total_gap_length": ga.route_analysis.route_stats.get("gap_total_length", 0.0)
                if hasattr(ga, "route_analysis") and ga.route_analysis
                else 0.0,
            },
        }

        log("\n=== DEB-FEASIBILITY CONSTRAINED RESULTS ===")
        log(f"Best base fitness: {best_solution['fitness']:.6f}")
        log(f"Segments: {best_solution['num_segments']}")
        log(
            f"Average segment length: {best_solution['avg_segment_length']:.3f} miles "
            f"(target: {target_avg_length:.3f})"
        )
        log(f"Length deviation: {best_solution['length_deviation']:.3f} miles")
        log(f"Feasible solution: {'Yes' if best_solution['is_feasible'] else 'No'}")
        log(f"Population compliance: {compliance:.1%}")
        log(f"Total time: {elapsed_time:.1f} seconds")
        log("[OK] Deb-feasibility constrained optimization complete!")

        resolved_route_id = getattr(data, "route_id", route_id) or route_id

        return AnalysisResult(
            method_name=self.method_name,
            method_key=self.method_key,
            route_id=resolved_route_id,
            all_solutions=[best_solution],
            optimization_stats=optimization_stats,
            mandatory_breakpoints=sorted(list(ga.mandatory_breakpoints)),
            processing_time=elapsed_time,
            input_parameters={**parameters, "gap_threshold": gap_threshold},
            data_summary=data_summary,
        )

    @staticmethod
    def _evaluate_individual(
        chromosome: List[float],
        ga: HighwaySegmentGA,
        target_avg_length: float,
        tolerance: float,
    ) -> Tuple[float, float, float, float]:
        """Return (base_fitness, avg_non_mandatory_length, deviation, violation)."""
        base_fitness = ga.fitness(chromosome)
        avg_length = ga._calculate_non_mandatory_avg_length(chromosome)
        deviation = abs(avg_length - target_avg_length)
        violation = max(0.0, deviation - tolerance)
        return float(base_fitness), float(avg_length), float(deviation), float(violation)

    @staticmethod
    def _best_index_deb(feasible: List[bool], violations: List[float], base_fitnesses: List[float]) -> int:
        """Return index of best individual by Deb ordering."""
        if not base_fitnesses:
            return 0

        best_idx = 0
        for i in range(1, len(base_fitnesses)):
            if DebFeasibilityConstrainedMethod._deb_better(
                feasible[i],
                violations[i],
                base_fitnesses[i],
                feasible[best_idx],
                violations[best_idx],
                base_fitnesses[best_idx],
            ):
                best_idx = i
        return best_idx

    @staticmethod
    def _deb_better(
        feas_a: bool,
        viol_a: float,
        fit_a: float,
        feas_b: bool,
        viol_b: float,
        fit_b: float,
    ) -> bool:
        """Return True if A is better than B by Deb rules."""
        if feas_a and not feas_b:
            return True
        if feas_b and not feas_a:
            return False
        if feas_a and feas_b:
            return fit_a > fit_b
        # both infeasible
        if viol_a < viol_b:
            return True
        if viol_b < viol_a:
            return False
        return fit_a > fit_b

    def _select_parents_deb(
        self,
        population: List[List[float]],
        base_fitnesses: List[float],
        violations: List[float],
        num_parents: int,
        tournament_size: int = 3,
    ) -> List[List[float]]:
        parents: List[List[float]] = []
        pop_size = len(population)
        if pop_size == 0 or num_parents <= 0:
            return parents

        t_size = min(max(2, tournament_size), pop_size)
        feasible = [v <= 0.0 for v in violations]

        for _ in range(num_parents):
            indices = random.sample(range(pop_size), k=t_size)
            winner = indices[0]
            for idx in indices[1:]:
                if self._deb_better(
                    feasible[idx],
                    violations[idx],
                    base_fitnesses[idx],
                    feasible[winner],
                    violations[winner],
                    base_fitnesses[winner],
                ):
                    winner = idx
            parents.append(population[winner])

        return parents

    def _elitist_selection_deb(
        self,
        population: List[List[float]],
        base_fitnesses: List[float],
        violations: List[float],
        offspring: List[List[float]],
        offspring_base: List[float],
        offspring_violations: List[float],
        elite_ratio: float,
    ) -> List[List[float]]:
        """Select next generation using Deb ordering with an elite carryover fraction."""
        combined = population + offspring
        combined_fit = list(base_fitnesses) + list(offspring_base)
        combined_viol = list(violations) + list(offspring_violations)
        combined_feas = [v <= 0.0 for v in combined_viol]

        # Sort by Deb ordering: feasible first, then violation asc, then base fitness desc
        indices = list(range(len(combined)))
        indices.sort(
            key=lambda i: (
                0 if combined_feas[i] else 1,
                combined_viol[i],
                -combined_fit[i],
            )
        )

        pop_size = len(population)
        elite_count = max(1, int(pop_size * elite_ratio))
        elite_indices = indices[:elite_count]

        # Fill remainder with best remaining individuals
        remaining = pop_size - elite_count
        selected_indices = elite_indices + indices[elite_count : elite_count + remaining]

        return [combined[i] for i in selected_indices]

    @staticmethod
    def _calculate_gap_aware_target(
        mandatory_breakpoints: List[float],
        total_distance: float,
        target_avg_length: float,
        min_length: float,
        max_length: float,
        log: Callable[[str], None],
    ) -> int:
        """Calculate realistic target segments considering mandatory breakpoints."""
        if len(mandatory_breakpoints) > 2:
            mandatory_distances = [
                mandatory_breakpoints[i + 1] - mandatory_breakpoints[i]
                for i in range(len(mandatory_breakpoints) - 1)
            ]
            mandatory_total_distance = float(sum(mandatory_distances))
            num_mandatory_segments = len(mandatory_distances)

            remaining_distance = float(total_distance - mandatory_total_distance)
            if remaining_distance > 0:
                total_segments_needed = float(total_distance / max(target_avg_length, 1e-9))
                target_regular_segments = max(0, int(round(total_segments_needed - num_mandatory_segments)))
                target_segments = num_mandatory_segments + target_regular_segments

                required_regular_avg = (
                    remaining_distance / target_regular_segments
                    if target_regular_segments > 0
                    else target_avg_length
                )

                log("Gap-aware calculation:")
                log(
                    f"  Mandatory segments: {num_mandatory_segments} covering {mandatory_total_distance:.2f} miles"
                )
                log(f"  Remaining distance: {remaining_distance:.2f} miles for regular segments")
                log(f"  Target regular segments: {target_regular_segments}")
                log(f"  Required regular avg: {required_regular_avg:.3f} miles")

                if required_regular_avg > max_length * 0.9:
                    log(
                        f"  WARNING: Required regular segment avg ({required_regular_avg:.2f}) is near max_length ({max_length:.2f})"
                    )
                elif required_regular_avg < min_length * 1.1:
                    log(
                        f"  WARNING: Required regular segment avg ({required_regular_avg:.2f}) is near min_length ({min_length:.2f})"
                    )
            else:
                target_segments = num_mandatory_segments
                log(f"  All distance covered by mandatory segments: {num_mandatory_segments} segments")
        else:
            target_segments = max(2, int(round(total_distance / max(target_avg_length, 1e-9))))
            log(f"Simple calculation (no gaps): {target_segments} segments for {total_distance:.2f} miles")

        return max(2, int(target_segments))
