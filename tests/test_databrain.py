"""Tests for DatasetBrain."""

import pytest
from dataset_collector.databrain import DatasetBrain


@pytest.fixture
def databrain(config_manager, logger):
    """Provide DatasetBrain instance."""
    return DatasetBrain(config_manager, logger)


def test_databrain_initialization(databrain):
    """Test DatasetBrain initialization."""
    assert databrain is not None
    assert databrain.behavior_tracker is not None
    assert databrain.embeddings_cache is not None
    assert databrain.model_manager is not None


def test_databrain_components(databrain):
    """Test that DatasetBrain has all expected components."""
    assert hasattr(databrain, "similar_datasets")
    assert hasattr(databrain, "recommendations")
    assert hasattr(databrain, "health_scorer")
    assert hasattr(databrain, "intent_classifier")
    assert hasattr(databrain, "query_expander")


def test_databrain_enabled_property(databrain):
    """Test databrain enabled property."""
    # Should not raise
    enabled = databrain.enabled
    assert isinstance(enabled, bool)


def test_databrain_enable_disable(databrain):
    """Test enabling and disabling DatasetBrain."""
    databrain.disable()
    assert databrain._enabled is False

    databrain.enable()
    assert databrain._enabled is True
