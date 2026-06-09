"""Internet Archive source connector."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Callable

import httpx

from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult, SearchFilters
from dataset_collector.search.connectors.base import BaseConnector


class InternetArchiveConnector(BaseConnector):
  source = DataSource.INTERNET_ARCHIVE

  async def search(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int = 100,
    progress_callback: Callable[[str, float], None] | None = None,
  ) -> list[DatasetResult]:
    self._report_progress(progress_callback, "Searching Internet Archive...", 0.0)
    results: list[DatasetResult] = []

    try:
      async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
          "https://archive.org/advancedsearch.php",
          params={
            "q": f"({query}) AND mediatype:data",
            "fl[]": ["identifier", "title", "description", "downloads", "item_size", "licenseurl"],
            "rows": min(max_results, 50),
            "page": 1,
            "output": "json",
          },
        )
        resp.raise_for_status()
        data = resp.json()
        docs = data.get("response", {}).get("docs", [])

        for i, doc in enumerate(docs[:max_results]):
          self._report_progress(
            progress_callback,
            f"Processing IA item {i + 1}/{len(docs)}",
            (i + 1) / max(len(docs), 1) * 100,
          )
          identifier = doc.get("identifier", "")
          title = doc.get("title", identifier)
          if isinstance(title, list):
            title = title[0] if title else identifier

          size_bytes = None
          item_size = doc.get("item_size")
          if item_size:
            try:
              size_bytes = int(item_size)
            except (ValueError, TypeError):
              pass

          license_info = doc.get("licenseurl", "Public Domain") or "Public Domain"
          if not self._matches_license(str(license_info), filters):
            continue
          if not self._matches_size(size_bytes, filters):
            continue

          results.append(
            DatasetResult(
              id=f"ia_{hashlib.md5(identifier.encode()).hexdigest()[:12]}",
              name=str(title),
              source=DataSource.INTERNET_ARCHIVE,
              url=f"https://archive.org/details/{identifier}",
              estimated_size_bytes=size_bytes,
              license_info=str(license_info),
              description=str(doc.get("description", ""))[:500],
              metadata={
                "identifier": identifier,
                "downloads": doc.get("downloads", 0),
              },
            )
          )
    except Exception:
      pass

    self._report_progress(
      progress_callback, f"Internet Archive: {len(results)} items found", 100.0
    )
    return results
