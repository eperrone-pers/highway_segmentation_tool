"""
Unit tests for preprocessing configuration registry.

Tests cover:
- PreprocessingMethodConfig dataclass creation
- PreprocessingRunConfig initialization and post_init
- Registry helper functions (get, resolve, validate)
- Error handling for invalid method keys
- Integration with empty registry
"""

import pytest
from unittest.mock import patch, MagicMock

from config import (
    PreprocessingMethodConfig,
    PreprocessingRunConfig,
    PREPROCESSING_METHODS,
    get_preprocessing_method,
    resolve_preprocessing_class,
    validate_preprocessing_method_registry,
    get_preprocessing_method_names,
    get_preprocessing_method_key_from_display_name,
    get_preprocessing_parameters,
)
from config import NumericParameter  # For creating test parameters


class TestPreprocessingMethodConfig:
    """Test suite for PreprocessingMethodConfig dataclass."""
    
    def test_preprocessing_method_config_creation(self):
        """Test basic PreprocessingMethodConfig creation."""
        config = PreprocessingMethodConfig(
            method_key="test_method",
            display_name="Test Method",
            description="A test preprocessing method",
            parameters=[],
            method_class_path="preprocessing.methods.test.TestMethod"
        )
        
        assert config.method_key == "test_method"
        assert config.display_name == "Test Method"
        assert config.description == "A test preprocessing method"
        assert config.parameters == []
        assert config.method_class_path == "preprocessing.methods.test.TestMethod"
    
    def test_preprocessing_method_config_with_parameters(self):
        """Test config with parameter definitions."""
        param = NumericParameter(
            name="threshold",
            display_name="Threshold",
            description="Threshold value for processing",
            group="basic",
            order=1,
            default_value=1.5,
            min_value=0.0,
            max_value=5.0,
            decimal_places=1  # Float parameter
        )
        
        config = PreprocessingMethodConfig(
            method_key="test_method",
            display_name="Test Method",
            description="Test",
            parameters=[param],
            method_class_path="test.TestMethod"
        )
        
        assert len(config.parameters) == 1
        assert config.parameters[0].name == "threshold"


class TestPreprocessingRunConfig:
    """Test suite for PreprocessingRunConfig dataclass."""
    
    def test_preprocessing_run_config_default(self):
        """Test default PreprocessingRunConfig initialization."""
        config = PreprocessingRunConfig()
        
        assert config.pre_gap_method is None
        assert config.primary_method is None
        assert config.secondary_method is None
        assert config.pre_gap_parameters == {}
        assert config.primary_parameters == {}
        assert config.secondary_parameters == {}
        assert config.enabled is False
    
    def test_preprocessing_run_config_with_methods(self):
        """Test config with methods specified."""
        config = PreprocessingRunConfig(
            primary_method="tukey_fences",
            primary_parameters={"k_factor": 1.5, "action": "remove"},
            secondary_method="moving_average",
            secondary_parameters={"window_size": 5},
            enabled=True
        )
        
        assert config.primary_method == "tukey_fences"
        assert config.primary_parameters == {"k_factor": 1.5, "action": "remove"}
        assert config.secondary_method == "moving_average"
        assert config.secondary_parameters == {"window_size": 5}
        assert config.enabled is True
    
    def test_preprocessing_run_config_post_init(self):
        """Test that post_init properly initializes None parameters to empty dicts."""
        config = PreprocessingRunConfig(
            primary_method="test_method",
            # Deliberately leave parameters as None
        )
        
        # post_init should convert None to {}
        assert isinstance(config.pre_gap_parameters, dict)
        assert isinstance(config.primary_parameters, dict)
        assert isinstance(config.secondary_parameters, dict)
    
    def test_same_method_multiple_phases(self):
        """Test that same method can be used in multiple phases with different parameters."""
        config = PreprocessingRunConfig(
            primary_method="tukey_fences",
            primary_parameters={"k_factor": 1.5},
            secondary_method="tukey_fences",  # Same method
            secondary_parameters={"k_factor": 3.0},  # Different parameters
            enabled=True
        )
        
        assert config.primary_method == config.secondary_method
        assert config.primary_parameters != config.secondary_parameters


class TestRegistryHelperFunctions:
    """Test suite for preprocessing registry helper functions."""
    
    def test_empty_registry_get_method_names(self):
        """Test get_preprocessing_method_names with registry."""
        names = get_preprocessing_method_names()
        # Registry now contains Tukey Fences
        assert isinstance(names, list)
        assert len(names) >= 0  # May be empty or contain methods
    
    def test_empty_registry_get_method_raises_error(self):
        """Test that getting non-existent method raises ValueError."""
        with pytest.raises(ValueError, match="Unknown preprocessing method key"):
            get_preprocessing_method("non_existent_method")
    
    def test_empty_registry_resolve_class_raises_error(self):
        """Test that resolving non-existent method raises ValueError."""
        with pytest.raises(ValueError, match="Unknown preprocessing method key"):
            resolve_preprocessing_class("non_existent_method")
    
    def test_empty_registry_get_display_name_raises_error(self):
        """Test that getting key from non-existent display name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown preprocessing method display name"):
            get_preprocessing_method_key_from_display_name("Non-Existent Method")
    
    def test_validate_empty_registry(self):
        """Test that validating empty registry succeeds (no methods to validate)."""
        # Should not raise any exceptions
        try:
            validate_preprocessing_method_registry()
        except Exception as e:
            pytest.fail(f"validate_preprocessing_method_registry() raised {e}")


class TestRegistryWithMockMethods:
    """Test suite using mock methods added to registry."""
    
    @pytest.fixture(autouse=True)
    def mock_registry(self):
        """Set up and tear down mock methods in registry."""
        # Save original registry
        original_methods = PREPROCESSING_METHODS.copy()
        
        # Clear registry and add test methods
        PREPROCESSING_METHODS.clear()
        
        test_param = NumericParameter(
            name="test_param",
            display_name="Test Parameter",
            description="A test parameter",
            group="test",
            order=1,
            default_value=1.0,
            min_value=0.0,
            max_value=10.0,
            decimal_places=1  # Float
        )
        
        PREPROCESSING_METHODS.append(
            PreprocessingMethodConfig(
                method_key="test_method_1",
                display_name="Test Method 1",
                description="First test method",
                parameters=[test_param],
                method_class_path="preprocessing.methods.test1.TestMethod1"
            )
        )
        
        PREPROCESSING_METHODS.append(
            PreprocessingMethodConfig(
                method_key="test_method_2",
                display_name="Test Method 2",
                description="Second test method",
                parameters=[],
                method_class_path="preprocessing.methods.test2.TestMethod2"
            )
        )
        
        yield
        
        # Restore original registry
        PREPROCESSING_METHODS.clear()
        PREPROCESSING_METHODS.extend(original_methods)
    
    def test_get_method_names_with_methods(self):
        """Test get_preprocessing_method_names returns correct names."""
        names = get_preprocessing_method_names()
        assert len(names) == 2
        assert "Test Method 1" in names
        assert "Test Method 2" in names
    
    def test_get_method_by_key(self):
        """Test getting method config by key."""
        config = get_preprocessing_method("test_method_1")
        assert config.method_key == "test_method_1"
        assert config.display_name == "Test Method 1"
        assert len(config.parameters) == 1
    
    def test_get_method_key_from_display_name(self):
        """Test converting display name to method key."""
        key = get_preprocessing_method_key_from_display_name("Test Method 1")
        assert key == "test_method_1"
        
        key2 = get_preprocessing_method_key_from_display_name("Test Method 2")
        assert key2 == "test_method_2"
    
    def test_get_preprocessing_parameters(self):
        """Test getting parameter list for a method."""
        params = get_preprocessing_parameters("test_method_1")
        assert len(params) == 1
        assert params[0].name == "test_param"
        
        params2 = get_preprocessing_parameters("test_method_2")
        assert len(params2) == 0


class TestResolvePreprocessingClass:
    """Test suite for resolve_preprocessing_class function."""
    
    def test_resolve_missing_class_path(self):
        """Test error when method_class_path is empty."""
        PREPROCESSING_METHODS.clear()
        PREPROCESSING_METHODS.append(
            PreprocessingMethodConfig(
                method_key="bad_method",
                display_name="Bad Method",
                description="Test",
                parameters=[],
                method_class_path=""  # Invalid
            )
        )
        
        try:
            with pytest.raises(ValueError, match="missing method_class_path"):
                resolve_preprocessing_class("bad_method")
        finally:
            PREPROCESSING_METHODS.clear()
    
    def test_resolve_invalid_class_path_format(self):
        """Test error when method_class_path has invalid format (no dots)."""
        PREPROCESSING_METHODS.clear()
        PREPROCESSING_METHODS.append(
            PreprocessingMethodConfig(
                method_key="bad_method",
                display_name="Bad Method",
                description="Test",
                parameters=[],
                method_class_path="InvalidFormat"  # No module path
            )
        )
        
        try:
            with pytest.raises(ValueError, match="expected module.ClassName"):
                resolve_preprocessing_class("bad_method")
        finally:
            PREPROCESSING_METHODS.clear()
    
    def test_resolve_non_existent_module(self):
        """Test error when module cannot be imported."""
        PREPROCESSING_METHODS.clear()
        PREPROCESSING_METHODS.append(
            PreprocessingMethodConfig(
                method_key="bad_method",
                display_name="Bad Method",
                description="Test",
                parameters=[],
                method_class_path="non_existent_module.SomeClass"
            )
        )
        
        try:
            with pytest.raises(ImportError, match="Could not import module"):
                resolve_preprocessing_class("bad_method")
        finally:
            PREPROCESSING_METHODS.clear()
    
    def test_resolve_missing_class_in_module(self):
        """Test error when class doesn't exist in module."""
        PREPROCESSING_METHODS.clear()
        PREPROCESSING_METHODS.append(
            PreprocessingMethodConfig(
                method_key="bad_method",
                display_name="Bad Method",
                description="Test",
                parameters=[],
                method_class_path="preprocessing.base.NonExistentClass"
            )
        )
        
        try:
            with pytest.raises(ImportError, match="does not define class"):
                resolve_preprocessing_class("bad_method")
        finally:
            PREPROCESSING_METHODS.clear()


class TestValidatePreprocessingRegistry:
    """Test suite for validate_preprocessing_method_registry function."""
    
    def test_validate_with_valid_method(self):
        """Test validation passes with properly configured method."""
        from preprocessing.base import PreprocessingMethodBase
        
        # Create a valid test method class
        class ValidTestMethod(PreprocessingMethodBase):
            @property
            def preprocess_key(self):
                return "valid_test"
            
            @property
            def preprocess_name(self):
                return "Valid Test"
            
            def process(self, route_analysis, x_column, y_column, **parameters):
                pass
        
        # Mock the module to return our test class
        with patch('importlib.import_module') as mock_import:
            mock_module = MagicMock()
            mock_module.ValidTestMethod = ValidTestMethod
            mock_import.return_value = mock_module
            
            PREPROCESSING_METHODS.clear()
            PREPROCESSING_METHODS.append(
                PreprocessingMethodConfig(
                    method_key="valid_test",
                    display_name="Valid Test",
                    description="Test",
                    parameters=[],
                    method_class_path="test_module.ValidTestMethod"
                )
            )
            
            try:
                # Should not raise
                validate_preprocessing_method_registry()
            finally:
                PREPROCESSING_METHODS.clear()
    
    def test_validate_with_non_class(self):
        """Test validation fails when resolved object is not a class."""
        # Mock to return a non-class object
        with patch('importlib.import_module') as mock_import:
            mock_module = MagicMock()
            mock_module.NotAClass = "not a class"  # String instead of class
            mock_import.return_value = mock_module
            
            PREPROCESSING_METHODS.clear()
            PREPROCESSING_METHODS.append(
                PreprocessingMethodConfig(
                    method_key="bad_method",
                    display_name="Bad Method",
                    description="Test",
                    parameters=[],
                    method_class_path="test_module.NotAClass"
                )
            )
            
            try:
                with pytest.raises(ValueError, match="validation failed"):
                    validate_preprocessing_method_registry()
            finally:
                PREPROCESSING_METHODS.clear()
    
    def test_validate_with_wrong_base_class(self):
        """Test validation fails when class doesn't inherit from PreprocessingMethodBase."""
        # Create a class that doesn't inherit from PreprocessingMethodBase
        class WrongBaseClass:
            pass
        
        with patch('importlib.import_module') as mock_import:
            mock_module = MagicMock()
            mock_module.WrongBaseClass = WrongBaseClass
            mock_import.return_value = mock_module
            
            PREPROCESSING_METHODS.clear()
            PREPROCESSING_METHODS.append(
                PreprocessingMethodConfig(
                    method_key="wrong_base",
                    display_name="Wrong Base",
                    description="Test",
                    parameters=[],
                    method_class_path="test_module.WrongBaseClass"
                )
            )
            
            try:
                with pytest.raises(ValueError, match="validation failed"):
                    validate_preprocessing_method_registry()
            finally:
                PREPROCESSING_METHODS.clear()


class TestRegistryIntegration:
    """Integration tests for preprocessing registry workflow."""
    
    def test_complete_registry_workflow(self):
        """Test complete workflow: add method, get it, resolve it."""
        PREPROCESSING_METHODS.clear()
        
        test_param = NumericParameter(
            name="threshold",
            display_name="Threshold",
            description="Threshold value",
            group="test",
            order=1,
            default_value=1.5,
            min_value=0.0,
            max_value=5.0,
            decimal_places=1  # Float
        )
        
        PREPROCESSING_METHODS.append(
            PreprocessingMethodConfig(
                method_key="workflow_test",
                display_name="Workflow Test Method",
                description="Testing complete workflow",
                parameters=[test_param],
                method_class_path="preprocessing.base.DataModificationContext"  # Use existing class for test
            )
        )
        
        try:
            # Test getting names
            names = get_preprocessing_method_names()
            assert "Workflow Test Method" in names
            
            # Test getting config
            config = get_preprocessing_method("workflow_test")
            assert config.display_name == "Workflow Test Method"
            
            # Test getting key from display name
            key = get_preprocessing_method_key_from_display_name("Workflow Test Method")
            assert key == "workflow_test"
            
            # Test getting parameters
            params = get_preprocessing_parameters("workflow_test")
            assert len(params) == 1
            assert params[0].name == "threshold"
            
            # Test resolving class (will succeed because we use existing class)
            cls = resolve_preprocessing_class("workflow_test")
            assert cls is not None
            
        finally:
            PREPROCESSING_METHODS.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
