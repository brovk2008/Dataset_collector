"""Local SQLite search index for fast caching and hybrid search."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from dataset_collector.core.models import DatasetResult
from dataset_collector.logging.logger import AppLogger


class SearchIndex:
  """SQLite-based local search cache for hybrid search."""

  def __init__(self, db_path: str | Path, logger: AppLogger | None = None) -> None:
    self._db_path = Path(db_path)
    self._logger = logger
    self._conn: sqlite3.Connection | None = None
    self._init_db()

  def _init_db(self) -> None:
    """Initialize database and schema."""
    try:
      conn = sqlite3.connect(str(self._db_path))
      cursor = conn.cursor()

      # Create datasets table
      cursor.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          description TEXT,
          source TEXT,
          source_id TEXT,
          url TEXT UNIQUE,
          license TEXT,
          size_bytes INTEGER,
          updated_date DATETIME,
          download_count INTEGER,
          stars INTEGER,
          quality_score FLOAT,
          health_score INTEGER,
          tags TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          last_indexed DATETIME DEFAULT CURRENT_TIMESTAMP
        )
      """)

      # Create indexes
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON datasets(name)")
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags ON datasets(tags)")
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON datasets(source)")
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality ON datasets(quality_score DESC)")
      cursor.execute("CREATE INDEX IF NOT EXISTS idx_health ON datasets(health_score DESC)")

      conn.commit()
      conn.close()
    except Exception as e:
      if self._logger:
        self._logger.error(f"Failed to initialize search index: {e}")

  @property
  def conn(self) -> sqlite3.Connection:
    """Get or create database connection."""
    if self._conn is None:
      self._conn = sqlite3.connect(str(self._db_path))
      self._conn.row_factory = sqlite3.Row
    return self._conn

  def search_local(self, query: str, limit: int = 100) -> list[DatasetResult]:
    """Fast local search using SQLite FTS-like pattern matching."""
    try:
      cursor = self.conn.cursor()
      query_pattern = f"%{query.lower()}%"

      cursor.execute("""
        SELECT * FROM datasets
        WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ?
        ORDER BY health_score DESC, quality_score DESC
        LIMIT ?
      """, [query_pattern, query_pattern, query_pattern, limit])

      rows = cursor.fetchall()
      return [self._row_to_result(row) for row in rows]
    except Exception as e:
      if self._logger:
        self._logger.error(f"Local search failed: {e}")
      return []

  def add_to_index(self, result: DatasetResult) -> None:
    """Add single result to local index."""
    try:
      cursor = self.conn.cursor()
      tags = ",".join(result.metadata.get("tags", []))

      cursor.execute("""
        INSERT OR REPLACE INTO datasets
        (id, name, description, source, url, license, size_bytes, updated_date,
         download_count, stars, quality_score, health_score, tags, last_indexed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      """, [
        result.id,
        result.name,
        result.description,
        result.source.value,
        result.url,
        result.license_info,
        result.estimated_size_bytes,
        result.last_updated,
        result.metadata.get("downloads", 0),
        result.metadata.get("stars", 0),
        result.quality_score,
        result.health_score,
        tags,
        datetime.now(),
      ])

      self.conn.commit()
    except Exception as e:
      if self._logger:
        self._logger.error(f"Failed to add to index: {e}")

  def update_index_from_search(self, results: list[DatasetResult]) -> None:
    """Batch add search results to local cache."""
    for result in results:
      self.add_to_index(result)

  def get_by_id(self, result_id: str) -> DatasetResult | None:
    """Retrieve dataset by ID from local index."""
    try:
      cursor = self.conn.cursor()
      cursor.execute("SELECT * FROM datasets WHERE id = ?", [result_id])
      row = cursor.fetchone()
      return self._row_to_result(row) if row else None
    except Exception as e:
      if self._logger:
        self._logger.error(f"Failed to get by ID: {e}")
      return None

  def get_count(self) -> int:
    """Get total cached datasets."""
    try:
      cursor = self.conn.cursor()
      cursor.execute("SELECT COUNT(*) FROM datasets")
      return cursor.fetchone()[0]
    except Exception:
      return 0

  def clear_old_entries(self, days: int = 30) -> int:
    """Remove entries older than N days."""
    try:
      cursor = self.conn.cursor()
      cursor.execute("""
        DELETE FROM datasets
        WHERE last_indexed < datetime('now', '-' || ? || ' days')
      """, [days])
      self.conn.commit()
      return cursor.rowcount
    except Exception as e:
      if self._logger:
        self._logger.error(f"Failed to clear old entries: {e}")
      return 0

  def _row_to_result(self, row: sqlite3.Row) -> DatasetResult:
    """Convert database row to DatasetResult."""
    from dataset_collector.core.enums import DataSource

    tags = row["tags"].split(",") if row["tags"] else []
    return DatasetResult(
      id=row["id"],
      name=row["name"],
      source=DataSource(row["source"]),
      url=row["url"],
      description=row["description"],
      license_info=row["license"] or "Unknown",
      estimated_size_bytes=row["size_bytes"],
      last_updated=row["updated_date"],
      quality_score=row["quality_score"] or 0.0,
      health_score=row["health_score"] or 0,
      metadata={
        "downloads": row["download_count"] or 0,
        "stars": row["stars"] or 0,
        "tags": tags,
      },
    )

  def close(self) -> None:
    """Close database connection."""
    if self._conn:
      self._conn.close()
      self._conn = None

  def __del__(self) -> None:
    """Ensure connection is closed on cleanup."""
    self.close()
