"""Base connector interface for dataset sources."""

from __future__ import annotations

import abc
from typing import Callable

from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult, SearchFilters


class BaseConnector(abc.ABC):
  """Abstract base class for all source connectors."""

  source: DataSource

  @abc.abstractmethod
  async def search(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int = 100,
    progress_callback: Callable[[str, float], None] | None = None,
  ) -> list[DatasetResult]:
    """Search the data source for datasets matching the query."""

  def _report_progress(
    self,
    callback: Callable[[str, float], None] | None,
    message: str,
    percent: float,
  ) -> None:
    if callback:
      callback(message, percent)

  def _matches_file_type(self, name: str, filters: SearchFilters) -> bool:
    from dataset_collector.core.enums import FileType

    if FileType.ANY in filters.file_types and not filters.custom_types:
      return True

    text = name.lower()
    ext = text.rsplit(".", 1)[-1] if "." in text else ""
    type_map = {
      FileType.CSV: {"csv"},
      FileType.JSON: {"json", "jsonl"},
      FileType.XLSX: {"xlsx", "xls"},
      FileType.IMAGES: {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp", "svg", "ico"},
      FileType.VIDEOS: {"mp4", "avi", "mkv", "mov", "webm"},
      FileType.AUDIO: {"mp3", "wav", "flac", "ogg", "aac", "m4a"},
      FileType.ZIP: {"zip"},
      FileType.TAR: {"tar", "gz", "tgz", "bz2"},
      FileType.PARQUET: {"parquet"},
    }
    allowed: set[str] = set()
    for ft in filters.file_types:
      if ft != FileType.ANY:
        allowed.update(type_map.get(ft, set()))
        if ft.value.lower() in text:
          return True

    for custom in filters.custom_types:
      token = custom.lower().strip()
      if token and (token in text or token == ext):
        return True

    if not allowed and filters.custom_types:
      return False
    if not allowed:
      return True
    return ext in allowed

  def _matches_license(self, license_info: str, filters: SearchFilters) -> bool:
    from dataset_collector.core.enums import LicenseFilter

    if filters.license_filter == LicenseFilter.ANY:
      return True
    lic = license_info.lower()
    if filters.license_filter == LicenseFilter.OPEN_SOURCE:
      return any(
        k in lic
        for k in ("mit", "apache", "bsd", "gpl", "open", "cc0", "cc-by", "public domain")
      )
    if filters.license_filter == LicenseFilter.COMMERCIAL:
      return any(k in lic for k in ("commercial", "mit", "apache", "bsd", "cc-by"))
    if filters.license_filter == LicenseFilter.RESEARCH_ONLY:
      return any(k in lic for k in ("research", "academic", "non-commercial", "nc"))
    return True

  def _matches_size(self, size_bytes: int | None, filters: SearchFilters) -> bool:
    # Total size budget is applied after search via auto-suggest, not per-dataset here.
    return True
