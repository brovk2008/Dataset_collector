"""Tests for ConfigManager."""

import pytest
from dataset_collector.core.config_manager import ConfigManager


def test_config_manager_initialization():
    """Test ConfigManager initialization."""
    config = ConfigManager()
    assert config is not None
    assert config.logs_dir is not None
    assert config.library_dir is not None


def test_config_manager_get_default():
    """Test getting config values with defaults."""
    config = ConfigManager()
    value = config.get("nonexistent", "key", default="default_value")
    assert value == "default_value"

