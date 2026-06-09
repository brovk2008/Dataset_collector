"""Search engine orchestrating source connectors."""

from __future__ import annotations

import asyncio
from typing import Callable

from dataset_collector.core.config_manager import ConfigManager
from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult, SearchRequest
from dataset_collector.logging.logger import AppLogger
from dataset_collector.search.connectors import (
    BaseConnector,
    GitHubConnector,
    GoogleDatasetConnector,
    GovernmentConnector,
    HuggingFaceConnector,
    InternetArchiveConnector,
    KaggleConnector,
    ResearchConnector,
)
from dataset_collector.core.credential_store import CredentialStore
from dataset_collector.search.dedup import merge_duplicates
from dataset_collector.search.relevance import rank_results


class SearchEngine:
  """Coordinates multi-source dataset searches."""

  def __init__(
    self,
    config: ConfigManager,
    logger: AppLogger,
    credential_store: CredentialStore | None = None,
  ) -> None:
    self._config = config
    self._logger = logger
    self._creds = credential_store or CredentialStore()
    self._connectors: dict[DataSource, BaseConnector] = self._build_connectors()
    self._cancelled = False

  def reload_connectors(self) -> None:
    """Refresh connectors after credential changes."""
    self._connectors = self._build_connectors()

  def _resolve(self, key: str) -> str:
    return self._creds.get(key) or self._config.get_api_key(key)

  def _build_connectors(self) -> dict[DataSource, BaseConnector]:
    return {
      DataSource.KAGGLE: KaggleConnector(
        username=self._resolve("kaggle_username"),
        api_key=self._resolve("kaggle_key"),
      ),
      DataSource.GITHUB: GitHubConnector(token=self._resolve("github_token")),
      DataSource.HUGGINGFACE: HuggingFaceConnector(
        token=self._resolve("huggingface_token")
      ),
      DataSource.GOVERNMENT: GovernmentConnector(
        india_api_key=self._resolve("india_data_api_key"),
      ),
      DataSource.RESEARCH: ResearchConnector(),
      DataSource.INTERNET_ARCHIVE: InternetArchiveConnector(),
      DataSource.GOOGLE_DATASET: GoogleDatasetConnector(),
    }

  def register_connector(self, source: DataSource, connector: BaseConnector) -> None:
    """Register a custom connector plugin."""
    self._connectors[source] = connector

  def cancel(self) -> None:
    self._cancelled = True

  async def search(
    self,
    request: SearchRequest,
    progress_callback: Callable[[str, float], None] | None = None,
  ) -> list[DatasetResult]:
    self._cancelled = False
    max_per_source = self._config.get("search", "max_results_per_source", default=100)
    rate_delay = self._config.get("search", "rate_limit_delay_seconds", default=0.5)

    all_results: list[DatasetResult] = []
    sources = request.sources
    total_sources = len(sources)

    for si, source in enumerate(sources):
      if self._cancelled:
        break

      connector = self._connectors.get(source)
      if not connector:
        continue

      source_progress_base = si / total_sources * 100

      def source_callback(msg: str, pct: float, base=source_progress_base, span=100 / total_sources):
        if progress_callback:
          progress_callback(msg, base + pct / 100 * span)

      try:
        results = await connector.search(
          request.query,
          request.filters,
          max_results=max_per_source,
          progress_callback=source_callback,
        )
        all_results.extend(results)
      except Exception as e:
        self._logger.error(f"Search failed for {source.value}: {e}", source=source.value)

      if si < total_sources - 1:
        await asyncio.sleep(rate_delay)

    # Merge cross-source duplicates, then score and rank
    merged = merge_duplicates(all_results)
    ranked = rank_results(request.query, merged)

    self._logger.log_search(
      request.query,
      [s.value for s in request.sources],
      len(ranked),
    )
    if progress_callback:
      progress_callback(f"Search complete: {len(ranked)} relevant datasets found", 100.0)

    return ranked
