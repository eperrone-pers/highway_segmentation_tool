#!/usr/bin/env python3
"""JSON Schema Validation for Highway Segmentation Results.

Validates JSON result files against the official schema specification.
Run from the project root:

    python src/validate_json_schema.py path/to/results.json
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from jsonschema import ValidationError, Draft202012Validator
except ImportError:
    print("ERROR: jsonschema package not installed")
    print("Install with: pip install jsonschema")
    sys.exit(1)


def load_schema(schema_path: Path) -> Dict[str, Any]:
    """Load the JSON schema from file."""
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Schema file not found: {schema_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in schema file: {e}")
        sys.exit(1)


def load_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON data from file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: JSON file not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in file {file_path}: {e}")
        return None


def validate_json_against_schema(
    json_data: Dict[str, Any], schema: Dict[str, Any], filename: str
) -> bool:
    """Validate JSON data against schema and return True if valid."""
    try:
        validator = Draft202012Validator(schema)
        validator.validate(json_data)
        print(f"OK {filename}: VALID - Passes all schema requirements")
        return True
    except ValidationError as e:
        print(f"FAIL {filename}: INVALID")
        print(f"   Error: {e.message}")
        print(f"   Path: {' -> '.join(str(p) for p in e.absolute_path) if e.absolute_path else 'root'}")
        if e.context:
            print("   Additional errors:")
            for ctx_error in e.context:
                print(f"     - {ctx_error.message}")
        return False
    except Exception as e:
        print(f"FAIL {filename}: VALIDATION ERROR - {e}")
        return False


def validate_single_file(file_path: str) -> bool:
    """Validate a single JSON file against the schema."""
    src_dir = Path(__file__).parent
    schema_path = src_dir / "highway_segmentation_results_schema.json"
    schema = load_schema(schema_path)
    json_data = load_json_file(Path(file_path))
    if json_data is None:
        return False
    return validate_json_against_schema(json_data, schema, Path(file_path).name)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        is_valid = validate_single_file(sys.argv[1])
        sys.exit(0 if is_valid else 1)
    else:
        print("Usage: python src/validate_json_schema.py path/to/results.json")
        sys.exit(1)
