"""arXiv connector for academic papers and preprints."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Callable

import feedparser

from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult
from dataset_collector.search.connectors.base import BaseConnector


class ArxivConnector(BaseConnector):
  """Search arXiv preprint repository (2.3M+ papers across physics, math, CS, bio, astro)."""

  BASE_URL = "http://export.arxiv.org/api/query"
  MAX_RESULTS_PER_REQUEST = 200
  DELAY_BETWEEN_REQUESTS = 0.4  # 3 requests/sec = 0.33s between requests

  async def search(
    self,
    query: str,
    filters: object | None = None,
    max_results: int = 50,
    progress_callback: Callable[[str, float], None] | None = None,
  ) -> list[DatasetResult]:
    """Search arXiv papers.

    Args:
      query: Search terms (e.g., "neural networks", "climate data")
      filters: Optional search filters (unused for arXiv)
      max_results: Maximum papers to return
      progress_callback: Optional progress reporting

    Returns:
      List of DatasetResult objects for matching papers.
    """
    try:
      if progress_callback:
        progress_callback("Searching arXiv...", 10.0)

      # Fetch from arXiv API
      url = self._build_search_url(query, max_results)
      results = await self._fetch_papers(url)

      if progress_callback:
        progress_callback(f"Found {len(results)} papers on arXiv", 100.0)

      return results
    except Exception:
      # Graceful degradation: return empty list on any error
      return []

  def _build_search_url(self, query: str, max_results: int) -> str:
    """Build arXiv API URL with query."""
    # Escape special characters
    safe_query = query.replace(" ", "+AND+")

    # Limit max results to API maximum
    page_size = min(max_results, self.MAX_RESULTS_PER_REQUEST)

    return (
      f"{self.BASE_URL}?"
      f"search_query=all:{safe_query}"
      f"&start=0"
      f"&max_results={page_size}"
      f"&sortBy=submittedDate"
      f"&sortOrder=descending"
    )

  async def _fetch_papers(self, url: str) -> list[DatasetResult]:
    """Fetch and parse arXiv feed."""
    # Respect rate limiting
    await asyncio.sleep(self.DELAY_BETWEEN_REQUESTS)

    try:
      import urllib.request
      with urllib.request.urlopen(url, timeout=10) as response:
        feed_data = response.read()
    except Exception:
      return []

    # Parse feed
    feed = feedparser.parse(feed_data)
    if not feed.entries:
      return []

    results = []
    for entry in feed.entries:
      try:
        result = self._parse_entry(entry)
        if result:
          results.append(result)
      except Exception:
        continue

    return results

  def _parse_entry(self, entry) -> DatasetResult | None:
    """Convert arXiv feed entry to DatasetResult."""
    try:
      # Extract basic fields
      title = entry.get("title", "Unknown").strip()
      arxiv_id = entry.get("id", "").split("/abs/")[-1]
      summary = entry.get("summary", "").strip()

      # Parse publication date
      published_str = entry.get("published", "")
      try:
        published_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
      except Exception:
        published_dt = datetime.now()

      # Extract authors
      authors = []
      for author_entry in entry.get("authors", []):
        author_name = author_entry.get("name", "")
        if author_name:
          authors.append(author_name)
      authors_str = ", ".join(authors[:5])  # Limit to first 5
      if len(authors) > 5:
        authors_str += f", and {len(authors) - 5} others"

      # Build PDF URL
      pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

      # Estimate size (most arXiv PDFs are 5-50 MB, average ~15 MB)
      estimated_size = 15 * 1024 * 1024

      # Create dataset result
      result = DatasetResult(
        id=f"arxiv_{arxiv_id.replace('/', '_')}",
        name=title,
        description=summary,
        source=DataSource.ARXIV,
        url=f"https://arxiv.org/abs/{arxiv_id}",
        size_display="~15 MB",
        estimated_size_bytes=estimated_size,
        license_info="arXiv",
        last_updated=published_dt,
        rank_score=75,
        quality_score=7,
        health_score=80,
        available_sources=[DataSource.ARXIV.value],
        requires_auth=False,
        auth_message=None,
        metadata={
          "arxiv_id": arxiv_id,
          "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}",
          "pdf_url": pdf_url,
          "authors": authors_str,
          "categories": entry.get("arxiv_primary_category", {}).get("term", ""),
          "source": "arXiv",
        },
      )

      return result
    except Exception:
      return None

  async def get_download_urls(self, dataset: DatasetResult) -> list[str]:
    """Return PDF download URL for arXiv paper."""
    pdf_url = dataset.metadata.get("pdf_url")
    if pdf_url:
      return [pdf_url]
    return []
