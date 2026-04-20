#!/usr/bin/env python3
"""
Regression Test JSON Schema Validation Utility

Comprehensive validation utility for highway segmentation optimization results
against the official JSON schema specification. This script provides thorough
validation of all regression test outputs to ensure schema compliance and
data integrity across all optimization methods and configurations.

Validation Features:
    Schema Compliance:
        - Validates against official highway_segmentation_results_schema.json
        - Uses Draft 2012 JSON Schema validator for comprehensive checking
        - Provides detailed error reporting with field-level diagnostics
        
    Comprehensive Coverage:
        - Validates all JSON files in regression test outputs directory
        - Handles multiple optimization methods and data configurations
        - Reports both individual file results and overall compliance summary
        
    Error Reporting:
        - Detailed validation error messages with field path information
        - Clear success/failure indicators for quick assessment
        - Comprehensive summary statistics for batch validation

Usage Scenarios:
    Development Workflow:
        - Run after regression tests to verify output schema compliance
        - Integrate into CI/CD pipeline for automated quality assurance
        - Use during schema evolution to validate backward compatibility
        
    Quality Assurance:
        - Verify all optimization methods produce compliant outputs
        - Validate schema changes don't break existing functionality
        - Ensure consistent data format across method implementations

Command Line Usage:
    # Validate all regression test outputs
    python validate_regression_outputs.py
    
    # Run from project root or tests/regression directory
    cd tests/regression && python validate_regression_outputs.py

Integration Benefits:
    - Automated compliance checking for continuous integration
    - Early detection of schema violations during development
    - Comprehensive validation reporting for quality metrics
    - Support for schema evolution and migration validation

Requirements:
    - jsonschema package: pip install jsonschema
    - Regression test outputs: Run regression tests first to generate JSON files
    - Schema file: highway_segmentation_results_schema.json in src/ directory

Author: Highway Segmentation GA Team
Version: 1.95+ (Enhanced Schema Validation)
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

try:
    import jsonschema
    from jsonschema import Draft202012Validator, ValidationError
except ImportError:
    print("ERROR: jsonschema package not installed")
    print("Install with: pip install jsonschema")
    sys.exit(1)


def load_schema() -> Dict[str, Any]:
    """
    Load and validate the JSON schema from the project source directory.
    
    This function locates and loads the official highway segmentation results
    schema file, providing comprehensive error handling for common issues
    like missing files or invalid JSON syntax.
    
    Schema Location Logic:
        1. Determine script location (tests/regression/validate_regression_outputs.py)
        2. Navigate to project root (../../)
        3. Locate schema in src/highway_segmentation_results_schema.json
        4. Load and parse JSON schema specification
    
    Error Handling:
        - FileNotFoundError: Schema file missing or incorrect path
        - JSONDecodeError: Invalid JSON syntax in schema file
        - Comprehensive error messages with troubleshooting guidance
        
    Returns:
        Dict[str, Any]: Parsed JSON schema specification ready for validation
        
    Raises:
        SystemExit: On any error condition with appropriate error message
        
    Usage:
        Called once at script startup to load schema for all file validations.
        Schema is cached and reused for efficient batch validation processing.
        
    Path Resolution:
        - Platform-independent path handling using pathlib
        - Robust navigation from script location to schema file
        - Clear error messages for debugging path issues
    """
    # Navigate from tests/regression to src directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    schema_path = project_root / "src" / "highway_segmentation_results_schema.json"
    
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Schema file not found: {schema_path}")
        print("Make sure you're running from the correct directory and schema exists in src/")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in schema file: {e}")
        sys.exit(1)


def validate_json_file(file_path: Path, schema: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a single JSON file against the schema with comprehensive error handling.
    
    This function performs thorough validation of individual JSON result files
    against the official schema specification, providing detailed error reporting
    for debugging and quality assurance.
    
    Validation Process:
        1. Load and parse JSON file with encoding handling
        2. Create Draft 2012 JSON Schema validator instance
        3. Perform comprehensive schema validation
        4. Generate detailed error reports with field path information
        5. Return validation status and descriptive messages
    
    Error Categories Handled:
        File System Errors:
            - FileNotFoundError: Missing JSON files
            - Permission errors: File access issues
            
        JSON Format Errors:
            - JSONDecodeError: Malformed JSON syntax
            - Encoding issues: Character set problems
            
        Schema Validation Errors:
            - ValidationError: Schema compliance failures
            - Field path reporting: Precise error location identification
            - Detailed constraint violation descriptions
    
    Args:
        file_path (Path): Path to JSON file for validation
        schema (Dict[str, Any]): JSON schema specification for validation
        
    Returns:
        Tuple[bool, str]: Validation result and descriptive message
            - bool: True if validation passes, False for any error
            - str: Success message or detailed error description
    
    Error Reporting Features:
        - Field path identification for precise error location
        - Human-readable error descriptions
        - Comprehensive coverage of all error types
        - Debugging-friendly output format
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        validator = Draft202012Validator(schema)
        validator.validate(json_data)
        return True, "VALID - Passes all schema requirements"
        
    except FileNotFoundError:
        return False, f"ERROR: File not found: {file_path}"
    except json.JSONDecodeError as e:
        return False, f"ERROR: Invalid JSON - {e}"
    except ValidationError as e:
        error_path = ' -> '.join(str(p) for p in e.absolute_path) if e.absolute_path else 'root'
        return False, f"INVALID - {e.message} (Path: {error_path})"
    except Exception as e:
        return False, f"ERROR: {e}"


def main():
    """
    Main validation function for comprehensive regression test output validation.
    
    This function orchestrates the complete validation workflow for all JSON
    outputs from regression tests, providing comprehensive reporting and
    quality assurance metrics.
    
    Validation Workflow:
        1. Environment Setup:
           - Locate outputs directory and verify existence
           - Load official JSON schema specification
           - Discover all JSON files for validation
           
        2. Batch Validation:
           - Validate each JSON file against schema
           - Collect validation results and error details
           - Generate per-file success/failure reports
           
        3. Summary Reporting:
           - Overall validation statistics (pass/fail counts)
           - Detailed error summary for failed validations
           - Success confirmation for compliant outputs
    
    Prerequisites:
        - Regression tests must be run first to generate JSON outputs
        - Schema file must exist in src/highway_segmentation_results_schema.json
        - jsonschema package must be installed (pip install jsonschema)
    
    Output Format:
        Console output with:
        - Clear section headers with emoji indicators
        - Per-file validation status (✅ pass, ❌ fail)
        - Detailed error messages for debugging
        - Summary statistics and recommendations
    
    Error Handling:
        - Missing outputs directory: Clear instructions to run tests first
        - No JSON files found: Guidance on test execution requirements  
        - Schema loading errors: File location and format troubleshooting
    
    Exit Codes:
        - 0: All validations passed successfully
        - 1: One or more validation failures or system errors
        
    Integration:
        Perfect for CI/CD pipelines, automated testing, and quality gates.
    """
    print("🔍 Regression Test JSON Schema Validation")
    print("=" * 60)
    
    # Get outputs directory
    outputs_dir = Path(__file__).parent / "outputs" / "json"
    
    if not outputs_dir.exists():
        print(f"❌ Outputs directory not found: {outputs_dir}")
        print("Run regression tests first to generate JSON outputs")
        sys.exit(1)
    
    # Load schema
    print("Loading schema from src/highway_segmentation_results_schema.json...")
    schema = load_schema()
    print("✅ Schema loaded successfully\n")
    
    # Find all JSON files
    json_files = list(outputs_dir.glob("*.json"))
    
    if not json_files:
        print(f"❌ No JSON files found in {outputs_dir}")
        print("Run regression tests first to generate outputs")
        sys.exit(1)
    
    print(f"Found {len(json_files)} JSON files to validate:\n")
    
    # Validate each file
    results = []
    for json_file in sorted(json_files):
        print(f"Validating: {json_file.name}")
        is_valid, message = validate_json_file(json_file, schema)
        
        if is_valid:
            print(f"   ✅ {message}")
        else:
            print(f"   ❌ {message}")
        
        results.append((json_file.name, is_valid, message))
        print()
    
    # Summary
    valid_count = sum(1 for _, is_valid, _ in results if is_valid)
    total_count = len(results)
    
    print("=" * 60)
    print(f"📊 Validation Summary:")
    print(f"   Valid files:   {valid_count}/{total_count}")
    print(f"   Invalid files: {total_count - valid_count}/{total_count}")
    print()
    
    if valid_count == total_count:
        print("🎉 All regression test outputs are schema-compliant!")
        print("✅ Ready for production - all optimization methods generate valid JSON")
        return True
    else:
        print("⚠️  Some files failed validation:")
        for filename, is_valid, message in results:
            if not is_valid:
                print(f"   • {filename}: {message}")
        print("\nReview errors above and rerun regression tests if needed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)