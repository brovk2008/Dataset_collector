"""GitHub dataset source connector."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Callable

import httpx

from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult, SearchFilters
from dataset_collector.search.connectors.base import BaseConnector


class GitHubConnector(BaseConnector):
  source = DataSource.GITHUB

  def __init__(self, token: str = "") -> None:
    self._token = token

  async def search(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int = 100,
    progress_callback: Callable[[str, float], None] | None = None,
  ) -> list[DatasetResult]:
    self._report_progress(progress_callback, "Searching GitHub...", 0.0)
    results: list[DatasetResult] = []

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Dataset_Collector/1.0"}
    if self._token:
      headers["Authorization"] = f"Bearer {self._token}"

    search_query = f"{query} dataset in:name,description,readme"
    try:
      async with httpx.AsyncClient(timeout=30) as client:
        page = 1
        per_page = min(30, max_results)
        while len(results) < max_results:
          resp = await client.get(
            "https://api.github.com/search/repositories",
            params={"q": search_query, "sort": "stars", "per_page": per_page, "page": page},
            headers=headers,
          )
          if resp.status_code == 403:
            break
          resp.raise_for_status()
          data = resp.json()
          items = data.get("items", [])
          if not items:
            break

          for i, repo in enumerate(items):
            if len(results) >= max_results:
              break
            self._report_progress(
              progress_callback,
              f"Processing GitHub repo {len(results) + 1}",
              len(results) / max_results * 100,
            )
            size_bytes = (repo.get("size") or 0) * 1024
            license_info = (repo.get("license") or {}).get("spdx_id", "Unknown") or "Unknown"
            if not self._matches_license(license_info, filters):
              continue
            if not self._matches_size(size_bytes, filters):
              continue

            updated = None
            if repo.get("updated_at"):
              try:
                updated = datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00"))
              except (ValueError, TypeError):
                pass

            full_name = repo.get("full_name", "")
            results.append(
              DatasetResult(
                id=f"github_{hashlib.md5(full_name.encode()).hexdigest()[:12]}",
                name=repo.get("name", full_name),
                source=DataSource.GITHUB,
                url=repo.get("html_url", ""),
                estimated_size_bytes=size_bytes,
                license_info=license_info,
                last_updated=updated,
                description=repo.get("description", "") or "",
                metadata={
                  "full_name": full_name,
                  "stars": repo.get("stargazers_count", 0),
                  "clone_url": repo.get("clone_url", ""),
                },
              )
            )
          page += 1
          if page > 3:
            break
    except Exception:
      pass

    self._report_progress(progress_callback, f"GitHub: {len(results)} repos found", 100.0)
    return results
