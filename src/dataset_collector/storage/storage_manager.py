"""Storage and library management."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dataset_collector.core.models import LibraryEntry
from dataset_collector.logging.logger import AppLogger


class StorageManager:
  """Manages downloaded dataset library and disk usage."""

  def __init__(self, library_dir: Path, logger: AppLogger) -> None:
    self._library_dir = Path(library_dir)
    self._library_dir.mkdir(parents=True, exist_ok=True)
    self._index_path = self._library_dir / "library_index.json"
    self._logger = logger
    self._entries: list[LibraryEntry] = []
    self._load_index()

  def _load_index(self) -> None:
    if self._index_path.exists():
      try:
        data = json.loads(self._index_path.read_text(encoding="utf-8"))
        self._entries = [
          LibraryEntry(
            id=e["id"],
            name=e["name"],
            source=e["source"],
            local_path=e["local_path"],
            size_bytes=e["size_bytes"],
            downloaded_at=datetime.fromisoformat(e["downloaded_at"]),
            file_count=e["file_count"],
            metadata=e.get("metadata", {}),
          )
          for e in data
        ]
      except (json.JSONDecodeError, KeyError):
        self._entries = []

  def _save_index(self) -> None:
    data = [
      {
        "id": e.id,
        "name": e.name,
        "source": e.source,
        "local_path": e.local_path,
        "size_bytes": e.size_bytes,
        "downloaded_at": e.downloaded_at.isoformat(),
        "file_count": e.file_count,
        "metadata": e.metadata,
      }
      for e in self._entries
    ]
    self._index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

  def add_dataset(
    self,
    name: str,
    source: str,
    local_path: str,
    metadata: dict | None = None,
  ) -> LibraryEntry:
    path = Path(local_path)
    size_bytes = self._dir_size(path) if path.is_dir() else path.stat().st_size
    file_count = sum(1 for _ in path.rglob("*") if _.is_file()) if path.is_dir() else 1

    entry = LibraryEntry(
      id=str(uuid.uuid4()),
      name=name,
      source=source,
      local_path=str(path.resolve()),
      size_bytes=size_bytes,
      downloaded_at=datetime.now(timezone.utc),
      file_count=file_count,
      metadata=metadata or {},
    )
    self._entries.append(entry)
    self._save_index()
    self._logger.info(f"Added to library: {name}")
    return entry

  def get_all(self) -> list[LibraryEntry]:
    return list(self._entries)

  def get_by_id(self, entry_id: str) -> LibraryEntry | None:
    return next((e for e in self._entries if e.id == entry_id), None)

  def delete_dataset(self, entry_id: str, remove_files: bool = True) -> bool:
    entry = self.get_by_id(entry_id)
    if not entry:
      return False
    if remove_files:
      path = Path(entry.local_path)
      if path.exists():
        if path.is_dir():
          shutil.rmtree(path, ignore_errors=True)
        else:
          path.unlink(missing_ok=True)
    self._entries = [e for e in self._entries if e.id != entry_id]
    self._save_index()
    self._logger.info(f"Deleted from library: {entry.name}")
    return True

  def get_disk_usage(self) -> dict:
    total_bytes = sum(e.size_bytes for e in self._entries)
    return {
      "total_datasets": len(self._entries),
      "total_bytes": total_bytes,
      "total_display": _format_bytes(total_bytes),
      "library_path": str(self._library_dir),
    }

  def export_metadata(self, output_path: str) -> Path:
    data = [
      {
        "id": e.id,
        "name": e.name,
        "source": e.source,
        "local_path": e.local_path,
        "size_bytes": e.size_bytes,
        "size_display": _format_bytes(e.size_bytes),
        "downloaded_at": e.downloaded_at.isoformat(),
        "file_count": e.file_count,
        "metadata": e.metadata,
      }
      for e in self._entries
    ]
    path = Path(output_path)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path

  def refresh_entry(self, entry_id: str) -> LibraryEntry | None:
    entry = self.get_by_id(entry_id)
    if not entry:
      return None
    path = Path(entry.local_path)
    if not path.exists():
      return entry
    entry.size_bytes = self._dir_size(path) if path.is_dir() else path.stat().st_size
    entry.file_count = sum(1 for _ in path.rglob("*") if _.is_file()) if path.is_dir() else 1
    self._save_index()
    return entry

  @staticmethod
  def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _format_bytes(size: int) -> str:
  for unit in ("B", "KB", "MB", "GB", "TB"):
    if size < 1024:
      return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
    size /= 1024
  return f"{size:.1f} PB"
