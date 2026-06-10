"""SQLite cache for dataset embeddings."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np

from dataset_collector.core.models import DatasetResult
from dataset_collector.logging.logger import AppLogger


class EmbeddingsCache:
  """SQLite-based cache for dataset embeddings with fast lookup."""

  def __init__(
    self,
    cache_dir: Path | None = None,
    logger: AppLogger | None = None,
  ) -> None:
    self._cache_dir = cache_dir or (Path.home() / ".dataset_collector" / "cache")
    self._cache_dir.mkdir(parents=True, exist_ok=True)
    self._logger = logger
    self._db_path = self._cache_dir / "embeddings.db"
    self._conn: sqlite3.Connection | None = None
    self._init_db()

  def _init_db(self) -> None:
    """Initialize database schema."""
    conn = self._get_connection()
    cursor = conn.cursor()

    cursor.execute(
      """
      CREATE TABLE IF NOT EXISTS embeddings (
        dataset_id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        tags TEXT,
        category TEXT,
        embedding BLOB NOT NULL,
        created_at DATETIME,
        last_updated DATETIME
      )
      """
    )

    cursor.execute(
      "CREATE INDEX IF NOT EXISTS idx_source ON embeddings(source)"
    )
    cursor.execute(
      "CREATE INDEX IF NOT EXISTS idx_category ON embeddings(category)"
    )

    conn.commit()

  def _get_connection(self) -> sqlite3.Connection:
    """Get or create database connection."""
    if self._conn is None:
      self._conn = sqlite3.connect(str(self._db_path), timeout=10.0)
      self._conn.row_factory = sqlite3.Row
    return self._conn

  def set(
    self,
    dataset_id: str,
    dataset: DatasetResult,
    embedding: np.ndarray,
  ) -> None:
    """Store dataset embedding."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      embedding_bytes = embedding.astype(np.float32).tobytes()

      cursor.execute(
        """
        INSERT OR REPLACE INTO embeddings
        (dataset_id, source, title, description, tags, category, embedding, created_at, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
          dataset_id,
          dataset.source.value,
          dataset.name,
          dataset.description or "",
          ",".join(dataset.metadata.get("tags", [])) if isinstance(
            dataset.metadata.get("tags"), list
          ) else dataset.metadata.get("tags", ""),
          dataset.metadata.get("category", ""),
          embedding_bytes,
          datetime.utcnow(),
          datetime.utcnow(),
        ),
      )
      conn.commit()
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to cache embedding for {dataset_id}: {e}",
          origin="EmbeddingsCache",
        )

  def get(self, dataset_id: str) -> np.ndarray | None:
    """Retrieve embedding by dataset ID."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      cursor.execute("SELECT embedding FROM embeddings WHERE dataset_id = ?", (dataset_id,))
      row = cursor.fetchone()

      if row:
        embedding_bytes = row[0]
        return np.frombuffer(embedding_bytes, dtype=np.float32)
      return None
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to retrieve embedding for {dataset_id}: {e}",
          origin="EmbeddingsCache",
        )
      return None

  def exists(self, dataset_id: str) -> bool:
    """Check if embedding is cached."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      cursor.execute("SELECT 1 FROM embeddings WHERE dataset_id = ? LIMIT 1", (dataset_id,))
      return cursor.fetchone() is not None
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to check cache for {dataset_id}: {e}",
          origin="EmbeddingsCache",
        )
      return False

  def get_by_ids(self, dataset_ids: list[str]) -> dict[str, np.ndarray]:
    """Retrieve multiple embeddings by IDs (batch query)."""
    result = {}
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      placeholders = ",".join("?" * len(dataset_ids))
      cursor.execute(
        f"SELECT dataset_id, embedding FROM embeddings WHERE dataset_id IN ({placeholders})",
        dataset_ids,
      )

      for row in cursor.fetchall():
        dataset_id = row[0]
        embedding_bytes = row[1]
        result[dataset_id] = np.frombuffer(embedding_bytes, dtype=np.float32)
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to retrieve batch embeddings: {e}",
          origin="EmbeddingsCache",
        )

    return result

  def clear(self) -> None:
    """Delete all cached embeddings."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()
      cursor.execute("DELETE FROM embeddings")
      conn.commit()

      if self._logger:
        self._logger.info("Embeddings cache cleared")
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to clear cache: {e}",
          origin="EmbeddingsCache",
        )

  def stats(self) -> dict:
    """Return cache statistics."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      cursor.execute("SELECT COUNT(*), SUM(LENGTH(embedding)) FROM embeddings")
      row = cursor.fetchone()

      count = row[0] or 0
      size_bytes = row[1] or 0
      size_mb = size_bytes / (1024 * 1024)

      # Get DB file size
      db_size_bytes = self._db_path.stat().st_size if self._db_path.exists() else 0
      db_size_mb = db_size_bytes / (1024 * 1024)

      return {
        "total_cached": count,
        "embedding_size_mb": size_mb,
        "db_size_mb": db_size_mb,
        "total_size_mb": size_mb + db_size_mb,
        "last_updated": datetime.utcnow().isoformat(),
      }
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to get cache stats: {e}",
          origin="EmbeddingsCache",
        )
      return {
        "total_cached": 0,
        "embedding_size_mb": 0,
        "db_size_mb": 0,
        "total_size_mb": 0,
        "last_updated": datetime.utcnow().isoformat(),
      }

  def close(self) -> None:
    """Close database connection."""
    if self._conn:
      self._conn.close()
      self._conn = None
