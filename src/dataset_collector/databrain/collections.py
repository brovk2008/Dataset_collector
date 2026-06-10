"""Auto-generated thematic dataset collections."""

from __future__ import annotations

from dataclasses import dataclass

from dataset_collector.core.models import DatasetResult
from dataset_collector.logging.logger import AppLogger


@dataclass
class Collection:
  """Thematic collection of related datasets."""

  id: str
  name: str
  description: str
  datasets: list[DatasetResult]
  quality_score: float
  size: int


class CollectionsGenerator:
  """Generate thematic collections from dataset embeddings."""

  def __init__(
    self,
    logger: AppLogger | None = None,
  ) -> None:
    self._logger = logger
    self._collections_cache: list[Collection] = []
    self._dataset_to_collection: dict[str, Collection] = {}  # O(1) lookup cache

  def detect_collections(
    self,
    all_datasets: list[DatasetResult],
    min_cluster_size: int = 3,
  ) -> list[Collection]:
    """Detect thematic clusters of related datasets."""
    try:
      if len(all_datasets) < min_cluster_size:
        return []

      # Group by category if available
      category_groups: dict[str, list[DatasetResult]] = {}
      for dataset in all_datasets:
        category = dataset.metadata.get("category", "Uncategorized")
        if category not in category_groups:
          category_groups[category] = []
        category_groups[category].append(dataset)

      # Create collections from categories
      collections = []
      for category, datasets in category_groups.items():
        if len(datasets) >= min_cluster_size:
          quality = sum(d.health_score for d in datasets) / len(datasets) if datasets else 0
          collection = Collection(
            id=f"collection_{category.lower().replace(' ', '_')}",
            name=category,
            description=f"{len(datasets)} related datasets",
            datasets=datasets,
            quality_score=quality,
            size=len(datasets),
          )
          collections.append(collection)

      self._collections_cache = collections

      # Build reverse mapping for O(1) lookup
      self._dataset_to_collection.clear()
      for collection in collections:
        for dataset in collection.datasets:
          self._dataset_to_collection[dataset.id] = collection

      return collections
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Collection detection failed: {e}",
          origin="CollectionsGenerator",
        )
      return []

  def get_collection_for_dataset(
    self, dataset_id: str
  ) -> Collection | None:
    """Find which collection a dataset belongs to (O(1) via cache)."""
    return self._dataset_to_collection.get(dataset_id)

  def get_all_collections(self) -> list[Collection]:
    """Return all detected collections."""
    return self._collections_cache
