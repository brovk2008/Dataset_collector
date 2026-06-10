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

COMMERCIAL_LICENSES = {
  "mit", "apache", "bsd", "isc", "cc-by", "cc-by-sa", "cc0",
  "public domain", "unlicense", "mpl", "gpl", "agpl"
}


def compute_quality_score(result: DatasetResult) -> float:
  """Return quality score 0.0–10.0 (legacy interface)."""
  score_100 = compute_health_score_v2(result)
  return round(score_100 / 10.0, 1)


def compute_health_score_v2(result: DatasetResult) -> int:
  """Enhanced health score v2: 0-100 scale with 10 factors.

  Factors:
  1. Documentation quality (>500 chars: +10)
  2. Last updated (6mo: +10, 12mo: +5, older: 0)
  3. Popularity signals (>1000 downloads or >100 stars: +10)
  4. Download count (if available: +5)
  5. Stars normalized (0-10 scale)
  6. License quality (commercial-friendly: +8, other: +4)
  7. Dataset size (10MB-100GB range: +3)
  8. Metadata completeness (name+desc+size+files+license: up to +10)
  9. Source credibility (multiplier: 0.5-0.9)
  10. Download availability (+10 for direct URLs)
  """
  score = 0.0

  # Factor 1: Documentation quality (max 10)
  desc = (result.description or "").strip()
  if len(desc) > 500:
    score += 10.0
  elif len(desc) > 200:
    score += 7.0
  elif len(desc) > 50:
    score += 4.0

  # Factor 2: Last updated recency (max 10)
  if result.last_updated:
    days = (datetime.now(timezone.utc) - result.last_updated.replace(tzinfo=timezone.utc)).days
    if days < 180:  # 6 months
      score += 10.0
    elif days < 365:  # 1 year
      score += 8.0
    elif days < 730:  # 2 years
      score += 5.0
    else:
      score += 2.0

  # Factor 3: Popularity signals (max 10)
  downloads = result.metadata.get("downloads", 0)
  stars = result.metadata.get("stars", 0)
  if (isinstance(downloads, int) and downloads > 1000) or (isinstance(stars, int) and stars > 100):
    score += 10.0
  elif (isinstance(downloads, int) and downloads > 500) or (isinstance(stars, int) and stars > 50):
    score += 7.0
  elif (isinstance(downloads, int) and downloads > 100) or (isinstance(stars, int) and stars > 20):
    score += 4.0

  # Factor 4: Download count available (max 5)
  if isinstance(downloads, int) and downloads > 0:
    score += 5.0

  # Factor 5: Stars normalized (max 10)
  if isinstance(stars, int):
    star_score = min(stars / 50.0, 1.0) * 10.0  # Normalize: 50+ stars = max score
    score += star_score

  # Factor 6: License quality (max 8)
  license_info = (result.license_info or "").lower().strip()
  if license_info and license_info not in ("unknown", "see source", "see kaggle page"):
    if any(comm in license_info for comm in COMMERCIAL_LICENSES):
      score += 8.0
    else:
      score += 4.0

  # Factor 7: Dataset size (max 3)
  if result.estimated_size_bytes:
    size_bytes = result.estimated_size_bytes
    if 10 * 1024 * 1024 <= size_bytes <= 100 * 1024 * 1024 * 1024:  # 10MB to 100GB
      score += 3.0
    elif size_bytes >= 1024 * 1024:  # At least 1MB
      score += 1.5

  # Factor 8: Metadata completeness (max 10)
  completeness = 0
  if result.name:
    completeness += 1
  if desc:
    completeness += 1
  if result.estimated_size_bytes is not None:
    completeness += 1
  if result.file_count is not None or result.files:
    completeness += 1
  if license_info and license_info not in ("unknown", "see source", "see kaggle page"):
    completeness += 1
  score += (completeness / 5.0) * 10.0

  # Factor 9: Download availability (max 10)
  if result.download_urls:
    score += 10.0
  elif result.url and result.url.startswith("http"):
    score += 5.0

  # Factor 10: Source credibility (multiplier 0.8-1.0)
  credibility = SOURCE_CREDIBILITY.get(result.source.value, 0.5)
  base_score = score
  score = base_score * (0.8 + credibility * 0.2)

  # Clamp to 0-100
  final_score = round(min(max(score, 0.0), 100.0))
  return final_score


def get_health_color(score: int) -> str:
  """Return color classification for health score."""
  if score >= 70:
    return "green"
  elif score >= 30:
    return "yellow"
  else:
    return "red"
