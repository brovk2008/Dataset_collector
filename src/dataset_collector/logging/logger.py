"""Local logging system for Dataset_Collector."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dataset_collector.core.enums import LogCategory


class AppLogger:
  """Structured local file logger for application events."""

  def __init__(self, logs_dir: Path) -> None:
    self._logs_dir = Path(logs_dir)
    self._logs_dir.mkdir(parents=True, exist_ok=True)
    self._setup_standard_logging()

  def _setup_standard_logging(self) -> None:
    log_file = self._logs_dir / "app.log"
    logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
      handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
      ],
      force=True,
    )
    self._logger = logging.getLogger("dataset_collector")

  def _write_category_log(self, category: LogCategory, data: dict[str, Any]) -> None:
    entry = {
      "timestamp": datetime.now(timezone.utc).isoformat(),
      "category": category.value,
      **data,
    }
    log_file = self._logs_dir / f"{category.value}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
      f.write(json.dumps(entry, default=str) + "\n")

  def info(self, message: str) -> None:
    self._logger.info(message)

  def warning(self, message: str) -> None:
    self._logger.warning(message)

  def error(self, message: str, **context: Any) -> None:
    self._logger.error(message)
    self._write_category_log(LogCategory.ERROR, {"message": message, **context})

  def log_search(self, query: str, sources: list[str], result_count: int) -> None:
    self.info(f"Search: '{query}' -> {result_count} results")
    self._write_category_log(
      LogCategory.SEARCH,
      {"query": query, "sources": sources, "result_count": result_count},
    )

  def log_download(self, dataset_name: str, status: str, **details: Any) -> None:
    self.info(f"Download [{status}]: {dataset_name}")
    self._write_category_log(
      LogCategory.DOWNLOAD,
      {"dataset_name": dataset_name, "status": status, **details},
    )

  def log_analysis(self, dataset_name: str, profile: dict[str, Any]) -> None:
    self.info(f"Analysis complete: {dataset_name}")
    self._write_category_log(
      LogCategory.ANALYSIS,
      {"dataset_name": dataset_name, "profile": profile},
    )

  def log_manifest(self, path: str, entry_count: int) -> None:
    self.info(f"Manifest saved: {path} ({entry_count} entries)")
    self._write_category_log(
      LogCategory.MANIFEST,
      {"path": path, "entry_count": entry_count},
    )
