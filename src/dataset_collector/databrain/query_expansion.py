"""Smart semantic query expansion to improve recall."""

from __future__ import annotations

import re
from collections import Counter

import numpy as np
from scipy.spatial.distance import cosine

from dataset_collector.core.models import DatasetResult
from dataset_collector.databrain.embeddings_cache import EmbeddingsCache
from dataset_collector.databrain.model_manager import ModelManager
from dataset_collector.logging.logger import AppLogger


class QueryExpander:
  """Automatically expand queries semantically to improve recall."""

  def __init__(
    self,
    model_manager: ModelManager,
    embeddings_cache: EmbeddingsCache,
    logger: AppLogger | None = None,
    expansion_limit: int = 10,
  ) -> None:
    self._model_manager = model_manager
    self._cache = embeddings_cache
    self._logger = logger
    self._expansion_limit = expansion_limit

  def expand_query(
    self,
    query: str,
    all_datasets: list[DatasetResult] | None = None,
    max_expansions: int = 10,
  ) -> list[str]:
    """Return original query + semantic variants."""
    try:
      encoder = self._model_manager.get_encoder()
      query_embedding = encoder.encode(query, convert_to_numpy=True)

      if not all_datasets:
        return [query]

      # Find semantically similar dataset titles/descriptions
      similar_texts = self._find_similar_texts(
        query_embedding,
        all_datasets,
        limit=max_expansions * 2,
      )

      # Extract terms from similar texts
      expanded_terms = self._extract_terms(similar_texts)

      # Return original + expanded terms
      result = [query]
      for term in expanded_terms[:max_expansions]:
        if term.lower() != query.lower() and term not in result:
          result.append(term)

      return result[:1 + max_expansions]
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Query expansion failed: {e}",
          origin="QueryExpander",
        )
      return [query]

  def _find_similar_texts(
    self,
    query_embedding: np.ndarray,
    datasets: list[DatasetResult],
    limit: int = 20,
  ) -> list[tuple[str, str]]:
    """Find semantically similar dataset titles/descriptions."""
    similarities = {}

    # Get embeddings for all datasets
    dataset_ids = [d.id for d in datasets]
    embeddings = self._cache.get_by_ids(dataset_ids)

    id_to_dataset = {d.id: d for d in datasets}

    # Compute similarities
    for dataset_id, embedding in embeddings.items():
      try:
        distance = cosine(query_embedding, embedding)
        similarity = 1 - distance
        dataset = id_to_dataset[dataset_id]
        similarities[dataset_id] = (similarity, dataset.name, dataset.description or "")
      except Exception:
        continue

    # Sort and return top N
    sorted_items = sorted(similarities.items(), key=lambda x: x[1][0], reverse=True)[:limit]
    return [(name, desc) for _, (_, name, desc) in sorted_items]

  def _extract_terms(self, texts: list[tuple[str, str]]) -> list[str]:
    """Extract meaningful terms from texts."""
    all_text = " ".join([f"{name} {desc}" for name, desc in texts])

    # Simple tokenization: split by non-word chars, filter by length
    tokens = re.findall(r"\b\w+\b", all_text.lower())
    tokens = [t for t in tokens if len(t) > 2]

    # Count term frequencies and return top unique terms
    counter = Counter(tokens)
    return [term for term, _ in counter.most_common(self._expansion_limit)]

  def boost_by_expansion(
    self,
    query: str,
    results: list[DatasetResult],
    all_datasets: list[DatasetResult],
  ) -> list[DatasetResult]:
    """Boost results that match expanded query terms."""
    try:
      expanded_terms = self.expand_query(query, all_datasets, max_expansions=10)

      # For each result, check if it matches any expanded term
      for result in results:
        text = f"{result.name} {result.description}".lower()
        matched_terms = sum(1 for term in expanded_terms if term.lower() in text)
        if matched_terms > 0:
          # Boost relevance score by 10% per matched expanded term (max 1.2x)
          boost = min(1.0 + (matched_terms * 0.1), 0.2)
          result.relevance_score = min(result.relevance_score * (1 + boost), 1.0)

      return results
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Boost by expansion failed: {e}",
          origin="QueryExpander",
        )
      return results
