"""Command-line interface for Highway Segmentation.

This CLI is intentionally small and stable. It delegates execution to the
headless runner in `cli_runner.py`.

Development usage (repo root):

Single file:
  python src/cli.py run --spec path/to/run_spec.json

Batch (directory of CSVs):
  python src/cli.py run --spec path/to/run_spec.json --input-dir data/ --output-dir results/

Packaging will later provide an executable/console-script entrypoint.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cli_runner import (
    BatchPartialFailureError,
    RunSpecError,
    run_analysis_from_spec_file,
    run_batch_analysis_from_spec_file,
    validate_run_spec,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="highway-seg",
        description="Highway Segmentation Tool (headless runner)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # -------------------------------------------------------------------------
    # run — single file or batch (batch activated by --input-dir)
    # -------------------------------------------------------------------------
    run_p = subparsers.add_parser("run", help="Execute an analysis defined by a run-spec JSON file")
    run_p.add_argument("--spec", required=True, help="Path to the run spec JSON file")
    run_p.add_argument(
        "--no-validate-spec",
        action="store_true",
        help="Skip JSON-schema validation of the run spec",
    )
    run_p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress logging (prints only the output path or summary path)",
    )

    batch_group = run_p.add_argument_group(
        "batch mode",
        "Activated when --input-dir is provided. Runs the spec against every matched file.",
    )
    batch_group.add_argument(
        "--input-dir",
        help="Directory containing input CSV files",
    )
    batch_group.add_argument(
        "--output-dir",
        help="Directory where per-file JSON results are written (required with --input-dir)",
    )
    batch_group.add_argument(
        "--glob",
        default="*.csv",
        help="Glob pattern for input files (default: *.csv)",
    )
    batch_group.add_argument(
        "--recurse",
        action="store_true",
        help="Recurse into subdirectories when discovering input files",
    )
    batch_group.add_argument(
        "--summary-json",
        help="Path for the batch summary JSON (default: <output-dir>/batch_summary.json)",
    )
    batch_group.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop on the first failure (default: continue and report all failures at end)",
    )
    batch_group.add_argument(
        "--export-excel",
        action="store_true",
        help="Export each result JSON to an adjacent XLSX file",
    )

    # -------------------------------------------------------------------------
    # validate-spec — schema check only
    # -------------------------------------------------------------------------
    val_p = subparsers.add_parser("validate-spec", help="Validate a run-spec JSON file against the schema")
    val_p.add_argument("--spec", required=True, help="Path to the run spec JSON file")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and dispatch to the appropriate command.

    Args:
        argv: Argument list; defaults to sys.argv[1:] when None.

    Returns:
        Exit code — 0 on success, 1 for partial batch failures, 2 on error.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "validate-spec":
            spec_path = Path(args.spec).expanduser().resolve()
            instance = __import__("json").loads(spec_path.read_text(encoding="utf-8"))
            validate_run_spec(instance)
            print("OK")
            return 0

        if args.command == "run":
            quiet = bool(args.quiet)
            log = (lambda _msg: None) if quiet else None

            if args.input_dir:
                if not args.output_dir:
                    parser.error("--output-dir is required when --input-dir is specified")

                try:
                    summary_path = run_batch_analysis_from_spec_file(
                        args.spec,
                        args.input_dir,
                        args.output_dir,
                        glob_pattern=args.glob,
                        recurse=bool(args.recurse),
                        summary_json=args.summary_json,
                        continue_on_error=not bool(args.stop_on_error),
                        export_excel=bool(args.export_excel),
                        validate_spec=not bool(args.no_validate_spec),
                        log_callback=log,
                    )
                except BatchPartialFailureError as e:
                    # Partial failures: summary was written; print path then exit non-zero.
                    print(str(e), file=sys.stderr)
                    return 1

                print(summary_path)
                return 0

            output_path = run_analysis_from_spec_file(
                args.spec,
                validate_spec=not bool(args.no_validate_spec),
                log_callback=log,
            )
            print(output_path)
            return 0

        parser.error(f"Unknown command: {args.command}")
        return 2

    except RunSpecError as e:
        print(str(e), file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
