"""Command-line interface for Highway Segmentation.

This CLI is intentionally small and stable. It delegates execution to the
headless runner in `cli_runner.py`.

Development usage (repo root):
- `python src/cli.py run --spec path/to/run_spec.json`

Packaging will later provide an executable/console-script entrypoint.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cli_runner import RunSpecError, run_analysis_from_spec_file, validate_run_spec


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="highway-seg",
        description="Highway Segmentation Tool (headless runner)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

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
        help="Suppress progress logging (prints only the output path)",
    )

    val_p = subparsers.add_parser("validate-spec", help="Validate a run-spec JSON file against the schema")
    val_p.add_argument("--spec", required=True, help="Path to the run spec JSON file")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and dispatch to the appropriate command.

    Args:
        argv: Argument list; defaults to sys.argv[1:] when None.

    Returns:
        Exit code — 0 on success, 2 on error.
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

            output_path = run_analysis_from_spec_file(
                args.spec,
                validate_spec=not bool(args.no_validate_spec),
                log_callback=log,
            )

            # Print output path as the final line for scripting.
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
