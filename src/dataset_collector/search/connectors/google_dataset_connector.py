"""Google Dataset Search connector — aggregates multiple open data catalogs."""

from __future__ import annotations

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
  "Accept": "application/json",
}


class GoogleDatasetConnector(BaseConnector):
  """Searches catalogs indexed by Google Dataset Search (Datacite, OpenAIRE, Dataverse)."""

  source = DataSource.GOOGLE_DATASET

  async def search(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int = 100,
    progress_callback: Callable[[str, float], None] | None = None,
  ) -> list[DatasetResult]:
    self._report_progress(progress_callback, "Searching dataset catalogs (Google index)...", 0.0)
    results: list[DatasetResult] = []
    per_source = max(max_results // 3, 10)

    try:
      async with httpx.AsyncClient(timeout=30, headers=BROWSER_HEADERS) as client:
        datacite = await self._search_datacite(client, query, per_source, filters, progress_callback)
        results.extend(datacite)

        openaire = await self._search_openaire(client, query, per_source, filters, progress_callback)
        results.extend(openaire)

        dataverse = await self._search_dataverse(client, query, per_source, filters, progress_callback)
        results.extend(dataverse)
    except Exception:
      pass

    # Deduplicate by name
    seen: set[str] = set()
    unique: list[DatasetResult] = []
    for r in results:
      key = r.name.lower()[:80]
      if key not in seen:
        seen.add(key)
        unique.append(r)

    self._report_progress(
      progress_callback, f"Dataset catalogs: {len(unique)} datasets found", 100.0
    )
    return unique[:max_results]

  async def _search_datacite(
    self,
    client: httpx.AsyncClient,
    query: str,
    limit: int,
    filters: SearchFilters,
    progress_callback: Callable[[str, float], None] | None,
  ) -> list[DatasetResult]:
    results: list[DatasetResult] = []
    try:
      resp = await client.get(
        "https://api.datacite.org/dois",
        params={"query": query, "resource-type-id": "dataset", "page[size]": min(limit, 25)},
        headers={"Accept": "application/vnd.api+json"},
      )
      if resp.status_code != 200:
        return results
      for item in resp.json().get("data", []):
        r = self._parse_datacite(item, filters)
        if r:
          results.append(r)
    except Exception:
      pass
    return results

  async def _search_openaire(
    self,
    client: httpx.AsyncClient,
    query: str,
    limit: int,
    filters: SearchFilters,
    progress_callback: Callable[[str, float], None] | None,
  ) -> list[DatasetResult]:
    results: list[DatasetResult] = []
    try:
      resp = await client.get(
        "https://api.openaire.eu/search/datasets",
        params={"keywords": query, "size": min(limit, 25), "format": "json"},
      )
      if resp.status_code != 200:
        return results
      data = resp.json()
      items = (
        data.get("response", {})
        .get("results", {})
        .get("result", [])
      )
      if isinstance(items, dict):
        items = [items]
      for item in items:
        title = item.get("title", {})
        if isinstance(title, dict):
          title = title.get("$", title.get("title", "Untitled"))
        title = str(title)
        doi = item.get("pid", [{}])
        if isinstance(doi, list) and doi:
          doi = doi[0].get("$", "")
        url = f"https://doi.org/{doi}" if doi else item.get("url", "")
        license_info = "See source"
        if not self._matches_license(license_info, filters):
          continue
        results.append(
          DatasetResult(
            id=f"gds_{hashlib.md5(title.encode()).hexdigest()[:12]}",
            name=title,
            source=DataSource.GOOGLE_DATASET,
            url=str(url),
            license_info=license_info,
            description=str(item.get("description", ""))[:500],
            metadata={"catalog": "OpenAIRE", "doi": doi},
          )
        )
    except Exception:
      pass
    return results

  async def _search_dataverse(
    self,
    client: httpx.AsyncClient,
    query: str,
    limit: int,
    filters: SearchFilters,
    progress_callback: Callable[[str, float], None] | None,
  ) -> list[DatasetResult]:
    results: list[DatasetResult] = []
    try:
      resp = await client.post(
        "https://dataverse.harvard.edu/api/search",
        json={"q": query, "type": "dataset", "per_page": min(limit, 20)},
        headers={"Content-Type": "application/json"},
      )
      if resp.status_code != 200:
        return results
      items = resp.json().get("data", {}).get("items", [])
      for item in items:
        title = item.get("name", "Untitled")
        url = item.get("url", item.get("global_id", ""))
        if url and not str(url).startswith("http"):
          url = f"https://dataverse.harvard.edu/dataset.xhtml?persistentId={url}"
        license_info = "See source"
        if not self._matches_license(license_info, filters):
          continue
        results.append(
          DatasetResult(
            id=f"gds_{hashlib.md5(str(url).encode()).hexdigest()[:12]}",
            name=title,
            source=DataSource.GOOGLE_DATASET,
            url=str(url),
            license_info=license_info,
            description=str(item.get("description", ""))[:500],
            metadata={"catalog": "Harvard Dataverse"},
          )
        )
    except Exception:
      pass
    return results

  def _parse_datacite(self, item: dict, filters: SearchFilters) -> DatasetResult | None:
    attrs = item.get("attributes", {})
    title = attrs.get("titles", [{}])[0].get("title", "Untitled")
    doi = attrs.get("doi", "")
    url = attrs.get("url", f"https://doi.org/{doi}")
    license_info = "See source"
    rights = attrs.get("rightsList", [])
    if rights:
      license_info = rights[0].get("rights", license_info)
    if not self._matches_license(license_info, filters):
      return None
    updated = None
    if attrs.get("updated"):
      try:
        updated = datetime.fromisoformat(attrs["updated"].replace("Z", "+00:00"))
      except (ValueError, TypeError):
        pass
    return DatasetResult(
      id=f"gds_{hashlib.md5(doi.encode()).hexdigest()[:12]}",
      name=title,
      source=DataSource.GOOGLE_DATASET,
      url=url,
      license_info=license_info,
      last_updated=updated,
      description=attrs.get("descriptions", [{}])[0].get("description", "")[:500]
      if attrs.get("descriptions")
      else "",
      metadata={"catalog": "Datacite", "doi": doi, "publisher": attrs.get("publisher", "")},
    )
