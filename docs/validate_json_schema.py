#!/usr/bin/env python3
"""
JSON Schema Validation for Highway Segmentation Results
Validates JSON result files against the official schema specification.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

try:
    import jsonschema
    from jsonschema import validate, ValidationError, Draft202012Validator
except ImportError:
    print("ERROR: jsonschema package not installed")
    print("Install with: pip install jsonschema")
    sys.exit(1)


def load_schema(schema_path: Path) -> Dict[str, Any]:
    """Load the JSON schema from file."""
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Schema file not found: {schema_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in schema file: {e}")
        sys.exit(1)


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load JSON data from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: JSON file not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in file {file_path}: {e}")
        return None


def validate_json_against_schema(json_data: Dict[str, Any], schema: Dict[str, Any], filename: str) -> bool:
    """Validate JSON data against schema and return True if valid."""
    try:
        # Use Draft 2020-12 validator for full feature support
        validator = Draft202012Validator(schema)
        validator.validate(json_data)
        print(f"✅ {filename}: VALID - Passes all schema requirements")
        return True
    except ValidationError as e:
        print(f"❌ {filename}: INVALID")
        print(f"   Error: {e.message}")
        print(f"   Path: {' -> '.join(str(p) for p in e.absolute_path) if e.absolute_path else 'root'}")
        if e.context:
            print(f"   Additional errors:")
            for ctx_error in e.context:
                print(f"     - {ctx_error.message}")
        return False
    except Exception as e:
        print(f"❌ {filename}: VALIDATION ERROR - {e}")
        return False


def main():
    """Main validation function."""
    print("Highway Segmentation JSON Schema Validator")
    print("=" * 50)
    
    # Define paths
    docs_dir = Path(__file__).parent
    src_dir = docs_dir.parent / "src"
    schema_path = src_dir / "highway_segmentation_results_schema.json"
    
    # Sample files to validate
    sample_files = [
        "sample_single_objective_results.json",
        "sample_multi_objective_results.json", 
        "sample_constrained_results.json"
    ]
    
    # Load schema
    print(f"Loading schema: {schema_path}")
    schema = load_schema(schema_path)
    print(f"✅ Schema loaded successfully")
    print()
    
    # Validate each sample file
    all_valid = True
    for sample_file in sample_files:
        file_path = docs_dir / sample_file
        print(f"Validating: {sample_file}")
        
        json_data = load_json_file(file_path)
        if json_data is None:
            all_valid = False
            continue
            
        is_valid = validate_json_against_schema(json_data, schema, sample_file)
        if not is_valid:
            all_valid = False
        print()
    
    # Summary
    if all_valid:
        print("🎉 All sample files are valid!")
        print("Schema validation successful - ready for production use.")
    else:
        print("⚠️  Some files failed validation")
        print("Review errors above and fix JSON structure.")
        sys.exit(1)


def validate_single_file(file_path: str) -> bool:
    """Validate a single JSON file - useful for external calls."""
    docs_dir = Path(__file__).parent
    src_dir = docs_dir.parent / "src"
    schema_path = src_dir / "highway_segmentation_results_schema.json"
    
    schema = load_schema(schema_path)
    json_data = load_json_file(Path(file_path))
    
    if json_data is None:
        return False
        
    return validate_json_against_schema(json_data, schema, Path(file_path).name)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        # Validate single file passed as argument
        file_path = sys.argv[1]
        is_valid = validate_single_file(file_path)
        sys.exit(0 if is_valid else 1)
    else:
        # Validate all sample files
        main()