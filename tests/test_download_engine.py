"""Tests for DownloadEngine."""

import pytest
from dataset_collector.download.download_engine import DownloadEngine


@pytest.fixture
def download_engine(config_manager, logger, credential_store):
    """Provide DownloadEngine instance."""
    return DownloadEngine(config_manager, logger, credential_store)


def test_download_engine_initialization(download_engine):
    """Test DownloadEngine initialization."""
    assert download_engine is not None


def test_download_engine_pause_resume(download_engine):
    """Test pause and resume functionality."""
    download_engine.pause()
    assert download_engine._paused is True

    download_engine.resume()
    assert download_engine._paused is False


def test_download_engine_cancel(download_engine):
    """Test cancel functionality."""
    download_engine.cancel()
    assert download_engine._cancelled is True
