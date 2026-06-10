"""Cross-source duplicate detection and merging."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

from dataset_collector.core.models import DatasetResult

if TYPE_CHECKING:
  import numpy as np


def _normalize_name(name: str) -> str:
  n = name.lower().strip()
  n = re.sub(r"[^a-z0-9]+", " ", n)
  return re.sub(r"\s+", " ", n).strip()


def _similarity(a: str, b: str) -> float:
  return SequenceMatcher(None, _normalize_name(a), _normalize_name(b)).ratio()


def merge_duplicates(results: list[DatasetResult], threshold: float = 0.82) -> list[DatasetResult]:
  """Merge datasets that appear across multiple sources (O(n log n) via hash buckets)."""
  if not results:
    return []

  merged: list[DatasetResult] = []
  used: set[int] = set()

  # Pre-compute normalized names and identifiers for O(1) bucket lookup
  normalized_names = [_normalize_name(r.name) for r in results]
  urls = [r.url for r in results]
  dois = [r.metadata.get("doi", "") for r in results]
  refs = [r.metadata.get("ref", "") for r in results]

  # Build hash buckets for quick candidate matching
  url_buckets: dict[str, list[int]] = {}
  name_buckets: dict[str, list[int]] = {}
  doi_buckets: dict[str, list[int]] = {}
  ref_buckets: dict[str, list[int]] = {}

  for idx, result in enumerate(results):
    if urls[idx]:
      url_buckets.setdefault(urls[idx], []).append(idx)
    if normalized_names[idx]:
      name_buckets.setdefault(normalized_names[idx], []).append(idx)
    if dois[idx]:
      doi_buckets.setdefault(dois[idx], []).append(idx)
    if refs[idx]:
      ref_buckets.setdefault(refs[idx], []).append(idx)

  # Process results, grouping by buckets + similarity
  for i, a in enumerate(results):
    if i in used:
      continue

    group = [i]
    used.add(i)

    # Find candidates from all buckets
    candidates = set()
    if urls[i]:
      candidates.update(url_buckets.get(urls[i], []))
    if normalized_names[i]:
      candidates.update(name_buckets.get(normalized_names[i], []))
    if dois[i]:
      candidates.update(doi_buckets.get(dois[i], []))
    if refs[i]:
      candidates.update(ref_buckets.get(refs[i], []))

    # Check only candidates (not all remaining items)
    for j in candidates:
      if j in used or j <= i:
        continue
      if _is_duplicate(results[i], results[j], threshold):
        group.append(j)
        used.add(j)

    # Merge group and add to result
    group_results = [results[idx] for idx in group]
    if len(group_results) == 1:
      merged.append(group_results[0])
    else:
      merged.append(_merge_group(group_results))

  return merged


def _is_duplicate(a: DatasetResult, b: DatasetResult, threshold: float) -> bool:
  if a.url == b.url and a.url:
    return True
  if _normalize_name(a.name) == _normalize_name(b.name):
    return True
  if _similarity(a.name, b.name) >= threshold:
    return True
  # Same DOI or ref
  doi_a = a.metadata.get("doi", "")
  doi_b = b.metadata.get("doi", "")
  if doi_a and doi_a == doi_b:
    return True
  ref_a = a.metadata.get("ref", "")
  ref_b = b.metadata.get("ref", "")
  if ref_a and ref_a == ref_b:
    return True
  return False


def _merge_group(group: list[DatasetResult]) -> DatasetResult:
  """Pick best representative and attach all sources."""
  primary = max(group, key=lambda r: (r.relevance_score, r.quality_score))
  sources = list(dict.fromkeys(
    [primary.source.value] + [g.source.value for g in group if g.source != primary.source]
  ))
  primary.available_sources = sources
  primary.metadata["merged_count"] = len(group)
  primary.metadata["alternate_urls"] = [g.url for g in group if g.url != primary.url]
  if not primary.download_urls:
    for g in group:
      if g.download_urls:
        primary.download_urls = g.download_urls
        break
  if primary.estimated_size_bytes is None:
    for g in group:
      if g.estimated_size_bytes:
        primary.estimated_size_bytes = g.estimated_size_bytes
        break
  return primary


def find_semantic_duplicates(
  results: list[DatasetResult],
  embeddings: dict[str, np.ndarray],
  threshold: float = 0.75,
) -> list[tuple[int, int, float]]:
  """Find semantically similar dataset pairs using embeddings.

  Returns list of (idx1, idx2, similarity_score) tuples where similarity >= threshold.
  """
  try:
    from scipy.spatial.distance import cosine
  except ImportError:
    return []

  duplicates = []

  for i, result_a in enumerate(results):
    if result_a.id not in embeddings:
      continue

    embedding_a = embeddings[result_a.id]

    for j in range(i + 1, len(results)):
      result_b = results[j]
      if result_b.id not in embeddings:
        continue

      embedding_b = embeddings[result_b.id]

      try:
        distance = cosine(embedding_a, embedding_b)
        similarity = 1 - distance
        if similarity >= threshold:
          duplicates.append((i, j, similarity))
      except Exception:
        continue

  return duplicates


def merge_duplicates_with_semantic(
  results: list[DatasetResult],
  embeddings: dict[str, float] | None = None,
  threshold: float = 0.82,
  semantic_threshold: float = 0.75,
) -> list[DatasetResult]:
  """Merge duplicates using both traditional + semantic matching.

  First applies traditional deduplication (URL, name, DOI), then adds
  semantic similarity matching if embeddings available.
  """
  # First pass: traditional deduplication
  merged = merge_duplicates(results, threshold=threshold)

  # Second pass: semantic deduplication (if embeddings available)
  if embeddings:
    try:
      semantic_dups = find_semantic_duplicates(merged, embeddings, semantic_threshold)

      if semantic_dups:
        # Build groups from semantic matches
        used: set[int] = set()
        final_merged: list[DatasetResult] = []

        for i, result in enumerate(merged):
          if i in used:
            continue

          group = [i]
          used.add(i)

          # Find all items semantically similar to this one
          for j, k, _sim in semantic_dups:
            if j == i and k not in used:
              group.append(k)
              used.add(k)
            elif k == i and j not in used:
              group.append(j)
              used.add(j)

          # Merge group
          group_results = [merged[idx] for idx in group]
          if len(group_results) == 1:
            final_merged.append(group_results[0])
          else:
            final_merged.append(_merge_group(group_results))

        return final_merged
    except Exception:
      # If semantic dedup fails, return traditional results
      pass

  return merged
