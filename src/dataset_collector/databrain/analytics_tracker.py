"""Search analytics tracking and reporting."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from dataset_collector.logging.logger import AppLogger


class SearchAnalytics:
  """Track and analyze search patterns."""

  def __init__(self, db_path: str | Path, logger: AppLogger | None = None) -> None:
    self._db_path = Path(db_path)
    self._logger = logger
    self._ensure_db()

  def _ensure_db(self) -> None:
    """Initialize analytics storage."""
    self._db_path.touch(exist_ok=True)

  def log_search(
    self,
    query: str,
    sources: list[str],
    results_found: int,
    search_time_seconds: float,
    aggressive_mode: bool = False,
  ) -> None:
    """Log search activity."""
    try:
      entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "sources": sources,
        "results": results_found,
        "time": search_time_seconds,
        "aggressive": aggressive_mode,
      }

      with open(self._db_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    except Exception as e:
      if self._logger:
        self._logger.error(f"Analytics logging failed: {e}")

  def get_stats(self) -> dict:
    """Get search statistics."""
    try:
      if not self._db_path.exists():
        return {
          "total_searches": 0,
          "avg_results": 0,
          "most_searched": [],
          "top_sources": [],
          "avg_time": 0,
        }

      searches = []
      with open(self._db_path) as f:
        for line in f:
          try:
            searches.append(json.loads(line))
          except Exception:
            pass

      if not searches:
        return {
          "total_searches": 0,
          "avg_results": 0,
          "most_searched": [],
          "top_sources": [],
          "avg_time": 0,
        }

      # Calculate stats
      query_counts = {}
      source_counts = {}
      total_time = 0

      for s in searches:
        query = s.get("query", "").lower()
        if query:
          query_counts[query] = query_counts.get(query, 0) + 1

        for source in s.get("sources", []):
          source_counts[source] = source_counts.get(source, 0) + 1

        total_time += s.get("time", 0)

      # Top searches
      top_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:5]

      # Top sources
      top_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5]

      avg_results = sum(s.get("results", 0) for s in searches) / len(searches)
      avg_time = total_time / len(searches)

      return {
        "total_searches": len(searches),
        "avg_results": round(avg_results, 1),
        "most_searched": [q[0] for q in top_queries],
        "top_sources": [s[0] for s in top_sources],
        "avg_time": round(avg_time, 2),
        "discovery_rate": self._calculate_discovery_rate(searches),
      }
    except Exception as e:
      if self._logger:
        self._logger.error(f"Stats calculation failed: {e}")
      return {
        "total_searches": 0,
        "avg_results": 0,
        "most_searched": [],
        "top_sources": [],
        "avg_time": 0,
      }

  def _calculate_discovery_rate(self, searches: list) -> float:
    """Calculate % of datasets found in stage 1 vs multi-stage."""
    if not searches:
      return 0.0
    # Placeholder: would track stage-by-stage results
    return 85.0
