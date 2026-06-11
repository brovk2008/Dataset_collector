"""Search engine orchestrating source connectors."""

from __future__ import annotations

import asyncio
from typing import Callable, cast

from dataset_collector.core.config_manager import ConfigManager
from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult, SearchRequest
from dataset_collector.logging.logger import AppLogger
from dataset_collector.search.connectors import (
    ArxivConnector,
    BaseConnector,
    BiorxivConnector,
    DataverseConnector,
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
from dataset_collector.search.dedup import merge_duplicates, merge_duplicates_with_semantic
from dataset_collector.search.relevance import rank_results
from dataset_collector.search.search_stats import SearchStats


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
    self.last_search_stats: SearchStats | None = None
    self.search_mode: str = "balanced"  # balanced or aggressive

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
      DataSource.BIORXIV: BiorxivConnector(),
      DataSource.DATAVERSE: DataverseConnector(),
    }

  def register_connector(self, source: DataSource, connector: BaseConnector) -> None:
    """Register a custom connector plugin."""
    self._connectors[source] = connector

  def cancel(self) -> None:
    self._cancelled = True

  async def search_multi_stage(
    self,
    request: SearchRequest,
    all_datasets: list[DatasetResult] | None = None,
    progress_callback: Callable[[str, float], None] | None = None,
    result_callback: Callable[[DatasetResult], None] | None = None,
  ) -> list[DatasetResult]:
    """Multi-stage search with query expansion for maximum recall."""
    self._cancelled = False
    all_results: dict[str, DatasetResult] = {}

    try:
      # Stage 1: Original query
      if progress_callback:
        progress_callback("Stage 1/5: Searching original query...", 15.0)

      stage1_results = await self.search(request, None, result_callback)
      for result in stage1_results:
        if result.id not in all_results:
          all_results[result.id] = result

      if self._cancelled:
        return list(all_results.values())

      # Stage 2: Expanded terms (if DatasetBrain available)
      if self._databrain and self._databrain.enabled:
        if progress_callback:
          progress_callback("Stage 2/5: Searching expanded terms...", 35.0)

        try:
          expanded = self._databrain.query_expansion.expand_query_aggressive(
            request.query,
            all_datasets=all_datasets,
            max_expansions=15,
          )
          expanded_terms = expanded.get("all_terms", [])[1:]  # Skip original

          for term in expanded_terms:
            if self._cancelled:
              break

            expanded_request = SearchRequest(
              query=term,
              sources=request.sources,
              filters=request.filters,
              aggressive_mode=False,
              max_results_per_source=50,
            )

            expanded_results = await self.search(expanded_request, None, result_callback)
            for result in expanded_results:
              if result.id not in all_results:
                all_results[result.id] = result
        except Exception as e:
          self._logger.error(f"Stage 2 expansion failed: {e}")

      if self._cancelled:
        return list(all_results.values())

      # Stage 3: Category-related terms
      if progress_callback:
        progress_callback("Stage 3/5: Searching category terms...", 55.0)

      category_terms = self._get_category_terms(request.query)
      for term in category_terms:
        if self._cancelled:
          break

        category_request = SearchRequest(
          query=term,
          sources=request.sources,
          filters=request.filters,
          aggressive_mode=False,
          max_results_per_source=30,
        )

        category_results = await self.search(category_request, None, result_callback)
        for result in category_results:
          if result.id not in all_results:
            all_results[result.id] = result

      if self._cancelled:
        return list(all_results.values())

      # Stage 4: User behavior (if aggressive mode)
      if progress_callback:
        progress_callback("Stage 4/5: Searching behavior patterns...", 70.0)

      if request.aggressive_mode and self._databrain:
        try:
          behavior_terms = self._databrain.behavior_tracker.get_related_searches(
            request.query,
            limit=5,
          )
          for term in behavior_terms:
            if self._cancelled:
              break

            behavior_request = SearchRequest(
              query=term,
              sources=request.sources,
              filters=request.filters,
              aggressive_mode=False,
              max_results_per_source=25,
            )

            behavior_results = await self.search(behavior_request, None, result_callback)
            for result in behavior_results:
              if result.id not in all_results:
                all_results[result.id] = result
        except Exception as e:
          self._logger.error(f"Stage 4 behavior search failed: {e}")

      if self._cancelled:
        return list(all_results.values())

      # Stage 5: Semantic similarity (if DatasetBrain available)
      if progress_callback:
        progress_callback("Stage 5/5: Finding semantic matches...", 85.0)

      if self._databrain and self._databrain.enabled and all_datasets:
        try:
          encoder = self._databrain.model_manager.get_encoder()
          query_embedding = encoder.encode(request.query, convert_to_numpy=True)

          similar_datasets = self._find_semantic_similar(
            query_embedding,
            all_datasets,
            limit=20,
          )

          for result in similar_datasets:
            if result.id not in all_results:
              all_results[result.id] = result
              if result_callback:
                result_callback(result)
        except Exception as e:
          self._logger.error(f"Stage 5 semantic search failed: {e}")

      # Final ranking
      if progress_callback:
        progress_callback("Finalizing results...", 95.0)

      final_results = list(all_results.values())

      # Use semantic deduplication if DatasetBrain available
      if self._databrain and self._databrain.enabled:
        try:
          embeddings = self._databrain.embeddings_cache.get_by_ids(
            [r.id for r in final_results]
          )
          merged = merge_duplicates_with_semantic(final_results, embeddings)
        except Exception as e:
          self._logger.error(f"Semantic deduplication failed, using traditional: {e}")
          merged = merge_duplicates(final_results)
      else:
        merged = merge_duplicates(final_results)

      if self._databrain and self._databrain.enabled:
        try:
          merged = self._databrain.semantic_ranker.score_results(request.query, merged)
        except Exception as e:
          self._logger.error(f"Final semantic scoring failed: {e}")

      ranked = rank_results(request.query, merged, use_hybrid=self._databrain is not None)

      # Preserve results - only remove critically invalid datasets
      ranked = self.preserve_results(ranked)

      # Limit results per source if specified
      if request.max_results_per_source:
        ranked = self._limit_results_per_source(ranked, request.max_results_per_source)

      if progress_callback:
        progress_callback(f"Search complete: {len(ranked)} relevant datasets found", 100.0)

      return ranked

    except Exception as e:
      self._logger.error(f"Multi-stage search failed: {e}")
      return []

  def _get_category_terms(self, query: str) -> list[str]:
    """Extract category-specific terms from query."""
    try:
      from dataset_collector.databrain.query_expansion import CATEGORY_PATTERNS
    except ImportError:
      return []

    category_terms = []
    query_lower = query.lower()

    for category, patterns in CATEGORY_PATTERNS.items():
      if any(pattern in query_lower for pattern in patterns):
        if category == "text":
          category_terms.extend(["corpus", "nlp dataset", "language data"])
        elif category == "image":
          category_terms.extend(["vision dataset", "visual data", "photography"])
        elif category == "audio":
          category_terms.extend(["audio dataset", "sound data", "music"])
        elif category == "video":
          category_terms.extend(["video dataset", "motion data"])

    return category_terms[:5]

  def _find_semantic_similar(
    self,
    query_embedding,
    datasets: list[DatasetResult],
    limit: int = 20,
  ) -> list[DatasetResult]:
    """Find semantically similar datasets."""
    if not self._databrain:
      return []

    try:
      from scipy.spatial.distance import cosine

      similarities: list[tuple[float, DatasetResult]] = []

      dataset_ids = [d.id for d in datasets]
      embeddings = self._databrain.embeddings_cache.get_by_ids(dataset_ids)

      for dataset in datasets:
        if dataset.id in embeddings:
          embedding = embeddings[dataset.id]
          distance = cosine(query_embedding, embedding)
          similarity = 1 - distance
          if similarity > 0.6:
            similarities.append((similarity, dataset))

      similarities.sort(key=lambda x: x[0], reverse=True)
      return [d for _, d in similarities[:limit]]
    except Exception as e:
      self._logger.error(f"Semantic similarity search failed: {e}")
      return []

  def _limit_results_per_source(
    self,
    results: list[DatasetResult],
    max_per_source: int,
  ) -> list[DatasetResult]:
    """Limit results to max_per_source per DataSource."""
    source_counts: dict[str, int] = {}
    limited = []

    for result in results:
      source_key = result.source.value
      if source_key not in source_counts:
        source_counts[source_key] = 0

      if source_counts[source_key] < max_per_source:
        limited.append(result)
        source_counts[source_key] += 1

    return limited

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
        all_results.extend(cast(list[DatasetResult], result))

    # Merge cross-source duplicates with semantic similarity if available
    if self._databrain and self._databrain.enabled:
      try:
        embeddings = self._databrain.embeddings_cache.get_by_ids(
          [r.id for r in all_results]
        )
        merged = merge_duplicates_with_semantic(all_results, embeddings)
      except Exception as e:
        self._logger.error(f"Semantic deduplication failed, using traditional: {e}")
        merged = merge_duplicates(all_results)
    else:
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

    # Preserve results - only remove critically invalid datasets
    ranked = self.preserve_results(ranked)

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

  def _is_dataset_valid(self, dataset: DatasetResult) -> tuple[bool, str]:
    """Check if dataset is critically invalid (preserve all others).

    Only remove for:
    - Broken/invalid URLs
    - Corrupted records

    Never remove for:
    - Missing metadata
    - Low scores
    - Unknown size/license
    """
    # Check for broken URLs
    if dataset.url:
      if not dataset.url.startswith(("http://", "https://", "file://", "ftp://")):
        return False, "invalid_url_format"
      if "invalid" in dataset.url.lower() or "null" in dataset.url.lower():
        return False, "invalid_url_content"

    # Check for corrupted records
    if not dataset.id or not dataset.name:
      return False, "missing_required_fields"

    # Check for obviously corrupted names
    if len(dataset.name) < 2 or len(dataset.name) > 500:
      return False, "invalid_name_length"

    # Everything else is valid - preserve it
    return True, "valid"

  def preserve_results(self, results: list[DatasetResult]) -> list[DatasetResult]:
    """Filter only critically invalid datasets, preserve everything else.

    This maximizes recall by keeping all datasets except those with:
    - Broken URLs
    - Corrupted data
    - Missing required fields
    """
    stats = SearchStats()
    stats.search_mode = self.search_mode
    stats.raw_count = len(results)

    preserved = []
    for dataset in results:
      is_valid, reason = self._is_dataset_valid(dataset)
      if is_valid:
        preserved.append(dataset)
        # Track source breakdown
        source_key = dataset.source.value
        stats.source_counts[source_key] = stats.source_counts.get(source_key, 0) + 1
      else:
        stats.log_removal(dataset, reason)
        if reason == "invalid_url_format" or reason == "invalid_url_content":
          stats.invalid_urls_removed += 1
        else:
          stats.corrupted_removed += 1

    stats.final_count = len(preserved)
    stats.deduplicated_count = len(preserved)
    self.last_search_stats = stats

    # Log removal summary
    if stats.removed_datasets:
      self._logger.warning(
        f"Removed {len(stats.removed_datasets)} corrupted/invalid datasets:"
      )
      for removal in stats.removed_datasets:
        self._logger.warning(
          f"  - {removal['name']} ({removal['source']}): {removal['reason']}"
        )

    return preserved

  def get_search_stats(self) -> dict | None:
    """Get statistics from last search."""
    return self.last_search_stats.get_summary() if self.last_search_stats else None

  def get_search_stats_display(self) -> str:
    """Get formatted stats for UI display."""
    if self.last_search_stats:
      return self.last_search_stats.format_display()
    return "No search performed yet"
