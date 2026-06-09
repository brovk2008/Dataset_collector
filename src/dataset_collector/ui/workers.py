"""Background workers for async operations."""

from __future__ import annotations

import asyncio
from typing import Callable

from PySide6.QtCore import QThread, Signal

from dataset_collector.core.models import DatasetResult, DownloadTask, SearchRequest
from dataset_collector.download.download_engine import DownloadEngine
from dataset_collector.search.search_engine import SearchEngine


class SearchWorker(QThread):
  progress = Signal(str, float)
  finished = Signal(list)
  error = Signal(str)

  def __init__(self, engine: SearchEngine, request: SearchRequest) -> None:
    super().__init__()
    self._engine = engine
    self._request = request

  def run(self) -> None:
    try:
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)
      results = loop.run_until_complete(
        self._engine.search(
          self._request,
          progress_callback=lambda msg, pct: self.progress.emit(msg, pct),
        )
      )
      loop.close()
      self.finished.emit(results)
    except Exception as e:
      self.error.emit(str(e))


class DownloadWorker(QThread):
  progress = Signal(object)
  finished = Signal(list)
  error = Signal(str)

  def __init__(self, engine: DownloadEngine, datasets: list[DatasetResult]) -> None:
    super().__init__()
    self._engine = engine
    self._datasets = datasets

  def run(self) -> None:
    try:
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)
      results = loop.run_until_complete(
        self._engine.download_datasets(
          self._datasets,
          progress_callback=lambda task: self.progress.emit(task),
        )
      )
      loop.close()
      self.finished.emit(results)
    except Exception as e:
      self.error.emit(str(e))


class RetryDownloadWorker(QThread):
  progress = Signal(object)
  finished = Signal(list)
  error = Signal(str)

  def __init__(self, engine: DownloadEngine) -> None:
    super().__init__()
    self._engine = engine

  def run(self) -> None:
    try:
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)
      results = loop.run_until_complete(
        self._engine.retry_failed(
          progress_callback=lambda task: self.progress.emit(task),
        )
      )
      loop.close()
      self.finished.emit(results)
    except Exception as e:
      self.error.emit(str(e))


class AnalysisWorker(QThread):
  finished = Signal(object)
  error = Signal(str)

  def __init__(self, analyzer, path: str, name: str) -> None:
    super().__init__()
    self._analyzer = analyzer
    self._path = path
    self._name = name

  def run(self) -> None:
    try:
      profile = self._analyzer.analyze(self._path, self._name)
      self.finished.emit(profile)
    except Exception as e:
      self.error.emit(str(e))
