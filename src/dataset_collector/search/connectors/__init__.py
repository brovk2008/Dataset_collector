"""Source connector plugins."""

from dataset_collector.search.connectors.base import BaseConnector
from dataset_collector.search.connectors.github_connector import GitHubConnector
from dataset_collector.search.connectors.google_dataset_connector import GoogleDatasetConnector
from dataset_collector.search.connectors.government_connector import GovernmentConnector
from dataset_collector.search.connectors.huggingface_connector import HuggingFaceConnector
from dataset_collector.search.connectors.internet_archive_connector import InternetArchiveConnector
from dataset_collector.search.connectors.kaggle_connector import KaggleConnector
from dataset_collector.search.connectors.research_connector import ResearchConnector

__all__ = [
    "BaseConnector",
    "GitHubConnector",
    "GoogleDatasetConnector",
    "GovernmentConnector",
    "HuggingFaceConnector",
    "InternetArchiveConnector",
    "KaggleConnector",
    "ResearchConnector",
]
