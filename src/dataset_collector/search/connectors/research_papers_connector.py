"""Research paper search connector (arXiv, OpenAlex, Zenodo publications)."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Callable
from urllib.parse import quote

import httpx

from dataset_collector.core.enums import DataSource
from dataset_collector.core.models import DatasetResult, SearchFilters
from dataset_collector.search.connectors.base import BaseConnector

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ResearchPapersConnector(BaseConnector):
  """Search and download open-access research papers."""

  source = DataSource.RESEARCH_PAPERS

  async def search(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int = 100,
    progress_callback: Callable[[str, float], None] | None = None,
  ) -> list[DatasetResult]:
    self._report_progress(progress_callback, "Searching research papers...", 0.0)
    per_source = max(max_results // 3, 10)
    results: list[DatasetResult] = []

    try:
      results.extend(await self._search_arxiv(query, filters, per_source, progress_callback))
      results.extend(await self._search_openalex(query, filters, per_source, progress_callback))
      results.extend(await self._search_zenodo_papers(query, filters, per_source, progress_callback))
    except Exception:
      pass

    deduped = _dedupe_papers(results)[:max_results]
    self._report_progress(
      progress_callback,
      f"Research Papers: {len(deduped)} papers found",
      100.0,
    )
    return deduped

  async def _search_arxiv(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int,
    progress_callback: Callable[[str, float], None] | None,
  ) -> list[DatasetResult]:
    self._report_progress(progress_callback, "Searching arXiv...", 10.0)
    results: list[DatasetResult] = []
    safe_query = quote(query)
    url = (
      f"http://export.arxiv.org/api/query?"
      f"search_query=all:{safe_query}&start=0&max_results={min(max_results, 30)}"
    )

    async with httpx.AsyncClient(timeout=30) as client:
      resp = await client.get(url)
      resp.raise_for_status()
      root = ET.fromstring(resp.text)

    for entry in root.findall("atom:entry", ATOM_NS):
      title = _clean_text(entry.findtext("atom:title", default="", namespaces=ATOM_NS))
      if not title:
        continue

      arxiv_id = _extract_arxiv_id(entry.findtext("atom:id", default="", namespaces=ATOM_NS))
      if not arxiv_id:
        continue

      authors = [
        _clean_text(a.findtext("atom:name", default="", namespaces=ATOM_NS))
        for a in entry.findall("atom:author", ATOM_NS)
      ]
      authors = [a for a in authors if a]
      summary = _clean_text(entry.findtext("atom:summary", default="", namespaces=ATOM_NS))
      published = entry.findtext("atom:published", default="", namespaces=ATOM_NS)
      updated = _parse_date(published)

      pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
      if not self._matches_file_type("paper.pdf", filters):
        continue

      results.append(
        DatasetResult(
          id=f"arxiv_{hashlib.md5(arxiv_id.encode()).hexdigest()[:12]}",
          name=title,
          source=DataSource.RESEARCH_PAPERS,
          url=f"https://arxiv.org/abs/{arxiv_id}",
          estimated_size_bytes=2 * 1024 * 1024,
          file_count=1,
          license_info="arXiv License",
          last_updated=updated,
          description=summary[:500],
          files=[f"{title[:80]}.pdf"],
          download_urls=[pdf_url],
          metadata={
            "content_type": "paper",
            "arxiv_id": arxiv_id,
            "authors": authors,
            "published": published,
            "abstract": summary,
            "provider": "arXiv",
          },
        )
      )

    return results

  async def _search_openalex(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int,
    progress_callback: Callable[[str, float], None] | None,
  ) -> list[DatasetResult]:
    self._report_progress(progress_callback, "Searching OpenAlex...", 40.0)
    results: list[DatasetResult] = []

    async with httpx.AsyncClient(timeout=30) as client:
      resp = await client.get(
        "https://api.openalex.org/works",
        params={
          "search": query,
          "per_page": min(max_results, 25),
          "filter": "has_oa_accepted_or_gold_version:true",
          "mailto": "dataset_collector@openalex.org",
        },
      )
      resp.raise_for_status()
      data = resp.json()

    for work in data.get("results", []):
      title = work.get("title") or work.get("display_name", "")
      if not title:
        continue

      pdf_url = _openalex_pdf_url(work)
      if not pdf_url:
        continue

      if not self._matches_license(work.get("license", "Open Access") or "Open Access", filters):
        continue

      authors = [
        a.get("author", {}).get("display_name", "")
        for a in work.get("authorships", [])
        if a.get("author", {}).get("display_name")
      ]
      doi = (work.get("doi") or "").replace("https://doi.org/", "")
      updated = _parse_date(work.get("publication_date", ""))
      abstract = work.get("abstract_inverted_index")
      abstract_text = ""
      if isinstance(abstract, dict):
        abstract_text = _reconstruct_abstract(abstract)

      work_id = work.get("id", "").rsplit("/", 1)[-1]
      results.append(
        DatasetResult(
          id=f"openalex_{hashlib.md5(work_id.encode()).hexdigest()[:12]}",
          name=title,
          source=DataSource.RESEARCH_PAPERS,
          url=work.get("id", pdf_url),
          estimated_size_bytes=2 * 1024 * 1024,
          file_count=1,
          license_info=work.get("license") or "Open Access",
          last_updated=updated,
          description=(abstract_text or work.get("title", ""))[:500],
          files=[f"{title[:80]}.pdf"],
          download_urls=[pdf_url],
          metadata={
            "content_type": "paper",
            "openalex_id": work_id,
            "doi": doi,
            "authors": authors,
            "citation_count": work.get("cited_by_count", 0),
            "abstract": abstract_text,
            "provider": "OpenAlex",
          },
        )
      )

    return results

  async def _search_zenodo_papers(
    self,
    query: str,
    filters: SearchFilters,
    max_results: int,
    progress_callback: Callable[[str, float], None] | None,
  ) -> list[DatasetResult]:
    self._report_progress(progress_callback, "Searching Zenodo publications...", 70.0)
    results: list[DatasetResult] = []

    async with httpx.AsyncClient(timeout=30) as client:
      resp = await client.get(
        "https://zenodo.org/api/records",
        params={
          "q": f"{query} resource_type.type:publication",
          "size": min(max_results, 25),
          "sort": "mostrecent",
        },
      )
      resp.raise_for_status()
      hits = resp.json().get("hits", {}).get("hits", [])

    for record in hits:
      metadata = record.get("metadata", {})
      title = metadata.get("title", "Untitled")
      record_id = str(record.get("id", ""))
      files_meta = record.get("files", [])
      pdf_files = [
        f for f in files_meta
        if f.get("key", "").lower().endswith(".pdf")
      ]
      if not pdf_files:
        continue

      download_urls = [f.get("links", {}).get("self", "") for f in pdf_files]
      download_urls = [u for u in download_urls if u]
      if not download_urls:
        continue

      license_info = metadata.get("license", {}).get("id", "Research Use") if isinstance(
        metadata.get("license"), dict
      ) else str(metadata.get("license", "Research Use"))

      if not self._matches_license(license_info, filters):
        continue

      creators = [c.get("name", "") for c in metadata.get("creators", []) if c.get("name")]
      updated = _parse_date(record.get("updated", ""))

      results.append(
        DatasetResult(
          id=f"zenodo_paper_{hashlib.md5(record_id.encode()).hexdigest()[:12]}",
          name=title,
          source=DataSource.RESEARCH_PAPERS,
          url=record.get("links", {}).get("self_html", f"https://zenodo.org/record/{record_id}"),
          estimated_size_bytes=sum(f.get("size", 0) for f in pdf_files) or None,
          file_count=len(pdf_files),
          license_info=license_info,
          last_updated=updated,
          description=(metadata.get("description") or "")[:500],
          files=[f.get("key", "") for f in pdf_files],
          download_urls=download_urls,
          metadata={
            "content_type": "paper",
            "zenodo_id": record_id,
            "doi": metadata.get("doi", ""),
            "authors": creators,
            "abstract": metadata.get("description", ""),
            "provider": "Zenodo",
          },
        )
      )

    return results


def _extract_arxiv_id(atom_id: str) -> str:
  if not atom_id:
    return ""
  match = re.search(r"arxiv\.org/abs/(.+)$", atom_id)
  return match.group(1) if match else atom_id.rsplit("/", 1)[-1]


def _clean_text(text: str) -> str:
  return re.sub(r"\s+", " ", text or "").strip()


def _parse_date(value: str) -> datetime | None:
  if not value:
    return None
  try:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
  except (ValueError, TypeError):
    return None


def _openalex_pdf_url(work: dict) -> str | None:
  oa = work.get("open_access") or {}
  if oa.get("oa_url") and "pdf" in oa["oa_url"].lower():
    return oa["oa_url"]
  best = work.get("best_oa_location") or {}
  if best.get("pdf_url"):
    return best["pdf_url"]
  if best.get("landing_page_url") and "pdf" in best["landing_page_url"].lower():
    return best["landing_page_url"]
  return oa.get("oa_url")


def _reconstruct_abstract(inverted_index: dict) -> str:
  words: list[tuple[int, str]] = []
  for word, positions in inverted_index.items():
    for pos in positions:
      words.append((pos, word))
  words.sort(key=lambda x: x[0])
  return " ".join(w for _, w in words)


def _dedupe_papers(results: list[DatasetResult]) -> list[DatasetResult]:
  seen: set[str] = set()
  unique: list[DatasetResult] = []
  for paper in results:
    key = re.sub(r"[^a-z0-9]+", "", paper.name.lower())[:80]
    if key in seen:
      continue
    seen.add(key)
    unique.append(paper)
  return unique
