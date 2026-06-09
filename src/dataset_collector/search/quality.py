"""Dataset quality scoring."""

from __future__ import annotations

from datetime import datetime, timezone

from dataset_collector.core.models import DatasetResult

SOURCE_CREDIBILITY = {
  "Kaggle": 0.9,
  "HuggingFace": 0.9,
  "GitHub": 0.75,
  "Government Data": 0.85,
  "Research Sources": 0.88,
  "Google Dataset Search": 0.8,
  "Internet Archive": 0.7,
}


def compute_quality_score(result: DatasetResult) -> float:
  """Return quality score 0.0–10.0."""
  score = 5.0

  # Documentation / description
  desc = (result.description or "").strip()
  if len(desc) > 200:
    score += 1.5
  elif len(desc) > 50:
    score += 0.8
  elif not desc:
    score -= 1.0

  # Metadata completeness
  if result.estimated_size_bytes is not None:
    score += 0.5
  if result.file_count is not None:
    score += 0.5
  if result.license_info and result.license_info.lower() not in ("unknown", "see source", "see kaggle page"):
    score += 0.8
  if result.files or result.download_urls:
    score += 0.7

  # Recency
  if result.last_updated:
    days = (datetime.now(timezone.utc) - result.last_updated.replace(tzinfo=timezone.utc)).days
    if days < 365:
      score += 1.0
    elif days < 1095:
      score += 0.4
    else:
      score -= 0.3

  # Download availability
  if result.download_urls:
    score += 1.0
  elif result.url.startswith("http"):
    score += 0.3

  # Popularity signals
  downloads = result.metadata.get("downloads", 0)
  stars = result.metadata.get("stars", 0)
  if isinstance(downloads, int) and downloads > 500:
    score += 0.8
  if isinstance(stars, int) and stars > 20:
    score += 0.6

  # Source credibility
  score += SOURCE_CREDIBILITY.get(result.source.value, 0.5) * 0.5

  return round(min(max(score, 0.0), 10.0), 1)
