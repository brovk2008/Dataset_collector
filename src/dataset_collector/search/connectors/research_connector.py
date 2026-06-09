"""Research repository source connector (Zenodo, etc.)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Callable

import httpx

from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult, SearchFilters
from dataset_collector.search.connectors.base import BaseConnector


class ResearchConnector(BaseConnector):
  source = DataSource.RESEARCH

  async def search(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int = 100,
    progress_callback: Callable[[str, float], None] | None = None,
  ) -> list[DatasetResult]:
    self._report_progress(progress_callback, "Searching research repositories...", 0.0)
    results: list[DatasetResult] = []

    try:
      async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
          "https://zenodo.org/api/records",
          params={
            "q": f"{query} type:dataset",
            "size": min(max_results, 25),
            "sort": "mostrecent",
          },
        )
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])

        for i, record in enumerate(hits[:max_results]):
          self._report_progress(
            progress_callback,
            f"Processing research record {i + 1}/{len(hits)}",
            (i + 1) / max(len(hits), 1) * 100,
          )
          metadata = record.get("metadata", {})
          title = metadata.get("title", "Untitled")
          record_id = str(record.get("id", ""))
          license_info = metadata.get("license", {}).get("id", "Research Use") if isinstance(
            metadata.get("license"), dict
          ) else str(metadata.get("license", "Research Use"))

          if not self._matches_license(license_info, filters):
            continue

          files_meta = record.get("files", [])
          files = [f.get("key", "") for f in files_meta]
          total_size = sum(f.get("size", 0) for f in files_meta)
          if not self._matches_size(total_size or None, filters):
            continue

          updated = None
          if record.get("updated"):
            try:
              updated = datetime.fromisoformat(record["updated"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
              pass

          results.append(
            DatasetResult(
              id=f"research_{hashlib.md5(record_id.encode()).hexdigest()[:12]}",
              name=title,
              source=DataSource.RESEARCH,
              url=record.get("links", {}).get("self_html", f"https://zenodo.org/record/{record_id}"),
              estimated_size_bytes=total_size or None,
              file_count=len(files_meta),
              license_info=license_info,
              last_updated=updated,
              description=metadata.get("description", "")[:500] if metadata.get("description") else "",
              files=files,
              metadata={"zenodo_id": record_id, "doi": metadata.get("doi", "")},
            )
          )
    except Exception:
      pass

    self._report_progress(
      progress_callback, f"Research: {len(results)} datasets found", 100.0
    )
    return results
