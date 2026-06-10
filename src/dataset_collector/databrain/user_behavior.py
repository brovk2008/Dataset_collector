"""Track user search behavior, clicks, and co-downloads."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from dataset_collector.logging.logger import AppLogger


class UserBehaviorTracker:
  """SQLite-based tracker for search queries, clicks, downloads, and co-downloads."""

  def __init__(
    self,
    cache_dir: Path | None = None,
    logger: AppLogger | None = None,
  ) -> None:
    self._cache_dir = cache_dir or (Path.home() / ".dataset_collector" / "cache")
    self._cache_dir.mkdir(parents=True, exist_ok=True)
    self._logger = logger
    self._db_path = self._cache_dir / "user_behavior.db"
    self._conn: sqlite3.Connection | None = None
    self._session_id = datetime.utcnow().isoformat()
    self._init_db()

  def _init_db(self) -> None:
    """Initialize database schema."""
    conn = self._get_connection()
    cursor = conn.cursor()

    cursor.execute(
      """
      CREATE TABLE IF NOT EXISTS searches (
        id INTEGER PRIMARY KEY,
        query TEXT NOT NULL,
        source_filter TEXT,
        timestamp DATETIME,
        results_count INTEGER,
        session_id TEXT
      )
      """
    )

    cursor.execute(
      """
      CREATE TABLE IF NOT EXISTS clicks (
        id INTEGER PRIMARY KEY,
        search_id INTEGER,
        dataset_id TEXT NOT NULL,
        rank_position INTEGER,
        timestamp DATETIME,
        time_on_result_seconds INTEGER,
        clicked_from_source TEXT
      )
      """
    )

    cursor.execute(
      """
      CREATE TABLE IF NOT EXISTS downloads (
        id INTEGER PRIMARY KEY,
        dataset_id TEXT NOT NULL,
        timestamp DATETIME,
        session_id TEXT
      )
      """
    )

    cursor.execute(
      """
      CREATE TABLE IF NOT EXISTS co_downloads (
        dataset_a_id TEXT NOT NULL,
        dataset_b_id TEXT NOT NULL,
        co_download_count INTEGER DEFAULT 1,
        last_occurrence DATETIME,
        PRIMARY KEY (dataset_a_id, dataset_b_id)
      )
      """
    )

    cursor.execute(
      """
      CREATE TABLE IF NOT EXISTS favorites (
        dataset_id TEXT PRIMARY KEY,
        favorited_at DATETIME,
        tags TEXT
      )
      """
    )

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dataset_clicks ON clicks(dataset_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_timestamp ON searches(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_download_timestamp ON downloads(timestamp)")

    conn.commit()

  def _get_connection(self) -> sqlite3.Connection:
    """Get or create database connection."""
    if self._conn is None:
      self._conn = sqlite3.connect(str(self._db_path), timeout=10.0)
      self._conn.row_factory = sqlite3.Row
    return self._conn

  def log_search(
    self, query: str, sources: list[str], results_count: int
  ) -> int:
    """Log a search query. Returns search_id."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      source_filter = ",".join(sources)

      cursor.execute(
        """
        INSERT INTO searches (query, source_filter, timestamp, results_count, session_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (query, source_filter, datetime.utcnow(), results_count, self._session_id),
      )
      conn.commit()

      return cursor.lastrowid
    except Exception as e:
      if self._logger:
        self._logger.error(f"Failed to log search: {e}")
      return -1

  def log_click(
    self,
    search_id: int,
    dataset_id: str,
    rank_position: int,
    clicked_from: str = "table",
  ) -> None:
    """Log a dataset click."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      cursor.execute(
        """
        INSERT INTO clicks (search_id, dataset_id, rank_position, timestamp, clicked_from_source)
        VALUES (?, ?, ?, ?, ?)
        """,
        (search_id, dataset_id, rank_position, datetime.utcnow(), clicked_from),
      )
      conn.commit()
    except Exception as e:
      if self._logger:
        self._logger.error(f"Failed to log click: {e}")

  def log_download(self, dataset_id: str) -> None:
    """Log a dataset download."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      cursor.execute(
        """
        INSERT INTO downloads (dataset_id, timestamp, session_id)
        VALUES (?, ?, ?)
        """,
        (dataset_id, datetime.utcnow(), self._session_id),
      )
      conn.commit()
    except Exception as e:
      if self._logger:
        self._logger.error(f"Failed to log download: {e}")

  def log_download_set(self, dataset_ids: list[str]) -> None:
    """Log a multi-dataset download (for co-download tracking)."""
    for i, dataset_a in enumerate(dataset_ids):
      for dataset_b in dataset_ids[i + 1 :]:
        self._log_co_download(dataset_a, dataset_b)

  def _log_co_download(self, dataset_a_id: str, dataset_b_id: str) -> None:
    """Track co-download pair."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      cursor.execute(
        """
        INSERT INTO co_downloads (dataset_a_id, dataset_b_id, co_download_count, last_occurrence)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(dataset_a_id, dataset_b_id)
        DO UPDATE SET
          co_download_count = co_download_count + 1,
          last_occurrence = excluded.last_occurrence
        """,
        (dataset_a_id, dataset_b_id, datetime.utcnow()),
      )
      conn.commit()
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to log co-download: {e}",
          origin="UserBehaviorTracker",
        )

  def log_favorite(self, dataset_id: str, tags: str | None = None) -> None:
    """Mark a dataset as favorited."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      cursor.execute(
        """
        INSERT OR REPLACE INTO favorites (dataset_id, favorited_at, tags)
        VALUES (?, ?, ?)
        """,
        (dataset_id, datetime.utcnow(), tags),
      )
      conn.commit()
    except Exception as e:
      if self._logger:
        self._logger.error(f"Failed to log favorite: {e}")

  def get_click_score(self, dataset_id: str) -> float:
    """Compute 0-1 click score based on frequency and recency."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      cursor.execute(
        """
        SELECT COUNT(*), MAX(timestamp) FROM clicks WHERE dataset_id = ?
        """,
        (dataset_id,),
      )
      row = cursor.fetchone()

      count = row[0] or 0
      last_click_time = row[1]

      if count == 0:
        return 0.0

      # Recency decay: 30 days ago = 50% credit
      if last_click_time:
        last_click = datetime.fromisoformat(last_click_time)
        days_ago = (datetime.utcnow() - last_click).days
        recency_factor = max(0, 1 - days_ago / 60)
      else:
        recency_factor = 0.5

      # Popularity factor: cap at 10 clicks for 1.0
      popularity_factor = min(count / 10, 1.0)

      return popularity_factor * 0.7 + recency_factor * 0.3
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to get click score: {e}",
          origin="UserBehaviorTracker",
        )
      return 0.0

  def get_co_downloads(
    self, dataset_id: str, limit: int = 5
  ) -> list[tuple[str, int]]:
    """Get datasets co-downloaded with this one, sorted by count."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      cursor.execute(
        """
        SELECT dataset_b_id, co_download_count FROM co_downloads
        WHERE dataset_a_id = ?
        ORDER BY co_download_count DESC
        LIMIT ?
        """,
        (dataset_id, limit),
      )

      return [(row[0], row[1]) for row in cursor.fetchall()]
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to get co-downloads: {e}",
          origin="UserBehaviorTracker",
        )
      return []

  def get_top_searches(self, limit: int = 10, days_back: int = 30) -> list[tuple[str, int]]:
    """Get most common search queries."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      cutoff_date = datetime.utcnow() - timedelta(days=days_back)

      cursor.execute(
        """
        SELECT query, COUNT(*) as count FROM searches
        WHERE timestamp > ?
        GROUP BY query
        ORDER BY count DESC
        LIMIT ?
        """,
        (cutoff_date, limit),
      )

      return [(row[0], row[1]) for row in cursor.fetchall()]
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to get top searches: {e}",
          origin="UserBehaviorTracker",
        )
      return []

  def get_most_clicked(
    self, limit: int = 10, days_back: int = 30
  ) -> list[tuple[str, int]]:
    """Get most clicked datasets."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      cutoff_date = datetime.utcnow() - timedelta(days=days_back)

      cursor.execute(
        """
        SELECT dataset_id, COUNT(*) as count FROM clicks
        WHERE timestamp > ?
        GROUP BY dataset_id
        ORDER BY count DESC
        LIMIT ?
        """,
        (cutoff_date, limit),
      )

      return [(row[0], row[1]) for row in cursor.fetchall()]
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to get most clicked: {e}",
          origin="UserBehaviorTracker",
        )
      return []

  def clear_all(self) -> None:
    """Clear all user behavior data."""
    try:
      conn = self._get_connection()
      cursor = conn.cursor()

      cursor.execute("DELETE FROM searches")
      cursor.execute("DELETE FROM clicks")
      cursor.execute("DELETE FROM downloads")
      cursor.execute("DELETE FROM co_downloads")
      cursor.execute("DELETE FROM favorites")

      conn.commit()

      if self._logger:
        self._logger.info("User behavior data cleared")
    except Exception as e:
      if self._logger:
        self._logger.error(
          f"Failed to clear behavior data: {e}",
          origin="UserBehaviorTracker",
        )

  def close(self) -> None:
    """Close database connection."""
    if self._conn:
      self._conn.close()
      self._conn = None
