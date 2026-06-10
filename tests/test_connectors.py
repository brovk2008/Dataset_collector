"""Tests for connectors."""

import pytest
from dataset_collector.search.connectors.arxiv_connector import ArxivConnector
from dataset_collector.search.connectors.dataverse_connector import DataverseConnector
from dataset_collector.search.connectors.biorxiv_connector import BiorxivConnector


def test_arxiv_connector_initialization():
    """Test ArxivConnector initialization."""
    connector = ArxivConnector()
    assert connector is not None
    assert connector.BASE_URL == "http://export.arxiv.org/api/query"


def test_dataverse_connector_initialization():
    """Test DataverseConnector initialization."""
    connector = DataverseConnector()
    assert connector is not None
    assert connector.API_URL == "https://dataverse.harvard.edu/api/search"


def test_biorxiv_connector_initialization():
    """Test BiorxivConnector initialization."""
    connector = BiorxivConnector()
    assert connector is not None
    assert connector.BIORXIV_URL == "https://www.biorxiv.org/search"

