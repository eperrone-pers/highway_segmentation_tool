"""
Unit tests for preprocessing framework base classes.

Tests cover:
- DataModification record creation and timestamp generation
- DataModificationContext data modification methods
- Automatic logging functionality
- Error handling for invalid operations
- PreprocessingMethodBase abstract interface
"""

import pytest
import pandas as pd
from datetime import datetime

from preprocessing.base import (
    DataModification,
    DataModificationContext,
    PreprocessingResult,
    PreprocessingMethodBase,
)


class TestDataModification:
    """Test suite for DataModification dataclass."""
    
    def test_datamodification_creation(self):
        """Test basic DataModification creation."""
        mod = DataModification(
            modification_type="point_removed",
            x_value=100.0,
            original_y_value=5.5,
            new_y_value=None,
            reason="outlier detected"
        )
        
        assert mod.modification_type == "point_removed"
        assert mod.x_value == 100.0
        assert mod.original_y_value == 5.5
        assert mod.new_y_value is None
        assert mod.reason == "outlier detected"
        assert mod.timestamp is not None  # Auto-generated
    
    def test_timestamp_auto_generation(self):
        """Test that timestamp is automatically generated."""
        mod = DataModification(
            modification_type="y_value_changed",
            x_value=50.0,
            original_y_value=3.0,
            new_y_value=2.5
        )
        
        # Should have a valid ISO format timestamp
        assert mod.timestamp is not None
        # Verify it's parseable as ISO format
        dt = datetime.fromisoformat(mod.timestamp)
        assert isinstance(dt, datetime)
    
    def test_manual_timestamp(self):
        """Test that manual timestamp is preserved."""
        manual_timestamp = "2026-05-20T10:30:00"
        mod = DataModification(
            modification_type="y_value_capped",
            x_value=75.0,
            original_y_value=10.0,
            new_y_value=8.0,
            timestamp=manual_timestamp
        )
        
        assert mod.timestamp == manual_timestamp


class TestDataModificationContext:
    """Test suite for DataModificationContext."""
    
    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            'Milepoint': [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            'IRI': [100.0, 150.0, 200.0, 250.0, 300.0, 350.0]
        })
    
    @pytest.fixture
    def context(self, sample_dataframe):
        """Create a DataModificationContext for testing."""
        return DataModificationContext(sample_dataframe, 'Milepoint', 'IRI')
    
    def test_context_initialization(self, sample_dataframe):
        """Test context initialization preserves original data."""
        ctx = DataModificationContext(sample_dataframe, 'Milepoint', 'IRI')
        
        # Should have working copy
        assert len(ctx.get_modified_data()) == 6
        # Should preserve original
        assert len(ctx.get_original_data()) == 6
        # Should be separate copies
        assert ctx.get_modified_data() is not sample_dataframe
        assert ctx.get_original_data() is not sample_dataframe
    
    def test_remove_point_success(self, context):
        """Test successful point removal."""
        initial_len = len(context.get_modified_data())
        
        context.remove_point(2.0, reason="test removal")
        
        # Check dataframe modified
        modified_df = context.get_modified_data()
        assert len(modified_df) == initial_len - 1
        assert 2.0 not in modified_df['Milepoint'].values
        
        # Check modification logged
        log = context.get_modification_log()
        assert len(log) == 1
        assert log[0].modification_type == "point_removed"
        assert log[0].x_value == 2.0
        assert log[0].original_y_value == 200.0
        assert log[0].new_y_value is None
        assert log[0].reason == "test removal"
    
    def test_remove_point_not_found(self, context):
        """Test error when removing non-existent point."""
        with pytest.raises(ValueError, match="not found in data"):
            context.remove_point(99.0)
    
    def test_modify_y_value_success(self, context):
        """Test successful Y value modification."""
        context.modify_y_value(3.0, 275.0, reason="adjusted value")
        
        # Check dataframe modified
        modified_df = context.get_modified_data()
        mask = modified_df['Milepoint'] == 3.0
        assert modified_df.loc[mask, 'IRI'].iloc[0] == 275.0
        
        # Check modification logged
        log = context.get_modification_log()
        assert len(log) == 1
        assert log[0].modification_type == "y_value_changed"
        assert log[0].x_value == 3.0
        assert log[0].original_y_value == 250.0
        assert log[0].new_y_value == 275.0
        assert log[0].reason == "adjusted value"

    def test_modify_y_value_allows_float_into_integer_y_column(self):
        """Integer source columns should be widened for float preprocessing results."""
        df = pd.DataFrame({
            'Milepoint': [0.0, 1.0, 2.0],
            'IRI': [100, 150, 200],
        })
        ctx = DataModificationContext(df, 'Milepoint', 'IRI')

        ctx.modify_y_value(1.0, 116.5, reason="capped to non-integer value")

        modified_df = ctx.get_modified_data()
        mask = modified_df['Milepoint'] == 1.0
        assert modified_df.loc[mask, 'IRI'].iloc[0] == 116.5
    
    def test_modify_y_value_not_found(self, context):
        """Test error when modifying non-existent point."""
        with pytest.raises(ValueError, match="not found in data"):
            context.modify_y_value(99.0, 100.0)
    
    def test_cap_y_value_upper(self, context):
        """Test capping to upper bound using modify_y_value."""
        context.modify_y_value(5.0, 320.0, reason="capped to upper fence (320.0)", 
                               modification_type="y_value_capped")
        
        # Check dataframe modified
        modified_df = context.get_modified_data()
        mask = modified_df['Milepoint'] == 5.0
        assert modified_df.loc[mask, 'IRI'].iloc[0] == 320.0
        
        # Check modification logged with correct type and reason
        log = context.get_modification_log()
        assert len(log) == 1
        assert log[0].modification_type == "y_value_capped"
        assert log[0].x_value == 5.0
        assert log[0].original_y_value == 350.0
        assert log[0].new_y_value == 320.0
        assert "upper fence" in log[0].reason
    
    def test_cap_y_value_lower(self, context):
        """Test capping to lower bound using modify_y_value."""
        context.modify_y_value(0.0, 110.0, reason="capped to lower fence (110.0)",
                               modification_type="y_value_capped")
        
        # Check modification logged
        log = context.get_modification_log()
        assert log[0].modification_type == "y_value_capped"
        assert "lower fence" in log[0].reason
    
    def test_interpolate_y_value(self, context):
        """Test interpolated value replacement using modify_y_value."""
        context.modify_y_value(2.0, 175.0, reason="interpolated from neighbors",
                               modification_type="point_interpolated")
        
        # Check dataframe modified
        modified_df = context.get_modified_data()
        mask = modified_df['Milepoint'] == 2.0
        assert modified_df.loc[mask, 'IRI'].iloc[0] == 175.0
        
        # Check modification logged with correct type and reason
        log = context.get_modification_log()
        assert len(log) == 1
        assert log[0].modification_type == "point_interpolated"
        assert log[0].x_value == 2.0
        assert log[0].original_y_value == 200.0
        assert log[0].new_y_value == 175.0
        assert "interpolated" in log[0].reason
    
    def test_multiple_modifications(self, context):
        """Test multiple modifications accumulate in log."""
        context.remove_point(0.0, reason="first removal")
        context.modify_y_value(2.0, 225.0, reason="adjustment")
        context.modify_y_value(5.0, 320.0, reason="capped to upper fence",
                               modification_type="y_value_capped")
        
        # Check all modifications logged
        log = context.get_modification_log()
        assert len(log) == 3
        
        # Verify order preserved
        assert log[0].modification_type == "point_removed"
        assert log[1].modification_type == "y_value_changed"
        assert log[2].modification_type == "y_value_capped"
    
    def test_original_data_preserved(self, context):
        """Test that original data remains unchanged after modifications."""
        original_df = context.get_original_data().copy()
        
        # Make multiple modifications
        context.remove_point(0.0)
        context.modify_y_value(2.0, 225.0)
        context.modify_y_value(5.0, 320.0, modification_type="y_value_capped")
        
        # Original should be unchanged
        current_original = context.get_original_data()
        pd.testing.assert_frame_equal(original_df, current_original)
        
        # Modified should be different
        modified_df = context.get_modified_data()
        assert len(modified_df) != len(original_df)  # Point was removed


class TestPreprocessingResult:
    """Test suite for PreprocessingResult dataclass."""
    
    def test_preprocessing_result_creation(self):
        """Test PreprocessingResult can be created with required fields."""
        # Note: We'll use mock objects since RouteAnalysis isn't imported
        result = PreprocessingResult(
            processed_route_analysis=None,  # Would be RouteAnalysis in real usage
            modification_log=[
                DataModification(
                    modification_type="point_removed",
                    x_value=10.0,
                    original_y_value=100.0,
                    new_y_value=None
                )
            ],
            preprocessing_metadata={
                'method': 'test_method',
                'points_removed': 1
            },
            original_y_values=[100.0, 150.0, 200.0],
            modifications_summary="Removed 1 outlier"
        )
        
        assert len(result.modification_log) == 1
        assert result.preprocessing_metadata['points_removed'] == 1
        assert result.modifications_summary == "Removed 1 outlier"
        assert len(result.original_y_values) == 3


class TestPreprocessingMethodBase:
    """Test suite for PreprocessingMethodBase abstract class."""
    
    def test_cannot_instantiate_abstract_class(self):
        """Test that PreprocessingMethodBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PreprocessingMethodBase()
    
    def test_concrete_implementation(self):
        """Test that a concrete implementation can be created."""
        
        class ConcretePreprocessor(PreprocessingMethodBase):
            @property
            def preprocess_key(self) -> str:
                return "test_method"
            
            @property
            def preprocess_name(self) -> str:
                return "Test Preprocessing Method"
            
            @property
            def description(self) -> str:
                return "A test preprocessing method"
            
            def process(self, route_analysis, x_column, y_column, **parameters):
                # Simple mock implementation
                return PreprocessingResult(
                    processed_route_analysis=route_analysis,
                    modification_log=[],
                    preprocessing_metadata={'test': True},
                    original_y_values=[],
                    modifications_summary="Test completed"
                )
        
        # Should be able to instantiate concrete class
        preprocessor = ConcretePreprocessor()
        assert preprocessor.preprocess_key == "test_method"
        assert preprocessor.preprocess_name == "Test Preprocessing Method"
        assert preprocessor.description == "A test preprocessing method"
    
    def test_missing_abstract_methods(self):
        """Test that missing abstract methods prevent instantiation."""
        
        # Missing process() method
        class IncompletePreprocessor(PreprocessingMethodBase):
            @property
            def preprocess_key(self) -> str:
                return "incomplete"
            
            @property
            def preprocess_name(self) -> str:
                return "Incomplete"
        
        with pytest.raises(TypeError):
            IncompletePreprocessor()


class TestIntegrationScenarios:
    """Integration tests for complete preprocessing workflows."""
    
    def test_complete_preprocessing_workflow(self):
        """Test a complete preprocessing workflow from start to finish."""
        # Create sample data
        df = pd.DataFrame({
            'Milepoint': [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            'IRI': [100.0, 150.0, 500.0, 250.0, 300.0, 350.0]  # 2.0 is outlier
        })
        
        # Create context
        ctx = DataModificationContext(df, 'Milepoint', 'IRI')
        
        # Simulate outlier detection and removal
        outlier_x = 2.0
        ctx.remove_point(outlier_x, reason="outlier beyond 3*IQR")
        
        # Simulate capping another high value
        ctx.modify_y_value(5.0, 320.0, reason="capped to upper fence",
                          modification_type="y_value_capped")
        
        # Get results
        modified_df = ctx.get_modified_data()
        log = ctx.get_modification_log()
        
        # Verify results
        assert len(modified_df) == 5  # One point removed
        assert outlier_x not in modified_df['Milepoint'].values
        assert len(log) == 2  # Two modifications logged
        
        # Verify log details
        assert log[0].modification_type == "point_removed"
        assert log[0].x_value == 2.0
        assert log[1].modification_type == "y_value_capped"
        assert log[1].x_value == 5.0
    
    def test_no_modifications_workflow(self):
        """Test workflow where no modifications are made."""
        df = pd.DataFrame({
            'Milepoint': [0.0, 1.0, 2.0],
            'IRI': [100.0, 150.0, 200.0]
        })
        
        ctx = DataModificationContext(df, 'Milepoint', 'IRI')
        
        # Don't make any modifications
        modified_df = ctx.get_modified_data()
        log = ctx.get_modification_log()
        
        # Data should be unchanged (but still a copy)
        assert len(modified_df) == 3
        assert len(log) == 0
        pd.testing.assert_frame_equal(modified_df, ctx.get_original_data())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
