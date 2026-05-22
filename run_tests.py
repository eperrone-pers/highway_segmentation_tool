#!/usr/bin/env python3
"""
Test Runner Script for Highway Segmentation GA.

This runner provides named test lanes, live-streamed output, UTF-8 log files,
and an optional matrix mode that runs multiple lanes and prints a compact end
summary.

Usage:
    python run_tests.py --help
    python run_tests.py --smoke
    python run_tests.py --regression
    python run_tests.py --full
    python run_tests.py --unit
    python run_tests.py --integration
    python run_tests.py --ui
    python run_tests.py --matrix
"""

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional


PROJECT_ROOT = Path(__file__).parent
DEFAULT_LOG_DIR = PROJECT_ROOT / "test-results"


def build_subprocess_env() -> Dict[str, str]:
    """Build a stable UTF-8 subprocess environment for pytest runs."""
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def format_duration(seconds: float) -> str:
    """Format a duration in seconds for summary output."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes, remaining = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m {remaining:.1f}s"
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h {int(minutes)}m {remaining:.1f}s"


def sanitize_name(value: str) -> str:
    """Create a filesystem-friendly name for log files."""
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)


def build_lane_specs(base_cmd: List[str]) -> Dict[str, Dict[str, object]]:
    """Return the supported test lane definitions."""
    return {
        "smoke": {
            "description": "Running Smoke Suite",
            "cmd": base_cmd + ["tests/", "-m", "not regression and not performance"],
            "allow_no_tests": False,
        },
        "regression": {
            "description": "Running Regression Suite",
            "cmd": base_cmd + ["tests/regression/", "-q"],
            "allow_no_tests": False,
        },
        "full": {
            "description": "Running Full Suite (except performance)",
            "cmd": base_cmd + ["tests/", "-m", "not performance"],
            "allow_no_tests": False,
        },
        "unit": {
            "description": "Running Unit Tests",
            "cmd": base_cmd + ["-m", "unit", "tests/unit/"],
            "allow_no_tests": True,
        },
        "integration": {
            "description": "Running Integration Tests",
            "cmd": base_cmd + ["-m", "integration", "tests/integration/"],
            "allow_no_tests": True,
        },
        "ui": {
            "description": "Running UI Tests",
            "cmd": base_cmd + ["-m", "ui", "tests/ui/"],
            "allow_no_tests": True,
        },
        "performance": {
            "description": "Running Performance Benchmarks",
            "cmd": base_cmd + ["-m", "performance", "--benchmark-only"],
            "allow_no_tests": True,
        },
    }


def run_command(
    cmd: List[str],
    description: str,
    *,
    log_path: Optional[Path] = None,
    allow_no_tests: bool = False,
    continue_on_failure: bool = False,
) -> Dict[str, object]:
    """Run a command with live output, UTF-8 logging, and structured results."""
    print(f"\n==== {description} ====")
    print(f"Running: {' '.join(cmd)}")

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)

    start_time = time.monotonic()
    log_handle = None
    returncode = 1

    try:
        if log_path is not None:
            log_handle = open(log_path, "w", encoding="utf-8", newline="")
            log_handle.write(f"==== {description} ====\n")
            log_handle.write(f"Running: {' '.join(cmd)}\n")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=build_subprocess_env(),
            cwd=PROJECT_ROOT,
        )
        assert process.stdout is not None

        for line in process.stdout:
            print(line, end="")
            if log_handle is not None:
                log_handle.write(line)

        returncode = process.wait()
    except FileNotFoundError:
        print("Error: Command not found. Make sure pytest is installed.")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)
    finally:
        if log_handle is not None:
            log_handle.flush()

    duration = time.monotonic() - start_time
    if returncode == 0:
        status = "PASS"
        note = ""
    elif allow_no_tests and returncode == 5:
        status = "SKIPPED"
        note = "No tests collected"
    else:
        status = "FAIL"
        note = f"Return code {returncode}"

    summary_line = f"[{status}] {description} completed in {format_duration(duration)}"
    if note:
        summary_line += f" ({note})"
    print(summary_line)

    if log_handle is not None:
        log_handle.write(f"\n{summary_line}\n")
        log_handle.write(f"EXIT:{returncode}\n")
        log_handle.close()

    result = {
        "description": description,
        "command": cmd,
        "returncode": returncode,
        "status": status,
        "note": note,
        "duration_seconds": round(duration, 3),
        "log_path": str(log_path) if log_path is not None else None,
    }

    if status == "FAIL" and not continue_on_failure:
        sys.exit(returncode)

    return result


def run_lane(
    lane_name: str,
    lane_spec: Dict[str, object],
    *,
    log_dir: Path,
    continue_on_failure: bool = False,
) -> Dict[str, object]:
    """Run a named lane and return its structured result."""
    log_path = log_dir / f"{sanitize_name(lane_name)}.log"
    result = run_command(
        lane_spec["cmd"],
        str(lane_spec["description"]),
        log_path=log_path,
        allow_no_tests=bool(lane_spec.get("allow_no_tests", False)),
        continue_on_failure=continue_on_failure,
    )
    result["lane"] = lane_name
    return result


def write_matrix_summary(
    results: List[Dict[str, object]],
    log_dir: Path,
    *,
    lane_names: Optional[List[str]] = None,
    run_status: str = "completed",
    current_lane: Optional[str] = None,
) -> Path:
    """Write a machine-readable matrix summary JSON file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    summary_path = log_dir / "summary.json"
    payload = {
        "generated_at_epoch": time.time(),
        "project_root": str(PROJECT_ROOT),
        "run_status": run_status,
        "current_lane": current_lane,
        "planned_lanes": lane_names or [],
        "completed_lane_count": len(results),
        "results": results,
    }
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return summary_path


def print_matrix_summary(results: List[Dict[str, object]], summary_path: Path) -> None:
    """Print a compact end-of-run summary table."""
    print("\n=== Test Matrix Summary ===")
    header = f"{'Lane':<12} {'Status':<8} {'Duration':<10} {'Notes'}"
    print(header)
    print("-" * len(header))

    for result in results:
        lane = str(result.get("lane", ""))
        status = str(result.get("status", ""))
        duration = format_duration(float(result.get("duration_seconds", 0.0)))
        note = str(result.get("note", "") or "")
        print(f"{lane:<12} {status:<8} {duration:<10} {note}")

    print(f"\nSummary written to: {summary_path}")


def run_matrix(lane_names: List[str], lane_specs: Dict[str, Dict[str, object]], log_dir: Path) -> None:
    """Run multiple lanes sequentially and continue to the end for a full report."""
    print("=== Running Test Matrix ===")
    results: List[Dict[str, object]] = []

    summary_path = write_matrix_summary(
        results,
        log_dir,
        lane_names=lane_names,
        run_status="running",
        current_lane=lane_names[0] if lane_names else None,
    )

    for lane_name in lane_names:
        result = run_lane(
            lane_name,
            lane_specs[lane_name],
            log_dir=log_dir,
            continue_on_failure=True,
        )
        results.append(result)

        next_lane_index = len(results)
        next_lane = lane_names[next_lane_index] if next_lane_index < len(lane_names) else None
        summary_path = write_matrix_summary(
            results,
            log_dir,
            lane_names=lane_names,
            run_status="running" if next_lane is not None else "completed",
            current_lane=next_lane,
        )

    print_matrix_summary(results, summary_path)

    if any(result.get("status") == "FAIL" for result in results):
        sys.exit(1)


def main() -> None:
    """Parse arguments and run the requested lane or matrix."""
    parser = argparse.ArgumentParser(description="Run Highway Segmentation GA Tests")
    parser.add_argument("--smoke", action="store_true", help="Run the default fast local suite (excludes regression/performance)")
    parser.add_argument("--regression", action="store_true", help="Run the regression suite only")
    parser.add_argument("--full", action="store_true", help="Run the full pytest suite except performance benchmarks")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--ui", action="store_true", help="Run UI tests only")
    parser.add_argument("--matrix", action="store_true", help="Run the standard lane matrix with per-lane logs and an end summary")
    parser.add_argument("--all", action="store_true", help="Alias for --matrix")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage report")
    parser.add_argument("--performance", action="store_true", help="Run performance benchmarks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--pattern", help="Run tests matching specific pattern")
    parser.add_argument("--file", help="Run specific test file")
    parser.add_argument("--log-dir", help="Directory for UTF-8 logs and summary output")
    args = parser.parse_args()

    base_cmd = [sys.executable, "-m", "pytest"]
    if args.verbose:
        base_cmd.append("-v")

    lane_specs = build_lane_specs(base_cmd)
    log_dir = Path(args.log_dir).expanduser() if args.log_dir else DEFAULT_LOG_DIR

    if args.smoke:
        run_lane("smoke", lane_specs["smoke"], log_dir=log_dir)
    elif args.regression:
        run_lane("regression", lane_specs["regression"], log_dir=log_dir)
    elif args.full:
        run_lane("full", lane_specs["full"], log_dir=log_dir)
    elif args.unit:
        run_lane("unit", lane_specs["unit"], log_dir=log_dir)
    elif args.integration:
        run_lane("integration", lane_specs["integration"], log_dir=log_dir)
    elif args.ui:
        run_lane("ui", lane_specs["ui"], log_dir=log_dir)
    elif args.matrix or args.all:
        run_matrix(["smoke", "regression", "unit", "integration", "ui", "full"], lane_specs, log_dir)
    elif args.performance:
        run_lane("performance", lane_specs["performance"], log_dir=log_dir)
    elif args.coverage:
        run_command(
            base_cmd + ["--cov=src", "--cov-report=html", "--cov-report=term"],
            "Running Tests with Coverage",
            log_path=log_dir / "coverage.log",
            allow_no_tests=False,
        )
        print("\nCoverage report generated in htmlcov/index.html")
    elif args.pattern:
        run_command(
            base_cmd + ["-k", args.pattern],
            f"Running Tests Matching Pattern: {args.pattern}",
            log_path=log_dir / f"pattern_{sanitize_name(args.pattern)}.log",
            allow_no_tests=True,
        )
    elif args.file:
        run_command(
            base_cmd + [args.file],
            f"Running Test File: {args.file}",
            log_path=log_dir / f"file_{sanitize_name(Path(args.file).stem)}.log",
            allow_no_tests=False,
        )
    else:
        run_lane("smoke", lane_specs["smoke"], log_dir=log_dir)


if __name__ == "__main__":
    if importlib.util.find_spec("pytest") is None:
        print("Error: pytest not found. Please install requirements:")
        print("pip install -r requirements.txt")
        sys.exit(1)

    if not (PROJECT_ROOT / "src").exists() or not (PROJECT_ROOT / "tests").exists():
        print("Error: Please run this script from the project root directory")
        print("(The directory containing 'src' and 'tests' folders)")
        sys.exit(1)

    os.chdir(PROJECT_ROOT)
    main()

if __name__ == "__main__":
    # Check if pytest is available
    if importlib.util.find_spec("pytest") is None:
        print("Error: pytest not found. Please install requirements:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    
    # Check if we're in the right directory
    if not Path("src").exists() or not Path("tests").exists():
        print("Error: Please run this script from the project root directory")
        print("(The directory containing 'src' and 'tests' folders)")
        sys.exit(1)
    
    main()