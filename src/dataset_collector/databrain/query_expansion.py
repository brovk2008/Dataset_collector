"""Smart semantic query expansion to improve recall."""

from __future__ import annotations

import re
from collections import Counter
from typing import TypedDict

import numpy as np
from scipy.spatial.distance import cosine

from dataset_collector.core.models import DatasetResult
from dataset_collector.databrain.embeddings_cache import EmbeddingsCache
from dataset_collector.databrain.model_manager import ModelManager
from dataset_collector.logging.logger import AppLogger


class ExpansionResult(TypedDict):
  """Result of multi-strategy query expansion."""
  original: str
  semantic: list[str]
  synonyms: list[str]
  category: list[str]
  related: list[str]
  all_terms: list[str]


# Domain-specific synonyms for common dataset search patterns
DOMAIN_SYNONYMS = {
  "anime": ["manga", "japanese animation", "visual novel", "fansub", "anime text"],
  "medical": ["healthcare", "clinical", "diagnostic", "radiology", "hospital"],
  "imaging": ["images", "vision", "pictures", "visual", "photos", "xray", "mri"],
  "dataset": ["data", "collection", "corpus", "benchmark", "database"],
  "satellite": ["earth observation", "remote sensing", "aerial", "geospatial"],
  "subtitle": ["caption", "dialogue", "transcript", "text", "srt"],
  "music": ["audio", "sound", "song", "mp3", "wav"],
  "video": ["movie", "film", "footage", "motion", "clip"],
  "text": ["document", "corpus", "language", "nlp", "document"],
  "image": ["photo", "picture", "visual", "picture", "imaging"],
}

# Category detection patterns
CATEGORY_PATTERNS = {
  "text": ["corpus", "nlp", "language", "dialogue", "transcript", "subtitle", "document"],
  "image": ["imaging", "vision", "photo", "xray", "mri", "medical", "visual"],
  "audio": ["music", "sound", "voice", "speech", "audio", "wav"],
  "video": ["video", "movie", "film", "footage", "clip"],
  "time_series": ["sensor", "sensor data", "temporal", "time series", "timeseries"],
  "graph": ["network", "graph", "knowledge graph", "relationship"],
  "tabular": ["csv", "spreadsheet", "table", "database", "sql"],
}


class QueryExpander:
  """Automatically expand queries using multiple strategies to maximize recall."""

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

  def expand_query_aggressive(
    self,
    query: str,
    all_datasets: list[DatasetResult] | None = None,
    max_expansions: int = 30,
  ) -> ExpansionResult:
    """Multi-strategy query expansion for maximum recall (15-30 terms).

    Strategies:
    1. Semantic: Similar dataset names/descriptions (8-10 terms)
    2. Synonyms: Domain-specific synonyms (5-8 terms)
    3. Category: Dataset type related terms (4-6 terms)
    4. Related: From previous searches (3-5 terms)
    5. Decomposition: Split multi-word query (2-4 terms)

    Returns:
        ExpansionResult with separate lists per strategy + all_terms combined
    """
    result: ExpansionResult = {
      "original": query,
      "semantic": [],
      "synonyms": [],
      "category": [],
      "related": [],
      "all_terms": [query],  # Always include original
    }

    try:
      # Strategy 1: Semantic expansion
      if all_datasets:
        result["semantic"] = self._expand_semantic(query, all_datasets, limit=10)
        result["all_terms"].extend(result["semantic"])

      # Strategy 2: Synonym expansion
      result["synonyms"] = self._expand_synonyms(query, limit=8)
      result["all_terms"].extend(result["synonyms"])

      # Strategy 3: Category-based expansion
      result["category"] = self._expand_category(query, limit=6)
      result["all_terms"].extend(result["category"])

      # Strategy 4: Related terms (from behavior - placeholder for now)
      result["related"] = self._expand_related(query, limit=5)
      result["all_terms"].extend(result["related"])

      # Strategy 5: Decomposition (split multi-word)
      result["all_terms"].extend(self._decompose_query(query, limit=4))

      # Remove duplicates and limit to max_expansions
      unique_terms = []
      seen = set()
      for term in result["all_terms"]:
        term_lower = term.lower()
        if term_lower not in seen:
          unique_terms.append(term)
          seen.add(term_lower)

      result["all_terms"] = unique_terms[:max_expansions]
      return result

    except Exception as e:
      if self._logger:
        self._logger.error(f"Aggressive query expansion failed: {e}", origin="QueryExpander")
      return result

  def _expand_semantic(
    self,
    query: str,
    datasets: list[DatasetResult],
    limit: int = 10,
  ) -> list[str]:
    """Find semantically similar dataset titles."""
    try:
      encoder = self._model_manager.get_encoder()
      query_embedding = encoder.encode(query, convert_to_numpy=True)

      similar_texts = self._find_similar_texts(query_embedding, datasets, limit=limit * 2)
      expanded = self._extract_terms(similar_texts, limit=limit)

      return [t for t in expanded if t.lower() != query.lower()][:limit]
    except Exception as e:
      if self._logger:
        self._logger.error(f"Semantic expansion failed: {e}", origin="QueryExpander")
      return []

  def _expand_synonyms(self, query: str, limit: int = 8) -> list[str]:
    """Find domain-specific synonyms."""
    synonyms = []
    query_lower = query.lower()

    # Check each word in query against domain synonyms
    for domain_term, syn_list in DOMAIN_SYNONYMS.items():
      if domain_term in query_lower:
        synonyms.extend(syn_list)

    # Remove duplicates and original query
    unique_syns = []
    seen = set()
    for syn in synonyms:
      if syn.lower() not in seen and syn.lower() != query_lower:
        unique_syns.append(syn)
        seen.add(syn.lower())

    return unique_syns[:limit]

  def _expand_category(self, query: str, limit: int = 6) -> list[str]:
    """Expand with category-related terms based on detected dataset type."""
    category_terms = []
    query_lower = query.lower()

    # Detect likely category
    for category, patterns in CATEGORY_PATTERNS.items():
      if any(pattern in query_lower for pattern in patterns):
        # Add category-specific terms
        if category == "text":
          category_terms.extend(["text dataset", "corpus", "nlp dataset", "language data"])
        elif category == "image":
          category_terms.extend(["image dataset", "vision dataset", "visual data", "photography"])
        elif category == "audio":
          category_terms.extend(["audio dataset", "sound data", "music dataset"])
        elif category == "video":
          category_terms.extend(["video dataset", "video data", "motion data"])

    return category_terms[:limit]

  def _expand_related(self, query: str, limit: int = 5) -> list[str]:
    """Expand with related terms from user behavior (placeholder)."""
    # TODO: Pull from UserBehaviorTracker similar queries
    # For now, return empty - will be enhanced in Phase 10
    return []

  def _decompose_query(self, query: str, limit: int = 4) -> list[str]:
    """Decompose multi-word queries into components."""
    # Split query and return significant words
    words = query.lower().split()
    significant = [w for w in words if len(w) > 3]
    return significant[:limit]

  def _find_similar_texts(
    self,
    query_embedding: np.ndarray,
    datasets: list[DatasetResult],
    limit: int = 20,
  ) -> list[tuple[str, str]]:
    """Find semantically similar dataset titles/descriptions."""
    similarities: dict[str, tuple[float, str, str]] = {}

    dataset_ids = [d.id for d in datasets]
    embeddings = self._cache.get_by_ids(dataset_ids)
    id_to_dataset = {d.id: d for d in datasets}

    for dataset_id, embedding in embeddings.items():
      try:
        distance = cosine(query_embedding, embedding)
        similarity = 1 - distance
        dataset = id_to_dataset[dataset_id]
        similarities[dataset_id] = (similarity, dataset.name, dataset.description or "")
      except Exception:
        continue

    sorted_items = sorted(similarities.items(), key=lambda x: x[1][0], reverse=True)[:limit]
    return [(name, desc) for _, (_, name, desc) in sorted_items]

  def _extract_terms(self, texts: list[tuple[str, str]], limit: int = 10) -> list[str]:
    """Extract meaningful terms from texts."""
    all_text = " ".join([f"{name} {desc}" for name, desc in texts])
    tokens = re.findall(r"\b\w+\b", all_text.lower())
    tokens = [t for t in tokens if len(t) > 2]
    counter = Counter(tokens)
    return [term for term, _ in counter.most_common(limit)]

  def expand_query(
    self,
    query: str,
    all_datasets: list[DatasetResult] | None = None,
    max_expansions: int = 10,
  ) -> list[str]:
    """Return original query + semantic variants (legacy interface)."""
    try:
      encoder = self._model_manager.get_encoder()
      query_embedding = encoder.encode(query, convert_to_numpy=True)

      if not all_datasets:
        return [query]

      similar_texts = self._find_similar_texts(
        query_embedding,
        all_datasets,
        limit=max_expansions * 2,
      )

      expanded_terms = self._extract_terms(similar_texts)

      result = [query]
      for term in expanded_terms[:max_expansions]:
        if term.lower() != query.lower() and term not in result:
          result.append(term)

      return result[:1 + max_expansions]
    except Exception as e:
      if self._logger:
        self._logger.error(f"Query expansion failed: {e}", origin="QueryExpander")
      return [query]

  def boost_by_expansion(
    self,
    query: str,
    results: list[DatasetResult],
    all_datasets: list[DatasetResult],
  ) -> list[DatasetResult]:
    """Boost results that match expanded query terms."""
    try:
      expanded_result = self.expand_query_aggressive(query, all_datasets, max_expansions=30)
      all_terms = expanded_result["all_terms"]

      for result in results:
        text = f"{result.name} {result.description}".lower()
        matched_terms = sum(1 for term in all_terms if term.lower() in text)
        if matched_terms > 0:
          boost = min(1.0 + (matched_terms * 0.1), 0.2)
          result.relevance_score = min(result.relevance_score * (1 + boost), 1.0)

      return results
    except Exception as e:
      if self._logger:
        self._logger.error(f"Boost by expansion failed: {e}", origin="QueryExpander")
      return results
