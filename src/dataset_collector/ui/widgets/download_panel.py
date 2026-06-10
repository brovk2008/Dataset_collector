"""Download progress and control panel."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from dataset_collector.core.enums import DownloadStatus
from dataset_collector.core.models import DownloadTask


class DownloadPanel(QWidget):
  """Download controls with pause/resume/cancel and progress display."""

  pause_clicked = Signal()
  resume_clicked = Signal()
  cancel_clicked = Signal()
  retry_clicked = Signal()
  download_clicked = Signal()
  manifest_clicked = Signal()

  def __init__(self, parent: QWidget | None = None) -> None:
    super().__init__(parent)
    self._build_ui()

  def _build_ui(self) -> None:
    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)

    # Controls
    btn_layout = QHBoxLayout()
    self._manifest_btn = QPushButton("Generate Manifest")
    self._manifest_btn.clicked.connect(self.manifest_clicked.emit)
    btn_layout.addWidget(self._manifest_btn)

    self._download_btn = QPushButton("Download Selected")
    self._download_btn.setObjectName("primaryButton")
    self._download_btn.clicked.connect(self.download_clicked.emit)
    self._download_btn.setEnabled(False)
    btn_layout.addWidget(self._download_btn)

    self._pause_btn = QPushButton("Pause")
    self._pause_btn.clicked.connect(self.pause_clicked.emit)
    self._pause_btn.setEnabled(False)
    btn_layout.addWidget(self._pause_btn)

    self._resume_btn = QPushButton("Resume")
    self._resume_btn.clicked.connect(self.resume_clicked.emit)
    self._resume_btn.setEnabled(False)
    btn_layout.addWidget(self._resume_btn)

    self._cancel_btn = QPushButton("Cancel")
    self._cancel_btn.setObjectName("dangerButton")
    self._cancel_btn.clicked.connect(self.cancel_clicked.emit)
    self._cancel_btn.setEnabled(False)
    btn_layout.addWidget(self._cancel_btn)

    self._retry_btn = QPushButton("Retry Failed")
    self._retry_btn.clicked.connect(self.retry_clicked.emit)
    self._retry_btn.setEnabled(False)
    btn_layout.addWidget(self._retry_btn)

    btn_layout.addStretch()
    layout.addLayout(btn_layout)

    # Progress
    progress_group = QGroupBox("Download Progress")
    progress_layout = QVBoxLayout(progress_group)

    self._current_label = QLabel("Current: —")
    progress_layout.addWidget(self._current_label)

    self._progress_bar = QProgressBar()
    self._progress_bar.setRange(0, 100)
    self._progress_bar.setValue(0)
    progress_layout.addWidget(self._progress_bar)

    stats_layout = QHBoxLayout()
    self._speed_label = QLabel("Speed: —")
    self._speed_label.setObjectName("secondaryLabel")
    self._speed_label.setMinimumWidth(100)

    self._remaining_label = QLabel("ETA: —")
    self._remaining_label.setObjectName("secondaryLabel")
    self._remaining_label.setMinimumWidth(100)

    self._remaining_size_label = QLabel("Left: —")
    self._remaining_size_label.setObjectName("secondaryLabel")
    self._remaining_size_label.setMinimumWidth(100)

    self._queue_label = QLabel("Queue: 0 | OK: 0 | Failed: 0")
    self._queue_label.setObjectName("secondaryLabel")
    self._queue_label.setMinimumWidth(150)

    stats_layout.addWidget(self._speed_label)
    stats_layout.addWidget(self._remaining_label)
    stats_layout.addWidget(self._remaining_size_label)
    stats_layout.addStretch()
    stats_layout.addWidget(self._queue_label)
    progress_layout.addLayout(stats_layout)

    self._log_output = QTextEdit()
    self._log_output.setReadOnly(True)
    self._log_output.setMaximumHeight(120)
    progress_layout.addWidget(self._log_output)

    layout.addWidget(progress_group)

  def set_download_enabled(self, enabled: bool) -> None:
    self._download_btn.setEnabled(enabled)

  def set_downloading(self, downloading: bool) -> None:
    self._pause_btn.setEnabled(downloading)
    self._cancel_btn.setEnabled(downloading)
    self._download_btn.setEnabled(not downloading)
    self._manifest_btn.setEnabled(not downloading)

  def set_paused(self, paused: bool) -> None:
    self._resume_btn.setEnabled(paused)
    self._pause_btn.setEnabled(not paused)

  def set_has_failures(self, has_failures: bool) -> None:
    self._retry_btn.setEnabled(has_failures)

  def update_task(self, task: DownloadTask) -> None:
    ds = task.dataset
    self._current_label.setText(f"Current: {ds.name} ({ds.source.value})")
    self._progress_bar.setValue(int(task.progress_percent))

    speed = _format_speed(task.speed_bps) if task.speed_bps > 0 else "—"
    self._speed_label.setText(f"Speed: {speed}")

    if task.total_bytes and task.speed_bps > 0:
      remaining = (task.total_bytes - task.downloaded_bytes) / task.speed_bps
      self._remaining_label.setText(f"ETA: {_format_time(remaining)}")
    else:
      self._remaining_label.setText("Remaining: —")

    if task.total_bytes:
      left = max(task.total_bytes - task.downloaded_bytes, 0)
      self._remaining_size_label.setText(f"Left: {_format_bytes(left)}")
    else:
      self._remaining_size_label.setText("Left: —")

    status_msg = f"[{task.status.value}] {ds.name}: {task.progress_percent:.1f}%"
    if task.error_message:
      status_msg += f" — {task.error_message}"
    self._append_log(status_msg)

  def _append_log(self, message: str) -> None:
    self._log_output.append(message)
    scrollbar = self._log_output.verticalScrollBar()
    scrollbar.setValue(scrollbar.maximum())

  def update_queue_stats(self, total: int, completed: int, failed: int) -> None:
    self._queue_label.setText(f"Queue: {total} | OK: {completed} | Failed: {failed}")

  def clear_log(self) -> None:
    self._log_output.clear()
    self._progress_bar.setValue(0)
    self._current_label.setText("Current: —")
    self._queue_label.setText("Queue: 0 | OK: 0 | Failed: 0")


def _format_bytes(size: int) -> str:
  for unit in ("B", "KB", "MB", "GB", "TB"):
    if size < 1024:
      return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
    size /= 1024
  return f"{size:.1f} PB"


def _format_speed(bps: float) -> str:
  for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
    if bps < 1024:
      return f"{bps:.1f} {unit}"
    bps /= 1024
  return f"{bps:.1f} TB/s"


def _format_time(seconds: float) -> str:
  if seconds < 60:
    return f"{seconds:.0f}s"
  if seconds < 3600:
    return f"{seconds / 60:.0f}m"
  return f"{seconds / 3600:.1f}h"
