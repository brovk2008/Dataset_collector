"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_dir(tmp_path):
    """Provide temporary directory for tests."""
    return tmp_path


@pytest.fixture
def config_manager():
    """Provide ConfigManager instance for tests."""
    from dataset_collector.core.config_manager import ConfigManager
    return ConfigManager()


@pytest.fixture
def logger(config_manager):
    """Provide AppLogger instance for tests."""
    from dataset_collector.logging.logger import AppLogger
    return AppLogger(config_manager.logs_dir)


@pytest.fixture
def credential_store():
    """Provide CredentialStore instance for tests."""
    from dataset_collector.core.credential_store import CredentialStore
    return CredentialStore()

