"""
Unit tests for CLI preprocessing integration.

Tests cover:
- JSON schema validation with preprocessing section
- ResolvedRunSpec preprocessing field parsing
- Preprocessing configuration extraction from run spec
- Integration with run_analysis_from_spec_file
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from cli_runner import (
    load_and_resolve_run_spec,
    validate_run_spec,
    RunSpecError,
    ResolvedRunSpec
)
from config import PreprocessingRunConfig


class TestPreprocessingSchemaValidation:
    """Test JSON schema validation for preprocessing section."""
    
    def test_schema_allows_preprocessing_section(self):
        """Test that schema accepts valid preprocessing configuration."""
        spec = {
            "spec_version": "1.0.0",
            "input": {
                "data_file_path": "data.csv",
                "x_column": "Mile",
                "y_column": "IRI",
                "gap_threshold": 0.5
            },
            "preprocessing": {
                "enabled": True,
                "primary_method": "tukey_fences",
                "primary_parameters": {
                    "k_factor": 1.5,
                    "action": "remove"
                }
            },
            "method": {
                "method_key": "single",
                "method_parameters": {}
            },
            "output": {
                "output_json_path": "results.json"
            }
        }
        
        # Should not raise
        validate_run_spec(spec)
    
    def test_schema_allows_omitted_preprocessing(self):
        """Test that preprocessing section is optional."""
        spec = {
            "spec_version": "1.0.0",
            "input": {
                "data_file_path": "data.csv",
                "x_column": "Mile",
                "y_column": "IRI",
                "gap_threshold": 0.5
            },
            "method": {
                "method_key": "single",
                "method_parameters": {}
            },
            "output": {
                "output_json_path": "results.json"
            }
        }
        
        # Should not raise - preprocessing is optional
        validate_run_spec(spec)
    
    def test_schema_allows_disabled_preprocessing(self):
        """Test that preprocessing can be explicitly disabled."""
        spec = {
            "spec_version": "1.0.0",
            "input": {
                "data_file_path": "data.csv",
                "x_column": "Mile",
                "y_column": "IRI",
                "gap_threshold": 0.5
            },
            "preprocessing": {
                "enabled": False
            },
            "method": {
                "method_key": "single",
                "method_parameters": {}
            },
            "output": {
                "output_json_path": "results.json"
            }
        }
        
        # Should not raise
        validate_run_spec(spec)
    
    def test_schema_allows_all_three_phases(self):
        """Test full preprocessing configuration with all three phases."""
        spec = {
            "spec_version": "1.0.0",
            "input": {
                "data_file_path": "data.csv",
                "x_column": "Mile",
                "y_column": "IRI",
                "gap_threshold": 0.5
            },
            "preprocessing": {
                "enabled": True,
                "pre_gap_method": "tukey_fences",
                "pre_gap_parameters": {"k_factor": 2.0, "action": "cap"},
                "primary_method": "tukey_fences",
                "primary_parameters": {"k_factor": 1.5, "action": "remove"},
                "secondary_method": "tukey_fences",
                "secondary_parameters": {"k_factor": 3.0, "action": "interpolate"}
            },
            "method": {
                "method_key": "single",
                "method_parameters": {}
            },
            "output": {
                "output_json_path": "results.json"
            }
        }
        
        # Should not raise
        validate_run_spec(spec)
    
    def test_schema_allows_null_methods(self):
        """Test that preprocessing methods can be explicitly null."""
        spec = {
            "spec_version": "1.0.0",
            "input": {
                "data_file_path": "data.csv",
                "x_column": "Mile",
                "y_column": "IRI",
                "gap_threshold": 0.5
            },
            "preprocessing": {
                "enabled": True,
                "pre_gap_method": None,
                "primary_method": "tukey_fences",
                "primary_parameters": {"k_factor": 1.5},
                "secondary_method": None
            },
            "method": {
                "method_key": "single",
                "method_parameters": {}
            },
            "output": {
                "output_json_path": "results.json"
            }
        }
        
        # Should not raise
        validate_run_spec(spec)


class TestResolvedRunSpecParsing:
    """Test preprocessing configuration parsing in ResolvedRunSpec."""
    
    @pytest.fixture
    def temp_spec_file(self, tmp_path):
        """Create a temporary spec file for testing."""
        def _create_spec(spec_dict):
            spec_path = tmp_path / "test_spec.json"
            spec_path.write_text(json.dumps(spec_dict), encoding="utf-8")
            return spec_path
        return _create_spec
    
    def test_parse_no_preprocessing(self, temp_spec_file):
        """Test parsing spec with no preprocessing section."""
        spec = {
            "spec_version": "1.0.0",
            "input": {
                "data_file_path": "data.csv",
                "x_column": "Mile",
                "y_column": "IRI",
                "gap_threshold": 0.5
            },
            "method": {
                "method_key": "single",
                "method_parameters": {}
            },
            "output": {
                "output_json_path": "results.json"
            }
        }
        
        spec_path = temp_spec_file(spec)
        resolved = load_and_resolve_run_spec(spec_path, validate=True)
        
        assert resolved.preprocessing_config is None
    
    def test_parse_disabled_preprocessing(self, temp_spec_file):
        """Test parsing spec with explicitly disabled preprocessing."""
        spec = {
            "spec_version": "1.0.0",
            "input": {
                "data_file_path": "data.csv",
                "x_column": "Mile",
                "y_column": "IRI",
                "gap_threshold": 0.5
            },
            "preprocessing": {
                "enabled": False,
                "primary_method": "tukey_fences",
                "primary_parameters": {"k_factor": 1.5}
            },
            "method": {
                "method_key": "single",
                "method_parameters": {}
            },
            "output": {
                "output_json_path": "results.json"
            }
        }
        
        spec_path = temp_spec_file(spec)
        resolved = load_and_resolve_run_spec(spec_path, validate=True)
        
        # Should be None when disabled
        assert resolved.preprocessing_config is None
    
    def test_parse_primary_preprocessing_only(self, temp_spec_file):
        """Test parsing spec with only primary preprocessing."""
        spec = {
            "spec_version": "1.0.0",
            "input": {
                "data_file_path": "data.csv",
                "x_column": "Mile",
                "y_column": "IRI",
                "gap_threshold": 0.5
            },
            "preprocessing": {
                "enabled": True,
                "primary_method": "tukey_fences",
                "primary_parameters": {"k_factor": 1.5, "action": "remove"}
            },
            "method": {
                "method_key": "single",
                "method_parameters": {}
            },
            "output": {
                "output_json_path": "results.json"
            }
        }
        
        spec_path = temp_spec_file(spec)
        resolved = load_and_resolve_run_spec(spec_path, validate=True)
        
        assert isinstance(resolved.preprocessing_config, PreprocessingRunConfig)
        assert resolved.preprocessing_config.primary_method == "tukey_fences"
        assert resolved.preprocessing_config.primary_parameters["k_factor"] == 1.5
        assert resolved.preprocessing_config.pre_gap_method is None
        assert resolved.preprocessing_config.secondary_method is None
    
    def test_parse_full_preprocessing_config(self, temp_spec_file):
        """Test parsing spec with all three preprocessing phases."""
        spec = {
            "spec_version": "1.0.0",
            "input": {
                "data_file_path": "data.csv",
                "x_column": "Mile",
                "y_column": "IRI",
                "gap_threshold": 0.5
            },
            "preprocessing": {
                "enabled": True,
                "pre_gap_method": "tukey_fences",
                "pre_gap_parameters": {"k_factor": 2.0},
                "primary_method": "tukey_fences",
                "primary_parameters": {"k_factor": 1.5},
                "secondary_method": "tukey_fences",
                "secondary_parameters": {"k_factor": 3.0}
            },
            "method": {
                "method_key": "single",
                "method_parameters": {}
            },
            "output": {
                "output_json_path": "results.json"
            }
        }
        
        spec_path = temp_spec_file(spec)
        resolved = load_and_resolve_run_spec(spec_path, validate=True)
        
        assert isinstance(resolved.preprocessing_config, PreprocessingRunConfig)
        assert resolved.preprocessing_config.pre_gap_method == "tukey_fences"
        assert resolved.preprocessing_config.primary_method == "tukey_fences"
        assert resolved.preprocessing_config.secondary_method == "tukey_fences"
        assert resolved.preprocessing_config.pre_gap_parameters["k_factor"] == 2.0
        assert resolved.preprocessing_config.primary_parameters["k_factor"] == 1.5
        assert resolved.preprocessing_config.secondary_parameters["k_factor"] == 3.0
    
    def test_parse_empty_parameters_defaults_to_dict(self, temp_spec_file):
        """Test that missing parameter blocks default to empty dicts."""
        spec = {
            "spec_version": "1.0.0",
            "input": {
                "data_file_path": "data.csv",
                "x_column": "Mile",
                "y_column": "IRI",
                "gap_threshold": 0.5
            },
            "preprocessing": {
                "enabled": True,
                "primary_method": "tukey_fences"
                # No primary_parameters specified
            },
            "method": {
                "method_key": "single",
                "method_parameters": {}
            },
            "output": {
                "output_json_path": "results.json"
            }
        }
        
        spec_path = temp_spec_file(spec)
        resolved = load_and_resolve_run_spec(spec_path, validate=True)
        
        assert isinstance(resolved.preprocessing_config.primary_parameters, dict)
        assert len(resolved.preprocessing_config.primary_parameters) == 0
    
    def test_parse_null_method_skips_preprocessing(self, temp_spec_file):
        """Test that null/empty methods result in no preprocessing config."""
        spec = {
            "spec_version": "1.0.0",
            "input": {
                "data_file_path": "data.csv",
                "x_column": "Mile",
                "y_column": "IRI",
                "gap_threshold": 0.5
            },
            "preprocessing": {
                "enabled": True,
                "primary_method": None
            },
            "method": {
                "method_key": "single",
                "method_parameters": {}
            },
            "output": {
                "output_json_path": "results.json"
            }
        }
        
        spec_path = temp_spec_file(spec)
        resolved = load_and_resolve_run_spec(spec_path, validate=True)
        
        # No preprocessing if all methods are null
        assert resolved.preprocessing_config is None


class TestErrorHandling:
    """Test error handling in preprocessing configuration."""
    
    @pytest.fixture
    def temp_spec_file(self, tmp_path):
        """Create a temporary spec file for testing."""
        def _create_spec(spec_dict):
            spec_path = tmp_path / "test_spec.json"
            spec_path.write_text(json.dumps(spec_dict), encoding="utf-8")
            return spec_path
        return _create_spec
    
    def test_invalid_parameters_type_raises_error(self, temp_spec_file):
        """Test that non-object parameter blocks raise error."""
        spec = {
            "spec_version": "1.0.0",
            "input": {
                "data_file_path": "data.csv",
                "x_column": "Mile",
                "y_column": "IRI",
                "gap_threshold": 0.5
            },
            "preprocessing": {
                "enabled": True,
                "primary_method": "tukey_fences",
                "primary_parameters": "invalid"  # Should be object
            },
            "method": {
                "method_key": "single",
                "method_parameters": {}
            },
            "output": {
                "output_json_path": "results.json"
            }
        }
        
        spec_path = temp_spec_file(spec)
        
        with pytest.raises(RunSpecError, match="primary_parameters must be an object"):
            load_and_resolve_run_spec(spec_path, validate=False)  # Skip schema validation to test our validation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
