"""Cross-source duplicate detection and merging."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult


def _normalize_name(name: str) -> str:
  n = name.lower().strip()
  n = re.sub(r"[^a-z0-9]+", " ", n)
  return re.sub(r"\s+", " ", n).strip()


def _similarity(a: str, b: str) -> float:
  return SequenceMatcher(None, _normalize_name(a), _normalize_name(b)).ratio()


def merge_duplicates(results: list[DatasetResult], threshold: float = 0.82) -> list[DatasetResult]:
  """Merge datasets that appear across multiple sources."""
  merged: list[DatasetResult] = []
  used: set[int] = set()

  for i, a in enumerate(results):
    if i in used:
      continue
    group = [a]
    used.add(i)

    for j, b in enumerate(results):
      if j in used or j <= i:
        continue
      if _is_duplicate(a, b, threshold):
        group.append(b)
        used.add(j)

    if len(group) == 1:
      merged.append(a)
    else:
      merged.append(_merge_group(group))

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
  all_urls = list(dict.fromkeys(
    u for g in group for u in ([g.url] + g.download_urls) if u
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
