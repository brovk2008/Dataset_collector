"""DatasetBrain: Semantic discovery platform orchestrator."""

from __future__ import annotations

from pathlib import Path

from dataset_collector.core.config_manager import ConfigManager
from dataset_collector.logging.logger import AppLogger
from dataset_collector.databrain.embeddings_cache import EmbeddingsCache
from dataset_collector.databrain.model_manager import ModelManager
from dataset_collector.databrain.user_behavior import UserBehaviorTracker
from dataset_collector.databrain.analytics import SearchAnalytics
from dataset_collector.databrain.co_downloads import CoDownloadsTracker
from dataset_collector.databrain.collections import CollectionsGenerator
from dataset_collector.databrain.health_score import HealthScorer
from dataset_collector.databrain.intent_classifier import IntentClassifier
from dataset_collector.databrain.query_expansion import QueryExpander
from dataset_collector.databrain.recommendations import RecommendationEngine
from dataset_collector.databrain.search_index import SearchIndex
from dataset_collector.databrain.semantic_ranker import SemanticRanker
from dataset_collector.databrain.similar_datasets import SimilarDatasetsEngine


class DatasetBrain:
  """Orchestrator for semantic search and intelligent discovery."""

  def __init__(
    self,
    config: ConfigManager,
    logger: AppLogger,
    cache_dir: Path | None = None,
  ) -> None:
    self._config = config
    self._logger = logger
    self._cache_dir = cache_dir or (Path.home() / ".dataset_collector" / "cache")
    self._cache_dir.mkdir(parents=True, exist_ok=True)

    # Core v2 components - download model on init if not present
    self.model_manager = ModelManager(config, logger, download_on_init=True)
    self.embeddings_cache = EmbeddingsCache(self._cache_dir, logger)
    self.behavior_tracker = UserBehaviorTracker(self._cache_dir, logger)

    # v2 Ranking
    self.semantic_ranker = SemanticRanker(
      self.model_manager,
      self.embeddings_cache,
      logger,
    )

    # v2.1 Discovery Features
    self.similar_datasets = SimilarDatasetsEngine(self.embeddings_cache, logger)
    self.query_expander = QueryExpander(
      self.model_manager,
      self.embeddings_cache,
      logger,
    )
    self.co_downloads_tracker = CoDownloadsTracker(self.behavior_tracker, logger)
    self.health_scorer = HealthScorer(self.behavior_tracker, logger)
    self.collections_generator = CollectionsGenerator(logger)
    self.intent_classifier = IntentClassifier(
      self.model_manager,
      self.embeddings_cache,
      logger,
    )
    self.recommendations = RecommendationEngine(self.behavior_tracker, logger)
    self.search_index = SearchIndex(self._cache_dir / "search_index.db", logger)

    # Analytics
    self.analytics = SearchAnalytics(
      self.behavior_tracker,
      self.embeddings_cache,
      logger,
    )

    self._enabled = True
    self._logger.info("DatasetBrain initialized")

  @property
  def enabled(self) -> bool:
    """Check if DatasetBrain is enabled."""
    return self._enabled and self.model_manager.is_installed()

  def enable(self) -> None:
    """Enable DatasetBrain."""
    self._enabled = True

  def disable(self) -> None:
    """Disable DatasetBrain (search will work without semantics)."""
    self._enabled = False

  def shutdown(self) -> None:
    """Cleanup resources."""
    self.embeddings_cache.close()
    self.behavior_tracker.close()
    self.search_index.close()
    self._logger.info("DatasetBrain shutdown")


__all__ = ["DatasetBrain"]

