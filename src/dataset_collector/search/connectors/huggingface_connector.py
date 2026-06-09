"""Hugging Face Datasets source connector."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Callable

import httpx

from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult, SearchFilters
from dataset_collector.search.connectors.base import BaseConnector


class HuggingFaceConnector(BaseConnector):
  source = DataSource.HUGGINGFACE

  def __init__(self, token: str = "") -> None:
    self._token = token

  async def search(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int = 100,
    progress_callback: Callable[[str, float], None] | None = None,
  ) -> list[DatasetResult]:
    self._report_progress(progress_callback, "Searching Hugging Face...", 0.0)
    results: list[DatasetResult] = []

    headers = {"User-Agent": "Dataset_Collector/1.0"}
    if self._token:
      headers["Authorization"] = f"Bearer {self._token}"

    try:
      async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
          "https://huggingface.co/api/datasets",
          params={"search": query, "limit": min(max_results, 100), "sort": "downloads"},
          headers=headers,
        )
        resp.raise_for_status()
        datasets = resp.json()

        for i, ds in enumerate(datasets[:max_results]):
          self._report_progress(
            progress_callback,
            f"Processing HF dataset {i + 1}/{len(datasets)}",
            (i + 1) / max(len(datasets), 1) * 100,
          )
          dataset_id = ds.get("id", "")
          license_info = ds.get("cardData", {}).get("license", "Unknown") if isinstance(
            ds.get("cardData"), dict
          ) else "Unknown"
          if license_info == "Unknown":
            license_info = str(ds.get("license", "Unknown"))

          if not self._matches_license(license_info, filters):
            continue

          size_bytes = ds.get("size_bytes") or ds.get("downloads", 0)
          if not self._matches_size(size_bytes if isinstance(size_bytes, int) else None, filters):
            continue

          last_updated = None
          if ds.get("lastModified"):
            try:
              last_updated = datetime.fromisoformat(
                ds["lastModified"].replace("Z", "+00:00")
              )
            except (ValueError, TypeError):
              pass

          tags = ds.get("tags", [])
          description = ds.get("description", "") or ", ".join(tags[:5]) if tags else ""
          download_urls = [
            f"https://huggingface.co/datasets/{dataset_id}/resolve/main/{{path}}"
          ]
          results.append(
            DatasetResult(
              id=f"hf_{hashlib.md5(dataset_id.encode()).hexdigest()[:12]}",
              name=dataset_id,
              source=DataSource.HUGGINGFACE,
              url=f"https://huggingface.co/datasets/{dataset_id}",
              estimated_size_bytes=size_bytes if isinstance(size_bytes, int) else None,
              license_info=license_info,
              last_updated=last_updated,
              description=description[:500],
              download_urls=download_urls,
              metadata={
                "dataset_id": dataset_id,
                "downloads": ds.get("downloads", 0),
                "likes": ds.get("likes", 0),
                "hf_resolve_base": f"https://huggingface.co/datasets/{dataset_id}/resolve/main/",
              },
            )
          )
    except Exception:
      pass

    self._report_progress(progress_callback, f"HuggingFace: {len(results)} datasets found", 100.0)
    return results
