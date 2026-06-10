"""Personalized dataset recommendations engine."""

from __future__ import annotations

from dataclasses import dataclass

from dataset_collector.core.models import DatasetResult
from dataset_collector.databrain.user_behavior import UserBehaviorTracker
from dataset_collector.logging.logger import AppLogger


@dataclass
class Recommendation:
  """Recommendation with reason and score."""

  dataset: DatasetResult
  reason: str
  score: float


class RecommendationEngine:
  """Generate personalized recommendations based on user behavior."""

  def __init__(
    self,
    user_behavior: UserBehaviorTracker,
    logger: AppLogger | None = None,
  ) -> None:
    self._behavior = user_behavior
    self._logger = logger

  def get_recommendations(
    self,
    all_datasets: list[DatasetResult] | None = None,
    limit: int = 10,
  ) -> list[Recommendation]:
    """Get top personalized recommendations."""
    try:
      if all_datasets is None:
        all_datasets = []
      id_to_dataset = {d.id: d for d in all_datasets}

      # Get most clicked datasets
      most_clicked = self._behavior.get_most_clicked(limit=5, days_back=30)
      downloaded_ids = set(did for did, _ in most_clicked)

      # Get datasets that were co-downloaded
      recommendations = {}
      for dataset_id, _ in most_clicked:
        co_downloads = self._behavior.get_co_downloads(dataset_id, limit=5)
        for co_id, count in co_downloads:
          if co_id not in downloaded_ids and co_id in id_to_dataset:
            if co_id not in recommendations:
              recommendations[co_id] = {"count": 0, "score": 0.0}
            recommendations[co_id]["count"] += count
            recommendations[co_id]["score"] = min(count / 10, 1.0)

      # Convert to Recommendation objects
      result = []
      for dataset_id, data in sorted(
        recommendations.items(), key=lambda x: x[1]["score"], reverse=True
      )[:limit]:
        dataset = id_to_dataset[dataset_id]
        reason = f"Because you downloaded similar datasets ({data['count']} co-downloads)"
        result.append(Recommendation(dataset=dataset, reason=reason, score=data["score"]))

      return result
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Recommendation generation failed: {e}",
          origin="RecommendationEngine",
        )
      return []

  def get_recommendations_for_search(
    self,
    query: str,
    all_datasets: list[DatasetResult],
    limit: int = 5,
  ) -> list[Recommendation]:
    """Get recommendations based on recent search."""
    try:
      # Get datasets similar to query
      similar_datasets = self._find_similar_to_query(query, all_datasets)

      result = []
      for dataset in similar_datasets[:limit]:
        reason = f"Because you searched '{query}'"
        score = min(0.8, 1.0)  # Fixed high score for search-based recs
        result.append(Recommendation(dataset=dataset, reason=reason, score=score))

      return result
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Search-based recommendations failed: {e}",
          origin="RecommendationEngine",
        )
      return []

  def _find_similar_to_query(
    self, query: str, all_datasets: list[DatasetResult]
  ) -> list[DatasetResult]:
    """Find datasets relevant to query (simplified)."""
    query_lower = query.lower()
    return [
      d for d in all_datasets if query_lower in d.name.lower()
      or query_lower in (d.description or "").lower()
    ]
