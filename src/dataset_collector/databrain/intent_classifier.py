"""Search intent detection from query text."""

from __future__ import annotations

from collections import Counter

import numpy as np
from scipy.spatial.distance import cosine

from dataset_collector.core.models import DatasetResult
from dataset_collector.databrain.embeddings_cache import EmbeddingsCache
from dataset_collector.databrain.model_manager import ModelManager
from dataset_collector.logging.logger import AppLogger


class IntentClassifier:
  """Detect user search intent from query to improve ranking and discovery."""

  def __init__(
    self,
    model_manager: ModelManager,
    embeddings_cache: EmbeddingsCache,
    logger: AppLogger | None = None,
  ) -> None:
    self._model_manager = model_manager
    self._cache = embeddings_cache
    self._logger = logger

  def classify_intent(
    self,
    query: str,
    all_datasets: list[DatasetResult] | None = None,
    limit: int = 3,
  ) -> list[str]:
    """Return intent tags detected from query."""
    try:
      if not all_datasets:
        return []

      encoder = self._model_manager.get_encoder()
      query_embedding = encoder.encode(query, convert_to_numpy=True)

      # Find semantically similar datasets
      similar_datasets = self._find_similar_datasets(
        query_embedding,
        all_datasets,
        limit=20,
      )

      # Extract tags from similar datasets
      all_tags = []
      for dataset in similar_datasets:
        tags = dataset.metadata.get("tags", [])
        if isinstance(tags, list):
          all_tags.extend(tags)
        elif isinstance(tags, str):
          all_tags.extend([t.strip() for t in tags.split(",")])

      # Also include category if available
      for dataset in similar_datasets:
        category = dataset.metadata.get("category")
        if category:
          all_tags.append(category)

      # Get most common tags
      if all_tags:
        counter = Counter(all_tags)
        intents = [tag for tag, _ in counter.most_common(limit)]
        return intents

      return []
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Intent classification failed: {e}",
          origin="IntentClassifier",
        )
      return []

  def _find_similar_datasets(
    self,
    query_embedding: np.ndarray,
    datasets: list[DatasetResult],
    limit: int = 20,
  ) -> list[DatasetResult]:
    """Find datasets most similar to query."""
    similarities = {}

    # Get embeddings
    dataset_ids = [d.id for d in datasets]
    embeddings = self._cache.get_by_ids(dataset_ids)

    id_to_dataset = {d.id: d for d in datasets}

    # Compute similarities
    for dataset_id, embedding in embeddings.items():
      try:
        distance = cosine(query_embedding, embedding)
        similarity = 1 - distance
        similarities[dataset_id] = similarity
      except Exception:
        continue

    # Return top N datasets
    sorted_ids = sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [id_to_dataset[did] for did, _ in sorted_ids if did in id_to_dataset]

  def get_intent_confidence(self, query: str, intents: list[str]) -> float:
    """Return 0-1 confidence score for detected intents."""
    if not intents:
      return 0.0

    # Simple heuristic: more intents detected = higher confidence
    return min(len(intents) / 3, 1.0)
