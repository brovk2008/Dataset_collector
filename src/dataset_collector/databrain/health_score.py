"""Dataset health score assessment (0-100)."""

from __future__ import annotations

from dataset_collector.core.models import DatasetResult
from dataset_collector.databrain.user_behavior import UserBehaviorTracker
from dataset_collector.logging.logger import AppLogger


class HealthScorer:
  """Compute dataset health score (0-100) based on multiple factors."""

  def __init__(
    self,
    behavior_tracker: UserBehaviorTracker | None = None,
    logger: AppLogger | None = None,
  ) -> None:
    self._behavior = behavior_tracker
    self._logger = logger

  def compute_health_score(self, result: DatasetResult) -> int:
    """Compute 0-100 health score."""
    score = 0

    # Documentation Quality (20 pts)
    if result.description and len(result.description) > 50:
      score += 20
    elif result.description:
      score += 10

    # Metadata Completeness (20 pts)
    metadata_count = 0
    if result.name:
      metadata_count += 1
    if result.description:
      metadata_count += 1
    if result.metadata.get("tags"):
      metadata_count += 1
    if result.metadata.get("category"):
      metadata_count += 1
    if result.license_info not in ("Unknown", "See source"):
      metadata_count += 1
    score += (metadata_count / 5) * 20

    # Download Availability (20 pts)
    if result.download_urls and len(result.download_urls) > 0:
      score += 20
    elif result.url:
      score += 10

    # Update Recency (20 pts)
    if result.last_updated:
      from datetime import datetime, timezone

      days_old = (datetime.now(timezone.utc) - result.last_updated.replace(tzinfo=timezone.utc)).days
      if days_old < 30:
        score += 20
      elif days_old < 180:
        score += 15
      elif days_old < 365:
        score += 10
      else:
        score += 5

    # Popularity (20 pts)
    downloads = result.metadata.get("downloads", 0)
    stars = result.metadata.get("stars", 0)
    popularity_count = 0

    if isinstance(downloads, int) and downloads > 1000:
      popularity_count += 10
    elif isinstance(downloads, int) and downloads > 100:
      popularity_count += 5

    if isinstance(stars, int) and stars > 50:
      popularity_count += 10
    elif isinstance(stars, int) and stars > 10:
      popularity_count += 5

    score += min(popularity_count, 20)

    return int(min(max(score, 0), 100))

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

  def populate_health_scores(
    self, results: list[DatasetResult]
  ) -> list[DatasetResult]:
    """Populate health_score field in results."""
    for result in results:
      result.health_score = self.compute_health_score(result)
    return results
