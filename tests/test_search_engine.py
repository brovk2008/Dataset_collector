"""Tests for SearchEngine."""

import pytest
from dataset_collector.search.search_engine import SearchEngine
from dataset_collector.core.models import SearchRequest
from dataset_collector.core.enums import DataSource


@pytest.fixture
def search_engine(config_manager, logger, credential_store):
    """Provide SearchEngine instance."""
    return SearchEngine(config_manager, logger, credential_store, databrain=None)


def test_search_engine_initialization(search_engine):
    """Test SearchEngine initialization."""
    assert search_engine is not None
    assert len(search_engine._connectors) > 0


def test_search_engine_has_connectors(search_engine):
    """Test that SearchEngine has all expected connectors."""
    assert DataSource.KAGGLE in search_engine._connectors
    assert DataSource.GITHUB in search_engine._connectors
    assert DataSource.ARXIV in search_engine._connectors
    assert DataSource.DATAVERSE in search_engine._connectors


def test_search_engine_connector_registration(search_engine):
    """Test registering a custom connector."""
    from dataset_collector.search.connectors.base import BaseConnector

    class DummyConnector(BaseConnector):
        async def search(self, query, filters=None, max_results=50, progress_callback=None):
            return []

    connector = DummyConnector()
    search_engine.register_connector(DataSource.RESEARCH, connector)
    assert search_engine._connectors[DataSource.RESEARCH] == connector

