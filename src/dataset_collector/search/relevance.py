"""Relevance scoring, intelligent ranking, and budget selection."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from dataset_collector.core.models import DatasetResult
from dataset_collector.search.quality import compute_quality_score

DEFAULT_UNKNOWN_SIZE = 50 * 1024 * 1024

SOURCE_WEIGHT = {
  "Kaggle": 1.0,
  "HuggingFace": 1.0,
  "GitHub": 0.85,
  "Government Data": 0.9,
  "Research Sources": 0.92,
  "Google Dataset Search": 0.88,
  "Internet Archive": 0.75,
}


def score_relevance(query: str, result: DatasetResult) -> float:
  """Query relevance 0.0–1.0."""
  query_clean = query.strip().lower()
  if not query_clean:
    return 0.0

  terms = [t for t in re.split(r"\W+", query_clean) if len(t) > 1] or [query_clean]
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

  downloads = result.metadata.get("downloads", 0)
  stars = result.metadata.get("stars", 0)
  if isinstance(downloads, int) and downloads > 1000:
    score += 0.05
  if isinstance(stars, int) and stars > 50:
    score += 0.05

  return min(score, 1.0)


def compute_rank_score(query: str, result: DatasetResult) -> int:
  """Composite rank score 0–100."""
  relevance = result.relevance_score * 40

  popularity = 0.0
  downloads = result.metadata.get("downloads", 0)
  stars = result.metadata.get("stars", 0)
  if isinstance(downloads, int):
    popularity += min(downloads / 10000, 1.0) * 15
  if isinstance(stars, int):
    popularity += min(stars / 500, 1.0) * 10

  recency = 0.0
  if result.last_updated:
    days = max((datetime.now(timezone.utc) - result.last_updated.replace(tzinfo=timezone.utc)).days, 0)
    recency = max(0, 15 - days / 365 * 15)

  completeness = 0.0
  if result.description:
    completeness += 5
  if result.estimated_size_bytes:
    completeness += 4
  if result.file_count:
    completeness += 3
  if result.download_urls:
    completeness += 5
  if result.license_info not in ("Unknown", "See source"):
    completeness += 3

  credibility = SOURCE_WEIGHT.get(result.source.value, 0.7) * 10
  quality = (result.quality_score / 10) * 10

  total = relevance + popularity + recency + completeness + credibility + quality
  return int(min(max(total, 0), 100))


def rank_results(query: str, results: list[DatasetResult], min_score: float = 0.12) -> list[DatasetResult]:
  """Score, quality-rate, and sort results."""
  for r in results:
    r.relevance_score = score_relevance(query, r)
    r.quality_score = compute_quality_score(r)
    r.rank_score = compute_rank_score(query, r)
    if not r.available_sources:
      r.available_sources = [r.source.value]

  filtered = [r for r in results if r.relevance_score >= min_score]
  if len(filtered) < 5 and results:
    filtered = sorted(results, key=lambda r: r.rank_score, reverse=True)[:max(20, len(results) // 2)]
  else:
    filtered = sorted(filtered, key=lambda r: r.rank_score, reverse=True)

  return filtered


def suggest_within_budget(results: list[DatasetResult], max_bytes: int) -> list[DatasetResult]:
  if max_bytes <= 0:
    return []
  sorted_results = sorted(results, key=lambda r: r.rank_score, reverse=True)
  selected: list[DatasetResult] = []
  used = 0
  for r in sorted_results:
    size = r.estimated_size_bytes if r.estimated_size_bytes is not None else DEFAULT_UNKNOWN_SIZE
    if used + size <= max_bytes:
      selected.append(r)
      used += size
    elif not selected and r.estimated_size_bytes is None and max_bytes >= DEFAULT_UNKNOWN_SIZE:
      selected.append(r)
      used += DEFAULT_UNKNOWN_SIZE
  return selected
