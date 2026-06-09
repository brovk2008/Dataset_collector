"""Relevance scoring and size-budget selection for search results."""

from __future__ import annotations

import re

from dataset_collector.core.models import DatasetResult

DEFAULT_UNKNOWN_SIZE = 50 * 1024 * 1024  # 50 MB estimate for unknown sizes


def score_relevance(query: str, result: DatasetResult) -> float:
  """Score how well a dataset matches the search query (0.0–1.0)."""
  query_clean = query.strip().lower()
  if not query_clean:
    return 0.0

  terms = [t for t in re.split(r"\W+", query_clean) if len(t) > 1]
  if not terms:
    terms = [query_clean]

  name = result.name.lower()
  desc = (result.description or "").lower()
  combined = f"{name} {desc}"

  term_hits = sum(1 for t in terms if t in combined)
  name_hits = sum(1 for t in terms if t in name)
  score = (term_hits / len(terms)) * 0.5 + (name_hits / len(terms)) * 0.4

  if query_clean in combined:
    score += 0.25
  if query_clean in name:
    score += 0.15

  # Boost well-known quality signals from metadata
  downloads = result.metadata.get("downloads", 0)
  stars = result.metadata.get("stars", 0)
  if isinstance(downloads, int) and downloads > 1000:
    score += 0.05
  if isinstance(stars, int) and stars > 50:
    score += 0.05

  return min(score, 1.0)


def rank_results(query: str, results: list[DatasetResult], min_score: float = 0.15) -> list[DatasetResult]:
  """Score, filter, and sort results by relevance."""
  for r in results:
    r.relevance_score = score_relevance(query, r)

  filtered = [r for r in results if r.relevance_score >= min_score]
  if len(filtered) < 5 and results:
    filtered = sorted(results, key=lambda r: r.relevance_score, reverse=True)[:max(20, len(results) // 2)]
  else:
    filtered = sorted(filtered, key=lambda r: r.relevance_score, reverse=True)

  return filtered


def suggest_within_budget(
  results: list[DatasetResult],
  max_bytes: int,
) -> list[DatasetResult]:
  """
  Greedily pick the highest-relevance datasets that fit within a total size budget.
  """
  if max_bytes <= 0:
    return []

  sorted_results = sorted(results, key=lambda r: r.relevance_score, reverse=True)
  selected: list[DatasetResult] = []
  used = 0

  for r in sorted_results:
    size = r.estimated_size_bytes if r.estimated_size_bytes is not None else DEFAULT_UNKNOWN_SIZE
    if used + size <= max_bytes:
      selected.append(r)
      used += size
    elif not selected and r.estimated_size_bytes is None:
      # Allow one unknown-size dataset if nothing selected yet and budget is large enough
      if max_bytes >= DEFAULT_UNKNOWN_SIZE:
        selected.append(r)
        used += DEFAULT_UNKNOWN_SIZE

  return selected
