"""Kaggle dataset source connector."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime
from typing import Callable

import httpx

from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult, SearchFilters
from dataset_collector.search.connectors.base import BaseConnector

BROWSER_HEADERS = {
  "User-Agent": (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
  ),
  "Accept": "application/json, text/plain, */*",
  "Accept-Language": "en-US,en;q=0.9",
  "Referer": "https://www.kaggle.com/datasets",
  "Origin": "https://www.kaggle.com",
}


class KaggleConnector(BaseConnector):
  source = DataSource.KAGGLE

  def __init__(self, username: str = "", api_key: str = "") -> None:
    self._username = username
    self._api_key = api_key

  async def search(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int = 100,
    progress_callback: Callable[[str, float], None] | None = None,
  ) -> list[DatasetResult]:
    self._report_progress(progress_callback, "Searching Kaggle...", 0.0)
    results: list[DatasetResult] = []

    if self._username and self._api_key:
      results = await self._search_kaggle_sdk(query, filters, max_results, progress_callback)
    if not results:
      results = await self._search_rest(query, filters, max_results, progress_callback)

    self._report_progress(progress_callback, f"Kaggle: {len(results)} datasets found", 100.0)
    return results

  async def _search_kaggle_sdk(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int,
    progress_callback: Callable[[str, float], None] | None,
  ) -> list[DatasetResult]:
    def _fetch() -> list[dict]:
      try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        items = api.dataset_list(search=query, sort_by="hottest", file_type="all", page=1)
        return [
          {
            "ref": getattr(d, "ref", ""),
            "titleNullable": getattr(d, "title", ""),
            "subtitleNullable": getattr(d, "subtitle", ""),
            "totalBytesNullable": getattr(d, "totalBytes", None),
            "licenseNameNullable": getattr(d, "licenseName", "Unknown"),
            "ownerNameNullable": getattr(d, "ownerName", ""),
          }
          for d in items[:max_results]
        ]
      except Exception:
        return []

    datasets = await asyncio.to_thread(_fetch)
    results: list[DatasetResult] = []
    for i, ds in enumerate(datasets):
      r = self._parse_dataset(ds, i, len(datasets), filters, progress_callback)
      if r:
        results.append(r)
    return results

  async def _search_rest(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int,
    progress_callback: Callable[[str, float], None] | None,
  ) -> list[DatasetResult]:
    def _fetch() -> list[dict]:
      import time

      headers = {
        "User-Agent": BROWSER_HEADERS["User-Agent"],
        "Accept": "application/json",
        "Referer": "https://www.kaggle.com/datasets",
      }
      terms = [t.lower() for t in query.split() if len(t) > 1]

      def _is_json_response(resp: httpx.Response) -> bool:
        return resp.status_code == 200 and "json" in resp.headers.get("content-type", "")

      def _filter_local(datasets: list[dict]) -> list[dict]:
        if not terms:
          return datasets
        matched = []
        for ds in datasets:
          text = " ".join(
            str(ds.get(k, ""))
            for k in ("titleNullable", "subtitleNullable", "ref", "title", "subtitle")
          ).lower()
          if any(t in text for t in terms):
            matched.append(ds)
        return matched

      try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
          for attempt in range(3):
            resp = client.get(
              "https://www.kaggle.com/api/v1/datasets/list",
              params={"search": query, "pageSize": min(max_results, 50)},
              headers=headers,
            )
            if _is_json_response(resp):
              data = resp.json()
              return data if isinstance(data, list) else []
            time.sleep(1 + attempt)

          # Fallback: fetch trending datasets and filter locally
          resp = client.get(
            "https://www.kaggle.com/api/v1/datasets/list",
            params={"pageSize": 100},
            headers=headers,
          )
          if _is_json_response(resp):
            data = resp.json()
            if isinstance(data, list):
              return _filter_local(data)[:max_results]
      except Exception:
        pass
      return []

    datasets = await asyncio.to_thread(_fetch)
    results: list[DatasetResult] = []
    for i, ds in enumerate(datasets[:max_results]):
      r = self._parse_dataset(ds, i, len(datasets), filters, progress_callback)
      if r:
        results.append(r)
    return results

  def _parse_dataset(
    self,
    ds: dict,
    index: int,
    total: int,
    filters: SearchFilters,
    progress_callback: Callable[[str, float], None] | None,
  ) -> DatasetResult | None:
    self._report_progress(
      progress_callback,
      f"Processing Kaggle result {index + 1}",
      (index + 1) / max(total, 1) * 100,
    )
    ref = ds.get("ref", "")
    if not ref:
      return None

    title = ds.get("titleNullable") or ds.get("title") or ref
    size_bytes = ds.get("totalBytesNullable") or ds.get("totalBytes")
    license_info = ds.get("licenseNameNullable") or ds.get("licenseName") or "See Kaggle page"
    subtitle = ds.get("subtitleNullable") or ds.get("subtitle") or ""

    if not self._matches_license(license_info, filters):
      return None

    last_updated = None
    if ds.get("lastUpdated"):
      try:
        last_updated = datetime.fromisoformat(ds["lastUpdated"].replace("Z", "+00:00"))
      except (ValueError, TypeError):
        pass

    download_url = f"https://www.kaggle.com/api/v1/datasets/download/{ref}"

    return DatasetResult(
      id=f"kaggle_{hashlib.md5(ref.encode()).hexdigest()[:12]}",
      name=title,
      source=DataSource.KAGGLE,
      url=f"https://www.kaggle.com/datasets/{ref}",
      estimated_size_bytes=size_bytes,
      license_info=license_info,
      last_updated=last_updated,
      description=subtitle,
      download_urls=[download_url],
      metadata={
        "ref": ref,
        "owner": ds.get("ownerNameNullable") or ds.get("ownerName", ""),
        "download_url": download_url,
      },
    )
