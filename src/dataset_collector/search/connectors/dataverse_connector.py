"""Harvard Dataverse connector for curated academic datasets."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Callable

import httpx

from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult
from dataset_collector.search.connectors.base import BaseConnector


class DataverseConnector(BaseConnector):
  """Search Harvard Dataverse (50K+ curated academic datasets)."""

  API_URL = "https://dataverse.harvard.edu/api/search"
  DELAY_BETWEEN_REQUESTS = 0.15  # ~7 requests/sec

  async def search(
    self,
    query: str,
    filters: object | None = None,
    max_results: int = 50,
    progress_callback: Callable[[str, float], None] | None = None,
  ) -> list[DatasetResult]:
    """Search Harvard Dataverse datasets.

    Args:
      query: Search terms (e.g., "climate data", "genomics")
      filters: Optional search filters (unused)
      max_results: Maximum datasets to return
      progress_callback: Optional progress reporting

    Returns:
      List of DatasetResult objects for matching datasets.
    """
    try:
      if progress_callback:
        progress_callback("Searching Harvard Dataverse...", 10.0)

      # Respect rate limiting
      await asyncio.sleep(self.DELAY_BETWEEN_REQUESTS)

      results = await self._fetch_datasets(query, max_results)

      if progress_callback:
        progress_callback(f"Found {len(results)} datasets on Harvard Dataverse", 100.0)

      return results
    except Exception:
      return []

  async def _fetch_datasets(self, query: str, limit: int) -> list[DatasetResult]:
    """Fetch datasets from Harvard Dataverse API."""
    try:
      params: dict[str, str | int] = {
        "q": query,
        "type": "dataset",
        "per_page": min(limit, 100),
        "start": 0,
        "sort": "date",
        "order": "desc",
      }

      async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(self.API_URL, params=params)
        response.raise_for_status()
        data = response.json()

      results = []
      for item in data.get("data", {}).get("items", []):
        try:
          result = self._parse_dataset(item)
          if result:
            results.append(result)
        except Exception:
          continue

      return results
    except Exception:
      return []

  def _parse_dataset(self, item: dict) -> DatasetResult | None:
    """Convert Dataverse dataset to DatasetResult."""
    try:
      entity_id = item.get("entity_id", "")
      name = item.get("name", "Unknown").strip()
      description = item.get("description", "").strip()

      # Parse publication date
      published_str = item.get("published_at", "")
      try:
        published_dt = datetime.fromisoformat(published_str.split("T")[0])
      except Exception:
        published_dt = datetime.now(timezone.utc)

      # Get DOI if available
      doi = item.get("global_id", "").replace("doi:", "")

      # Estimate dataset size from file count
      # Average file size estimation: 5 MB per file
      file_count = item.get("file_count", 1)
      estimated_size = max(file_count, 1) * 5 * 1024 * 1024

      # Build URL
      dataverse_url = item.get("url", f"https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:{doi}")

      # Get metadata
      metadata_str = item.get("metadata", {})
      if isinstance(metadata_str, str):
        metadata_str = {}

      # Extract subject/discipline
      subject = ""
      if isinstance(metadata_str, dict):
        subject = metadata_str.get("subject", [""])[0] if metadata_str.get("subject") else ""

      # Get license info
      license_info = item.get("license", "CC0")

      result = DatasetResult(
        id=f"dataverse_{entity_id}",
        name=name,
        description=description,
        source=DataSource.DATAVERSE,
        url=dataverse_url,
        estimated_size_bytes=estimated_size,
        license_info=license_info,
        last_updated=published_dt,
        rank_score=76,
        quality_score=8.0,
        health_score=85,
        available_sources=[DataSource.DATAVERSE.value],
        requires_auth=False,
        auth_message="",
        metadata={
          "doi": doi,
          "entity_id": entity_id,
          "file_count": file_count,
          "subject": subject,
          "citation": item.get("citation", ""),
          "source": "Harvard Dataverse",
        },
      )

      return result
    except Exception:
      return None

  def _format_size(self, size_bytes: int) -> str:
    """Format bytes to human readable size."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
      if size < 1024:
        return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
      size /= 1024
    return f"{size:.1f} TB"

  async def get_download_urls(self, dataset: DatasetResult) -> list[str]:
    """Return download URL for Dataverse dataset."""
    # Dataverse datasets contain multiple files - return the dataset page
    # which allows downloading all files
    if dataset.url:
      return [dataset.url]
    return []
