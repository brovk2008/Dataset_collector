"""Search analytics aggregation."""

from __future__ import annotations

from dataset_collector.databrain.embeddings_cache import EmbeddingsCache
from dataset_collector.databrain.user_behavior import UserBehaviorTracker
from dataset_collector.logging.logger import AppLogger


class SearchAnalytics:
  """Compute search analytics for analytics panel."""

  def __init__(
    self,
    user_behavior: UserBehaviorTracker,
    embeddings_cache: EmbeddingsCache | None = None,
    logger: AppLogger | None = None,
  ) -> None:
    self._behavior = user_behavior
    self._cache = embeddings_cache
    self._logger = logger

  def get_top_searches(
    self, limit: int = 10, days_back: int = 30
  ) -> list[tuple[str, int]]:
    """Get most common search queries."""
    return self._behavior.get_top_searches(limit, days_back)

  def get_top_clicked_datasets(
    self, limit: int = 10, days_back: int = 30
  ) -> list[tuple[str, int]]:
    """Get most clicked datasets."""
    return self._behavior.get_most_clicked(limit, days_back)

  def get_search_success_rate(self, days_back: int = 30) -> float:
    """Compute percentage of searches with ≥1 click (uses connection pool)."""
    return self._behavior.get_search_success_rate(days_back)

  def get_model_stats(self) -> dict:
    """Get DatasetBrain model and cache statistics."""
    cache_stats = self._cache.stats() if self._cache else {}
    return {
      "embeddings_cached": cache_stats.get("total_cached", 0),
      "cache_size_mb": cache_stats.get("total_size_mb", 0),
      "last_updated": cache_stats.get("last_updated", ""),
    }

  def get_full_report(self, days_back: int = 30) -> dict:
    """Get complete analytics report."""
    return {
      "top_searches": self.get_top_searches(limit=10, days_back=days_back),
      "top_clicked": self.get_top_clicked_datasets(limit=10, days_back=days_back),
      "success_rate": self.get_search_success_rate(days_back),
      "model_stats": self.get_model_stats(),
    }
