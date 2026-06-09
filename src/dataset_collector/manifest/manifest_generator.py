"""Manifest generation for selected datasets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from dataset_collector.core.enums import ManifestFormat
from dataset_collector.core.models import DatasetResult, ManifestEntry
from dataset_collector.logging.logger import AppLogger


class ManifestGenerator:
  """Generates and saves download manifests."""

  def __init__(self, manifest_dir: Path, logger: AppLogger) -> None:
    self._manifest_dir = Path(manifest_dir)
    self._manifest_dir.mkdir(parents=True, exist_ok=True)
    self._logger = logger

  def generate_entries(self, datasets: list[DatasetResult]) -> list[ManifestEntry]:
    timestamp = datetime.now(timezone.utc).isoformat()
    return [
      ManifestEntry(
        dataset_name=ds.name,
        source=ds.source.value,
        url=ds.url,
        size=ds.size_display,
        files=ds.files or [f"Primary resource at {ds.url}"],
        license=ds.license_info,
        timestamp=timestamp,
      )
      for ds in datasets
    ]

  def save(
    self,
    datasets: list[DatasetResult],
    fmt: ManifestFormat = ManifestFormat.JSON,
  ) -> Path:
    entries = self.generate_entries(datasets)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if fmt == ManifestFormat.JSON:
      path = self._manifest_dir / f"manifest_{timestamp}.json"
      data = [
        {
          "dataset_name": e.dataset_name,
          "source": e.source,
          "url": e.url,
          "size": e.size,
          "files": e.files,
          "license": e.license,
          "timestamp": e.timestamp,
        }
        for e in entries
      ]
      with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    else:
      path = self._manifest_dir / f"manifest_{timestamp}.txt"
      lines: list[str] = []
      for e in entries:
        lines.append(f"Dataset Name: {e.dataset_name}")
        lines.append(f"Source: {e.source}")
        lines.append(f"URL: {e.url}")
        lines.append(f"Size: {e.size}")
        lines.append("Files:")
        for f_name in e.files:
          lines.append(f"  * {f_name}")
        lines.append(f"License: {e.license}")
        lines.append(f"Timestamp: {e.timestamp}")
        lines.append("")
      with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    self._logger.log_manifest(str(path), len(entries))
    return path
