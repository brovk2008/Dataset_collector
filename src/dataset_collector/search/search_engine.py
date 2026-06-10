"""Search engine orchestrating source connectors."""

from __future__ import annotations

import asyncio
from typing import Callable

from dataset_collector.core.config_manager import ConfigManager
from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult, SearchRequest
from dataset_collector.logging.logger import AppLogger
from dataset_collector.search.connectors import (
    ArxivConnector,
    BaseConnector,
    GitHubConnector,
    GoogleDatasetConnector,
    GovernmentConnector,
    HuggingFaceConnector,
    InternetArchiveConnector,
    KaggleConnector,
    ResearchConnector,
    ResearchPapersConnector,
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
    databrain = None,
  ) -> None:
    self._config = config
    self._logger = logger
    self._creds = credential_store or CredentialStore()
    self._connectors: dict[DataSource, BaseConnector] = self._build_connectors()
    self._databrain = databrain
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
      DataSource.RESEARCH_PAPERS: ResearchPapersConnector(),
      DataSource.INTERNET_ARCHIVE: InternetArchiveConnector(),
      DataSource.GOOGLE_DATASET: GoogleDatasetConnector(),
      DataSource.ARXIV: ArxivConnector(),
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
    result_callback: Callable[[DatasetResult], None] | None = None,  # NEW
  ) -> list[DatasetResult]:
    self._cancelled = False
    max_per_source = self._config.get("search", "max_results_per_source", default=100)
    rate_delay = self._config.get("search", "rate_limit_delay_seconds", default=0.5)

    sources = request.sources
    total_sources = len(sources)

    # NEW: Create parallel search tasks for all sources
    search_tasks = []
    for si, source in enumerate(sources):
      connector = self._connectors.get(source)
      if not connector:
        continue

      # Create progress callback for this source (20% per source in progress bar)
      def make_callback(source_index, total):
        def source_callback(msg: str, pct: float):
          if progress_callback and not self._cancelled:
            base = (source_index / total) * 100
            span = 100 / total
            progress_callback(msg, base + (pct / 100) * span)
        return source_callback

      # Create task with staggered start (rate limiting)
      task = self._search_source(
        connector,
        source,
        request,
        max_per_source,
        make_callback(si, total_sources),
        delay_seconds=si * rate_delay,
        result_callback=result_callback,  # NEW: Pass result callback
      )
      search_tasks.append(task)

    # Execute all searches in parallel
    if progress_callback:
      progress_callback("Searching all sources...", 5.0)

    results_per_source = await asyncio.gather(*search_tasks, return_exceptions=True)

    # Collect results, filtering out exceptions
    all_results: list[DatasetResult] = []
    for result in results_per_source:
      if isinstance(result, Exception):
        continue
      if result:
        all_results.extend(result)

    # Merge cross-source duplicates, then score and rank
    merged = merge_duplicates(all_results)

    # Compute semantic scores if DatasetBrain is available
    if self._databrain and self._databrain.enabled:
      try:
        if progress_callback:
          progress_callback("Computing semantic similarities...", 85.0)

        # Initialize semantic ranker if not already done
        if self._databrain.semantic_ranker is None:
          from dataset_collector.databrain.semantic_ranker import SemanticRanker
          self._databrain.semantic_ranker = SemanticRanker(
            self._databrain.model_manager,
            self._databrain.embeddings_cache,
            self._logger,
          )

        # Score results with semantic similarity
        merged = self._databrain.semantic_ranker.score_results(request.query, merged)
      except Exception as e:
        self._logger.error(f"Semantic scoring failed: {e}")
        # Continue with keyword-only ranking if semantic fails

    # Perform hybrid ranking
    ranked = rank_results(request.query, merged, use_hybrid=self._databrain is not None)

    # Log search for user behavior tracking
    if self._databrain:
      search_id = self._databrain.behavior_tracker.log_search(
        request.query,
        [s.value for s in request.sources],
        len(ranked),
      )
      # Store search_id in metadata for click tracking
      for r in ranked:
        r.metadata["_search_id"] = search_id

    self._logger.log_search(
      request.query,
      [s.value for s in request.sources],
      len(ranked),
    )
    if progress_callback:
      progress_callback(f"Search complete: {len(ranked)} relevant datasets found", 100.0)

    return ranked

  async def _search_source(
    self,
    connector: BaseConnector,
    source: DataSource,
    request: SearchRequest,
    max_results: int,
    progress_callback: Callable[[str, float], None] | None = None,
    delay_seconds: float = 0.0,
    result_callback: Callable[[DatasetResult], None] | None = None,  # NEW
  ) -> list[DatasetResult]:
    """Search a single source with optional delay for rate limiting."""
    try:
      # Stagger requests to respect rate limits
      if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)

      if self._cancelled:
        return []

      results = await connector.search(
        request.query,
        request.filters,
        max_results=max_results,
        progress_callback=progress_callback,
      )

      # NEW: Emit each result immediately for streaming
      if result_callback and results:
        for result in results:
          result_callback(result)

      return results or []
    except Exception as e:
      self._logger.error(f"Search failed for {source.value}: {e}")
      return []  # Graceful degradation: return empty list
