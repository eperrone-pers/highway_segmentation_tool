"""Quick performance comparison: single vs multi objective methods.

Runs both methods on the same route with a fixed seed and instruments
crossover/mutation retry attempts to show where time is going.

Usage examples:
  python perf_compare_single_vs_multi.py --route "FM1836 K" --gens 500 --pop 100
  python perf_compare_single_vs_multi.py --route "FM1936 Test" --gens 200 --pop 100
"""

from __future__ import annotations

import argparse
import random
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class OperatorStats:
    crossover_calls: int = 0
    crossover_attempts: int = 0
    crossover_failed_pairs: int = 0

    mutation_calls: int = 0
    mutation_attempts: int = 0
    mutation_failed: int = 0


def _load_route_df(csv_path: Path, route_column: str, route_id: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if route_column not in df.columns:
        raise ValueError(f"Route column '{route_column}' not in CSV columns: {list(df.columns)}")
    df_route = df[df[route_column] == route_id].copy()
    if df_route.empty:
        raise ValueError(f"No rows found for route_id='{route_id}'")
    return df_route


def _instrument_operators(stats: OperatorStats):
    """Monkeypatch method modules to wrap real crossover/mutation.

    This preserves current operator behavior while counting call/failure rates.
    """
    import analysis.utils.ga_utilities as gau
    import analysis.methods.single_objective as single_mod
    import analysis.methods.multi_objective as multi_mod

    def crossover_with_retries(parent1, parent2, x_data, mandatory_breakpoints, validate_function):
        stats.crossover_calls += 1
        child1, child2 = gau.crossover_with_retries(parent1, parent2, x_data, mandatory_breakpoints, validate_function)
        if child1 is None or child2 is None:
            stats.crossover_failed_pairs += 1
        return child1, child2

    def mutation_with_retries(chromosome, x_data, mandatory_breakpoints, validate_function):
        stats.mutation_calls += 1
        mutated = gau.mutation_with_retries(chromosome, x_data, mandatory_breakpoints, validate_function)
        if mutated is None:
            stats.mutation_failed += 1
        return mutated

    # Patch both method modules so their already-imported symbols are replaced.
    single_mod.crossover_with_retries = crossover_with_retries
    single_mod.mutation_with_retries = mutation_with_retries
    multi_mod.crossover_with_retries = crossover_with_retries
    multi_mod.mutation_with_retries = mutation_with_retries


def _run_method(method_key: str, df_route: pd.DataFrame, *, x_col: str, y_col: str, gap_threshold: float,
                pop: int, gens: int, min_length: float, max_length: float,
                mutation_rate: float, crossover_rate: float, elite_ratio: float) -> dict:
    if method_key == "single":
        from analysis.methods.single_objective import SingleObjectiveMethod
        method = SingleObjectiveMethod()
        t0 = time.perf_counter()
        res = method.run_analysis(
            df_route,
            route_id="ROUTE",
            x_column=x_col,
            y_column=y_col,
            gap_threshold=gap_threshold,
            population_size=pop,
            num_generations=gens,
            min_length=min_length,
            max_length=max_length,
            mutation_rate=mutation_rate,
            crossover_rate=crossover_rate,
            elite_ratio=elite_ratio,
            # keep logs quiet
            enable_performance_stats=False,
        )
        elapsed = time.perf_counter() - t0
        best = res.all_solutions[0]
        return {
            "method": "single",
            "elapsed_s": elapsed,
            "best_fitness": best.get("fitness"),
            "segments": best.get("segment_count") or best.get("num_segments"),
        }

    if method_key == "multi":
        from analysis.methods.multi_objective import MultiObjectiveMethod
        method = MultiObjectiveMethod()
        t0 = time.perf_counter()
        res = method.run_analysis(
            df_route,
            route_id="ROUTE",
            x_column=x_col,
            y_column=y_col,
            gap_threshold=gap_threshold,
            population_size=pop,
            num_generations=gens,
            min_length=min_length,
            max_length=max_length,
            mutation_rate=mutation_rate,
            crossover_rate=crossover_rate,
            enable_performance_stats=False,
        )
        elapsed = time.perf_counter() - t0
        # Pareto front; pick first solution for summary
        first = res.all_solutions[0] if res.all_solutions else {}
        obj = first.get("objective_values") or first.get("fitness")
        neg_dev = obj[0] if isinstance(obj, (list, tuple)) and obj else None
        return {
            "method": "multi",
            "elapsed_s": elapsed,
            "best_fitness": neg_dev,
            "segments": first.get("num_segments"),
            "pareto_front": len(res.all_solutions),
        }

    raise ValueError(f"Unknown method_key: {method_key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/AndreTestMultiRoute.csv")
    parser.add_argument("--route-column", default="RDB")
    parser.add_argument("--route", default="FM1836 K")
    parser.add_argument("--x", default="BDFO")
    parser.add_argument("--y", default="D60")
    parser.add_argument("--gap-threshold", type=float, default=0.5)

    parser.add_argument("--pop", type=int, default=100)
    parser.add_argument("--gens", type=int, default=300)
    parser.add_argument("--min-length", type=float, default=0.5)
    parser.add_argument("--max-length", type=float, default=10.0)
    parser.add_argument("--mutation-rate", type=float, default=0.05)
    parser.add_argument("--crossover-rate", type=float, default=0.8)
    parser.add_argument("--elite-ratio", type=float, default=0.05)

    parser.add_argument("--seed", type=int, default=123)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent

    # Ensure `src/` is importable as a top-level package root.
    import sys
    sys.path.insert(0, str(root / "src"))

    # Fix RNG for repeatability.
    random.seed(args.seed)
    np.random.seed(args.seed)

    df_route = _load_route_df(root / args.csv, args.route_column, args.route)

    stats = OperatorStats()
    _instrument_operators(stats)

    print(f"Route: {args.route} | points={len(df_route)} | pop={args.pop} | gens={args.gens} | seed={args.seed}")

    # Run single then multi (reset RNG between runs for fair-ish comparison).
    random.seed(args.seed)
    np.random.seed(args.seed)
    stats_single = OperatorStats()
    _instrument_operators(stats_single)
    single_out = _run_method(
        "single",
        df_route,
        x_col=args.x,
        y_col=args.y,
        gap_threshold=args.gap_threshold,
        pop=args.pop,
        gens=args.gens,
        min_length=args.min_length,
        max_length=args.max_length,
        mutation_rate=args.mutation_rate,
        crossover_rate=args.crossover_rate,
        elite_ratio=args.elite_ratio,
    )

    random.seed(args.seed)
    np.random.seed(args.seed)
    stats_multi = OperatorStats()
    _instrument_operators(stats_multi)
    multi_out = _run_method(
        "multi",
        df_route,
        x_col=args.x,
        y_col=args.y,
        gap_threshold=args.gap_threshold,
        pop=args.pop,
        gens=args.gens,
        min_length=args.min_length,
        max_length=args.max_length,
        mutation_rate=args.mutation_rate,
        crossover_rate=args.crossover_rate,
        elite_ratio=args.elite_ratio,
    )

    def fmt_ops(label: str, s: OperatorStats) -> str:
        return (
            f"{label}: xover calls={s.crossover_calls}, failed_pairs={s.crossover_failed_pairs} | "
            f"mut calls={s.mutation_calls}, failed={s.mutation_failed}"
        )

    print("\n=== Results ===")
    print(single_out)
    print(fmt_ops("single ops", stats_single))
    print(multi_out)
    print(fmt_ops("multi ops", stats_multi))

    print("\n=== Timing ===")
    print(f"single elapsed: {single_out['elapsed_s']:.3f}s")
    print(f"multi   elapsed: {multi_out['elapsed_s']:.3f}s")
    if multi_out["elapsed_s"] > 0:
        print(f"ratio (single/multi): {single_out['elapsed_s'] / multi_out['elapsed_s']:.2f}x")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
