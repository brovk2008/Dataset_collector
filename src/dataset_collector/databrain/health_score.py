"""Dataset health score assessment (0-100)."""

from __future__ import annotations

from dataset_collector.core.models import DatasetResult
from dataset_collector.databrain.user_behavior import UserBehaviorTracker
from dataset_collector.logging.logger import AppLogger
from dataset_collector.search.quality import compute_health_score_v2, get_health_color


class HealthScorer:
  """Compute dataset health score (0-100) based on 10 factors."""

  def __init__(
    self,
    behavior_tracker: UserBehaviorTracker | None = None,
    logger: AppLogger | None = None,
  ) -> None:
    self._behavior = behavior_tracker
    self._logger = logger

  def compute_health_score(self, result: DatasetResult) -> int:
    """Compute 0-100 health score using v2 algorithm (10 factors)."""
    return compute_health_score_v2(result)

  def compute_batch(self, results: list[DatasetResult]) -> list[int]:
    """Batch compute health scores."""
    return [self.compute_health_score(r) for r in results]

  def get_health_label(self, score: int) -> str:
    """Get human-readable health label."""
    if score >= 80:
      return "Excellent"
    elif score >= 60:
      return "Good"
    elif score >= 40:
      return "Fair"
    else:
      return "Poor"

  def get_health_color(self, score: int) -> str:
    """Get color for health score visualization."""
    return get_health_color(score)

  def populate_health_scores(
    self, results: list[DatasetResult]
  ) -> list[DatasetResult]:
    """Populate health_score field in results."""
    for result in results:
      result.health_score = self.compute_health_score(result)
    return results
