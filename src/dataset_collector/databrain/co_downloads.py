"""Track co-downloads for \"People Also Downloaded\" discovery."""

from __future__ import annotations

from dataset_collector.databrain.user_behavior import UserBehaviorTracker
from dataset_collector.logging.logger import AppLogger


class CoDownloadsTracker:
  """Track which datasets are downloaded together for discovery."""

  def __init__(
    self,
    user_behavior: UserBehaviorTracker,
    logger: AppLogger | None = None,
  ) -> None:
    self._behavior = user_behavior
    self._logger = logger

  def log_download_set(self, dataset_ids: list[str]) -> None:
    """Log a multi-dataset download session."""
    self._behavior.log_download_set(dataset_ids)

  def get_co_downloads(
    self,
    dataset_id: str,
    limit: int = 5,
  ) -> list[tuple[str, int]]:
    """Get datasets co-downloaded with this one, sorted by count."""
    return self._behavior.get_co_downloads(dataset_id, limit)

  def get_co_download_score(
    self,
    dataset_a_id: str,
    dataset_b_id: str,
  ) -> float:
    """Compute 0-1 score for co-download relationship."""
    co_downloads = self.get_co_downloads(dataset_a_id, limit=1000)

    for dataset_id, count in co_downloads:
      if dataset_id == dataset_b_id:
        # Normalize: 10+ co-downloads = 1.0
        return min(count / 10, 1.0)

    return 0.0
