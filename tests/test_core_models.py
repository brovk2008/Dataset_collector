"""Tests for core models and enums."""

import pytest
from datetime import datetime
from dataset_collector.core.models import DatasetResult, SearchRequest, SearchFilters
from dataset_collector.core.enums import DataSource, FileType, SizeFilter, LicenseFilter


def test_dataset_result_creation():
    """Test creating a DatasetResult."""
    dataset = DatasetResult(
        id="test_1",
        name="Test Dataset",
        source=DataSource.KAGGLE,
        url="https://example.com",
        estimated_size_bytes=1024 * 1024,
        description="A test dataset"
    )
    assert dataset.id == "test_1"
    assert dataset.name == "Test Dataset"
    assert dataset.source == DataSource.KAGGLE
    assert dataset.auth_message == ""
    assert dataset.rank_score == 0


def test_dataset_result_size_display():
    """Test size_display property."""
    dataset = DatasetResult(
        id="test_1",
        name="Test",
        source=DataSource.KAGGLE,
        url="https://example.com",
        estimated_size_bytes=1024 * 1024 * 100  # 100 MB
    )
    assert "MB" in dataset.size_display or "m" in dataset.size_display.lower()


def test_search_request_creation():
    """Test creating a SearchRequest."""
    from dataset_collector.core.enums import SizeFilter

    filters = SearchFilters(
        file_types=[FileType.CSV],
        size_filter=SizeFilter.ANY,  # Use ANY instead of SMALL
        license_filter=LicenseFilter.ANY
    )
    request = SearchRequest(
        query="climate data",
        sources=[DataSource.KAGGLE, DataSource.GITHUB],
        filters=filters
    )
    assert request.query == "climate data"
    assert len(request.sources) == 2
    assert request.filters.size_filter == SizeFilter.ANY


def test_data_source_enum():
    """Test DataSource enum values."""
    # Check that enum values exist (don't assume lowercase)
    assert hasattr(DataSource, 'KAGGLE')
    assert hasattr(DataSource, 'GITHUB')
    assert hasattr(DataSource, 'ARXIV')
    assert hasattr(DataSource, 'DATAVERSE')

