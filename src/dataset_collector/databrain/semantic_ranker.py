"""Semantic similarity ranking and hybrid ranking integration."""

from __future__ import annotations

import numpy as np
from scipy.spatial.distance import cosine

from dataset_collector.core.models import DatasetResult
from dataset_collector.databrain.embeddings_cache import EmbeddingsCache
from dataset_collector.databrain.model_manager import ModelManager
from dataset_collector.logging.logger import AppLogger


class SemanticRanker:
  """Compute cosine similarity and integrate semantic scoring into hybrid ranking."""

  def __init__(
    self,
    model_manager: ModelManager,
    embeddings_cache: EmbeddingsCache,
    logger: AppLogger | None = None,
  ) -> None:
    self._model_manager = model_manager
    self._cache = embeddings_cache
    self._logger = logger

  def compute_query_embedding(self, query: str) -> np.ndarray:
    """Generate embedding for search query."""
    try:
      encoder = self._model_manager.get_encoder()
      embedding = encoder.encode(query, convert_to_numpy=True)
      return embedding
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to compute query embedding: {e}",
          origin="SemanticRanker",
        )
      raise

  def compute_result_embeddings(
    self, results: list[DatasetResult]
  ) -> list[DatasetResult]:
    """Ensure each result has cached embedding, populate cache."""
    try:
      encoder = self._model_manager.get_encoder()

      # Check which embeddings are missing
      missing_ids = [r.id for r in results if not self._cache.exists(r.id)]

      if missing_ids:
        # Batch compute missing embeddings
        missing_results = {r.id: r for r in results if r.id in missing_ids}
        texts_to_embed = [
          f"{missing_results[rid].name} {missing_results[rid].description}"
          for rid in missing_ids
        ]

        embeddings = encoder.encode(texts_to_embed, convert_to_numpy=True)

        # Cache all computed embeddings
        for rid, embedding in zip(missing_ids, embeddings):
          self._cache.set(rid, missing_results[rid], embedding)

      return results
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to compute result embeddings: {e}",
          origin="SemanticRanker",
        )
      return results

  def score_semantic_similarity(
    self,
    query_embedding: np.ndarray,
    dataset_embeddings: dict[str, np.ndarray],
  ) -> dict[str, float]:
    """Compute cosine similarity between query and datasets (0-1 scale)."""
    scores = {}

    for dataset_id, dataset_embedding in dataset_embeddings.items():
      try:
        # Cosine distance is 0-2, convert to similarity 0-1
        distance = cosine(query_embedding, dataset_embedding)
        similarity = 1 - distance
        scores[dataset_id] = max(0.0, min(1.0, similarity))
      except Exception as e:
        if self._logger:
          self._logger.debug(
            f"Failed to compute similarity for {dataset_id}: {e}",
            origin="SemanticRanker",
          )
        scores[dataset_id] = 0.0

    return scores

  def score_results(
    self,
    query: str,
    results: list[DatasetResult],
  ) -> list[DatasetResult]:
    """Score all results with semantic similarity."""
    try:
      # Compute query embedding
      query_embedding = self.compute_query_embedding(query)

      # Ensure all results have cached embeddings
      self.compute_result_embeddings(results)

      # Get all embeddings from cache
      result_ids = [r.id for r in results]
      embeddings = self._cache.get_by_ids(result_ids)

      # Compute similarities
      similarities = self.score_semantic_similarity(query_embedding, embeddings)

      # Populate semantic_score in results
      for result in results:
        result.semantic_score = similarities.get(result.id, 0.0)

      return results
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to score results semantically: {e}",
          origin="SemanticRanker",
        )
      # Return results unchanged if semantic scoring fails
      return results
