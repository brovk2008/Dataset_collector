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
    """Compute percentage of searches with ≥1 click."""
    try:
      import sqlite3
      from datetime import datetime, timedelta

      conn = sqlite3.connect(str(self._behavior._db_path))
      cursor = conn.cursor()

      cutoff_date = datetime.utcnow() - timedelta(days=days_back)

      # Count searches with at least 1 click
      cursor.execute(
        """
        SELECT COUNT(DISTINCT s.id)
        FROM searches s
        INNER JOIN clicks c ON s.id = c.search_id
        WHERE s.timestamp > ?
        """,
        (cutoff_date,),
      )
      searches_with_clicks = cursor.fetchone()[0] or 0

      # Count total searches
      cursor.execute(
        "SELECT COUNT(*) FROM searches WHERE timestamp > ?",
        (cutoff_date,),
      )
      total_searches = cursor.fetchone()[0] or 1

      conn.close()

      return searches_with_clicks / total_searches if total_searches > 0 else 0.0
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to compute success rate: {e}",
          origin="SearchAnalytics",
        )
      return 0.0

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
