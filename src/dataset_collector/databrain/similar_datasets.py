"""Find semantically related datasets using embedding similarity."""

from __future__ import annotations

from scipy.spatial.distance import cosine

from dataset_collector.core.models import DatasetResult
from dataset_collector.databrain.embeddings_cache import EmbeddingsCache
from dataset_collector.logging.logger import AppLogger


class SimilarDatasetsEngine:
  """Find semantically related datasets via cosine similarity."""

  def __init__(
    self,
    embeddings_cache: EmbeddingsCache,
    logger: AppLogger | None = None,
  ) -> None:
    self._cache = embeddings_cache
    self._logger = logger

  def find_similar(
    self,
    dataset_id: str,
    all_datasets: list[DatasetResult],
    limit: int = 5,
  ) -> list[DatasetResult]:
    """Find top N similar datasets using embedding similarity."""
    try:
      # Get target embedding
      target_embedding = self._cache.get(dataset_id)
      if target_embedding is None:
        if self._logger:
          self._logger.info(
            f"No embedding for {dataset_id}",
          )
        return []

      # Get all other embeddings
      other_ids = [d.id for d in all_datasets if d.id != dataset_id]
      embeddings = self._cache.get_by_ids(other_ids)

      # Compute similarities
      similarities = {}
      for other_id, other_embedding in embeddings.items():
        try:
          distance = cosine(target_embedding, other_embedding)
          similarity = 1 - distance
          similarities[other_id] = max(0.0, min(1.0, similarity))
        except Exception as e:
          if self._logger:
            self._logger.info(
              f"Similarity computation failed for {other_id}: {e}",
            )
          continue

      # Sort by similarity and return top N
      sorted_ids = sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:limit]

      # Map back to DatasetResults
      id_to_result = {d.id: d for d in all_datasets}
      results = [id_to_result[sid] for sid, _ in sorted_ids if sid in id_to_result]

      return results
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to find similar datasets: {e}",
          origin="SimilarDatasetsEngine",
        )
      return []

  def find_similar_batch(
    self,
    dataset_ids: list[str],
    all_datasets: list[DatasetResult],
    limit: int = 5,
  ) -> dict[str, list[DatasetResult]]:
    """Batch query for similar datasets (load embeddings once)."""
    try:
      results: dict[str, list[DatasetResult]] = {}

      # Load all embeddings once (not per dataset)
      all_ids = [d.id for d in all_datasets]
      all_embeddings = self._cache.get_by_ids(all_ids)

      id_to_result = {d.id: d for d in all_datasets}

      # For each requested dataset, compute similarities
      for dataset_id in dataset_ids:
        if dataset_id not in all_embeddings:
          results[dataset_id] = []
          continue

        target_embedding = all_embeddings[dataset_id]
        similarities = {}

        # Compute similarities against all others
        for other_id, other_embedding in all_embeddings.items():
          if other_id == dataset_id:
            continue
          try:
            distance = cosine(target_embedding, other_embedding)
            similarity = 1 - distance
            similarities[other_id] = max(0.0, min(1.0, similarity))
          except Exception:
            continue

        # Sort by similarity and return top N
        sorted_ids = sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:limit]
        results[dataset_id] = [id_to_result[sid] for sid, _ in sorted_ids if sid in id_to_result]

      return results
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to batch find similar: {e}",
          origin="SimilarDatasetsEngine",
        )
      return {did: [] for did in dataset_ids}
