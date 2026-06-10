"""Background workers for async operations."""

from __future__ import annotations

import asyncio

from PySide6.QtCore import QThread, Signal

from dataset_collector.core.models import DatasetResult, SearchRequest
from dataset_collector.download.download_engine import DownloadEngine


class SearchWorker(QThread):
  progress = Signal(str, float)
  result_received = Signal(object)  # result
  source_progress = Signal(str, int)  # source_name, count_from_source
  finished = Signal(list)
  error = Signal(str)

  def __init__(self, search_engine, request: SearchRequest) -> None:
    super().__init__()
    self._engine = search_engine
    self._request = request
    self._all_results: list[DatasetResult] = []
    self._source_counts: dict[str, int] = {}  # Track results per source
    self._cancelled = False

  def cancel(self) -> None:
    """Request cancellation of the search."""
    self._cancelled = True
    self._engine.cancel()

  def run(self) -> None:
    try:
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)

      # Use multi-stage search if aggressive mode enabled
      if self._request.aggressive_mode:
        results = loop.run_until_complete(
          self._engine.search_multi_stage(
            self._request,
            all_datasets=None,
            progress_callback=lambda msg, pct: self.progress.emit(msg, pct),
            result_callback=self._on_result_received,
          )
        )
      else:
        # Standard single-pass search
        results = loop.run_until_complete(
          self._engine.search(
            self._request,
            progress_callback=lambda msg, pct: self.progress.emit(msg, pct),
            result_callback=self._on_result_received,
          )
        )
      loop.close()

      if not self._cancelled:
        self.finished.emit(results)
    except Exception as e:
      if not self._cancelled:
        self.error.emit(str(e))

  def _on_result_received(self, result: DatasetResult) -> None:
    """Called when a single result arrives from any source."""
    if self._cancelled:
      return
    self._all_results.append(result)

    # Track results per source
    source_name = result.source.value
    if source_name not in self._source_counts:
      self._source_counts[source_name] = 0
    self._source_counts[source_name] += 1

    # Emit both the result and source progress
    self.result_received.emit(result)
    self.source_progress.emit(source_name, self._source_counts[source_name])


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


class ModelDownloadWorker(QThread):
  progress = Signal(str, float)
  finished = Signal(bool)
  error = Signal(str)

  def __init__(self, model_manager) -> None:
    super().__init__()
    self._model_manager = model_manager

  def run(self) -> None:
    try:
      success = self._model_manager.download_model(
        progress_callback=lambda msg, pct: self.progress.emit(msg, pct)
      )
      self.finished.emit(success)
    except Exception as e:
      self.error.emit(str(e))
