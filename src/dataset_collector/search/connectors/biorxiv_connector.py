"""bioRxiv and medRxiv connector for life sciences preprints."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Callable

from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult
from dataset_collector.search.connectors.base import BaseConnector


class BiorxivConnector(BaseConnector):
  """Search bioRxiv and medRxiv preprint servers (400K+ life sciences papers)."""

  BIORXIV_URL = "https://www.biorxiv.org/search"
  MEDRXIV_URL = "https://www.medrxiv.org/search"
  DELAY_BETWEEN_REQUESTS = 0.2  # 5 requests/sec

  async def search(
    self,
    query: str,
    filters: object | None = None,
    max_results: int = 50,
    progress_callback: Callable[[str, float], None] | None = None,
  ) -> list[DatasetResult]:
    """Search bioRxiv and medRxiv papers.

    Args:
      query: Search terms (e.g., "COVID-19", "vaccine", "gene therapy")
      filters: Optional search filters (unused)
      max_results: Maximum papers to return (split between bioRxiv and medRxiv)
      progress_callback: Optional progress reporting

    Returns:
      List of DatasetResult objects for matching papers.
    """
    try:
      if progress_callback:
        progress_callback("Searching bioRxiv and medRxiv...", 10.0)

      results = []

      # Split max_results between the two sources
      per_source = max_results // 2

      # Search both sources in parallel
      biorxiv_results = await self._search_server(
        self.BIORXIV_URL, query, per_source, "bioRxiv"
      )
      results.extend(biorxiv_results)

      medrxiv_results = await self._search_server(
        self.MEDRXIV_URL, query, per_source, "medRxiv"
      )
      results.extend(medrxiv_results)

      if progress_callback:
        progress_callback(f"Found {len(results)} papers on bioRxiv and medRxiv", 100.0)

      return results
    except Exception:
      return []

  async def _search_server(
    self, base_url: str, query: str, limit: int, server_name: str
  ) -> list[DatasetResult]:
    """Search a single bioRxiv or medRxiv server."""
    try:
      # Respect rate limiting
      await asyncio.sleep(self.DELAY_BETWEEN_REQUESTS)

      import httpx

      # Build search URL with JSON response format
      search_url = f"{base_url}?q={query}&format=json&page=0&limit={limit}&sort=date"

      async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(search_url)
        response.raise_for_status()
        data = response.json()

      results = []
      for article in data.get("articles", []):
        try:
          result = self._parse_article(article, server_name)
          if result:
            results.append(result)
        except Exception:
          continue

      return results
    except Exception:
      return []

  def _parse_article(self, article: dict, server_name: str) -> DatasetResult | None:
    """Convert bioRxiv/medRxiv article to DatasetResult."""
    try:
      title = article.get("title", "Unknown").strip()
      doi = article.get("doi", "")
      abstract = article.get("abstract", "").strip()

      # Parse publication date
      published_str = article.get("published", "")
      try:
        published_dt = datetime.fromisoformat(published_str.split("T")[0])
      except Exception:
        published_dt = datetime.now()

      # Get authors
      authors = article.get("authors", [])
      authors_str = ", ".join([a.get("name", "") for a in authors[:5]])
      if len(authors) > 5:
        authors_str += f", and {len(authors) - 5} others"

      # Build URL
      if server_name == "bioRxiv":
        paper_url = f"https://www.biorxiv.org/content/{doi}"
        pdf_url = f"https://www.biorxiv.org/content/{doi}.full.pdf"
      else:  # medRxiv
        paper_url = f"https://www.medrxiv.org/content/{doi}"
        pdf_url = f"https://www.medrxiv.org/content/{doi}.full.pdf"

      # Estimate size (most PDFs are 3-20 MB, average ~10 MB)
      estimated_size = 10 * 1024 * 1024

      result = DatasetResult(
        id=f"biorxiv_{doi.replace('/', '_')}",
        name=title,
        description=abstract,
        source=DataSource.BIORXIV,
        url=paper_url,
        estimated_size_bytes=estimated_size,
        license_info="CC-BY",
        last_updated=published_dt,
        rank_score=72,
        quality_score=7.0,
        health_score=78,
        available_sources=[DataSource.BIORXIV.value],
        requires_auth=False,
        auth_message="",
        metadata={
          "doi": doi,
          "pdf_url": pdf_url,
          "authors": authors_str,
          "server": server_name,
          "categories": article.get("category", ""),
        },
      )

      return result
    except Exception:
      return None

  async def get_download_urls(self, dataset: DatasetResult) -> list[str]:
    """Return PDF download URL for bioRxiv/medRxiv paper."""
    pdf_url = dataset.metadata.get("pdf_url")
    if pdf_url:
      return [pdf_url]
    return []
