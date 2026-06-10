"""Government data portal source connector."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
from datetime import datetime
from typing import Callable
from urllib.parse import quote

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


class GovernmentConnector(BaseConnector):
  source = DataSource.GOVERNMENT

  def __init__(self, india_api_key: str = "") -> None:
    self._india_api_key = india_api_key or os.environ.get("DATA_GOV_IN_API_KEY", "")

  PORTALS = [
    {
      "name": "Socrata Open Data (US)",
      "type": "socrata",
      "url": "https://api.us.socrata.com/api/catalog/v1",
      "country": "United States",
    },
    {
      "name": "data.gov.uk",
      "type": "ckan",
      "url": "https://ckan.publishing.service.gov.uk/api/3/action/package_search",
      "country": "United Kingdom",
    },
    {
      "name": "open.canada.ca",
      "type": "ckan",
      "url": "https://open.canada.ca/data/en/api/3/action/package_search",
      "country": "Canada",
    },
    {
      "name": "data.europa.eu",
      "type": "europa",
      "url": "https://data.europa.eu/api/hub/search/search",
      "country": "Worldwide",
    },
    {
      "name": "data.gov.in (India OGD)",
      "type": "india",
      "url": "https://data.gov.in",
      "country": "India",
    },
  ]

  async def search(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int = 100,
    progress_callback: Callable[[str, float], None] | None = None,
  ) -> list[DatasetResult]:
    self._report_progress(progress_callback, "Searching government portals...", 0.0)
    results: list[DatasetResult] = []
    portals = self._filter_portals(filters)

    try:
      async with httpx.AsyncClient(timeout=30, headers=BROWSER_HEADERS) as client:
        per_portal = max(max_results // max(len(portals), 1), 10)
        for pi, portal in enumerate(portals):
          if len(results) >= max_results:
            break
          self._report_progress(
            progress_callback,
            f"Searching {portal['name']}...",
            (pi / len(portals) * 100) if len(portals) > 0 else 0.0,
          )
          try:
            if portal["type"] == "socrata":
              batch = await self._search_socrata(client, portal, query, per_portal)
            elif portal["type"] == "europa":
              batch = await self._search_europa(client, portal, query, per_portal)
            elif portal["type"] == "india":
              batch = await self._search_india(client, portal, query, per_portal, filters)
            else:
              batch = await self._search_ckan(client, portal, query, per_portal, filters)
            results.extend(batch)
          except Exception:
            continue
    except Exception:
      pass

    self._report_progress(
      progress_callback, f"Government: {len(results)} datasets found", 100.0
    )
    return results[:max_results]

  async def _search_socrata(
    self, client: httpx.AsyncClient, portal: dict, query: str, limit: int
  ) -> list[DatasetResult]:
    results: list[DatasetResult] = []
    resp = await client.get(
      portal["url"],
      params={"q": query, "limit": limit, "only": "datasets"},
    )
    resp.raise_for_status()
    for item in resp.json().get("results", []):
      resource = item.get("resource", {})
      name = resource.get("name", "Untitled")
      resource_id = resource.get("id", "")
      download_url = resource.get("download_url") or resource.get("link") or ""
      permalink = resource.get("permalink") or download_url
      if not permalink:
        continue

      results.append(
        DatasetResult(
          id=f"gov_{hashlib.md5(resource_id.encode()).hexdigest()[:12]}",
          name=name,
          source=DataSource.GOVERNMENT,
          url=permalink,
          license_info="Public Domain",
          description=(resource.get("description") or "")[:500],
          files=[resource.get("name", "data")],
          download_urls=[download_url] if download_url else [],
          metadata={"portal": portal["name"], "country": portal["country"], "format": resource.get("format")},
        )
      )
    return results

  async def _search_ckan(
    self,
    client: httpx.AsyncClient,
    portal: dict,
    query: str,
    limit: int,
    filters: SearchFilters,
  ) -> list[DatasetResult]:
    results: list[DatasetResult] = []
    resp = await client.get(portal["url"], params={"q": query, "rows": limit})
    resp.raise_for_status()
    packages = resp.json().get("result", {}).get("results", [])

    for pkg in packages:
      title = pkg.get("title", "Untitled")
      pkg_id = pkg.get("id", title)
      license_info = pkg.get("license_title", "Public Domain")
      if not self._matches_license(license_info, filters):
        continue

      resources = pkg.get("resources", [])
      download_urls = [r.get("url", "") for r in resources if r.get("url")]
      files = [r.get("name", r.get("url", "")) for r in resources]

      if not self._matches_any_file_type(files, [r.get("format", "") for r in resources], filters):
        continue

      last_updated = None
      if pkg.get("metadata_modified"):
        try:
          last_updated = datetime.fromisoformat(pkg["metadata_modified"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
          pass

      total_size = sum(r.get("size", 0) or 0 for r in resources)
      notes = pkg.get("notes", "") or ""
      clean_notes = re.sub(r"<[^>]+>", "", notes)[:500]

      results.append(
        DatasetResult(
          id=f"gov_{hashlib.md5(pkg_id.encode()).hexdigest()[:12]}",
          name=title,
          source=DataSource.GOVERNMENT,
          url=pkg.get("url") or (download_urls[0] if download_urls else ""),
          estimated_size_bytes=total_size or None,
          file_count=len(resources),
          license_info=license_info,
          last_updated=last_updated,
          description=clean_notes,
          files=files,
          download_urls=download_urls,
          metadata={"portal": portal["name"], "country": portal["country"]},
        )
      )
    return results

  async def _search_europa(
    self, client: httpx.AsyncClient, portal: dict, query: str, limit: int
  ) -> list[DatasetResult]:
    results: list[DatasetResult] = []
    resp = await client.get(portal["url"], params={"q": query, "limit": limit, "page": 1})
    resp.raise_for_status()
    data = resp.json()
    items = data.get("result", {}).get("results", data.get("results", []))

    for item in items:
      title = item.get("title", {})
      if isinstance(title, dict):
        title = title.get("en") or next(iter(title.values()), "Untitled")
      title = str(title)
      item_id = item.get("id", title)
      download_urls = []
      for dist in item.get("distributions", item.get("distribution", [])):
        url = dist.get("access_url") or dist.get("download_url") or dist.get("url")
        if isinstance(url, list):
          download_urls.extend(url)
        elif url:
          download_urls.append(url)

      landing = item.get("landing_page") or item.get("identifier") or ""
      if isinstance(landing, list):
        landing = landing[0] if landing else ""

      results.append(
        DatasetResult(
          id=f"gov_{hashlib.md5(str(item_id).encode()).hexdigest()[:12]}",
          name=title,
          source=DataSource.GOVERNMENT,
          url=str(landing) if landing else (download_urls[0] if download_urls else ""),
          license_info=item.get("license", "Open Data"),
          description=str(item.get("description", ""))[:500],
          download_urls=download_urls,
          metadata={"portal": portal["name"], "country": portal["country"]},
        )
      )
    return results

  async def _search_india(
    self,
    client: httpx.AsyncClient,
    portal: dict,
    query: str,
    limit: int,
    filters: SearchFilters,
  ) -> list[DatasetResult]:
    results: list[DatasetResult] = []

    # OGD India catalog API (API key recommended — register at data.gov.in)
    if self._india_api_key:
      try:
        resp = await client.get(
          "https://api.data.gov.in/catalogrequest",
          params={
            "api-key": self._india_api_key,
            "format": "json",
            "limit": limit,
            "offset": 0,
            "filters[title]": query,
          },
        )
        if resp.status_code == 200 and "json" in resp.headers.get("content-type", ""):
          records = resp.json().get("records", resp.json().get("data", []))
          if isinstance(records, dict):
            records = records.get("resources", [])
          for rec in records[:limit]:
            title = rec.get("title", rec.get("catalog_title", "Untitled"))
            resource_id = rec.get("id", rec.get("resource_id", title))
            download_url = rec.get("download_url", rec.get("field_download_url", ""))
            page_url = rec.get("source", f"https://www.data.gov.in/resource/{resource_id}")
            if not self._matches_any_file_type([title], [rec.get("format", "")], filters):
              continue
            results.append(
              DatasetResult(
                id=f"gov_{hashlib.md5(str(resource_id).encode()).hexdigest()[:12]}",
                name=str(title),
                source=DataSource.GOVERNMENT,
                url=str(page_url),
                license_info="Government Open Data India",
                description=str(rec.get("description", ""))[:500],
                download_urls=[download_url] if download_url else [],
                metadata={"portal": portal["name"], "country": "India", "resource_id": resource_id},
              )
            )
      except Exception:
        pass

    if results:
      return results

    # CKAN package_search on data.gov.in
    try:
      resp = await client.post(
        "https://data.gov.in/api/3/action/package_search",
        json={"q": query, "rows": limit},
        headers={**BROWSER_HEADERS, "Content-Type": "application/json"},
      )
      if resp.status_code == 200 and "json" in resp.headers.get("content-type", ""):
        packages = resp.json().get("result", {}).get("results", [])
        results.extend(await self._search_ckan_packages(packages, portal, filters))
    except Exception:
      pass

    if results:
      return results

    # HTML catalog scrape fallback
    scraped = await asyncio.to_thread(self._scrape_india_catalog, query, limit)
    for item in scraped:
      if not self._matches_any_file_type([item["name"]], [item.get("format", "")], filters):
        continue
      results.append(
        DatasetResult(
          id=f"gov_{hashlib.md5(item['url'].encode()).hexdigest()[:12]}",
          name=item["name"],
          source=DataSource.GOVERNMENT,
          url=item["url"],
          license_info="Government Open Data India",
          description=item.get("description", "")[:500],
          metadata={"portal": portal["name"], "country": "India"},
        )
      )
    return results[:limit]

  async def _search_ckan_packages(
    self, packages: list[dict], portal: dict, filters: SearchFilters
  ) -> list[DatasetResult]:
    results: list[DatasetResult] = []
    for pkg in packages:
      title = pkg.get("title", "Untitled")
      pkg_id = pkg.get("id", title)
      resources = pkg.get("resources", [])
      download_urls = [r.get("url", "") for r in resources if r.get("url")]
      files = [r.get("name", "") for r in resources]
      if not self._matches_any_file_type(files, [r.get("format", "") for r in resources], filters):
        continue
      results.append(
        DatasetResult(
          id=f"gov_{hashlib.md5(pkg_id.encode()).hexdigest()[:12]}",
          name=title,
          source=DataSource.GOVERNMENT,
          url=pkg.get("url") or (download_urls[0] if download_urls else ""),
          file_count=len(resources),
          license_info=pkg.get("license_title", "Government Open Data India"),
          description=re.sub(r"<[^>]+>", "", pkg.get("notes", "") or "")[:500],
          files=files,
          download_urls=download_urls,
          metadata={"portal": portal["name"], "country": "India"},
        )
      )
    return results

  @staticmethod
  def _scrape_india_catalog(query: str, limit: int) -> list[dict]:
    items: list[dict] = []
    try:
      with httpx.Client(timeout=30, follow_redirects=True, headers=BROWSER_HEADERS) as client:
        resp = client.get(
          f"https://www.data.gov.in/catalog/dataset?q={quote(query)}",
        )
        if resp.status_code != 200:
          return items
        titles = re.findall(r'"title":"([^"]{5,200})"', resp.text)
        links = re.findall(r'"(/resource/[a-f0-9-]{36})"', resp.text)
        seen: set[str] = set()
        for title, link in zip(titles, links):
          if title in seen:
            continue
          seen.add(title)
          items.append({
            "name": title,
            "url": f"https://www.data.gov.in{link}",
            "description": f"India OGD: {title}",
          })
          if len(items) >= limit:
            break
        if not items:
          for title in titles[:limit]:
            items.append({
              "name": title,
              "url": f"https://www.data.gov.in/catalog/dataset?q={quote(query)}",
              "description": f"India OGD search result: {title}",
            })
    except Exception:
      pass
    return items

  def _filter_portals(self, filters: SearchFilters) -> list[dict]:
    if filters.country == "Worldwide":
      return self.PORTALS
    matched = [p for p in self.PORTALS if filters.country.lower() in p["country"].lower()]
    return matched if matched else self.PORTALS

  def _matches_any_file_type(
    self, files: list[str], formats: list[str], filters: SearchFilters
  ) -> bool:
    from dataset_collector.core.enums import FileType

    if FileType.ANY in filters.file_types and not filters.custom_types:
      return True
    for f, fmt in zip(files, formats):
      if self._matches_file_type(f, filters) or self._matches_file_type(fmt, filters):
        return True
    if filters.custom_types and not files:
      return True
    return not files and not filters.custom_types
